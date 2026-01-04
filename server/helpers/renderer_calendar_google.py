# image_home_calendar.py

# TODO: Make today like work calendar, full left col w/weather.

import datetime as dt
import logging

# from nws_weather import Weather
from calendar_google import CalendarGoogle
from db import DB, DeviceState

from kindle import Color, fonts, ResolutionLandscape
from renderer import RendererBase, text_fill_box
from PIL import Image, ImageDraw, ImageFont

CALENDARS = [
    "primary",
    "Family",
    "Portland Timbers",
    "Portland Timbers Thorns FC",
    "USMNT",
    "MACHO KICK - Spring 2023",
    "PCU 05/06 Boys",
]

# Logging config
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


class RendererCalendarGoogle(RendererBase):
    def __init__(self, name: str = None):
        super().__init__(name=name)

    def render(self, device: str, filename: str):
        """
        Renders an image for the device.
        """

        # Create the new, base image, landscape
        mode = "L"  # 8-bit grayscale.
        background = Color.WHITE
        self._image = Image.new(
            mode, (ResolutionLandscape.HORIZ, ResolutionLandscape.VERT), background
        )

        self._draw = ImageDraw.Draw(self._image)  # drawing context
        self._image_needs_rotation = True

        # Get device info.
        db = DB()
        if device in db.devices:
            data = db.device_latest(device)
        else:
            # Default data since none pushed to server yet.
            data = {"battery_soc": 101, "temperature": 99, "ipaddr": "000.000.0.000"}
            data = DeviceState(**data)
            db.store(data)

        # Get weather info
        # weather = Weather()

        # Grab latest calendar events
        # Outlook calendar is running in test mode until IT
        # provides the necessary permissions to query on demand.
        cal = CalendarGoogle()
        cal.from_file()  # Load calendar active data.
        today = dt.datetime.today()
        today = dt.datetime(today.year, today.month, today.day)
        logger.debug(f"Today: {today}")

        # Add text
        x = 10
        y = 0
        x_pad = 5
        y_pad = 4

        # Header
        y = self.render_header(
            width=ResolutionLandscape.HORIZ, battery_soc=data.battery_soc
        )

        # List events for next several days.
        n_days = 7
        days = [today + dt.timedelta(days=i) for i in range(n_days)]
        col_width = 260
        row_height = 100
        y_day = y
        for i, day in enumerate(days):
            # Day header
            fontsz = "medium_small"
            if i == 0:
                day_str = "Today"
            else:
                day_str = day.strftime("%A")

            # Second row.
            if i == 4:
                x = 10 + col_width
                y_day = ResolutionLandscape.VERT // 2

            self._draw.text((x, y_day), day_str, font=fonts[fontsz], fill=Color.BLACK)
            y = y_day + fonts[fontsz].getbbox(day_str)[3] + y_pad

            # Event list
            # Events for the day
            cal.clear()
            cal.events_query(date=day)

            events = cal.events
            fontsz = "tiny"
            if not events:
                self._draw.text(
                    (x, y), "No Events", font=fonts[fontsz], fill=Color.BLACK
                )
            else:
                first_non_all_day = True
                for event in events:
                    if event.all_day:
                        text = event.summary

                        # Add in box
                        sz_text = fonts[fontsz].getbbox(text)
                        self._draw.rounded_rectangle(
                            (
                                x - x_pad,
                                y - y_pad / 2,
                                x + sz_text[2] + x_pad,
                                y + sz_text[3] + y_pad,
                            ),
                            radius=5,
                            fill=Color.GRAY_MID_DARK,
                            outline=Color.WHITE,
                        )

                        # Left justified in column
                        text = text_fill_box(
                            self._draw,
                            text,
                            font=fonts[fontsz],
                            width=col_width - x_pad,
                            height=row_height,
                        )

                        self._draw.text(
                            (x, y), text, font=fonts[fontsz], fill=Color.WHITE
                        )
                        y += sz_text[3] + y_pad

                    else:
                        if first_non_all_day:
                            first_non_all_day = False
                            y += y_pad

                        # Row with start and end times
                        text = f"{event.start.strftime('%-I:%M %p')} - "
                        text += f"{event.end.strftime('%-I:%M %p')}"
                        self._draw.text(
                            (x, y), text, font=fonts[fontsz], fill=Color.BLACK
                        )
                        y += fonts[fontsz].getbbox(text)[3] + y_pad

                        # Inset summary
                        text = f"{event.summary}"
                        inset = 20

                        # Stay way from right edge
                        width = col_width - inset - 2 * x_pad
                        x_right = x + width

                        if x_right >= ResolutionLandscape.HORIZ - inset:
                            width = ResolutionLandscape.HORIZ - x - inset - x_pad

                        text = text_fill_box(
                            self._draw,
                            text,
                            font=fonts[fontsz],
                            width=width,
                            height=row_height,
                        )

                        self._draw.text(
                            (x + inset, y), text, font=fonts[fontsz], fill=Color.BLACK
                        )

                        def multiline_textsz(text: str, font: ImageFont.FreeTypeFont):
                            sz = self._draw.multiline_textbbox((0, 0), text, font=font)
                            return (sz[2] - sz[0], sz[3] - sz[1])

                        y += multiline_textsz(text, font=fonts[fontsz])[1] + y_pad

                    y += y_pad

            # Next column x
            x += col_width

        # -------------------------------------------------------------
        # Footer
        # -------------------------------------------------------------
        # Update Status & Device Name
        self.render_footer(
            device=device,
            width=ResolutionLandscape.HORIZ,
            y=ResolutionLandscape.VERT - fonts[fontsz].getbbox("X")[3] - 4 * y_pad,
            device_ip=data.ipaddr,
        )

        # The Kindle eips binary paints the screen in letter format by default.
        # Rotate the image into that format.
        self._image = self._image.rotate(90, expand=True)

        # Generate PNG
        self._image.save(filename, "PNG")


if __name__ == "__main__":
    renderer = RendererCalendarGoogle()
    renderer.render()
