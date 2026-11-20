from typing import TYPE_CHECKING, Annotated

import strawberry
import strawberry_django
from netbox.graphql.filters import NetBoxModelFilter, PrimaryModelFilter
from strawberry import ID
from strawberry_django import DatetimeFilterLookup, StrFilterLookup

from .. import models

if TYPE_CHECKING:
    from dcim.graphql.filters import DeviceFilter, InterfaceFilter

    from .enums import DestinationKindEnum, MirrorDirectionEnum, MirrorSessionStatusEnum

ENUMS = "netbox_mirror_session.graphql.enums"
FILTERS = "netbox_mirror_session.graphql.filters"


@strawberry_django.filter_type(models.MirrorSession, lookups=True)
class MirrorSessionFilter(PrimaryModelFilter):
    device: Annotated["DeviceFilter", strawberry.lazy("dcim.graphql.filters")] | None = strawberry_django.filter_field()
    device_id: ID | None = strawberry_django.filter_field()
    name: StrFilterLookup | None = strawberry_django.filter_field()
    status: Annotated["MirrorSessionStatusEnum", strawberry.lazy(ENUMS)] | None = strawberry_django.filter_field()
    expires: DatetimeFilterLookup | None = strawberry_django.filter_field()
    destination_kind: Annotated["DestinationKindEnum", strawberry.lazy(ENUMS)] | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.MirrorSource, lookups=True)
class MirrorSourceFilter(NetBoxModelFilter):
    session: Annotated["MirrorSessionFilter", strawberry.lazy(FILTERS)] | None = strawberry_django.filter_field()
    session_id: ID | None = strawberry_django.filter_field()
    interface: Annotated["InterfaceFilter", strawberry.lazy("dcim.graphql.filters")] | None = (
        strawberry_django.filter_field()
    )
    interface_id: ID | None = strawberry_django.filter_field()
    direction: Annotated["MirrorDirectionEnum", strawberry.lazy(ENUMS)] | None = strawberry_django.filter_field()
