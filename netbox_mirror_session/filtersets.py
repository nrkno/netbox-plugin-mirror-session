import django_filters
from dcim.models import Device, Interface, Site
from django.db.models import Q
from netbox.filtersets import NetBoxModelFilterSet, PrimaryModelFilterSet
from utilities.filtersets import register_filterset

from .choices import DestinationKindChoices, MirrorDirectionChoices, MirrorSessionStatusChoices
from .models import MirrorSession, MirrorSource


@register_filterset
class MirrorSessionFilterSet(PrimaryModelFilterSet):
    site_id = django_filters.ModelMultipleChoiceFilter(
        field_name="device__site",
        queryset=Site.objects.all(),
        label="Site (ID)",
    )
    device_id = django_filters.ModelMultipleChoiceFilter(
        field_name="device",
        queryset=Device.objects.all(),
        label="Device (ID)",
    )
    device = django_filters.ModelMultipleChoiceFilter(
        field_name="device__name",
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (name)",
    )
    status = django_filters.MultipleChoiceFilter(
        choices=MirrorSessionStatusChoices,
    )
    destination_kind = django_filters.MultipleChoiceFilter(
        choices=DestinationKindChoices,
    )

    class Meta:
        model = MirrorSession
        fields = ("id", "name", "expires", "truncate", "description")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))


@register_filterset
class MirrorSourceFilterSet(NetBoxModelFilterSet):
    site_id = django_filters.ModelMultipleChoiceFilter(
        field_name="session__device__site",
        queryset=Site.objects.all(),
        label="Site (ID)",
    )
    session_id = django_filters.ModelMultipleChoiceFilter(
        field_name="session",
        queryset=MirrorSession.objects.all(),
        label="Session (ID)",
    )
    device_id = django_filters.ModelMultipleChoiceFilter(
        field_name="session__device",
        queryset=Device.objects.all(),
        label="Device (ID)",
    )
    interface_id = django_filters.ModelMultipleChoiceFilter(
        field_name="interface",
        queryset=Interface.objects.all(),
        label="Interface (ID)",
    )
    direction = django_filters.MultipleChoiceFilter(
        choices=MirrorDirectionChoices,
    )

    class Meta:
        model = MirrorSource
        fields = ("id",)

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(session__name__icontains=value) | Q(interface__name__icontains=value))
