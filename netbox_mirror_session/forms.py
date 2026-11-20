from dcim.models import Device, Interface, Site
from django import forms
from django.db.models import Q
from ipam.models import VRF, IPAddress
from netbox.forms import (
    NetBoxModelFilterSetForm,
    NetBoxModelForm,
    PrimaryModelFilterSetForm,
    PrimaryModelForm,
)
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField, TagFilterField
from utilities.forms.rendering import FieldSet
from utilities.forms.utils import get_field_value
from utilities.forms.widgets import DateTimePicker

from .choices import DestinationKindChoices, MirrorDirectionChoices, MirrorSessionStatusChoices
from .constants import LONG_EXPIRY, MAX_EXPIRY
from .models import MirrorSession, MirrorSource

# Mimics NetBox's HTMXSelect: re-render the form when this field changes, so dependent lists can follow it.
RERENDER_FORM_ON_CHANGE = {
    "hx-get": ".",
    "hx-include": "#form_fields",
    "hx-target": "#form_fields",
}


def vrfs_on_device(device, keep_vrf_id=None):
    """Return the VRFs used by the device's interfaces or their IP addresses, plus keep_vrf_id if given."""
    condition = Q(interfaces__device=device) | Q(ip_addresses__interface__device=device)
    if keep_vrf_id is not None:
        condition |= Q(pk=keep_vrf_id)
    return VRF.objects.filter(condition).distinct().order_by("name")


def ip_addresses_on_device(device):
    """Return the IP addresses assigned to the device's interfaces."""
    return IPAddress.objects.filter(interface__device=device).prefetch_related("assigned_object").order_by("address")


class IPAddressWithInterfaceField(forms.ModelChoiceField):
    def label_from_instance(self, address):
        return f"{address.address} ({address.assigned_object.name})"


def selected_object(form, field_name, model):
    """Return the object currently chosen in a form field, or None if nothing is chosen yet."""
    value = get_field_value(form, field_name)
    if value in (None, ""):
        return None
    if isinstance(value, model):
        return value
    # A malformed ID is reported by the field's own validation.
    if not str(value).isdigit():
        return None
    return model.objects.filter(pk=int(value)).first()


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
        help_text="For a local interface destination.",
    )
    vrf = forms.ModelChoiceField(
        queryset=VRF.objects.none(),
        required=False,
        label="VRF",
        help_text="A VRF on this device. Leave empty for the global table.",
    )
    gre_source = IPAddressWithInterfaceField(
        queryset=IPAddress.objects.none(),
        required=False,
        label="GRE source",
        help_text="An address on this device.",
    )
    gre_destination = DynamicModelChoiceField(
        queryset=IPAddress.objects.all(),
        required=False,
        label="GRE destination",
        help_text="The capture host's address, in the chosen VRF.",
    )

    fieldsets = (
        FieldSet("site", "device", "name", "status", "expires", "description", "tags", name="Mirror Session"),
        FieldSet("destination_kind", "destination_interface", name="Destination"),
        FieldSet("vrf", "gre_source", "gre_destination", name="GRE Tunnel"),
        FieldSet("truncate", name="Options"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["device"].widget.attrs.update(RERENDER_FORM_ON_CHANGE)
        self.fields["vrf"].widget.attrs.update(RERENDER_FORM_ON_CHANGE)

        device = selected_object(self, "device", Device)
        if device is None:
            for field_name in ("destination_interface", "vrf", "gre_source"):
                self.fields[field_name].disabled = True
                self.fields[field_name].help_text = "Choose a device first."
        else:
            self.fields["destination_interface"].widget.add_query_param("device_id", device.pk)
            # An existing session may use a VRF that is not on the device; keep it selectable when editing.
            keep_vrf_id = None
            if self.instance.device_id == device.pk:
                keep_vrf_id = self.instance.vrf_id
            self.fields["vrf"].queryset = vrfs_on_device(device, keep_vrf_id)
            self.fields["gre_source"].queryset = ip_addresses_on_device(device)

        vrf = selected_object(self, "vrf", VRF)
        if vrf is None:
            self.fields["gre_destination"].widget.add_query_param("vrf_id", "null")
        else:
            self.fields["gre_destination"].widget.add_query_param("vrf_id", vrf.pk)

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
    session = DynamicModelChoiceField(
        queryset=MirrorSession.objects.all(),
        context={"parent": "device"},
    )
    interface = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        help_text="Interfaces on the session's device, except its destination.",
    )

    fieldsets = (FieldSet("session", "interface", "direction", "tags", name="Mirror Source"),)

    class Meta:
        model = MirrorSource
        fields = ("session", "interface", "direction", "tags")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["session"].widget.attrs.update(RERENDER_FORM_ON_CHANGE)

        session = selected_object(self, "session", MirrorSession)
        if session is None:
            self.fields["interface"].disabled = True
            self.fields["interface"].help_text = "Choose a session first."
            return

        self.fields["interface"].widget.add_query_param("device_id", session.device_id)
        if session.destination_interface_id is not None:
            self.fields["interface"].widget.add_query_param("id__n", session.destination_interface_id)


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
