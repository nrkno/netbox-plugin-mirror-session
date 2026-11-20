from datetime import timedelta

from dcim.choices import InterfaceTypeChoices
from django.test import TestCase
from django.utils import timezone

from ..forms import MirrorSessionForm, MirrorSourceForm
from ..models import MirrorSource
from .data import build_session, create_device, create_interface


class MirrorSessionFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leaf = create_device("leaf-01")

    def test_site_is_required(self):
        form = MirrorSessionForm(
            data={
                "device": self.leaf.pk,
                "name": "capture",
                "status": "active",
                "expires": (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                "destination_kind": "cpu",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("site", form.errors)

    def test_valid_with_site(self):
        form = MirrorSessionForm(
            data={
                "site": self.leaf.site_id,
                "device": self.leaf.pk,
                "name": "capture",
                "status": "active",
                "expires": (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                "destination_kind": "cpu",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)


class MirrorSourceFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leaf = create_device("leaf-01")
        cls.mixer_port = create_interface(cls.leaf, "Ethernet5", InterfaceTypeChoices.TYPE_1GE_FIXED)
        cls.session = build_session(cls.leaf)
        cls.session.save()

    def test_device_is_required(self):
        form = MirrorSourceForm(
            data={
                "site": self.leaf.site_id,
                "session": self.session.pk,
                "interface": self.mixer_port.pk,
                "direction": "both",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("device", form.errors)

    def test_edit_prefills_site_and_device(self):
        source = MirrorSource.objects.create(session=self.session, interface=self.mixer_port)

        form = MirrorSourceForm(instance=source)

        self.assertEqual(form.initial["device"], self.leaf.pk)
        self.assertEqual(form.initial["site"], self.leaf.site_id)
