from dcim.models import Device, Interface, Site
from django import forms
from ipam.models import VRF, IPAddress
from netbox.forms import (
    NetBoxModelFilterSetForm,
    NetBoxModelForm,
    PrimaryModelFilterSetForm,
    PrimaryModelForm,
)
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField, TagFilterField
from utilities.forms.rendering import FieldSet
from utilities.forms.widgets import DateTimePicker

from .choices import DestinationKindChoices, MirrorDirectionChoices, MirrorSessionStatusChoices
from .constants import LONG_EXPIRY, MAX_EXPIRY
from .models import MirrorSession, MirrorSource


class MirrorSessionForm(PrimaryModelForm):
    # Not saved: it narrows the device list, which is too long to search without it.
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        initial_params={"devices": "$device"},
    )
    device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        query_params={"site_id": "$site"},
    )
    destination_interface = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        required=False,
        query_params={"device_id": "$device"},
        help_text="For a local interface destination.",
    )
    gre_source = DynamicModelChoiceField(
        queryset=IPAddress.objects.all(),
        required=False,
        query_params={"device_id": "$device"},
        label="GRE source",
        help_text="An address on this device, for a GRE tunnel destination.",
    )
    gre_destination = DynamicModelChoiceField(
        queryset=IPAddress.objects.all(),
        required=False,
        label="GRE destination",
        help_text="The capture host's address, for a GRE tunnel destination.",
    )
    vrf = DynamicModelChoiceField(
        queryset=VRF.objects.all(),
        required=False,
        label="VRF",
    )

    fieldsets = (
        FieldSet("site", "device", "name", "status", "expires", "description", "tags", name="Mirror Session"),
        FieldSet("destination_kind", "destination_interface", name="Destination"),
        FieldSet("gre_source", "gre_destination", "vrf", name="GRE Tunnel"),
        FieldSet("truncate", name="Options"),
    )

    class Meta:
        model = MirrorSession
        fields = (
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
        )
        widgets = {
            "expires": DateTimePicker(),
        }
        help_texts = {
            "expires": (
                f"At most {MAX_EXPIRY.days} days ahead; more than {LONG_EXPIRY.days} days gives a warning. "
                "After this the session is set to planned."
            ),
        }


class MirrorSessionFilterForm(PrimaryModelFilterSetForm):
    model = MirrorSession
    fieldsets = (
        FieldSet("q", "filter_id", "tag"),
        FieldSet("site_id", "device_id", "status", "destination_kind", name="Attributes"),
    )

    site_id = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label="Site",
    )
    device_id = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
        query_params={"site_id": "$site_id"},
        label="Device",
    )
    status = forms.MultipleChoiceField(
        choices=MirrorSessionStatusChoices,
        required=False,
    )
    destination_kind = forms.MultipleChoiceField(
        choices=DestinationKindChoices,
        required=False,
    )
    tag = TagFilterField(model)


class MirrorSourceForm(NetBoxModelForm):
    # Site and device are not saved: they narrow the session and interface lists to one device.
    # The session page's Add button prefills both.
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
    )
    device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        query_params={"site_id": "$site"},
    )
    session = DynamicModelChoiceField(
        queryset=MirrorSession.objects.all(),
        query_params={"device_id": "$device"},
    )
    interface = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        query_params={"device_id": "$device"},
    )

    fieldsets = (FieldSet("site", "device", "session", "interface", "direction", "tags", name="Mirror Source"),)

    class Meta:
        model = MirrorSource
        fields = ("session", "interface", "direction", "tags")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is not None:
            device = self.instance.session.device
            self.initial["device"] = device.pk
            self.initial["site"] = device.site_id


class MirrorSourceFilterForm(NetBoxModelFilterSetForm):
    model = MirrorSource
    fieldsets = (
        FieldSet("q", "filter_id", "tag"),
        FieldSet("site_id", "device_id", "session_id", "direction", name="Attributes"),
    )

    site_id = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label="Site",
    )
    session_id = DynamicModelMultipleChoiceField(
        queryset=MirrorSession.objects.all(),
        required=False,
        label="Session",
    )
    device_id = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
        query_params={"site_id": "$site_id"},
        label="Device",
    )
    direction = forms.MultipleChoiceField(
        choices=MirrorDirectionChoices,
        required=False,
    )
    tag = TagFilterField(model)
