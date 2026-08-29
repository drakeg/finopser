from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .audit import record_audit
from .billing import (
    BillingDisabled,
    BillingError,
    BillingSignatureError,
    StripeBillingProvider,
    apply_stripe_event,
    billing_provider_configured,
    get_billing_provider,
)
from .entitlements import entitlement_payload, organization_subscription, user_organization


def _subscription_for_user(user):
    organization = user_organization(user)
    if organization is None:
        return None
    return organization_subscription(organization)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def billing_status(request):
    organization = user_organization(request.user)
    if organization is None:
        return Response({"detail": "Complete organization setup first."}, status=400)
    subscription = organization_subscription(organization)
    entitlements = entitlement_payload(organization)
    return Response(
        {
            "configured": billing_provider_configured(),
            "provider": subscription.billing_provider or None,
            "plan": subscription.plan,
            "effective_plan": entitlements["effective_plan"],
            "status": subscription.status,
            "current_period_end": subscription.current_period_end,
            "can_manage": bool(subscription.provider_customer_id and billing_provider_configured()),
            "max_cloud_accounts": entitlements["max_cloud_accounts"],
            "usage": entitlements["usage"],
            "over_limit": entitlements["over_limit"],
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def checkout(request):
    subscription = _subscription_for_user(request.user)
    if subscription is None:
        return Response({"detail": "Complete organization setup first."}, status=400)
    plan = str(request.data.get("plan", "")).strip().lower()
    if plan not in {subscription.Plan.PRO, subscription.Plan.BUSINESS}:
        return Response({"detail": "Choose Pro or Business for checkout."}, status=400)
    try:
        session = get_billing_provider().create_checkout(
            subscription,
            plan,
            str(request.data.get("return_url", "")).strip(),
        )
    except BillingDisabled as exc:
        return Response(
            {"detail": str(exc), "billing_provider_configured": False},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except BillingError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"url": session.url})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def portal(request):
    subscription = _subscription_for_user(request.user)
    if subscription is None:
        return Response({"detail": "Complete organization setup first."}, status=400)
    try:
        session = get_billing_provider().create_portal(
            subscription,
            str(request.data.get("return_url", "")).strip(),
        )
    except BillingDisabled as exc:
        return Response(
            {"detail": str(exc), "billing_provider_configured": False},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except BillingError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"url": session.url})


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def stripe_webhook(request):
    try:
        provider = get_billing_provider()
        if not isinstance(provider, StripeBillingProvider):
            raise BillingDisabled("Stripe billing is not configured for this deployment.")
        event = provider.verify_event(
            request.body,
            request.headers.get("Stripe-Signature", ""),
        )
        billing_event, processed = apply_stripe_event(event)
    except BillingSignatureError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except BillingDisabled as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except BillingError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    if processed and billing_event.organization_id and billing_event.event_type.startswith(
        "customer.subscription."
    ):
        subscription = organization_subscription(billing_event.organization)
        record_audit(
            None,
            f"billing.{billing_event.event_type}",
            subscription,
            {
                "provider": "stripe",
                "provider_event_id": billing_event.event_id,
                "plan": subscription.plan,
                "status": subscription.status,
            },
        )

    return Response(
        {
            "received": True,
            "processed": processed,
            "event_id": billing_event.event_id,
        }
    )
