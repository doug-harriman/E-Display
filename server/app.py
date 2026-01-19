# app.py
# Web app

import os
import logging
from fastapi.responses import RedirectResponse

from nicegui import ui, app
import paths  # Importing adds paths to sys.path  # noqa: F401

from plugin_manager import PluginManager
from string_filters import StringFilter, StringFilterManager

# Root logger config
logger = logging.getLogger()
logger.setLevel(level=logging.WARNING)
fh = logging.StreamHandler()
fh_formatter = logging.Formatter(
    "%(asctime)s, %(levelname)s, %(filename)s:%(lineno)d - %(message)s"
)
fh.setFormatter(fh_formatter)
logger.addHandler(fh)

# File logging config
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)


def LoadPlugins():
    """
    Load plugins via the Plugin Manager class.
    Plugin manager stored into app as an attribute.
    """

    plugmgr = PluginManager()

    # Discovered plugins
    for plugin in plugmgr.plugins:
        if plugin.device:
            logger.debug(f"Plugin device added: {plugin.device.text}")

        for menu in plugin.menuitems:
            logger.debug(f"Plugin menu   added: {menu.text}")

        for tab in plugin.tabitems:
            logger.debug(f"Plugin tab   added: {tab.text}")

    # Plugin defined routes.
    for router in plugmgr.routers:
        app.include_router(router)
        for route in router.routes:
            logger.debug(f"Plugin route added: {route.path}")

    # Store with app for later use.
    setattr(app, "plugin_manager", plugmgr)

    # Store filters in the app.
    # Basic filters will be added from file.
    fm = StringFilterManager()
    filter_file = os.path.join(os.getcwd(), "string-filters.json")
    try:
        fm.load(filename=filter_file)
        logger.debug(f"Loaded string filters from: {fm.filename}")
    except FileExistsError:
        # Exception raised if file does not exist, ignore.
        logger.debug("No string filter file found.")
        pass

    if len(fm.filters) == 0:
        # Need at least one filter.
        logger.debug(f"No string filters, saving default to: {filter_file}")
        filt = StringFilter(regexp=r"[\(\[<].*?[\)\]>]", replacement="")
        fm += filt
        fm.save(filename=filter_file)

    logger.debug(f"Subject Filters [{len(fm.filters)}]:")
    for i, filt in enumerate(fm.filters):
        logger.debug(f"[{i}] {filt}")

    setattr(app, "string_filter_manager", fm)


app.on_startup(handler=LoadPlugins)


@app.exception_handler(404)
async def custom_404_handler(_, __):
    # TODO: Add notification displaying unknown URL
    return RedirectResponse("/")


if __name__ in {"__main__", "__mp_main__"}:
    # Run the server
    from theme import PAGE_ICON

    print("--- Starting Server ---", flush=True)

    ui.run(title="E-Display Manager", port=8123, favicon=PAGE_ICON)
