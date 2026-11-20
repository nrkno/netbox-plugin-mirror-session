from typing import TYPE_CHECKING, Annotated

import strawberry
import strawberry_django
from netbox.graphql.types import NetBoxObjectType, PrimaryObjectType

from .. import models
from . import filters

if TYPE_CHECKING:
    from dcim.graphql.types import DeviceType, InterfaceType
    from ipam.graphql.types import IPAddressType, VRFType


@strawberry_django.type(models.MirrorSession, fields="__all__", filters=filters.MirrorSessionFilter)
class MirrorSessionType(PrimaryObjectType):
    device: Annotated["DeviceType", strawberry.lazy("dcim.graphql.types")]
    destination_interface: Annotated["InterfaceType", strawberry.lazy("dcim.graphql.types")] | None
    gre_source: Annotated["IPAddressType", strawberry.lazy("ipam.graphql.types")] | None
    gre_destination: Annotated["IPAddressType", strawberry.lazy("ipam.graphql.types")] | None
    vrf: Annotated["VRFType", strawberry.lazy("ipam.graphql.types")] | None
    sources: list[Annotated["MirrorSourceType", strawberry.lazy("netbox_mirror_session.graphql.types")]]


@strawberry_django.type(models.MirrorSource, fields="__all__", filters=filters.MirrorSourceFilter)
class MirrorSourceType(NetBoxObjectType):
    session: Annotated["MirrorSessionType", strawberry.lazy("netbox_mirror_session.graphql.types")]
    interface: Annotated["InterfaceType", strawberry.lazy("dcim.graphql.types")]
