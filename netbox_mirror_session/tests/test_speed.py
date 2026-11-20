from dcim.choices import InterfaceTypeChoices
from django.test import SimpleTestCase

from ..speed import speed_kbps_from_type


class SpeedFromTypeTests(SimpleTestCase):
    def test_megabit_type(self):
        self.assertEqual(speed_kbps_from_type("1000base-t"), 1_000_000)

    def test_gigabit_type(self):
        self.assertEqual(speed_kbps_from_type("10gbase-x-sfpp"), 10_000_000)

    def test_fractional_gigabit_type(self):
        self.assertEqual(speed_kbps_from_type("2.5gbase-t"), 2_500_000)

    def test_terabit_type(self):
        self.assertEqual(speed_kbps_from_type("1.6tbase-x-osfp1600"), 1_600_000_000)

    def test_lag_is_unknown(self):
        self.assertIsNone(speed_kbps_from_type("lag"))

    def test_fibre_channel_is_unknown(self):
        self.assertIsNone(speed_kbps_from_type("16gfc-sfpp"))

    def test_missing_rate_is_unknown(self):
        self.assertIsNone(speed_kbps_from_type("base-t"))

    def test_every_netbox_ethernet_type_parses(self):
        # Guards against new NetBox type slugs that silently fall back to "unknown speed".
        for interface_type in InterfaceTypeChoices.values():
            if "base-" not in interface_type:
                continue
            with self.subTest(interface_type=interface_type):
                self.assertIsNotNone(speed_kbps_from_type(interface_type))
