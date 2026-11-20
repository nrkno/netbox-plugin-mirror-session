from netbox.ui import attrs, panels


class MirrorSessionPanel(panels.ObjectAttributesPanel):
    device = attrs.RelatedObjectAttr("device", linkify=True)
    name = attrs.TextAttr("name")
    status = attrs.ChoiceAttr("status")
    expires = attrs.DateTimeAttr("expires")
    description = attrs.TextAttr("description")


class MirrorDestinationPanel(panels.ObjectAttributesPanel):
    destination_kind = attrs.ChoiceAttr("destination_kind", label="Kind")
    destination = attrs.RelatedObjectAttr("destination", linkify=True)
    gre_source = attrs.RelatedObjectAttr("gre_source", linkify=True, label="GRE source")
    vrf = attrs.RelatedObjectAttr("vrf", linkify=True, label="VRF")
    truncate = attrs.BooleanAttr("truncate")


class MirrorSourcePanel(panels.ObjectAttributesPanel):
    session = attrs.RelatedObjectAttr("session", linkify=True)
    device = attrs.RelatedObjectAttr("session.device", linkify=True)
    interface = attrs.RelatedObjectAttr("interface", linkify=True)
    speed = attrs.TemplatedAttr("speed_kbps", template_name="netbox_mirror_session/inc/speed.html")
    direction = attrs.ChoiceAttr("direction")
