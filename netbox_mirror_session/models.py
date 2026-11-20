from dcim.models import Interface
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from netbox.models import NetBoxModel, PrimaryModel

from .choices import (
    DestinationKindChoices,
    ExpiryWarningChoices,
    MirrorDirectionChoices,
    MirrorSessionStatusChoices,
)
from .constants import HIGH_SPEED_KBPS, LONG_EXPIRY, MAX_EXPIRY
from .speed import interface_speed_kbps

SESSION_NAME_EXTRA_CHARACTERS = {"-", "_", "."}

# Prefetch this on session querysets that call sources_with_high_or_unknown_speed() for many sessions.
SOURCES_WITH_INTERFACES = "sources__interface"

DESTINATION_FIELDS = ("destination_interface", "gre_source", "gre_destination", "vrf")

# Per destination kind: (fields that must be set, fields that may be set).
DESTINATION_FIELD_RULES = {
    DestinationKindChoices.INTERFACE: (("destination_interface",), ("destination_interface",)),
    DestinationKindChoices.GRE: (("gre_source", "gre_destination"), ("gre_source", "gre_destination", "vrf")),
    DestinationKindChoices.CPU: ((), ()),
}


def is_allowed_in_session_name(character):
    """Return True if EOS accepts the character in a monitor session name."""
    if not character.isascii():
        return False
    return character.isalnum() or character in SESSION_NAME_EXTRA_CHARACTERS


def validate_session_name(value):
    for character in value:
        if not is_allowed_in_session_name(character):
            raise ValidationError(f"{character!r} is not allowed. Use letters, digits, '-', '_' and '.'.")


class MirrorSession(PrimaryModel):
    device = models.ForeignKey(
        to="dcim.Device",
        on_delete=models.CASCADE,
        related_name="mirror_sessions",
    )
    name = models.CharField(
        max_length=100,
        validators=[validate_session_name],
    )
    status = models.CharField(
        max_length=30,
        choices=MirrorSessionStatusChoices,
        default=MirrorSessionStatusChoices.PLANNED,
    )
    expires = models.DateTimeField()
    destination_kind = models.CharField(
        max_length=30,
        choices=DestinationKindChoices,
    )
    destination_interface = models.ForeignKey(
        to="dcim.Interface",
        on_delete=models.PROTECT,
        related_name="mirror_destination_sessions",
        blank=True,
        null=True,
    )
    gre_source = models.ForeignKey(
        to="ipam.IPAddress",
        on_delete=models.PROTECT,
        related_name="+",
        blank=True,
        null=True,
        verbose_name="GRE source",
    )
    gre_destination = models.ForeignKey(
        to="ipam.IPAddress",
        on_delete=models.PROTECT,
        related_name="+",
        blank=True,
        null=True,
        verbose_name="GRE destination",
    )
    vrf = models.ForeignKey(
        to="ipam.VRF",
        on_delete=models.PROTECT,
        related_name="+",
        blank=True,
        null=True,
        verbose_name="VRF",
    )
    truncate = models.BooleanField(
        default=False,
    )

    clone_fields = ("device", "status", "destination_kind", "truncate")

    class Meta:
        ordering = ("device", "name")
        verbose_name = "Mirror Session"
        constraints = [
            models.UniqueConstraint(
                fields=("device", "name"),
                name="netbox_mirror_session_unique_device_name",
                violation_error_message="A mirror session with this name already exists on the device.",
            ),
        ]

    def __str__(self):
        return self.name

    def get_status_color(self):
        return MirrorSessionStatusChoices.colors.get(self.status)

    def get_destination_kind_color(self):
        return DestinationKindChoices.colors.get(self.destination_kind)

    @property
    def destination(self):
        """The object the session mirrors to: an interface, the GRE destination address, or None for the CPU."""
        if self.destination_kind == DestinationKindChoices.INTERFACE:
            return self.destination_interface
        elif self.destination_kind == DestinationKindChoices.GRE:
            return self.gre_destination
        elif self.destination_kind == DestinationKindChoices.CPU:
            return None
        else:
            raise ValueError(f"Unknown destination kind {self.destination_kind!r} on mirror session {self.pk}.")

    def clean(self):
        super().clean()
        # full_clean() already reports a missing device; every check below needs one.
        if self.device_id is None:
            return

        errors = {}
        self._check_destination_fields(errors)
        self._check_destination_interface(errors)
        self._check_gre_source(errors)
        self._check_expiry(errors)
        self._check_existing_sources(errors)
        if errors:
            raise ValidationError(errors)

    def _check_destination_fields(self, errors):
        if self.destination_kind not in DESTINATION_FIELD_RULES:
            errors["destination_kind"] = f"Unknown destination kind {self.destination_kind!r}."
            return

        required_fields, allowed_fields = DESTINATION_FIELD_RULES[self.destination_kind]
        kind_label = self.get_destination_kind_display()
        for field_name in DESTINATION_FIELDS:
            value = getattr(self, field_name)
            if field_name in required_fields and value is None:
                errors[field_name] = f"Required when the destination is {kind_label}."
            elif field_name not in allowed_fields and value is not None:
                errors[field_name] = f"Must be empty when the destination is {kind_label}."

    def _check_destination_interface(self, errors):
        interface = self.destination_interface
        if interface is None:
            return
        if interface.device_id != self.device_id:
            errors["destination_interface"] = f"{interface} is on {interface.device}, not on {self.device}."

    def _check_gre_source(self, errors):
        address = self.gre_source
        if address is None:
            return
        assigned = address.assigned_object
        if isinstance(assigned, Interface) and assigned.device_id == self.device_id:
            return
        errors["gre_source"] = f"{address} must be assigned to an interface on {self.device}."

    def _check_expiry(self, errors):
        if self.expires is None:
            return
        now = timezone.now()
        if self.expires > now + MAX_EXPIRY:
            errors["expires"] = f"Must be at most {MAX_EXPIRY.days} days ahead."
        elif self.status == MirrorSessionStatusChoices.ACTIVE and self.expires <= now:
            errors["expires"] = "An active session must expire in the future."

    def _check_existing_sources(self, errors):
        # Messages name only what the user chose, never source details they may lack permission to view.
        if self.pk is None:
            return
        sources_elsewhere = self.sources.exclude(interface__device_id=self.device_id).count()
        if sources_elsewhere:
            errors["device"] = f"{sources_elsewhere} source(s) of this session are on another device; remove them."
        if self.destination_interface_id is not None:
            if self.sources.filter(interface_id=self.destination_interface_id).exists():
                errors["destination_interface"] = f"{self.destination_interface} is a source in this session."

    def is_expired(self):
        return self.expires <= timezone.now()

    def sources_with_high_or_unknown_speed(self):
        """Return the sources whose interface runs at HIGH_SPEED_KBPS or faster, or whose speed is unknown."""
        flagged = []
        for source in self.sources.all():
            speed = source.speed_kbps
            if speed is None or speed >= HIGH_SPEED_KBPS:
                flagged.append(source)
        return flagged

    @property
    def expiry_warning(self):
        """The ExpiryWarningChoices value for this session, or None when the expiry is short."""
        if self.expires - timezone.now() <= LONG_EXPIRY:
            return None
        if self.sources_with_high_or_unknown_speed():
            return ExpiryWarningChoices.LONG_HIGH_SPEED
        return ExpiryWarningChoices.LONG

    def get_expiry_warning_display(self):
        return dict(ExpiryWarningChoices).get(self.expiry_warning)

    def get_expiry_warning_color(self):
        return ExpiryWarningChoices.colors.get(self.expiry_warning)


class MirrorSource(NetBoxModel):
    session = models.ForeignKey(
        to="netbox_mirror_session.MirrorSession",
        on_delete=models.CASCADE,
        related_name="sources",
    )
    interface = models.ForeignKey(
        to="dcim.Interface",
        on_delete=models.CASCADE,
        related_name="mirror_sources",
    )
    direction = models.CharField(
        max_length=30,
        choices=MirrorDirectionChoices,
        default=MirrorDirectionChoices.BOTH,
    )

    clone_fields = ("session", "direction")

    class Meta:
        ordering = ("session", "interface")
        verbose_name = "Mirror Source"
        constraints = [
            models.UniqueConstraint(
                fields=("session", "interface"),
                name="netbox_mirror_session_unique_session_interface",
                violation_error_message="This interface is already a source in the session.",
            ),
        ]

    def __str__(self):
        return f"{self.session}: {self.interface}"

    def get_direction_color(self):
        return MirrorDirectionChoices.colors.get(self.direction)

    @property
    def speed_kbps(self):
        """The interface speed in kbit/s, from its speed field or else its type; None when unknown."""
        return interface_speed_kbps(self.interface)

    def clean(self):
        super().clean()
        if self.session_id is None or self.interface_id is None:
            return
        if self.interface.device_id != self.session.device_id:
            raise ValidationError(
                {"interface": f"{self.interface} is on {self.interface.device}, not on {self.session.device}."}
            )
        if self.interface_id == self.session.destination_interface_id:
            raise ValidationError({"interface": f"{self.interface} is the session's destination."})
