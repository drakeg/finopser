from django.utils import timezone

from .models import CloudResource, InventorySync
from .providers import ProviderDiscoveryError, get_provider


def sync_inventory(account) -> InventorySync:
    started_at = timezone.now()
    sync = InventorySync.objects.create(
        cloud_account=account,
        status=InventorySync.Status.RUNNING,
        started_at=started_at,
    )

    provider = get_provider(account.provider)
    try:
        result = provider.discover_resources(
            account_id=account.provider_account_id,
            role_arn=account.role_arn,
            external_id=account.external_id,
        )
    except ProviderDiscoveryError as exc:
        sync.status = InventorySync.Status.FAILED
        sync.completed_at = timezone.now()
        sync.errors = [str(exc)[:255]]
        sync.save(update_fields=["status", "completed_at", "errors"])
        return sync

    seen_at = timezone.now()
    seen_ids: list[str] = []
    created_count = 0
    updated_count = 0

    for record in result.resources:
        seen_ids.append(record.provider_resource_id)
        _, created = CloudResource.objects.update_or_create(
            provider=account.provider,
            cloud_account=account,
            provider_resource_id=record.provider_resource_id,
            defaults={
                "resource_type": record.resource_type,
                "name": record.name,
                "region": record.region,
                "state": record.state,
                "is_active": True,
                "last_seen": seen_at,
                "metadata": record.metadata,
                "tags": record.tags,
            },
        )
        if created:
            created_count += 1
        else:
            updated_count += 1

    stale_count = 0
    if not result.errors:
        stale_queryset = CloudResource.objects.filter(
            cloud_account=account,
            is_active=True,
        )
        if seen_ids:
            stale_queryset = stale_queryset.exclude(provider_resource_id__in=seen_ids)
        stale_count = stale_queryset.update(is_active=False)

    sync.status = (
        InventorySync.Status.PARTIAL if result.errors else InventorySync.Status.SUCCESS
    )
    sync.completed_at = timezone.now()
    sync.discovered_count = len(result.resources)
    sync.created_count = created_count
    sync.updated_count = updated_count
    sync.stale_count = stale_count
    sync.errors = [error[:255] for error in result.errors]
    sync.save(
        update_fields=[
            "status",
            "completed_at",
            "discovered_count",
            "created_count",
            "updated_count",
            "stale_count",
            "errors",
        ]
    )
    return sync
