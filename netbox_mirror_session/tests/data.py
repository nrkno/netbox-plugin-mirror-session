from datetime import timedelta

from dcim.choices import InterfaceTypeChoices
from dcim.models import Device, DeviceRole, DeviceType, Interface, Manufacturer, Site
from django.utils import timezone
from ipam.models import IPAddress

from ..choices import DestinationKindChoices, MirrorSessionStatusChoices
from ..models import MirrorSession


def create_device(name):
    site, _ = Site.objects.get_or_create(name="Test site", slug="test-site")
    manufacturer, _ = Manufacturer.objects.get_or_create(name="Arista", slug="arista")
    device_type, _ = DeviceType.objects.get_or_create(
        manufacturer=manufacturer, model="DCS-7050SX3-48YC8", slug="dcs-7050sx3-48yc8"
    )
    role, _ = DeviceRole.objects.get_or_create(name="Leaf", slug="leaf")
    return Device.objects.create(name=name, site=site, device_type=device_type, role=role)


def create_interface(device, name, interface_type=InterfaceTypeChoices.TYPE_1GE_FIXED, speed=None):
    return Interface.objects.create(device=device, name=name, type=interface_type, speed=speed)


def create_ip(address, interface=None):
    return IPAddress.objects.create(address=address, assigned_object=interface)


def build_session(device, **overrides):
    """Return an unsaved, valid CPU-destination session expiring in one day; overrides replace fields."""
    fields = {
        "device": device,
        "name": "capture",
        "status": MirrorSessionStatusChoices.ACTIVE,
        "expires": timezone.now() + timedelta(days=1),
        "destination_kind": DestinationKindChoices.CPU,
    }
    fields.update(overrides)
    return MirrorSession(**fields)
