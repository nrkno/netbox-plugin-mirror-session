from django.urls import include, path
from utilities.urls import get_model_urls

from . import views  # noqa: F401  (registers the model views)

urlpatterns = (
    path("sessions/", include(get_model_urls("netbox_mirror_session", "mirrorsession", detail=False))),
    path("sessions/<int:pk>/", include(get_model_urls("netbox_mirror_session", "mirrorsession"))),
    path("sources/", include(get_model_urls("netbox_mirror_session", "mirrorsource", detail=False))),
    path("sources/<int:pk>/", include(get_model_urls("netbox_mirror_session", "mirrorsource"))),
)
