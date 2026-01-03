import datetime as dt
import json
from pathlib import Path
import tomllib
from typing import Any, Self
from datetime import datetime, timedelta

import msal
import pexpect
import requests

from calendar_base import CalendarBase, EventBase

# TODO: Use pexect like calendar_outlook.py for authentication UI to capture URL & code.

class CalendarOutlook(CalendarBase):
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
        self.sort()

if __name__ == "__main__":

    cal = CalendarOutlook()

    if not cal.authenticate():
        raise Exception("MSAL Authentication to Outlook Calendar failed")

    cal.query()
    for event in cal.events:
        print(f"Event: {event.summary}, Start: {event.start}, End: {event.end}")