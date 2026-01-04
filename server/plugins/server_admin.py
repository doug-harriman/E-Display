# admin.py
# Basic server based administration.
#
# Plugin manager will discover the APIRouter and the PluginBase
# class instances and add them to the application.

import datetime as dt
import logging

from fastapi import Request, status
from fastapi.responses import RedirectResponse

from nicegui import APIRouter, ui
import theme

from repo import Repo

from plugin_base import PluginBase, MenuItem

# Hang admin routes off the root
router_admin = APIRouter(tags=["admin"])

# Logger config
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)

# Set up plugin menu item
ROUTE_ADMIN = "/admin"
ROUTE_UPDATE = "/update"
mnu = MenuItem("Admin", ROUTE_ADMIN)
mnu.sort_order = 1

# Plugin
plugin = PluginBase()
plugin += mnu


# TODO: Server admin page should periodically check for updates.
@router_admin.page(ROUTE_ADMIN, favicon=theme.PAGE_ICON)
async def list_current_server_version_info():
    repo = Repo()

    with theme.header():
        ui.markdown("### Server Administration")

        with ui.grid(columns=2):
            ui.label("Git Repository")
            ui.markdown(f"[{repo.url_base}]({repo.url_base})")

            ui.label("Working Branch")
            ui.label(repo.branch)

            ui.label("Last Commit")
            ui.markdown(f"[{repo.current.sha[:6]}]({repo.current.url})")

            ui.label("Last Updated")
            tz = dt.datetime.now().astimezone().tzinfo
            time = f"{repo.current.timestamp.astimezone(tz):%Y-%m-%d %H:%M:%S}"
            ui.markdown(time)

            ui.label("Status")

            import time

            t1 = time.process_time()
            status = repo.remote_status()
            t2 = time.process_time()
            logger.debug(f"Time to retrieve git status: {t2 - t1}")

            current = status == "up to date"
            if current:
                ui.markdown(f'<span style="color:green">{status.title()}</span>')

            else:
                ui.markdown(f'<span style="color:red">{status.title()}</span>')

                ui.label("Server Last Updated")
                time = (
                    f"{repo.remote_current.timestamp.astimezone(tz):%Y-%m-%d %H:%M:%S}"
                )
                ui.markdown(time)

        # TODO: Enable/disable button based on if up to date or not.
        ui.button("Update to Latest", on_click=lambda: ui.navigate.to(ROUTE_UPDATE))


@router_admin.get(ROUTE_UPDATE)
def update_server_to_latest_commit(request: Request):
    """
    Updates server software to latest by pulling from git repo.

    Args:
        request (Request): HTTP Request.

    Returns:
        RedirectResponse: Redirects to admin page.
    """

    repo = Repo()
    res = repo.git.pull().strip()

    msg = f"Pull result: {res}"
    logger.info("Log: " + msg)
    print("Print: " + msg)

    # TODO: Instead of reloading (slow), just update elements that need it.
    resp = RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)
    return resp
