from importlib import metadata

from netbox.plugins import PluginConfig


class MirrorSessionConfig(PluginConfig):
    name = "netbox_mirror_session"
    verbose_name = "Mirror Sessions"
    description = "Port mirror sessions (SPAN, GRE mirror, CPU) with a mandatory expiry"
    version = metadata.version("netbox-plugin-mirror-session")
    base_url = "mirror-sessions"
    min_version = "4.6.0"
    max_version = "4.6.99"

    def ready(self):
        super().ready()
        from . import jobs  # noqa: F401  (registers the system job)


config = MirrorSessionConfig
