from datetime import timedelta

from dcim.choices import InterfaceTypeChoices
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from ..choices import DestinationKindChoices, ExpiryWarningChoices, MirrorSessionStatusChoices
from ..constants import MAX_EXPIRY
from ..models import MirrorSource
from .data import build_session, create_device, create_interface, create_ip


class SessionDestinationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leaf = create_device("leaf-01")
        cls.other_leaf = create_device("leaf-02")
        cls.capture_port = create_interface(cls.leaf, "Ethernet48")
        cls.other_port = create_interface(cls.other_leaf, "Ethernet48")
        cls.loopback = create_interface(cls.leaf, "Loopback0", InterfaceTypeChoices.TYPE_VIRTUAL)
        cls.leaf_address = create_ip("10.0.0.1/32", cls.loopback)
        cls.collector_address = create_ip("10.9.9.9/32")

    def test_cpu_destination_is_valid(self):
        build_session(self.leaf).full_clean()

    def test_interface_destination_is_valid(self):
        session = build_session(
            self.leaf,
            destination_kind=DestinationKindChoices.INTERFACE,
            destination_interface=self.capture_port,
        )
        session.full_clean()

    def test_interface_destination_requires_interface(self):
        session = build_session(self.leaf, destination_kind=DestinationKindChoices.INTERFACE)
        with self.assertRaisesMessage(ValidationError, "Required when the destination is Local interface"):
            session.full_clean()

    def test_interface_destination_on_other_device_is_rejected(self):
        session = build_session(
            self.leaf,
            destination_kind=DestinationKindChoices.INTERFACE,
            destination_interface=self.other_port,
        )
        with self.assertRaisesMessage(ValidationError, "is on leaf-02, not on leaf-01"):
            session.full_clean()

    def test_gre_destination_is_valid(self):
        session = build_session(
            self.leaf,
            destination_kind=DestinationKindChoices.GRE,
            gre_source=self.leaf_address,
            gre_destination=self.collector_address,
        )
        session.full_clean()

    def test_gre_destination_requires_destination_address(self):
        session = build_session(
            self.leaf,
            destination_kind=DestinationKindChoices.GRE,
            gre_source=self.leaf_address,
        )
        with self.assertRaises(ValidationError) as caught:
            session.full_clean()
        self.assertIn("gre_destination", caught.exception.error_dict)

    def test_gre_destination_requires_source_address(self):
        session = build_session(
            self.leaf,
            destination_kind=DestinationKindChoices.GRE,
            gre_destination=self.collector_address,
        )
        with self.assertRaises(ValidationError) as caught:
            session.full_clean()
        self.assertIn("gre_source", caught.exception.error_dict)

    def test_all_destination_errors_are_reported_together(self):
        session = build_session(
            self.leaf,
            destination_interface=self.capture_port,
            gre_source=self.leaf_address,
        )
        with self.assertRaises(ValidationError) as caught:
            session.full_clean()
        self.assertIn("destination_interface", caught.exception.error_dict)
        self.assertIn("gre_source", caught.exception.error_dict)

    def test_gre_source_must_be_on_the_device(self):
        session = build_session(
            self.leaf,
            destination_kind=DestinationKindChoices.GRE,
            gre_source=self.collector_address,
            gre_destination=self.collector_address,
        )
        with self.assertRaisesMessage(ValidationError, "must be assigned to an interface on leaf-01"):
            session.full_clean()

    def test_cpu_destination_rejects_interface(self):
        session = build_session(self.leaf, destination_interface=self.capture_port)
        with self.assertRaisesMessage(ValidationError, "Must be empty when the destination is CPU"):
            session.full_clean()

    def test_missing_device_is_a_field_error(self):
        session = build_session(None)
        with self.assertRaises(ValidationError) as caught:
            session.full_clean()
        self.assertIn("device", caught.exception.error_dict)

    def test_session_name_with_space_is_rejected(self):
        session = build_session(self.leaf, name="span debug")
        with self.assertRaisesMessage(ValidationError, "' ' is not allowed"):
            session.full_clean()


class SessionExpiryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leaf = create_device("leaf-01")

    def test_expiry_at_the_limit_is_valid(self):
        build_session(self.leaf, expires=timezone.now() + MAX_EXPIRY).full_clean()

    def test_expiry_one_minute_past_the_limit_is_rejected(self):
        session = build_session(self.leaf, expires=timezone.now() + MAX_EXPIRY + timedelta(minutes=1))
        with self.assertRaisesMessage(ValidationError, "Must be at most 183 days ahead"):
            session.full_clean()

    def test_active_session_in_the_past_is_rejected(self):
        session = build_session(self.leaf, expires=timezone.now() - timedelta(hours=1))
        with self.assertRaisesMessage(ValidationError, "An active session must expire in the future"):
            session.full_clean()

    def test_planned_session_in_the_past_is_valid(self):
        session = build_session(
            self.leaf,
            status=MirrorSessionStatusChoices.PLANNED,
            expires=timezone.now() - timedelta(hours=1),
        )
        session.full_clean()


class ExpiryWarningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leaf = create_device("leaf-01")
        cls.one_gig_port = create_interface(cls.leaf, "Ethernet1", InterfaceTypeChoices.TYPE_1GE_FIXED)
        cls.ten_gig_port = create_interface(cls.leaf, "Ethernet2", InterfaceTypeChoices.TYPE_10GE_SFP_PLUS)
        cls.slow_port_with_fast_type = create_interface(
            cls.leaf, "Ethernet3", InterfaceTypeChoices.TYPE_10GE_SFP_PLUS, speed=1_000_000
        )
        cls.lag = create_interface(cls.leaf, "Port-Channel1", InterfaceTypeChoices.TYPE_LAG)

    def session_with_source(self, days, interface):
        session = build_session(self.leaf, expires=timezone.now() + timedelta(days=days))
        session.save()
        MirrorSource.objects.create(session=session, interface=interface)
        return session

    def test_short_expiry_has_no_warning(self):
        session = self.session_with_source(days=7, interface=self.ten_gig_port)
        self.assertIsNone(session.expiry_warning)

    def test_long_expiry_on_slow_source_warns(self):
        session = self.session_with_source(days=8, interface=self.one_gig_port)
        self.assertEqual(session.expiry_warning, ExpiryWarningChoices.LONG)

    def test_long_expiry_on_ten_gig_source_warns_strongly(self):
        session = self.session_with_source(days=8, interface=self.ten_gig_port)
        self.assertEqual(session.expiry_warning, ExpiryWarningChoices.LONG_HIGH_SPEED)

    def test_speed_field_wins_over_type(self):
        session = self.session_with_source(days=8, interface=self.slow_port_with_fast_type)
        self.assertEqual(session.expiry_warning, ExpiryWarningChoices.LONG)

    def test_unknown_speed_warns_strongly(self):
        session = self.session_with_source(days=8, interface=self.lag)
        self.assertEqual(session.expiry_warning, ExpiryWarningChoices.LONG_HIGH_SPEED)


class MirrorSourceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leaf = create_device("leaf-01")
        cls.other_leaf = create_device("leaf-02")
        cls.mixer_port = create_interface(cls.leaf, "Ethernet5")
        cls.capture_port = create_interface(cls.leaf, "Ethernet48")
        cls.other_port = create_interface(cls.other_leaf, "Ethernet5")
        cls.session = build_session(
            cls.leaf,
            destination_kind=DestinationKindChoices.INTERFACE,
            destination_interface=cls.capture_port,
        )
        cls.session.save()

    def test_source_on_same_device_is_valid(self):
        MirrorSource(session=self.session, interface=self.mixer_port).full_clean()

    def test_source_on_other_device_is_rejected(self):
        source = MirrorSource(session=self.session, interface=self.other_port)
        with self.assertRaisesMessage(ValidationError, "is on leaf-02, not on leaf-01"):
            source.full_clean()

    def test_destination_interface_cannot_be_a_source(self):
        source = MirrorSource(session=self.session, interface=self.capture_port)
        with self.assertRaisesMessage(ValidationError, "is the session's destination"):
            source.full_clean()


class SessionEditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leaf = create_device("leaf-01")
        cls.other_leaf = create_device("leaf-02")
        cls.mixer_port = create_interface(cls.leaf, "Ethernet5")
        cls.session = build_session(cls.leaf)
        cls.session.save()
        MirrorSource.objects.create(session=cls.session, interface=cls.mixer_port)

    def test_moving_session_away_from_its_sources_is_rejected(self):
        self.session.device = self.other_leaf
        with self.assertRaisesMessage(ValidationError, "1 source(s) of this session are on another device"):
            self.session.full_clean()

    def test_source_interface_as_destination_is_rejected(self):
        self.session.destination_kind = DestinationKindChoices.INTERFACE
        self.session.destination_interface = self.mixer_port
        with self.assertRaisesMessage(ValidationError, "Ethernet5 is a source in this session"):
            self.session.full_clean()
