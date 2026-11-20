from django.db.models import Count
from extras.ui.panels import CustomFieldsPanel, TagsPanel
from netbox.ui import actions, layout, panels
from netbox.views import generic
from utilities.templatetags.helpers import humanize_speed
from utilities.views import register_model_view

from . import filtersets, forms, models, tables
from .choices import ExpiryWarningChoices, MirrorSessionStatusChoices
from .constants import HIGH_SPEED_KBPS, LONG_EXPIRY
from .ui import panels as mirror_panels

#
# Mirror sessions
#


def sources_the_user_can_view(sources, visible_sources):
    """Return the sources that are also in the user's permission-restricted queryset."""
    visible_ids = set(visible_sources.values_list("pk", flat=True))
    result = []
    for source in sources:
        if source.pk in visible_ids:
            result.append(source)
    return result


@register_model_view(models.MirrorSession)
class MirrorSessionView(generic.ObjectView):
    queryset = models.MirrorSession.objects.prefetch_related(models.SOURCES_WITH_INTERFACES)
    template_name = "netbox_mirror_session/mirrorsession.html"
    layout = layout.SimpleLayout(
        left_panels=[
            mirror_panels.MirrorSessionPanel(),
            CustomFieldsPanel(),
            TagsPanel(),
            panels.CommentsPanel(),
        ],
        right_panels=[
            mirror_panels.MirrorDestinationPanel(title="Destination"),
        ],
        bottom_panels=[
            panels.ObjectsTablePanel(
                model="netbox_mirror_session.MirrorSource",
                title="Sources",
                filters={"session_id": lambda ctx: ctx["object"].pk},
                exclude_columns=["session", "device"],
                actions=[
                    actions.AddObject(
                        "netbox_mirror_session.MirrorSource",
                        url_params={"session": lambda ctx: ctx["object"].pk},
                    ),
                ],
            ),
        ],
    )

    def get_extra_context(self, request, instance):
        expiry_warning = instance.expiry_warning

        # The warning counts every source, so it never disappears for a user who cannot view all of them.
        flagged_sources = instance.sources_with_high_or_unknown_speed()
        visible_sources = instance.sources.restrict(request.user, "view")
        visible_flagged_sources = sources_the_user_can_view(flagged_sources, visible_sources)

        return {
            "show_expired_but_active": (instance.status == MirrorSessionStatusChoices.ACTIVE and instance.is_expired()),
            "show_long_warning": expiry_warning == ExpiryWarningChoices.LONG,
            "show_high_speed_warning": expiry_warning == ExpiryWarningChoices.LONG_HIGH_SPEED,
            "flagged_sources": visible_flagged_sources,
            "hidden_flagged_source_count": len(flagged_sources) - len(visible_flagged_sources),
            "long_expiry_days": LONG_EXPIRY.days,
            "high_speed": humanize_speed(HIGH_SPEED_KBPS),
        }


@register_model_view(models.MirrorSession, "list", path="", detail=False)
class MirrorSessionListView(generic.ObjectListView):
    queryset = (
        models.MirrorSession.objects.annotate(source_count=Count("sources"))
        .select_related("device", "destination_interface", "gre_destination")
        .prefetch_related(models.SOURCES_WITH_INTERFACES)
    )
    table = tables.MirrorSessionTable
    filterset = filtersets.MirrorSessionFilterSet
    filterset_form = forms.MirrorSessionFilterForm


@register_model_view(models.MirrorSession, "add", detail=False)
@register_model_view(models.MirrorSession, "edit")
class MirrorSessionEditView(generic.ObjectEditView):
    queryset = models.MirrorSession.objects.all()
    form = forms.MirrorSessionForm


@register_model_view(models.MirrorSession, "delete")
class MirrorSessionDeleteView(generic.ObjectDeleteView):
    queryset = models.MirrorSession.objects.all()


@register_model_view(models.MirrorSession, "bulk_delete", path="delete", detail=False)
class MirrorSessionBulkDeleteView(generic.BulkDeleteView):
    queryset = models.MirrorSession.objects.all()
    filterset = filtersets.MirrorSessionFilterSet
    table = tables.MirrorSessionTable


#
# Mirror sources
#


@register_model_view(models.MirrorSource)
class MirrorSourceView(generic.ObjectView):
    queryset = models.MirrorSource.objects.select_related("session__device", "interface")
    template_name = "generic/object.html"
    layout = layout.SimpleLayout(
        left_panels=[
            mirror_panels.MirrorSourcePanel(),
            CustomFieldsPanel(),
            TagsPanel(),
        ],
    )


@register_model_view(models.MirrorSource, "list", path="", detail=False)
class MirrorSourceListView(generic.ObjectListView):
    queryset = models.MirrorSource.objects.select_related("session__device", "interface")
    table = tables.MirrorSourceTable
    filterset = filtersets.MirrorSourceFilterSet
    filterset_form = forms.MirrorSourceFilterForm


@register_model_view(models.MirrorSource, "add", detail=False)
@register_model_view(models.MirrorSource, "edit")
class MirrorSourceEditView(generic.ObjectEditView):
    queryset = models.MirrorSource.objects.all()
    form = forms.MirrorSourceForm


@register_model_view(models.MirrorSource, "delete")
class MirrorSourceDeleteView(generic.ObjectDeleteView):
    queryset = models.MirrorSource.objects.all()


@register_model_view(models.MirrorSource, "bulk_delete", path="delete", detail=False)
class MirrorSourceBulkDeleteView(generic.BulkDeleteView):
    queryset = models.MirrorSource.objects.all()
    filterset = filtersets.MirrorSourceFilterSet
    table = tables.MirrorSourceTable
