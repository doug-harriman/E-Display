import pexpect

from fastapi import Form, status
from fastapi.responses import RedirectResponse
from nicegui import APIRouter, ui, app

import theme
from plugin_base import PluginBase, TabItem

from calendar_outlook_msal import CalendarOutlook

# TODO: Use pexect like calendar_outlook.py for authentication UI to capture URL & code.

# Hang admin routes off the root
router_outlook = APIRouter(tags=["outlook"])
router_outlook.userdata = None

# Tab
tab = TabItem("Outlook", "/outlook")
tab.tooltip = "Read Outlook calendar data"

# Plugin
plugin = PluginBase()
plugin += tab

@router_outlook.get("/outlook/authenticate")
def route_outlook():
    # Called with authenticate link is clicked

    cmd = f"python {__file__}"

    try:
        PROC = pexpect.spawn(cmd, timeout=5)
        # print(str(proc))
        PROC.expect("Paste the authenticated url here:\r\n")
        # print(str(proc))
    except:  # noqa: E722
        print("Failed to start outlook_calendar.py")
        print(f"Return code: {PROC.exitstatus}")
        print(f"Before: {PROC.before}")
        PROC.kill(0)

    router_outlook.userdata = PROC

    res = PROC.before.decode("utf-8").split("\r\n")
    url = filter(lambda x: x.startswith("https"), res)
    url = list(url)[0]
    print(f"Redirect to: {url}")

    return RedirectResponse(url)


@router_outlook.page("/outlook", favicon=theme.PAGE_ICON)
async def route_outlook_login():
    with theme.header() as tabs:
        tabs.set_value("Outlook")

        ui.markdown("### Outlook Calendar Data Request")
        with ui.card():
            ui.markdown("Request calendar data from server for current day.")
            ui.markdown(
                """A request will be sent to the Outlook server. The server
                        then returns an authentication URL.  Copy the returned URL
                        from the browser address bar and paste it into the box below.
                        """
            )

        ui.button(
            "Request Authentication URL",
            on_click=lambda: ui.navigate.to("/outlook/authenticate"),
        )

        ui.label("Paste the authenticated URL below:")
        ui.input(
            label="Authentication URL", on_change=lambda e: pass_auth_url(e.value)
        ).classes("w-full")

        def pass_auth_url(auth_url: str):
            print(f"Auth URL: {auth_url}")

            # Send data to process
            if router_outlook.userdata:
                router_outlook.userdata.sendline(auth_url)
                router_outlook.userdata.expect(pexpect.EOF)
                router_outlook.userdata.kill(0)
                router_outlook.userdata = None

            # Go to index page.
            ui.navigate.to("/")


@router_outlook.post("/outlook")
def route_outlook_post(auth_url: str = Form()):
    print(f"Auth URL: {auth_url}")

    # Send data to process
    if router_outlook.userdata:
        router_outlook.userdata.sendline(auth_url)
        router_outlook.userdata.expect(pexpect.EOF)
        router_outlook.userdata.kill(0)
        router_outlook.userdata = None

    resp = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    return resp
