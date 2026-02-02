# image_work_calendar.py
# Generates image for Kindle PW1 showing Outlook calendar events and weather.

# imports
import datetime as dt
import logging
from dateutil import tz

from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None  # Disable DecompressionBombError

from trmnl_7_5in import Color, fonts
from trmnl_7_5in import ResolutionPortrait as Resolution
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

        # If temperature is 99, look to see if we have a better value for the device.
        if data.temperature == 99:
            # Check for last temperature entry for device "home-office-tmp"
            data_device_tmp = db.device_latest("home-office-tmp")
            if data_device_tmp:
                data.temperature = data_device_tmp.temperature

        # Get weather info
        weather = Weather()

        # Grab latest calendar events
        # Outlook calendar is running in test mode until IT
        # provides the necessary permissions to query on demand.
        cal = CalendarOutlook()
        if not cal.authenticate():
            logger.warning("Outlook authentication failed - calendar will be empty")
        else:
            cal.query()
            logger.debug(f"Calendar query completed - events: {len(cal.events) if cal.events else 0}")

        # Create the base image
        # mode = "L"  # 8-bit grayscale.
        mode = "1"  # 1-bit pixels, black and white, stored with one pixel per byte.
        background = Color.WHITE
        self._image = Image.new(mode, (Resolution.HORIZ, Resolution.VERT), background)
        self._draw = ImageDraw.Draw(self._image)  # drawing context

        # TODO: Put resolution into constructor.

        # Add text
        x = 10
        y = 0
        y_pad = 4

        # Header
        y = self.render_header(width=Resolution.HORIZ, battery_soc=data.battery_soc)

        # Render all-day events (comma-separated, left-justified on same line as temperature)
        x = 10
        y_allday_start = y
        max_height_this_section = 0

        if cal.upcoming:
            all_day_events = [event for event in cal.upcoming if event.all_day]
            if all_day_events:
                all_day_text = ", ".join([event.summary for event in all_day_events])
                fontsz_allday = "small"

                # Calculate available width (subtract temp width and padding)
                temp_width = 0
                if data.temperature is not None:
                    fontsz = "medium_small"
                    datastr = f"{data.temperature}°F"
                    temp_width = fonts[fontsz].getbbox(datastr)[2] + 20  # temp + padding
                available_width = Resolution.HORIZ - 20 - temp_width  # 20 = left + right padding

                # Wrap text to fit
                wrapped_text = text_fill_box(
                    draw=self._draw,
                    text=all_day_text,
                    font=fonts[fontsz_allday],
                    width=available_width,
                    height=100,  # max height for all-day events
                    spacing=2,
                )

                # Render the all-day events text
                self._draw.multiline_text(
                    (x, y + y_pad),
                    wrapped_text,
                    font=fonts[fontsz_allday],
                    fill=Color.BLACK,
                    align="left",
                    spacing=2,
                )

                # Calculate height of all-day events text
                text_bbox = self._draw.multiline_textbbox(
                    (x, y + y_pad),
                    wrapped_text,
                    font=fonts[fontsz_allday],
                    spacing=2,
                )
                max_height_this_section = text_bbox[3] - text_bbox[1]

        # Device state info (temperature - right justified on same line)
        if data.temperature is not None:
            fontsz = "medium_small"

            # Field - right justified
            datastr = f"{data.temperature}°F"
            text_width = fonts[fontsz].getbbox(datastr)[2]
            x_temp = Resolution.HORIZ - text_width - 20  # 20 pixels padding from right edge
            self._draw.text(
                (x_temp, y + y_pad), datastr, font=fonts[fontsz], fill=Color.BLACK
            )

            temp_height = fonts[fontsz].getbbox(datastr)[3]
            max_height_this_section = max(max_height_this_section, temp_height)

        # Update y position based on the taller of the two elements
        if max_height_this_section > 0:
            y += max_height_this_section + y_pad

        # Add upcoming stuff
        y += y_pad * 2

        # Filter out all-day events before passing to TimeGrid
        cal_timed = CalendarOutlook()
        if cal.upcoming:
            for event in cal.upcoming:
                if not event.all_day:
                    cal_timed.add(event)

        bottom_margin = 4
        TimeGrid(
            draw=self._draw,
            weather=weather,
            calendar=cal_timed,
            timeframe_hours=7,
            x_base=0,
            y_base=y,
            width=Resolution.HORIZ,
            height=Resolution.VERT - y - fonts[fontsz].getbbox("X")[3] - bottom_margin,
        )

        # Footer
        if not data.ipaddr:
            data.ipaddr = "(not connected)"
        self.render_footer(
            device=device,
            width=Resolution.HORIZ,
            y=Resolution.VERT - fonts[fontsz].getbbox("X")[3] - bottom_margin + y_pad,
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
        draw.line((x_base + x_pad, y, x_base + width - x_pad, y),
                  fill=Color.BLACK
                #   fill=Color.GRAY_MID
                  )

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
        draw.line((x_offset, y_mid, x_weather, y_mid),
                  fill=Color.BLACK
                #   fill=Color.GRAY_LIGHT
                  )

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
    draw.line((x_base + x_pad, y, x_base + width - x_pad, y),
              fill=Color.BLACK
            #   fill=Color.GRAY_MID
              )

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
                # fill=Color.GRAY_FAINT,
                # outline=Color.GRAY_MID,
                fill=Color.WHITE,
                outline=Color.BLACK,
            )

            # Add 45-degree diagonal hatching to indicate busy time
            hatch_spacing = 8  # pixels between diagonal lines
            box_width = (x_weather - x_pad * 2) - x_event
            box_height = y_end - y_start

            # Draw diagonal lines from top-left to bottom-right
            # Start from the left edge and move right
            for offset in range(-box_height, box_width, hatch_spacing):
                # Calculate line start and end points
                x1 = x_event + offset
                y1 = y_start
                x2 = x_event + offset + box_height
                y2 = y_end

                # Clip to box boundaries
                if x1 < x_event:
                    y1 = y_start + (x_event - x1)
                    x1 = x_event
                if x2 > x_weather - x_pad * 2:
                    y2 = y_end - (x2 - (x_weather - x_pad * 2))
                    x2 = x_weather - x_pad * 2

                # Draw the diagonal line
                draw.line((x1, y1, x2, y2), fill=Color.BLACK, width=1)

        # Draw the subject
        text = text_fill_box(
            draw=draw,
            text=event.summary,
            font=fonts[fontsz],
            width=(x_weather - x_event) - 4 * x_pad,
            height=(y_end - y_start) - y_pad / 2,
            spacing=2,
        )

        # Draw white background behind text to cover hatching
        text_x = x_event + x_pad
        text_y = y_start + 1
        text_bbox = draw.multiline_textbbox(
            (text_x, text_y),
            text,
            font=fonts[fontsz],
            spacing=2,
        )
        # Add small padding around text
        text_padding = 2
        draw.rectangle(
            (text_bbox[0] - text_padding, text_bbox[1] - text_padding,
             text_bbox[2] + text_padding, text_bbox[3] + text_padding),
            fill=Color.WHITE,
        )

        draw.multiline_text(
            (text_x, text_y),
            text,
            font=fonts[fontsz],
            fill=Color.BLACK,
            align="left",
            spacing=2,
        )
