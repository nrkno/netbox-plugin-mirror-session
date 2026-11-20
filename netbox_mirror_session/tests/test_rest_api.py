from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from ipam.models import VRF, IPAddress
from utilities.testing import APITestCase

from .data import create_device, create_ip

SESSION_LIST_URL = "plugins-api:netbox_mirror_session-api:mirrorsession-list"


class MirrorSessionRestApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leaf = create_device("leaf-01")

    def post_session(self, expires):
        self.add_permissions("netbox_mirror_session.add_mirrorsession", "dcim.view_device")
        return self.client.post(
            reverse(SESSION_LIST_URL),
            {
                "device": self.leaf.pk,
                "name": "capture",
                "status": "active",
                "expires": expires.isoformat(),
                "destination_kind": "cpu",
            },
            format="json",
            **self.header,
        )

    def test_create_valid_session(self):
        response = self.post_session(timezone.now() + timedelta(days=2))
        self.assertEqual(response.status_code, 201, response.content)

    def test_create_beyond_six_months_is_rejected(self):
        response = self.post_session(timezone.now() + timedelta(days=200))
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("expires", response.json())


class GlobalTableFilterTests(APITestCase):
    """The GRE destination dropdown relies on NetBox reading vrf_id=null as the global table."""

    def test_ip_address_api_filters_global_table_with_null_vrf(self):
        self.add_permissions("ipam.view_ipaddress")
        media_vrf = VRF.objects.create(name="media")
        create_ip("10.9.9.9/32")
        IPAddress.objects.create(address="10.8.8.8/32", vrf=media_vrf)

        response = self.client.get(reverse("ipam-api:ipaddress-list") + "?vrf_id=null", **self.header)

        self.assertEqual(response.status_code, 200, response.content)
        addresses = [result["address"] for result in response.json()["results"]]
        self.assertEqual(addresses, ["10.9.9.9/32"])
