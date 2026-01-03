# image_work_calendar.py
# Generates image for Kindle PW1 showing Outlook calendar events and weather.

# imports
import datetime as dt
import logging
from dateutil import tz

from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None  # Disable DecompressionBombError

from kindle import Color, fonts
from kindle import ResolutionPortrait as Resolution
from nws_weather import Weather
from db import DB, DeviceState
from renderer import RendererBase, text_fill_box

from calendar_outlook_msal import CalendarOutlook

# Logging config
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)

# Development/debugging
DEBUG = False
if DEBUG:
    tz = dt.datetime.now().astimezone().tzinfo
    DEBUG_NOW = dt.datetime(2023, 5, 23, 9, 47, 0, tzinfo=tz)


class RendererCalendarOutlook(RendererBase):
    def __init__(self, name: str = None):
        super().__init__(name=name)

    def render(self, device: str, filename: str):
        """
        Renders an image for the device.
        """

        # Get device info.
        db = DB()
        if device in db.devices:
            data = db.device_latest(device)
        else:
            # Default data since none pushed to server yet.
            data = {"battery_soc": 101, "temperature": 99, "ipaddr": "000.000.0.000"}
            data = DeviceState(**data)

        # Get weather info
        weather = Weather()

        # Grab latest calendar events
        # Outlook calendar is running in test mode until IT
        # provides the necessary permissions to query on demand.
        cal = CalendarOutlook()
        cal.authenticate()
        # cal.events_load()
        cal.query()

        # Create the base image
        mode = "L"  # 8-bit grayscale.
        background = Color.WHITE
        self._image = Image.new(mode, (Resolution.HORIZ, Resolution.VERT), background)
        self._draw = ImageDraw.Draw(self._image)  # drawing context

        # TODO: Put resolution into constructor.

        # Add text
        x = 10
        y = 0
        x_pad = 5
        y_pad = 4

        # Header
        y = self.render_header(width=Resolution.HORIZ, battery_soc=data.battery_soc)

        # Kindle state info
        x = 10
        if data.temperature is not None:
            fontsz = "medium_small"

            # Field
            datastr = f"Inside {data.temperature}°F"
            self._draw.text(
                (x, y + y_pad), datastr, font=fonts[fontsz], fill=Color.BLACK
            )

            y += fonts[fontsz].getbbox(datastr)[3] + y_pad

        # Add upcoming stuff
        y += y_pad * 4
        TimeGrid(
            draw=self._draw,
            weather=weather,
            calendar=cal,
            timeframe_hours=7,
            x_base=0,
            y_base=y,
            width=Resolution.HORIZ,
            height=Resolution.VERT - y - fonts[fontsz].getbbox("X")[3],
        )

        # Footer
        if not data.ipaddr:
            data.ipaddr = "(not connected)"
        self.render_footer(
            device=device,
            width=Resolution.HORIZ,
            y=Resolution.VERT - fonts[fontsz].getbbox("X")[3] + y_pad,
            device_ip=data.ipaddr,
        )

        # Generate PNG
        self._image.save(filename, "PNG")


def TimeGrid(
    draw: ImageDraw = None,
    weather: Weather = None,
    calendar: CalendarOutlook = None,
    timeframe_hours: int = 6,
    x_base: int = 0,
    y_base: int = 0,
    width: int = 100,
    height: int = 100,
) -> None:
    """
    Draws a grid of calendar events and weather conditions
    for the next few hours
    """

    # Layout constants
    x_pad = 5
    y_pad = 3
    width_weather = 100
    x_weather = x_base + width - width_weather

    # Size the rows for hours
    row_height = height / timeframe_hours

    # Draw the grid
    y = y_base
    fontsz = "small"
    tz = dt.datetime.now().astimezone().tzinfo
    now = dt.datetime.now(tz=tz)
    if DEBUG:
        now = DEBUG_NOW

    now = now.replace(minute=0, second=0, microsecond=0)
    for i in range(timeframe_hours):
        # Top Line
        draw.line((x_base + x_pad, y, x_base + width - x_pad, y), fill=Color.GRAY_MID)

        # Hour string
        hour = now + dt.timedelta(hours=i)
        hour_str = hour.strftime("%-I %p")
        draw.text(
            (x_base + 3 * x_pad, y + y_pad),
            hour_str,
            font=fonts[fontsz],
            fill=Color.BLACK,
        )
        x_offset = fonts[fontsz].getbbox(hour_str)[2] + 2 * x_pad

        # Mid line
        y_mid = y + row_height / 2
        draw.line((x_offset, y_mid, x_weather, y_mid), fill=Color.GRAY_LIGHT)

        # Weather forecast
        if weather is not None and not DEBUG:
            weather.Render(
                draw=draw,
                hour=hour,
                x_base=x_weather,
                y_base=y,
                width=width_weather,
                height=row_height,
            )

        y += row_height

    # Bottom line
    draw.line((x_base + x_pad, y, x_base + width - x_pad, y), fill=Color.GRAY_MID)

    # Draw in events
    if calendar.upcoming is None:
        logger.debug("--- Event list empty ---")
        return

    timeframe_seconds = timeframe_hours * 60 * 60
    y_pixels = height - 2 * y_pad
    x_event = x_offset + 30
    for event in calendar.upcoming:
        start = event.start.astimezone(tz) - now
        end = event.end.astimezone(tz) - now

        # Handle in-progress events
        if start.days < 0:
            start = dt.timedelta(seconds=0)

        logger.debug(f"Event: {event.summary} ")
        logger.debug(f"   times: {start} {end}")
        logger.debug(f"     sec: {start.seconds} {end.seconds}")

        # Determine rectangle y position based on time
        # Start
        y_start = y_base + y_pixels * (start.seconds / timeframe_seconds)
        # Offset for added lines
        y_start += int(float(start.seconds) / 3600.0)
        y_start = round(y_start)

        # End
        y_end = y_base + y_pixels * (end.seconds / timeframe_seconds)
        y_end = round(y_end)

        # Apply padding
        y_start += y_pad
        y_end -= y_pad / 2
        y_start = round(y_start)
        y_end = round(y_end)

        # If event starts past end of grid, skip it
        if y_start > y_base + height:
            continue

        # If event continues past end of grid, truncate it
        y_max = y_base + height - y_pad
        y_end = min(y_end, y_max)

        # Only show rectangle if event is long enough.
        if event.duration > dt.timedelta(minutes=12):
            logger.debug(f"  x pixels: {x_event} {x_weather - x_pad*2}")
            logger.debug(f"  y pixels: {y_start} {y_end}")

            # Draw the rectangle
            draw.rounded_rectangle(
                (x_event, y_start, x_weather - x_pad * 2, y_end),
                radius=5,
                fill=Color.GRAY_FAINT,
                outline=Color.GRAY_MID,
            )

        # Draw the subject
        text = text_fill_box(
            draw=draw,
            text=event.summary,
            font=fonts[fontsz],
            width=(x_weather - x_event) - 4 * x_pad,
            height=(y_end - y_start) - y_pad / 2,
            spacing=2,
        )

        draw.multiline_text(
            (x_event + x_pad, y_start - 3),
            text,
            font=fonts[fontsz],
            fill=Color.BLACK,
            align="left",
            spacing=2,
        )
