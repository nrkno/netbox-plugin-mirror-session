from datetime import timedelta

from dcim.choices import InterfaceTypeChoices
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from utilities.testing import TestCase

from ..models import MirrorSource
from .data import build_session, create_device, create_interface, create_ip

VIEW_SESSIONS = "netbox_mirror_session.view_mirrorsession"
VIEW_SOURCES = "netbox_mirror_session.view_mirrorsource"
VIEW_INTERFACES = "dcim.view_interface"


class MirrorSessionPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leaf = create_device("leaf-01")
        cls.mixer_port = create_interface(cls.leaf, "Ethernet5", InterfaceTypeChoices.TYPE_25GE_SFP28)
        cls.session = build_session(cls.leaf, expires=timezone.now() + timedelta(days=30))
        cls.session.save()
        MirrorSource.objects.create(session=cls.session, interface=cls.mixer_port)

    def test_detail_page_shows_high_speed_warning(self):
        self.add_permissions(VIEW_SESSIONS, VIEW_SOURCES, VIEW_INTERFACES)

        response = self.client.get(self.session.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Long-running mirror of high-speed interfaces")
        self.assertContains(response, "Ethernet5")

    def test_detail_page_hides_sources_the_user_cannot_view(self):
        self.add_permissions(VIEW_SESSIONS)

        response = self.client.get(self.session.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Long-running mirror of high-speed interfaces")
        self.assertContains(response, "1 more that you do not have permission to view")
        self.assertNotContains(response, "Ethernet5")

    def test_source_detail_page_renders(self):
        self.add_permissions(VIEW_SOURCES)
        source = MirrorSource.objects.get(session=self.session)

        response = self.client.get(source.get_absolute_url())

        self.assertEqual(response.status_code, 200)

    def test_session_add_page_renders(self):
        self.add_permissions("netbox_mirror_session.add_mirrorsession")

        response = self.client.get(reverse("plugins:netbox_mirror_session:mirrorsession_add"))

        self.assertEqual(response.status_code, 200)

    def test_session_form_rerender_lists_the_device_addresses(self):
        self.add_permissions("netbox_mirror_session.add_mirrorsession", "dcim.view_device", "ipam.view_ipaddress")
        loopback = create_interface(self.leaf, "Loopback0", InterfaceTypeChoices.TYPE_VIRTUAL)
        create_ip("10.0.0.1/32", loopback)
        url = reverse("plugins:netbox_mirror_session:mirrorsession_add")

        response = self.client.get(f"{url}?device={self.leaf.pk}", HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "10.0.0.1/32 (Loopback0)")

    def test_source_add_page_renders(self):
        self.add_permissions("netbox_mirror_session.add_mirrorsource")

        response = self.client.get(reverse("plugins:netbox_mirror_session:mirrorsource_add"))

        self.assertEqual(response.status_code, 200)


class MirrorSessionListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leaf = create_device("leaf-01")

    def create_long_session_with_source(self, name, port_name):
        session = build_session(self.leaf, name=name, expires=timezone.now() + timedelta(days=30))
        session.save()
        port = create_interface(self.leaf, port_name, InterfaceTypeChoices.TYPE_25GE_SFP28)
        MirrorSource.objects.create(session=session, interface=port)

    def count_session_list_queries(self):
        url = reverse("plugins:netbox_mirror_session:mirrorsession_list")
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return len(queries)

    def test_session_list_shows_expiry_warning(self):
        self.add_permissions(VIEW_SESSIONS)
        self.create_long_session_with_source("one", "Ethernet11")

        response = self.client.get(reverse("plugins:netbox_mirror_session:mirrorsession_list"))

        self.assertContains(response, "Long expiry on high-speed source")

    def test_source_list_renders(self):
        self.add_permissions(VIEW_SOURCES)
        self.create_long_session_with_source("one", "Ethernet11")

        response = self.client.get(reverse("plugins:netbox_mirror_session:mirrorsource_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ethernet11")

    def test_session_list_query_count_does_not_grow_with_sessions(self):
        self.add_permissions(VIEW_SESSIONS)
        self.create_long_session_with_source("one", "Ethernet11")
        queries_for_one = self.count_session_list_queries()

        self.create_long_session_with_source("two", "Ethernet12")
        self.create_long_session_with_source("three", "Ethernet13")
        queries_for_three = self.count_session_list_queries()

        self.assertEqual(queries_for_three, queries_for_one)
