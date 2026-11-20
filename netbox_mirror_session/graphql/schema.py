import strawberry
import strawberry_django

from .types import MirrorSessionType, MirrorSourceType


@strawberry.type(name="Query")
class MirrorSessionQuery:
    mirror_session: MirrorSessionType = strawberry_django.field()
    mirror_session_list: list[MirrorSessionType] = strawberry_django.field()

    mirror_source: MirrorSourceType = strawberry_django.field()
    mirror_source_list: list[MirrorSourceType] = strawberry_django.field()
