from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from utilities.testing import APITestCase

from .data import create_device

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
