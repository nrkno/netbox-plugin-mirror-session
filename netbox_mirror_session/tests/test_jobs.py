from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from extras.models import JournalEntry

from ..choices import MirrorSessionStatusChoices
from ..jobs import expire_sessions
from ..models import MirrorSession
from .data import build_session, create_device


class ExpireSessionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leaf = create_device("leaf-01")

    def save_session(self, name, status, expires):
        session = build_session(self.leaf, name=name, status=status, expires=expires)
        session.save()
        return session

    def test_expired_active_session_becomes_planned(self):
        now = timezone.now()
        session = self.save_session("old", MirrorSessionStatusChoices.ACTIVE, now - timedelta(minutes=1))

        changed = expire_sessions(now)

        self.assertEqual(changed, [session])
        session.refresh_from_db()
        self.assertEqual(session.status, MirrorSessionStatusChoices.PLANNED)

    def test_expired_session_gets_journal_entry(self):
        now = timezone.now()
        session = self.save_session("old", MirrorSessionStatusChoices.ACTIVE, now - timedelta(minutes=1))

        expire_sessions(now)

        entry = JournalEntry.objects.get(assigned_object_id=session.pk)
        self.assertIn("removed from leaf-01 on the next config push", entry.comments)

    def test_future_active_session_is_untouched(self):
        now = timezone.now()
        self.save_session("current", MirrorSessionStatusChoices.ACTIVE, now + timedelta(days=1))

        self.assertEqual(expire_sessions(now), [])
        self.assertEqual(MirrorSession.objects.get(name="current").status, MirrorSessionStatusChoices.ACTIVE)

    def test_expired_planned_session_is_untouched(self):
        now = timezone.now()
        self.save_session("parked", MirrorSessionStatusChoices.PLANNED, now - timedelta(days=1))

        self.assertEqual(expire_sessions(now), [])
        self.assertFalse(JournalEntry.objects.exists())
