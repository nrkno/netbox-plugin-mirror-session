from netbox.plugins import PluginMenuButton, PluginMenuItem

menu_items = (
    PluginMenuItem(
        link="plugins:netbox_mirror_session:mirrorsession_list",
        link_text="Mirror Sessions",
        permissions=["netbox_mirror_session.view_mirrorsession"],
        buttons=(
            PluginMenuButton(
                link="plugins:netbox_mirror_session:mirrorsession_add",
                title="Add",
                icon_class="mdi mdi-plus-thick",
                permissions=["netbox_mirror_session.add_mirrorsession"],
            ),
        ),
    ),
    PluginMenuItem(
        link="plugins:netbox_mirror_session:mirrorsource_list",
        link_text="Mirror Sources",
        permissions=["netbox_mirror_session.view_mirrorsource"],
    ),
)
