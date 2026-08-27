from django.contrib import admin

from .models import (
    AuditEvent,
    CloudAccount,
    CloudResource,
    InventorySync,
    Organization,
    OrganizationNode,
    Project,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    search_fields = ("name",)


@admin.register(OrganizationNode)
class OrganizationNodeAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "parent", "node_type")
    list_filter = ("organization", "node_type")
    search_fields = ("name",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "node", "owner")
    list_filter = ("organization",)
    search_fields = ("name", "owner")


@admin.register(CloudAccount)
class CloudAccountAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "provider_account_id", "organization", "status")
    list_filter = ("provider", "status", "organization")
    search_fields = ("name", "provider_account_id", "role_arn")
    readonly_fields = ("status", "last_validated_at", "last_error", "metadata")


@admin.register(CloudResource)
class CloudResourceAdmin(admin.ModelAdmin):
    list_display = ("name", "resource_type", "cloud_account", "region", "state", "is_active")
    list_filter = ("resource_type", "region", "state", "is_active")
    search_fields = ("name", "provider_resource_id")
    readonly_fields = (
        "provider",
        "cloud_account",
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
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InventorySync)
class InventorySyncAdmin(admin.ModelAdmin):
    list_display = ("started_at", "cloud_account", "status", "discovered_count", "stale_count")
    list_filter = ("status",)
    readonly_fields = (
        "cloud_account",
        "status",
        "started_at",
        "completed_at",
        "discovered_count",
        "created_count",
        "updated_count",
        "stale_count",
        "errors",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "object_type", "object_repr")
    list_filter = ("action", "object_type")
    search_fields = ("actor__username", "object_repr")
    readonly_fields = ("actor", "action", "object_type", "object_id", "object_repr", "metadata", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
