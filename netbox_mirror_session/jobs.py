from core.choices import JobIntervalChoices
from django.db import transaction
from django.utils import timezone
from extras.choices import JournalEntryKindChoices
from extras.models import JournalEntry
from netbox.jobs import JobRunner, system_job

from .choices import MirrorSessionStatusChoices
from .models import MirrorSession


def expire_sessions(now):
    """Set active sessions whose expiry has passed to planned, with a journal entry on each."""
    changed = []
    with transaction.atomic():
        # The row lock makes a concurrent renewal either wait for this job or drop the session from the result.
        expired = (
            MirrorSession.objects.select_for_update(of=("self",))
            .filter(status=MirrorSessionStatusChoices.ACTIVE, expires__lte=now)
            .select_related("device")
        )
        for session in expired:
            session.snapshot()
            session.status = MirrorSessionStatusChoices.PLANNED
            session.save(update_fields=["status", "last_updated"])
            JournalEntry.objects.create(
                assigned_object=session,
                kind=JournalEntryKindChoices.KIND_WARNING,
                comments=(
                    f"Expired {session.expires.isoformat()} and set to planned. "
                    f"It is removed from {session.device} on the next config push."
                ),
            )
            changed.append(session)
    return changed


@system_job(interval=JobIntervalChoices.INTERVAL_HOURLY)
class ExpireMirrorSessionsJob(JobRunner):
    class Meta:
        name = "Expire mirror sessions"

    def run(self, *args, **kwargs):
        changed = expire_sessions(timezone.now())
        if not changed:
            self.logger.info("No active mirror sessions have expired.")
            return
        for session in changed:
            self.logger.warning(f"{session.device} / {session}: expired, set to planned. Needs a config push.")
