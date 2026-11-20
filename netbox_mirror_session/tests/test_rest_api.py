from datetime import timedelta

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from ipam.models import VRF, IPAddress
from utilities.testing import APITestCase

from ..models import MirrorSource
from .data import build_session, create_device, create_interface, create_ip

SESSION_LIST_URL = "plugins-api:netbox_mirror_session-api:mirrorsession-list"
SOURCE_LIST_URL = "plugins-api:netbox_mirror_session-api:mirrorsource-list"


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


class MirrorSourceRestApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leaf = create_device("leaf-01")

    def count_source_list_queries(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse(SOURCE_LIST_URL), **self.header)
        self.assertEqual(response.status_code, 200, response.content)
        return len(queries)

    def create_session_with_source(self, name, port_name):
        session = build_session(self.leaf, name=name)
        session.save()
        MirrorSource.objects.create(session=session, interface=create_interface(self.leaf, port_name))

    def test_source_list_query_count_does_not_grow_with_sources(self):
        self.add_permissions("netbox_mirror_session.view_mirrorsource")
        self.create_session_with_source("one", "Ethernet1")
        # The first API call also updates the token's last_used; measure from the second call on.
        self.count_source_list_queries()
        queries_for_one = self.count_source_list_queries()

        self.create_session_with_source("two", "Ethernet2")
        self.create_session_with_source("three", "Ethernet3")
        queries_for_three = self.count_source_list_queries()

        self.assertEqual(queries_for_three, queries_for_one)


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
