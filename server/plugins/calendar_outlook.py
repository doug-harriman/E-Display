# outlook_calendar.py

# Registration per:
# https://pietrowicz-eric.medium.com/how-to-read-microsoft-outlook-calendars-with-python-bdf257132318
# Note: App must be created as multi-tennet, not single-tennet

# App registration name: Kindle-Calendar

import datetime as dt
import pexpect

from O365 import Account, MSGraphProtocol, FileSystemTokenBackend

from fastapi import Form, status
from fastapi.responses import RedirectResponse

from nicegui import APIRouter, ui, app

from calendar_base import CalendarBase, EventBase
import theme
from plugin_base import PluginBase, TabItem

# Hang admin routes off the root
router_outlook = APIRouter(tags=["outlook"])
router_outlook.userdata = None

# Tab
tab = TabItem("Outlook", "/outlook")
tab.tooltip = "Read Outlook calendar data"

# Plugin
plugin = PluginBase()
plugin += tab


class CalendarOutlook(CalendarBase):
    def __init__(self, test: bool = False):
        super().__init__(test=test)

    @property
    def account(self) -> Account:
        """
        O365 Outlook Calendar Read Account object.
        """

        # Set up for login
        protocol = MSGraphProtocol()
        from ms_credentials import credentials

        token_backend = FileSystemTokenBackend(
            token_path="./", token_filename="o365_token.txt"
        )

        self._account = Account(
            credentials, protocol=protocol, token_backend=token_backend
        )

        return self._account

    def authenticate(self) -> None:
        """
        Authenticate with O365 server.
        """

        scopes = ["Calendars.Read", "offline_access"]

        if self.account.authenticate(scopes=scopes):
            self._logger.debug("O365 authenticated successful")
            self._authenticated = True
        else:
            self._logger.debug("O365 authentication failed")
            self._authenticated = False

        if not self._authenticated:
            self._logger.debug("Event query failed, not authenticated")

    def query(self, date: dt.datetime = None) -> list:
        """
        Queries the online database for events on the specified date.

        Args:
            date (datetime.datetime, optional): Date of events. Defaults to dt.date.today().

        Returns:
            list: List of events on date of interest.
        """

        if date is None:
            # Use today's date as the default
            date = dt.date.today()

        self._logger.debug(f"Querying events for: {date}")

        # Get default calendar
        schedule = self.account.schedule()
        calendar = schedule.get_default_calendar()

        # Query for events on date of interest
        q = calendar.new_query("start").greater_equal(date)
        q.chain("and").on_attribute("end").less(date + dt.timedelta(days=1))
        evts = calendar.get_events(query=q, include_recurring=True)

        # Convert to list from generator
        events_outlook = list(evts)
        fm = app.string_filter_manager
        for event in events_outlook:
            # Skip all day events
            if event.is_all_day:
                continue

            summary = event.subject
            summary = fm.apply(summary)
            if len(summary) == 0:
                continue

            e = EventBase(
                summary=summary,
                start=event.start,
                end=event.end,
                all_day=event.is_all_day,
            )

            self.add(e)

        self.sort()
        self.save()

        self._logger.debug(f"Events: {self._events}")

        return self


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
    cal = CalendarOutlook()
    cal.authenticate()
    events = cal.query()
