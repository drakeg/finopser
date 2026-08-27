from django.db import transaction
from django.utils import timezone

from .models import CloudAccount, CostRecord, CostSync
from .providers import get_provider
from .providers.base import ProviderCostError


@transaction.atomic
def sync_costs(account: CloudAccount, *, start_date, end_date) -> CostSync:
    sync = CostSync.objects.create(
        cloud_account=account,
        start_date=start_date,
        end_date=end_date,
        started_at=timezone.now(),
    )
    provider = get_provider(account.provider)
    try:
        result = provider.fetch_costs(
            account_id=account.provider_account_id,
            role_arn=account.role_arn,
            external_id=account.external_id,
            start_date=start_date,
            end_date=end_date,
        )
    except ProviderCostError as exc:
        sync.status = CostSync.Status.FAILED
        sync.errors = [str(exc)[:255]]
        sync.completed_at = timezone.now()
        sync.save(update_fields=["status", "errors", "completed_at"])
        return sync

    synced = 0
    for record in result.records:
        CostRecord.objects.update_or_create(
            cloud_account=account,
            usage_date=record.usage_date,
            service=record.service,
            region=record.region,
            currency=record.currency,
            defaults={
                "provider": account.provider,
                "project": account.project,
                "provider_account_id": record.provider_account_id,
                "amount": record.amount,
                "updated_at": timezone.now(),
            },
        )
        synced += 1

    sync.record_count = synced
    sync.errors = result.errors
    sync.status = CostSync.Status.PARTIAL if result.errors else CostSync.Status.SUCCESS
    sync.completed_at = timezone.now()
    sync.save(update_fields=["record_count", "errors", "status", "completed_at"])
    return sync
