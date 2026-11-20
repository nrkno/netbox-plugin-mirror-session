from netbox.search import SearchIndex, register_search

from .models import MirrorSession


@register_search
class MirrorSessionIndex(SearchIndex):
    model = MirrorSession
    fields = (
        ("name", 100),
        ("description", 500),
        ("comments", 5000),
    )
    display_attrs = ("device", "status", "expires", "destination_kind", "description")
