# **************************************************************************************
# Handling token expiration:
# 1. Delete token file `google-token.json`
# 2. Run this script
# 3. Follow the link to authenticate
# **************************************************************************************


# Google Calendar API & account authorization instructions.
# https://developers.google.com/calendar/api/quickstart/python#set_up_your_environment

from calendar_base import CalendarBase, EventBase
import datetime as dt
import os
from glob import glob
import os.path
from typing import Union
import logging
import json

from nicegui import ui, APIRouter, app

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import theme
from plugin_base import PluginBase, MenuItem

# Logging config
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)

# Hang admin routes off the root
router_googlecalendar = APIRouter(tags=["googlecalendar"])
router_googlecalendar.userdata = None

# Menu
ROUTE_GOOGLE_CALENDARS = "/googlecalendars"
mnu = MenuItem("Google Calendars", ROUTE_GOOGLE_CALENDARS)
mnu.sort_order = 40

# Plugin
plugin = PluginBase()
plugin += mnu


class CalendarGoogle(CalendarBase):
    def __init__(self, test: bool = False):
        super().__init__(test=test)

        if test:
            return

        # If modifying these scopes, delete the file token.json.
        SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
        TOKEN_FILE = "google-token.json"
        CREDENTIALS_FILE = "google-credentials.json"

        self._creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(TOKEN_FILE):
            self._creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

            # Handle credential expiry
            try:
                if self._creds and self._creds.expired and self._creds.refresh_token:
                    self._creds.refresh(Request())

                # Save the refreshed credentials to the token file
                if self._creds:
                    with open(TOKEN_FILE, "w") as token:
                        token.write(self._creds.to_json())
            except Exception as e:
                logger.warning(f"Error refreshing credentials: {e}")
                os.remove(TOKEN_FILE)

        # If there are no (valid) credentials available, let the user log in.
        if not self._creds or not self._creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            self._creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(TOKEN_FILE, "w") as token:
                token.write(self._creds.to_json())

        self._service = build("calendar", "v3", credentials=self._creds)

        # Stored data
        self._events = None
        self._calendars = None
        self._filename = "google-calendars.json"

    def events_query(
        self,
        date: dt.datetime = dt.datetime.today(),
        calendars: Union[str, list] = "primary",
    ) -> list:
        """
        Queries the online database for events on the specified date.
        All active calendars are queried.

        Args:
            date (datetime.datetime, optional): Date for which to get events.
                                                Defaults to datetime.date.today().

        Raises:
            ValueError: If no valid calendar names are provided.

        Returns:
            list: List of events.
        """

        if not isinstance(date, dt.datetime):
            raise TypeError("Date must be a datetime object")

        # Start and end times for date
        timezone = dt.datetime.now().astimezone().tzinfo
        date = dt.datetime(date.year, date.month, date.day, tzinfo=timezone)
        # print(f"Local timezone: {timezone}")
        t_start = date.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        t_end = date.replace(
            hour=23, minute=59, second=59, microsecond=999999
        ).isoformat()

        # print(f"t_start: {t_start}")
        # print(f"t_end: {t_end}")

        # Local timezone
        tz = dt.datetime.now().astimezone().tzinfo

        # Grab events for each calendar
        fm = app.string_filter_manager
        for cal_name in self._calendars:
            if self._calendars[cal_name]["active"] is False:
                continue

            events_result = (
                self._service.events()
                .list(
                    calendarId=self._calendars[cal_name]["id"],
                    timeMin=t_start,
                    timeMax=t_end,
                    singleEvents=True,
                    maxResults=9999,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])

            for event in events:
                # Determine if event is all day
                all_day = True
                start = event.get("start").get("date")
                end = event.get("end").get("date")

                # Check for non-ful day events
                if not start:
                    all_day = False
                    start = event.get("start").get("dateTime").replace("Z", "+00:00")
                    end = event.get("end").get("dateTime").replace("Z", "+00:00")

                # Convert to datetimes.
                start = dt.datetime.fromisoformat(start)
                end = dt.datetime.fromisoformat(end)

                # Convert to local timezone
                start = start.astimezone(tz)
                end = end.astimezone(tz)

                # Now, drop timezones.
                start = start.replace(tzinfo=None)
                end = end.replace(tzinfo=None)

                # If we got an all day event that's over, skip it.
                # if end < date:
                #     continue

                summary = event["summary"].strip()
                summary = fm.apply(summary)
                if len(summary) == 0:
                    continue

                evt = EventBase(
                    summary=summary,
                    start=start,
                    end=end,
                    all_day=all_day,
                )

                self.add(evt)

        self.sort()

    def calendars_query(self, merge: bool = True) -> dict:
        """
        Query Google for calendars associated with account.
        Calendar dictionary is stored in calendars property.

        Args:
            merge (bool, optional): Merge calendars with existing list. Defaults to True.

        Returns:
            dict: Calendars. Keys = calendar names, values = calendar IDs.
        """

        # List all available calendars
        calendar_list = self._service.calendarList().list().execute()

        # from pprint import pprint
        # pprint(calendar_list)

        calendars = {}
        for cal in calendar_list["items"]:
            values = {}
            values["id"] = cal["id"]

            values["active"] = False
            if "selected" in cal:
                values["active"] = True

            # Drop default Weather calendar.
            if "Weather" in cal["summary"]:
                continue

            calendars[cal["summary"]] = values

        # If we're not merging, use the values from the query
        if not merge or not self._calendars:
            self._calendars = calendars
            return self.calendars

        # Merge calendars with existing list
        # We do not expect ID's to change and we want to use our internal
        # value for 'active', so really only adding new calendars.
        for cal in calendars:
            # If new, just take the new one
            if cal not in self._calendars:
                self._calendars[cal] = calendars[cal]

        # Now we need to remove any calendars that are no longer in the list
        keys = []
        for cal in self._calendars:
            if cal not in calendars:
                keys.append(cal)
        for key in keys:
            del self._calendars[key]

        # Update saved data.
        self.to_file()

        return self.calendars

    def to_json(self) -> dict:
        """
        Returns a JSON representation of the calendar list.

        Returns:
            dict: _description_
        """

        # Convert dict to JSON string
        data = json.dumps(self.calendars)
        return data

    def from_json(self, data: str) -> None:
        """
        Loads a JSON representation of the calendar list.

        Args:
            data (str): JSON string representation of the calendar list.

        Returns:
            None: Calendars are loaded into the class.
        """

        # Convert JSON string to dict
        calendars = json.loads(data)
        self._calendars = calendars

    def to_list(self) -> list:
        """
        Returns a list of calendar data.

        Returns:
            list: List of calendar dicts.
        """

        data = []
        for key in self.calendars:
            cal = {}
            cal["name"] = key
            cal["active"] = self.calendars[key]["active"]
            cal["id"] = self.calendars[key]["id"]
            data.append(cal)
        return data

    @property
    def filename(self) -> str:
        """
        Default file name for saving calendar list.

        Returns:
            str: File name
        """

        return self._filename

    @filename.setter
    def filename(self, filename: str) -> None:
        self._filename = filename

    def to_file(self, filename: str = None) -> None:
        """
        Saves the calendar list to a file.

        Args:
            filename (str): File to save.  Defaults to self.filename
        """

        if filename is None:
            filename = self.filename

        with open(filename, "w") as file:
            json.dump(self.calendars, file, indent=2, sort_keys=True)

    def from_file(self, filename: str = None) -> None:
        """
        Loads the calendar list from a file.

        Args:
            filename (str): File to save.  Defaults to self.filename
        """

        if filename is None:
            filename = self.filename

        if not os.path.exists(filename):
            logger.warning(f"File not found: {filename}")
            return

        with open(filename, "r") as file:
            calendars = json.load(file)
            self._calendars = calendars

    @property
    def calendars(self) -> dict:
        """
        Dictionary of calendars associated with Google account.

        Returns:
            dict: Calendars. Keys = calendar names.
        """

        if self._calendars is None:
            self.calendars_query()

        return self._calendars

    def calendar_is_active(self, calendar: str) -> bool:
        """
        Returns True if calendar is active.

        Args:
            calendar (str): Calendar name

        Returns:
            bool: True if active.

        Raises:
            ValueError: If calendar is not found.
        """

        if calendar not in self.calendars.keys():
            raise ValueError(f"Calendar not found: {calendar}")

        return self.calendars[calendar]["active"]

    def calendar_active_set(self, calendar: str, active: bool) -> None:
        """
        Set calendar active state

        Args:
            calendar (str): Calendar name.
            active (bool): Active or not.

        Raises:
            ValueError: If calendar is not found.
        """

        if calendar not in self.calendars.keys():
            raise ValueError(f"Calendar not found: {calendar}")

        if active:
            self.calendars[calendar]["active"] = True
        else:
            self.calendars[calendar]["active"] = False


@router_googlecalendar.page(ROUTE_GOOGLE_CALENDARS, favicon=theme.PAGE_ICON)
def calendars_list():
    """

    Returns a list of calendars associated with the Google account.
    """
    cal = CalendarGoogle()
    cal.from_file()  # Load any stored calendar data
    cal.calendars_query()  # Update from server.
    data = cal.to_list()

    # Add common layout elements
    with theme.header():
        ui.label("Select rows to toggle display status of calendar.")

        grid = ui.aggrid(
            {
                "columnDefs": [
                    {"headerName": "Calendar", "field": "name", "sortable": "true"},
                    {
                        "headerName": "Display on Kindle",
                        "field": "active",
                        "sortable": "true",
                    },
                ],
                "rowData": data,
                "rowSelection": "single",
            }
        )  # style("height: 300px")

        async def on_click(args):
            sel = await grid.get_selected_row()

            # Toggle active state
            name = sel["name"]
            active = not cal.calendar_is_active(name)
            cal.calendar_active_set(name, active)

            # Determine current row index.
            # Do this each time a table sorting might change index.
            idx = None
            for i, row in enumerate(grid.options["rowData"]):
                if row["name"] == name:
                    idx = i
                    break

            # Update display
            grid.options["rowData"][idx]["active"] = active
            grid.update()

            # Store out data, as the render creates its own instance.
            cal.to_file()

            # Delete any existing PNG files, as they may not longer be valid.
            image_files = glob("*.png")
            for file in image_files:
                os.remove(file)

        grid.on("click", handler=on_click)


if __name__ == "__main__":
    from pprint import pprint

    cal = CalendarGoogle()
    cal.to_file()

    cals = cal.calendars
    print()
    print(f"Available calendars:")
    pprint(cals)
    print()

    # Test a specific date
    if False:
        date = dt.datetime(2023, 6, 3)

        cal.events_query(date=date)

        cal.events_sort()
        print(f"Query date: {date}")
        print(f"Event cnt: {len(cal.events)}")
        print(cal.events)
