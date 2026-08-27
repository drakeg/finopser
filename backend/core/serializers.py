from django.contrib.auth.models import Group, User
from rest_framework import serializers

from .models import AuditEvent, Organization, OrganizationNode, Project
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
