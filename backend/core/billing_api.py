from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .billing import BillingDisabled, billing_provider_configured, get_billing_provider
from .entitlements import organization_subscription, user_organization


def _subscription_for_user(user):
    organization = user_organization(user)
    if organization is None:
        return None
    return organization_subscription(organization)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def billing_status(request):
    subscription = _subscription_for_user(request.user)
    if subscription is None:
        return Response({"detail": "Complete organization setup first."}, status=400)
    return Response(
        {
            "configured": billing_provider_configured(),
            "provider": subscription.billing_provider or None,
            "plan": subscription.plan,
            "status": subscription.status,
            "current_period_end": subscription.current_period_end,
            "can_manage": bool(subscription.provider_customer_id and billing_provider_configured()),
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
    return Response({"url": session.url})
