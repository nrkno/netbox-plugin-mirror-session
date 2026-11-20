from datetime import timedelta

from dcim.choices import InterfaceTypeChoices
from django.test import TestCase
from django.utils import timezone
from ipam.models import VRF

from ..choices import DestinationKindChoices
from ..forms import MirrorSessionForm, MirrorSourceForm
from ..models import MirrorSource
from .data import build_session, create_device, create_interface, create_ip


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


class MirrorSessionFormDeviceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leaf = create_device("leaf-01")
        cls.other_leaf = create_device("leaf-02")
        cls.media_vrf = VRF.objects.create(name="media")
        cls.other_vrf = VRF.objects.create(name="office")
        cls.loopback = create_interface(cls.leaf, "Loopback0", InterfaceTypeChoices.TYPE_VIRTUAL)
        cls.loopback_address = create_ip("10.0.0.1/32", cls.loopback)
        cls.media_svi = create_interface(cls.leaf, "Vlan100", InterfaceTypeChoices.TYPE_VIRTUAL)
        cls.media_svi.vrf = cls.media_vrf
        cls.media_svi.save()
        cls.other_loopback = create_interface(cls.other_leaf, "Loopback0", InterfaceTypeChoices.TYPE_VIRTUAL)
        cls.other_address = create_ip("10.0.0.2/32", cls.other_loopback)
        cls.other_loopback.vrf = cls.other_vrf
        cls.other_loopback.save()

    def test_without_device_dependent_fields_are_disabled(self):
        form = MirrorSessionForm()

        self.assertTrue(form.fields["destination_interface"].disabled)
        self.assertTrue(form.fields["vrf"].disabled)
        self.assertTrue(form.fields["gre_source"].disabled)

    def test_vrf_choices_are_the_vrfs_on_the_device(self):
        form = MirrorSessionForm(initial={"device": self.leaf.pk})

        self.assertEqual(list(form.fields["vrf"].queryset), [self.media_vrf])

    def test_editing_keeps_a_stored_vrf_that_is_not_on_the_device(self):
        session = build_session(
            self.leaf,
            destination_kind=DestinationKindChoices.GRE,
            gre_source=self.loopback_address,
            gre_destination=self.other_address,
            vrf=self.other_vrf,
        )
        session.save()

        form = MirrorSessionForm(instance=session)

        self.assertEqual(list(form.fields["vrf"].queryset), [self.media_vrf, self.other_vrf])

    def test_malformed_device_id_leaves_fields_disabled(self):
        form = MirrorSessionForm(initial={"device": "abc"})

        self.assertTrue(form.fields["vrf"].disabled)

    def test_gre_source_choices_are_addresses_on_the_device(self):
        form = MirrorSessionForm(initial={"device": self.leaf.pk})

        self.assertEqual(list(form.fields["gre_source"].queryset), [self.loopback_address])

    def test_gre_source_label_shows_the_interface(self):
        form = MirrorSessionForm(initial={"device": self.leaf.pk})

        label = form.fields["gre_source"].label_from_instance(self.loopback_address)

        self.assertEqual(label, "10.0.0.1/32 (Loopback0)")

    def test_destination_interfaces_are_filtered_by_device(self):
        form = MirrorSessionForm(initial={"device": self.leaf.pk})

        self.assertEqual(form.fields["destination_interface"].widget.static_params, {"device_id": [self.leaf.pk]})

    def test_gre_destination_without_vrf_uses_the_global_table(self):
        form = MirrorSessionForm(initial={"device": self.leaf.pk})

        self.assertEqual(form.fields["gre_destination"].widget.static_params, {"vrf_id": ["null"]})

    def test_gre_destination_follows_the_chosen_vrf(self):
        form = MirrorSessionForm(initial={"device": self.leaf.pk, "vrf": self.media_vrf.pk})

        self.assertEqual(form.fields["gre_destination"].widget.static_params, {"vrf_id": [self.media_vrf.pk]})


class MirrorSourceFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leaf = create_device("leaf-01")
        cls.mixer_port = create_interface(cls.leaf, "Ethernet5", InterfaceTypeChoices.TYPE_1GE_FIXED)
        cls.session = build_session(cls.leaf)
        cls.session.save()

    def interface_filter(self, form):
        return form.fields["interface"].widget.static_params

    def test_without_session_interface_is_disabled(self):
        form = MirrorSourceForm()

        self.assertTrue(form.fields["interface"].disabled)

    def test_session_from_url_filters_interfaces_by_its_device(self):
        form = MirrorSourceForm(initial={"session": self.session.pk})

        self.assertFalse(form.fields["interface"].disabled)
        self.assertEqual(self.interface_filter(form), {"device_id": [self.leaf.pk]})

    def test_submitted_session_filters_interfaces_by_its_device(self):
        form = MirrorSourceForm(data={"session": str(self.session.pk)})

        self.assertEqual(self.interface_filter(form), {"device_id": [self.leaf.pk]})

    def test_edit_filters_interfaces_by_the_session_device(self):
        source = MirrorSource.objects.create(session=self.session, interface=self.mixer_port)

        form = MirrorSourceForm(instance=source)

        self.assertEqual(self.interface_filter(form), {"device_id": [self.leaf.pk]})

    def test_valid_with_session_and_interface(self):
        form = MirrorSourceForm(data={"session": self.session.pk, "interface": self.mixer_port.pk, "direction": "both"})

        self.assertTrue(form.is_valid(), form.errors)

    def test_destination_interface_is_excluded_from_sources(self):
        capture_port = create_interface(self.leaf, "Ethernet48", InterfaceTypeChoices.TYPE_1GE_FIXED)
        self.session.destination_kind = DestinationKindChoices.INTERFACE
        self.session.destination_interface = capture_port
        self.session.save()

        form = MirrorSourceForm(initial={"session": self.session.pk})

        self.assertEqual(
            self.interface_filter(form),
            {"device_id": [self.leaf.pk], "id__n": [capture_port.pk]},
        )
