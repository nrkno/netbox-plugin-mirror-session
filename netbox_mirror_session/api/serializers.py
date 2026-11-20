from dcim.api.serializers import DeviceSerializer, InterfaceSerializer
from ipam.api.serializers import IPAddressSerializer, VRFSerializer
from netbox.api.fields import ChoiceField
from netbox.api.serializers import NetBoxModelSerializer, PrimaryModelSerializer

from ..choices import DestinationKindChoices, MirrorDirectionChoices, MirrorSessionStatusChoices
from ..models import MirrorSession, MirrorSource


class MirrorSessionSerializer(PrimaryModelSerializer):
    device = DeviceSerializer(nested=True)
    status = ChoiceField(choices=MirrorSessionStatusChoices, required=False)
    destination_kind = ChoiceField(choices=DestinationKindChoices)
    destination_interface = InterfaceSerializer(nested=True, required=False, allow_null=True)
    gre_source = IPAddressSerializer(nested=True, required=False, allow_null=True)
    gre_destination = IPAddressSerializer(nested=True, required=False, allow_null=True)
    vrf = VRFSerializer(nested=True, required=False, allow_null=True)

    class Meta:
        model = MirrorSession
        fields = (
            "id",
            "url",
            "display_url",
            "display",
            "device",
            "name",
            "status",
            "expires",
            "destination_kind",
            "destination_interface",
            "gre_source",
            "gre_destination",
            "vrf",
            "truncate",
            "owner",
            "description",
            "comments",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        )
        brief_fields = ("id", "url", "display", "device", "name", "description")


class MirrorSourceSerializer(NetBoxModelSerializer):
    session = MirrorSessionSerializer(nested=True)
    interface = InterfaceSerializer(nested=True)
    direction = ChoiceField(choices=MirrorDirectionChoices, required=False)

    class Meta:
        model = MirrorSource
        fields = (
            "id",
            "url",
            "display_url",
            "display",
            "session",
            "interface",
            "direction",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        )
        brief_fields = ("id", "url", "display", "direction")
