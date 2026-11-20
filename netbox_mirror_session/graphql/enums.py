import strawberry

from ..choices import DestinationKindChoices, MirrorDirectionChoices, MirrorSessionStatusChoices

MirrorSessionStatusEnum = strawberry.enum(MirrorSessionStatusChoices.as_enum(prefix="status"))
DestinationKindEnum = strawberry.enum(DestinationKindChoices.as_enum(prefix="kind"))
MirrorDirectionEnum = strawberry.enum(MirrorDirectionChoices.as_enum(prefix="direction"))
