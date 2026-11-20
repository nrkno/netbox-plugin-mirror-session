from netbox.api.routers import NetBoxRouter

from . import views

app_name = "netbox_mirror_session"

router = NetBoxRouter()
router.register("sessions", views.MirrorSessionViewSet)
router.register("sources", views.MirrorSourceViewSet)

urlpatterns = router.urls
