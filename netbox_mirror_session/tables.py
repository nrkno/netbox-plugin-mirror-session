import django_tables2 as tables
from netbox.tables import NetBoxTable, PrimaryModelTable, columns

from .models import MirrorSession, MirrorSource

EXPIRY_WARNING_TEMPLATE = (
    "{% load helpers %}{% badge record.get_expiry_warning_display bg_color=record.get_expiry_warning_color %}"
)
SPEED_TEMPLATE = "{% load helpers %}{{ record.speed_kbps|humanize_speed|placeholder }}"


class MirrorSessionTable(PrimaryModelTable):
    name = tables.Column(linkify=True)
    device = tables.Column(linkify=True)
    status = columns.ChoiceFieldColumn()
    expires = columns.DateTimeColumn()
    destination_kind = columns.ChoiceFieldColumn(verbose_name="Destination kind")
    destination = tables.Column(linkify=True, orderable=False)
    expiry_warning = columns.TemplateColumn(
        template_code=EXPIRY_WARNING_TEMPLATE,
        orderable=False,
        verbose_name="Expiry warning",
    )
    source_count = tables.Column(verbose_name="Sources")
    tags = columns.TagColumn(url_name="plugins:netbox_mirror_session:mirrorsession_list")

    class Meta(PrimaryModelTable.Meta):
        model = MirrorSession
        fields = (
            "pk",
            "id",
            "name",
            "device",
            "status",
            "expires",
            "expiry_warning",
            "destination_kind",
            "destination",
            "source_count",
            "truncate",
            "description",
            "tags",
            "actions",
        )
        default_columns = (
            "name",
            "device",
            "status",
            "expires",
            "expiry_warning",
            "destination_kind",
            "destination",
            "source_count",
        )


class MirrorSourceTable(NetBoxTable):
    session = tables.Column(linkify=True)
    interface = tables.Column(linkify=True)
    device = tables.Column(accessor="session__device", linkify=True, verbose_name="Device")
    direction = columns.ChoiceFieldColumn()
    speed = columns.TemplateColumn(template_code=SPEED_TEMPLATE, orderable=False, verbose_name="Speed")
    tags = columns.TagColumn(url_name="plugins:netbox_mirror_session:mirrorsource_list")

    class Meta(NetBoxTable.Meta):
        model = MirrorSource
        fields = ("pk", "id", "session", "device", "interface", "speed", "direction", "tags", "actions")
        default_columns = ("session", "device", "interface", "speed", "direction")
