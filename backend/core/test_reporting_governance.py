from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .account_models import OrganizationMembership, Subscription
from .models import (
    AuditEvent,
    CloudAccount,
    CloudResource,
    ComplianceControl,
    ComplianceFinding,
    ComplianceFramework,
    GovernancePolicy,
    Organization,
    OrganizationNode,
    PolicyViolation,
    Project,
)


class GovernanceReportingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="governance-report-user", password="test-password-long")
        self.organization = Organization.objects.create(name="Governance Reporting Workspace")
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.subscription = Subscription.objects.create(
            organization=self.organization,
            plan=Subscription.Plan.FREE,
            status=Subscription.Status.FREE,
        )
        node = OrganizationNode.objects.create(organization=self.organization, name="Root")
        project = Project.objects.create(organization=self.organization, node=node, name="Default")
        self.account = CloudAccount.objects.create(
            organization=self.organization,
            project=project,
            name="Primary AWS",
            provider_account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
        )
        self.resource = CloudResource.objects.create(
            provider="aws",
            cloud_account=self.account,
            provider_resource_id="arn:aws:s3:::report-bucket",
            resource_type="aws.s3.bucket",
            name="report-bucket",
            region="global",
            state="available",
            is_active=True,
            last_seen=timezone.now(),
        )
        framework = ComplianceFramework.objects.create(code="CIS", name="CIS")
        control = ComplianceControl.objects.create(
            framework=framework,
            code="1.1",
            title="Encryption",
            severity=ComplianceControl.Severity.HIGH,
            resource_type="aws.s3.bucket",
            check_key="s3_encryption",
        )
        now = timezone.now()
        ComplianceFinding.objects.create(
            control=control,
            resource=self.resource,
            cloud_account=self.account,
            severity=ComplianceControl.Severity.HIGH,
            status=ComplianceFinding.Status.OPEN,
            first_seen=now,
            last_seen=now,
        )
        policy = GovernancePolicy.objects.create(
            code="tenant-report-policy",
            name="Tenant report policy",
            severity=GovernancePolicy.Severity.HIGH,
            resource_type="aws.s3.bucket",
            rule_key="require_owner_tag",
            organization=self.organization,
        )
        PolicyViolation.objects.create(
            policy=policy,
            resource=self.resource,
            cloud_account=self.account,
            severity=GovernancePolicy.Severity.HIGH,
            status=PolicyViolation.Status.OPEN,
            first_seen=now,
            last_seen=now,
        )
        AuditEvent.objects.create(
            organization=self.organization,
            actor=self.user,
            action="policy.evaluate",
            object_type="organization",
            object_id=str(self.organization.id),
            object_repr=self.organization.name,
        )

        other = Organization.objects.create(name="Other Governance Reporting Workspace")
        other_node = OrganizationNode.objects.create(organization=other, name="Root")
        other_project = Project.objects.create(organization=other, node=other_node, name="Default")
        other_account = CloudAccount.objects.create(
            organization=other,
            project=other_project,
            name="Other AWS",
            provider_account_id="210987654321",
            role_arn="arn:aws:iam::210987654321:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
        )
        other_resource = CloudResource.objects.create(
            provider="aws",
            cloud_account=other_account,
            provider_resource_id="arn:aws:s3:::secret-other-bucket",
            resource_type="aws.s3.bucket",
            name="secret-other-bucket",
            region="global",
            state="available",
            is_active=True,
            last_seen=now,
        )
        ComplianceFinding.objects.create(
            control=control,
            resource=other_resource,
            cloud_account=other_account,
            severity=ComplianceControl.Severity.HIGH,
            status=ComplianceFinding.Status.OPEN,
            first_seen=now,
            last_seen=now,
        )
        AuditEvent.objects.create(
            organization=other,
            action="secret.other.action",
            object_type="organization",
            object_id=str(other.id),
            object_repr=other.name,
        )

        self.client = APIClient()
        self.client.login(username=self.user.username, password="test-password-long")

    def test_free_catalog_hides_governance_reports_and_endpoint_denies(self):
        catalog = self.client.get("/api/reports/").json()["reports"]
        codes = {report["code"] for report in catalog}
        self.assertNotIn("compliance-findings", codes)
        self.assertNotIn("policy-violations", codes)
        self.assertIn("audit-events", codes)
        self.assertEqual(self.client.get("/api/reports/compliance-findings.csv").status_code, 403)

    def test_pro_catalog_and_compliance_export_preserve_tenant_isolation(self):
        self.subscription.plan = Subscription.Plan.PRO
        self.subscription.status = Subscription.Status.ACTIVE
        self.subscription.save(update_fields=["plan", "status"])

        catalog = self.client.get("/api/reports/").json()["reports"]
        codes = {report["code"] for report in catalog}
        self.assertIn("compliance-findings", codes)
        self.assertIn("policy-violations", codes)

        response = self.client.get("/api/reports/compliance-findings.csv", {"status": "open", "severity": "high"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("report-bucket", content)
        self.assertNotIn("secret-other-bucket", content)

    def test_audit_export_is_tenant_scoped(self):
        response = self.client.get("/api/reports/audit-events.csv")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("policy.evaluate", content)
        self.assertNotIn("secret.other.action", content)
