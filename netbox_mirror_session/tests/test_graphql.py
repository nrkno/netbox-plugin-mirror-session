from dcim.choices import InterfaceTypeChoices
from django.urls import reverse
from utilities.testing import TestCase

from ..models import MirrorSource
from .data import build_session, create_device, create_interface


class MirrorSessionGraphqlTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leaf = create_device("leaf-01")
        cls.mixer_port = create_interface(cls.leaf, "Ethernet5", InterfaceTypeChoices.TYPE_25GE_SFP28)
        cls.session = build_session(cls.leaf)
        cls.session.save()
        MirrorSource.objects.create(session=cls.session, interface=cls.mixer_port, direction="tx")

    def test_lists_sessions_with_sources(self):
        self.add_permissions(
            "netbox_mirror_session.view_mirrorsession",
            "netbox_mirror_session.view_mirrorsource",
            "dcim.view_interface",
        )
        query = (
            """{
            mirror_session_list(filters: {device_id: "%d"}) {
                name status expires destination_kind
                sources { direction interface { name } }
            }
        }"""
            % self.leaf.pk
        )

        response = self.client.post(reverse("graphql"), {"query": query}, content_type="application/json")

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertNotIn("errors", body)
        sessions = body["data"]["mirror_session_list"]
        self.assertEqual(sessions[0]["name"], "capture")
        self.assertEqual(sessions[0]["sources"], [{"direction": "tx", "interface": {"name": "Ethernet5"}}])
