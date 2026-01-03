import datetime as dt
import json
from pathlib import Path
import tomllib
from typing import Any, Self
from datetime import datetime, timedelta, timezone

import msal
import pexpect
import requests

from fastapi import Form, status
from fastapi.responses import RedirectResponse
from nicegui import APIRouter, ui, app

import theme
from calendar_base import CalendarBase, EventBase
from plugin_base import PluginBase, TabItem

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

class CalendarOutlookMsal(CalendarBase):
    """Outlook Calendar read object using MSAL for authentication."""

    def __init__(self, test: bool = False):
        super().__init__(test=test)

        self.MS_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
        self.SCOPES = ["Calendars.Read"]
        self.TOKEN_CACHE_FILE = Path("token_cache.json")

        self._authenticated = False
        self._headers = None

    def token_save(self, token):
        with open(self.TOKEN_CACHE_FILE, "w") as f:
            json.dump(token, f)

    def token_load(self):
        if self.TOKEN_CACHE_FILE.exists():
            with open(self.TOKEN_CACHE_FILE, "r") as f:
                return json.load(f)

        self._logger.debug("No MSAL token cache file found.")
        return None

    @property
    def is_authenticated(self) -> bool:
        """Return authentication status."""
        return self._authenticated

    @property
    def headers(self) -> dict[str, str] | None:
        """Return HTTP headers for MS Graph requests."""
        return self._headers

    def authenticate(self) -> bool:
        """
        Authenticate with MS Graph using MSAL.

        Returns:
            bool: True if authenticated, False otherwise.
        """

        self._authenticated = False
        self._headers = None

        # Load MSAL app config
        if not Path("ms-auth.toml").exists():
            self._logger.debug("MSAL auth config file 'ms-auth.toml' not found.")
            return self._authenticated
        with open("ms-auth.toml", "rb") as f:
            config = tomllib.load(f)
        app_id = config["APPLICATION_ID"]
        tennent_id = config["TENNANT_ID"]

        authority = f'https://login.microsoftonline.com/{tennent_id}'
        app = msal.PublicClientApplication(app_id, authority=authority)

        # Try to load and use refresh token
        token = self.token_load()
        if token and "refresh_token" in token:
            result = app.acquire_token_by_refresh_token(token["refresh_token"], self.SCOPES)
            if "access_token" in result:
                self.token_save(result)
                token = result["access_token"]
                self._authenticated = True

        if not self._authenticated:
            # Device code flow
            flow = app.initiate_device_flow(scopes=self.SCOPES)
            if "user_code" not in flow:
                raise Exception("Failed to create device flow")
            print(flow["message"])
            result = app.acquire_token_by_device_flow(flow)
            if "access_token" in result:
                self.token_save(result)
                token = result["access_token"]
                self._authenticated = True

        if self._authenticated:
            self._headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            self._logger.debug("MSAL authenticated successful")

        return self._authenticated

    def query(self, date: dt.datetime | None = None) -> Self:
        """
        Queries the online database for events on the specified date.

        Args:
            date (datetime.datetime, optional): Date of events.
                                                Defaults to datetime.date.today().
        """

        if not self.is_authenticated:
            self._logger.debug("Event query failed, not authenticated")
            return self

        if date is None:
            # Use today's date as the default
            date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Prepare date range for the query
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0) # type: ignore
        end_of_day = start_of_day + timedelta(days=1) - timedelta(seconds=1)
        self._logger.debug(f"Querying events for: {start_of_day}")

        # Query MS Graph for events
        url = (
            f"{self.MS_GRAPH_BASE_URL}/me/calendarView"
            f"?startDateTime={start_of_day.isoformat()}"
            f"&endDateTime={end_of_day.isoformat()}"
            "&$orderby=start/dateTime"
        )
        resp = requests.get(url, headers=self._headers)
        resp.raise_for_status()
        if resp.status_code != 200:
            self._logger.debug(f"Error fetching events: {resp.status_code} {resp.text}")
            return self

        events = []
        data = resp.json().get("value", [])
        for item in data:
            event = EventBase(
                summary=item.get("subject", "No Subject"),
                start=dt.datetime.fromisoformat(item["start"]["dateTime"]),
                end=dt.datetime.fromisoformat(item["end"]["dateTime"]),
                all_day=item.get("isAllDay", False) )
            if not item['isCancelled']:
                self.add(event)
        self._logger.debug(f"Retrieved {len(events)} events from MS Graph")

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
            on_click=lambda: ui.open("/outlook/authenticate"),
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
            ui.open("/")


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

if __name__ == "__main__":

    cal = CalendarOutlookMsal()

    if not cal.authenticate():
        raise Exception("MSAL Authentication to Outlook Calendar failed")

    cal.query()
    for event in cal.events:
        print(f"Event: {event.summary}, Start: {event.start}, End: {event.end}")