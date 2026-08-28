from django.http import JsonResponse

from .entitlements import has_feature


FEATURE_PATHS = (
    ("/api/budgets/", "budgets"),
    ("/api/budget-alerts/", "budgets"),
    ("/api/compliance/", "compliance"),
    ("/api/policies/", "policies"),
    ("/api/policy-violations/", "policies"),
    ("/api/policy-runs/", "policies"),
    ("/api/recommendations/", "recommendations"),
    ("/api/recommendation-runs/", "recommendations"),
    ("/api/remediations/", "remediation_simulation"),
)


class SubscriptionEntitlementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and not user.is_superuser:
            path = request.path
            required_feature = None
            if path.startswith("/api/remediations/") and path.endswith("/execute/"):
                required_feature = "remediation_live"
            else:
                for prefix, feature in FEATURE_PATHS:
                    if path.startswith(prefix):
                        required_feature = feature
                        break
            if required_feature and not has_feature(user, required_feature):
                return JsonResponse(
                    {
                        "detail": "Your current subscription does not include this feature.",
                        "upgrade_required": True,
                        "required_feature": required_feature,
                    },
                    status=402,
                )
        return self.get_response(request)
