from contextlib import contextmanager
from nicegui import ui, app

# See: https://nicegui.io/documentation#page_layout

# Icon per: https://thenounproject.com/icon/kindle-612906/
PAGE_ICON = "icons/noun-kindle-612906.svg"


@contextmanager
def header():
    # Access to google material icons.
    # https://fonts.google.com/icons
    ui.add_head_html(
        '<link rel="stylesheet" \
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@48,600,1,0" />'  # noqa: E501
    )

    with ui.header(elevated=True).classes(replace="items-center"):
        with ui.row().classes("items-center justify-between").style("padding:5px;"):
            ui.markdown("### Kindle E-Display Image Server")

            with ui.tabs() as tabs:
                for plugin in app.plugin_manager.plugins:
                    for tab in plugin.tabitems:
                        tab.to_tab()

            with ui.button(on_click=lambda: menu.open()).props("icon=menu"):
                with ui.menu() as menu:
                    for menuitem in app.plugin_manager.menuitems:
                        menuitem.to_menu_item()

                    ui.separator()
                    ui.menu_item("Documentation", on_click=lambda: ui.open("/docs"))
                    ui.separator()
                    ui.menu_item("Close", on_click=lambda: menu.close())

    yield tabs
