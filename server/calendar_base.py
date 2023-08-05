import dill
import logging
import datetime as dt
import os


# Logging config
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)


class EventBase:
    def __init__(
        self,
        summary: str = None,
        start: dt.datetime = None,
        end: dt.datetime = None,
        all_day: bool = False,
    ):
        self.summary = summary
        self._start = start
        self._end = end
        self._all_day = all_day

    def __repr__(self):
        res = f"{self.summary} "

        if self.all_day:
            # Check to see if a single day event
            if self.start.date() == self.end.date():
                res += f"{self.start.date()}"
            else:
                # Multi-day event
                res += f"from {self.start.date()} to {self.end.date()}"
        else:
            res += f"from {self.start} to {self.end}"

        return res

    @property
    def summary(self) -> str:
        return self._summary

    @summary.setter
    def summary(self, value: str):
        if not isinstance(value, str):
            raise TypeError("Summary must be a string")

        if len(value) == 0:
            raise ValueError("Summary cannot be empty")

        self._summary = value

    @property
    def start(self) -> dt.datetime:
        return self._start

    @property
    def end(self) -> dt.datetime:
        return self._end

    @property
    def duration(self) -> dt.timedelta:
        """
        Duration of event.

        Returns:
            datetime.timedelta: Time delta object representing duration of event.
        """

        return self.end - self.start

    @property
    def all_day(self) -> bool:
        return self._all_day


class CalendarBase:
    def __init__(self, test: bool = False):
        self._test = test
        self._test_file_name = self.__class__.__name__ + ".dill"
        self._test_time = None

        # Set up logging
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(level=logging.DEBUG)

        self._events = None

    def add(self, event: EventBase = None):
        """
        Add an event to the calendar.

        Returns:
            CalendarBase: Self.
        """

        if event is None:
            return

        if not isinstance(event, EventBase):
            raise TypeError("Event must be of type EventBase")

        if event.summary is None or len(event.summary) == 0:
            self._logger.warning("Event summary is empty, event not added")
            return

        if self._events is None:
            self._events = [event]
        else:
            self._events.append(event)

        return self

    def clear(self) -> None:
        """
        Clear the event list.

        Returns:
            CalendarBase: Self.
        """

        self._events = None

        return self

    @property
    def events(self) -> list:
        return self._events

    def sort(self) -> None:
        """
        Sorts events by start time.
        Events sorted in place.

        Returns:
            CalendarBase: Self.
        """

        if self._events is None:
            return

        self._events.sort(key=lambda x: x.start)

        return self

    @property
    def upcoming(self) -> list:
        """
        Processes an event list, returning a list filtered such that
        it contains only events currently in progress or occurring in the
        future.
        """

        # Null case
        if self._events is None:
            self._logger.debug("Event list is empty")
            return None

        # Local system timezone
        tz = dt.datetime.now().astimezone().tzinfo
        now = dt.datetime.now(tz=tz)

        if self._test:
            # Load event list
            with open(self._test_file_name, "rb") as file:
                self._events = dill.load(file)

            # Force current time to a specific previous time
            if self._test_time is not None:
                now = self._test_time

        # Treat current time as if it was at the start of the hour.
        now = now.replace(minute=0, second=0, microsecond=0)

        # Filter out past events
        self._events = [evt for evt in self._events if evt.end > now]

        return self._events

    def save(self):
        """
        Save the event list to disk.

        Returns:
            CalendarBase: Self.
        """

        if self._events is None:
            return

        with open(self._test_file_name, "wb") as file:
            dill.dump(self._events, file)
            self._logger.debug(f'Calendar data saved to "{self._test_file_name}"')

        return self

    def load(self) -> list:
        """
        Loads events from local file.

        Returns:
            CalendarBase: Self.
        """

        if not os.path.exists(self._test_file_name):
            events = None

        with open(self._test_file_name, "rb") as file:
            events = dill.load(file)

        self._events = events

        return self
