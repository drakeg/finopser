import re

from django.contrib.auth.models import Group, User
from rest_framework import serializers

from .models import (
    AuditEvent,
    CloudAccount,
    CloudResource,
    InventorySync,
    Organization,
    OrganizationNode,
    Project,
)
from .rbac import MANAGED_ROLES


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "description", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class OrganizationNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationNode
        fields = ["id", "organization", "parent", "name", "node_type", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        organization = attrs.get("organization") or getattr(self.instance, "organization", None)
        parent = attrs.get("parent") if "parent" in attrs else getattr(self.instance, "parent", None)
        if parent and organization and parent.organization_id != organization.id:
            raise serializers.ValidationError({"parent": "Parent must belong to the same organization."})
        if self.instance and parent:
            ancestor = parent
            while ancestor:
                if ancestor.pk == self.instance.pk:
                    raise serializers.ValidationError({"parent": "A node cannot be its own ancestor."})
                ancestor = ancestor.parent
        return attrs


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "organization", "node", "name", "description", "owner", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        organization = attrs.get("organization") or getattr(self.instance, "organization", None)
        node = attrs.get("node") or getattr(self.instance, "node", None)
        if node and organization and node.organization_id != organization.id:
            raise serializers.ValidationError({"node": "Project node must belong to the same organization."})
        return attrs


class CloudAccountSerializer(serializers.ModelSerializer):
    external_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    FORBIDDEN_CREDENTIAL_FIELDS = {
        "access_key",
        "secret_key",
        "session_token",
        "aws_access_key_id",
        "aws_secret_access_key",
        "aws_session_token",
    }

    class Meta:
        model = CloudAccount
        fields = [
            "id",
            "provider",
            "organization",
            "project",
            "name",
            "provider_account_id",
            "role_arn",
            "external_id",
            "status",
            "last_validated_at",
            "last_error",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["status", "last_validated_at", "last_error", "metadata", "created_at", "updated_at"]

    def to_internal_value(self, data):
        forbidden = sorted(self.FORBIDDEN_CREDENTIAL_FIELDS.intersection(data.keys()))
        if forbidden:
            raise serializers.ValidationError(
                {"credentials": "Long-lived AWS credentials are not accepted by finopser."}
            )
        return super().to_internal_value(data)

    def validate_provider_account_id(self, value):
        if not re.fullmatch(r"\d{12}", value):
            raise serializers.ValidationError("AWS account ID must contain exactly 12 digits.")
        return value

    def validate_role_arn(self, value):
        if not re.fullmatch(r"arn:(aws|aws-us-gov|aws-cn):iam::\d{12}:role/.+", value):
            raise serializers.ValidationError("Enter a valid AWS IAM role ARN.")
        return value

    def validate(self, attrs):
        provider = attrs.get("provider") or getattr(self.instance, "provider", CloudAccount.Provider.AWS)
        if provider != CloudAccount.Provider.AWS:
            raise serializers.ValidationError({"provider": "AWS is the only supported provider in Sprint 4."})
        organization = attrs.get("organization") or getattr(self.instance, "organization", None)
        project = attrs.get("project") if "project" in attrs else getattr(self.instance, "project", None)
        if project and organization and project.organization_id != organization.id:
            raise serializers.ValidationError({"project": "Project must belong to the same organization."})
        return attrs


class CloudResourceSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="cloud_account.name", read_only=True)

    class Meta:
        model = CloudResource
        fields = [
            "id",
            "provider",
            "cloud_account",
            "account_name",
            "provider_resource_id",
            "resource_type",
            "name",
            "region",
            "state",
            "is_active",
            "first_seen",
            "last_seen",
            "metadata",
            "tags",
        ]
        read_only_fields = fields


class InventorySyncSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="cloud_account.name", read_only=True)

    class Meta:
        model = InventorySync
        fields = [
            "id",
            "cloud_account",
            "account_name",
            "status",
            "started_at",
            "completed_at",
            "discovered_count",
            "created_count",
            "updated_count",
            "stale_count",
            "errors",
        ]
        read_only_fields = fields


class AuditEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = AuditEvent
        fields = ["id", "actor", "actor_username", "action", "object_type", "object_id", "object_repr", "metadata", "created_at"]
        read_only_fields = fields


class UserRoleSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "is_active", "roles"]
        read_only_fields = ["id", "username", "email", "is_active"]

    def get_roles(self, obj):
        return list(obj.groups.filter(name__in=MANAGED_ROLES).values_list("name", flat=True))

    def update(self, instance, validated_data):
        requested = self.context.get("requested_roles")
        if requested is None:
            return instance
        unknown = sorted(set(requested) - set(MANAGED_ROLES))
        if unknown:
            raise serializers.ValidationError({"roles": f"Unknown managed roles: {', '.join(unknown)}"})
        managed_groups = Group.objects.filter(name__in=MANAGED_ROLES)
        instance.groups.remove(*managed_groups)
        if requested:
            instance.groups.add(*Group.objects.filter(name__in=requested))
        return instance
