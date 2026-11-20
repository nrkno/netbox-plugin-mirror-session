from netbox.api.viewsets import NetBoxModelViewSet

from .. import filtersets, models
from .serializers import MirrorSessionSerializer, MirrorSourceSerializer


class MirrorSessionViewSet(NetBoxModelViewSet):
    queryset = models.MirrorSession.objects.select_related(
        "device", "destination_interface", "gre_source", "gre_destination", "vrf", "owner"
    ).prefetch_related("tags")
    serializer_class = MirrorSessionSerializer
    filterset_class = filtersets.MirrorSessionFilterSet


class MirrorSourceViewSet(NetBoxModelViewSet):
    queryset = models.MirrorSource.objects.select_related("session", "interface__device").prefetch_related("tags")
    serializer_class = MirrorSourceSerializer
    filterset_class = filtersets.MirrorSourceFilterSet
