from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import (
    account_api,
    audit_integrity_api,
    billing_api,
    budget_api,
    compliance_api,
    identity_api,
    notification_api,
    policy_api,
    recommendation_api,
    remediation_api,
    report_api,
    views,
)
from .api import (
    AuditEventViewSet,
    CloudAccountViewSet,
    CloudResourceViewSet,
    InventorySyncViewSet,
    OrganizationNodeViewSet,
    OrganizationViewSet,
    ProjectViewSet,
    UserRoleViewSet,
)
from .cost_api import CostRecordViewSet, CostSyncViewSet, sync_account_costs
from .dashboard_api import operational_dashboard

router = DefaultRouter()
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("organization-nodes", OrganizationNodeViewSet, basename="organization-node")
router.register("projects", ProjectViewSet, basename="project")
router.register("cloud-accounts", CloudAccountViewSet, basename="cloud-account")
router.register("resources", CloudResourceViewSet, basename="resource")
router.register("inventory-syncs", InventorySyncViewSet, basename="inventory-sync")
router.register("costs", CostRecordViewSet, basename="cost")
router.register("cost-syncs", CostSyncViewSet, basename="cost-sync")
router.register("compliance/frameworks", compliance_api.FrameworkViewSet, basename="compliance-framework")
router.register("compliance/controls", compliance_api.ControlViewSet, basename="compliance-control")
router.register("compliance/findings", compliance_api.FindingViewSet, basename="compliance-finding")
router.register("compliance/exceptions", compliance_api.ExceptionViewSet, basename="compliance-exception")
router.register("compliance/runs", compliance_api.RunViewSet, basename="compliance-run")
router.register("policies", policy_api.PolicyViewSet, basename="policy")
router.register("policy-violations", policy_api.ViolationViewSet, basename="policy-violation")
router.register("policy-runs", policy_api.PolicyRunViewSet, basename="policy-run")
router.register("budgets", budget_api.BudgetViewSet, basename="budget")
router.register("budget-alerts", budget_api.BudgetAlertViewSet, basename="budget-alert")
router.register("recommendations", recommendation_api.RecommendationViewSet, basename="recommendation")
router.register("recommendation-runs", recommendation_api.RecommendationRunViewSet, basename="recommendation-run")
router.register("remediations", remediation_api.RemediationActionViewSet, basename="remediation")
router.register("audit-events", AuditEventViewSet, basename="audit-event")
router.register("users", UserRoleViewSet, basename="user-role")

urlpatterns = [
    path("", views.root, name="api-root"),
    path("health/", views.health, name="health"),
    path("ready/", views.ready, name="ready"),
    path("auth/session/", views.session, name="session"),
    path("auth/login/", views.login, name="login"),
    path("auth/register/", views.register, name="register"),
    path("auth/logout/", views.logout, name="logout"),
    path("auth/me/", views.me, name="me"),
    path("auth/sso/discover/", identity_api.discover, name="enterprise-identity-discover"),
    path("enterprise-identity/", identity_api.configuration, name="enterprise-identity-configuration"),
    path("plans/", account_api.plan_catalog, name="plan-catalog"),
    path("billing/status/", billing_api.billing_status, name="billing-status"),
    path("billing/checkout/", billing_api.checkout, name="billing-checkout"),
    path("billing/portal/", billing_api.portal, name="billing-portal"),
    path("billing/webhooks/stripe/", billing_api.stripe_webhook, name="billing-stripe-webhook"),
    path("notifications/", notification_api.notification_list, name="notification-list"),
    path("notifications/unread-count/", notification_api.unread_count, name="notification-unread-count"),
    path("notifications/mark-all-read/", notification_api.mark_all_read, name="notification-mark-all-read"),
    path("notifications/<int:pk>/read/", notification_api.mark_read, name="notification-mark-read"),
    path("notifications/<int:pk>/unread/", notification_api.mark_unread, name="notification-mark-unread"),
    path("audit-integrity/", audit_integrity_api.integrity, name="audit-integrity"),
    path("reports/", report_api.catalog, name="report-catalog"),
    path("reports/resource-inventory.csv", report_api.resource_inventory_csv, name="report-resource-inventory-csv"),
    path("reports/cost-detail.csv", report_api.cost_detail_csv, name="report-cost-detail-csv"),
    path("reports/compliance-findings.csv", report_api.compliance_findings_csv, name="report-compliance-findings-csv"),
    path("reports/policy-violations.csv", report_api.policy_violations_csv, name="report-policy-violations-csv"),
    path("reports/recommendations.csv", report_api.recommendations_csv, name="report-recommendations-csv"),
    path("reports/remediation-history.csv", report_api.remediation_history_csv, name="report-remediation-history-csv"),
    path("reports/audit-events.csv", report_api.audit_events_csv, name="report-audit-events-csv"),
    path("account/bootstrap/", account_api.bootstrap, name="account-bootstrap"),
    path(
        "onboarding/organization/",
        account_api.create_organization,
        name="onboarding-create-organization",
    ),
    path(
        "onboarding/cloud-account/",
        account_api.connect_cloud_account,
        name="onboarding-connect-cloud-account",
    ),
    path(
        "onboarding/cloud-account/<int:pk>/validate/",
        account_api.validate_cloud_account,
        name="onboarding-validate-cloud-account",
    ),
    path(
        "onboarding/cloud-account/<int:pk>/sync/",
        account_api.initial_sync,
        name="onboarding-initial-sync",
    ),
    path("dashboard/", operational_dashboard, name="operational-dashboard"),
    path("compliance/evaluate/", compliance_api.evaluate, name="compliance-evaluate"),
    path("compliance/summary/", compliance_api.summary, name="compliance-summary"),
    path("policies/evaluate/", policy_api.evaluate, name="policy-evaluate"),
    path("policies/summary/", policy_api.summary, name="policy-summary"),
    path("budgets/evaluate/", budget_api.evaluate, name="budget-evaluate"),
    path("budgets/summary/", budget_api.summary, name="budget-summary"),
    path("recommendations/generate/", recommendation_api.generate, name="recommendation-generate"),
    path("recommendations/summary/", recommendation_api.summary, name="recommendation-summary"),
    path("remediations/catalog/", remediation_api.action_catalog, name="remediation-catalog"),
    path("remediations/summary/", remediation_api.summary, name="remediation-summary"),
    path("cloud-accounts/<int:pk>/sync-costs/", sync_account_costs, name="sync-account-costs"),
    path("", include(router.urls)),
]
