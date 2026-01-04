# renderer.py
# Class and tools for rendering images for remote display with PIL.

# imports
import datetime as dt
import logging
import os

import pyvips
from PIL import Image, ImageDraw, ImageFont

# from kindle import Color, ResolutionPortrait, fonts
from trmnl_7_5in import Color, ResolutionPortrait, fonts

# Logging config
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)

# Battery icon path
ICON_PATH = "./icons/"


class RendererBase:
    """
    Base class for display image renderer.
    """

    def __init__(self, name: str = None):
        self._image = None
        self._draw = None
        self._font = None

    def render(self, device: str, filename: str):
        """
        Renders the image.
        """

        # Note, if you need the device name, it is in the renederer.name field.
        raise RuntimeError("Base class render called.")

    def render_battery(self, battery_soc: int = 100, position: tuple = (0, 0)) -> None:
        """
        Renders battery state of charge icon and text.

        Args:
            battery_soc (int, optional): Battery state of charge %. Defaults to 100.

        Returns: None
        """

        # Determine battery icon to use.
        if battery_soc is None:
            icon_file = "ic_battery_unknown_48px.svg"
        elif battery_soc <= 10:
            icon_file = "ic_battery_alert_48px.svg"
        elif battery_soc <= 25:
            icon_file = "ic_battery_20_48px.svg"
        elif battery_soc <= 37:
            icon_file = "ic_battery_30_48px.svg"
        elif battery_soc <= 55:
            icon_file = "ic_battery_50_48px.svg"
        elif battery_soc <= 65:
            icon_file = "ic_battery_60_48px.svg"
        elif battery_soc <= 82:
            icon_file = "ic_battery_80_48px.svg"
        elif battery_soc <= 95:
            icon_file = "ic_battery_90_48px.svg"
        else:
            icon_file = "ic_battery_full_48px.svg"

        # Load icon
        icon_path_svg = os.path.join(ICON_PATH, icon_file)
        icon_path_png = icon_path_svg.replace(".svg", ".png")
        icon = pyvips.Image.new_from_file(
            icon_path_svg,
            dpi=ResolutionPortrait.PPI,
            scale=0.5
        )
        # Resize icon
        icon = icon.rotate(270)  # Ensure correct orientation
        icon.write_to_file(icon_path_png)
        icon_png = Image.open(icon_path_png)

        # Render icon
        icon_height = 48
        self._draw._image.paste(icon_png, position, icon_png)

        # Battery percentage text
        fontsz = "tiny"
        x_status_field = position[0] #+ 5
        y_status = position[1] + icon_height - 10

        # Center up the battery value
        self._draw.text(
            (x_status_field, y_status),
            f"{battery_soc}%",
            font=fonts[fontsz],
            # fill=Color.GRAY_DARK,
            fill=Color.BLACK,
        )

    def render_header(
        self,
        width: int = ResolutionPortrait.HORIZ,
        battery_soc: int = 99,
    ) -> int:
        x = 10
        y = 0
        y_pad = 4

        # Date
        today = dt.datetime.today()

        # Header
        day_str = f"{today.strftime('%A')}, {today.strftime('%B %-d')}"
        logger.debug(f"Day string: {day_str}")
        fontsz = "large"
        self._draw.text((x, y), day_str, font=fonts[fontsz], fill=Color.BLACK)

        y += fonts[fontsz].getbbox(day_str)[3] + y_pad

        # Battery status
        pos = (width - 48, 8)
        self.render_battery(battery_soc=battery_soc, position=pos)

        # Separator line
        self._draw.line((x, y, width - 2 * x, y),
                        # fill=Color.GRAY_MID
                        fill=Color.BLACK
                        )
        y += y_pad

        return y

    def render_footer(
        self,
        device: str = None,
        y: int = None,
        width: int = ResolutionPortrait.HORIZ,
        device_ip: str = None,
    ) -> int:
        # Configure footer
        fontsz = "tiny"
        x_pad = 5
        y_pad = 4

        if y is None:
            y = ResolutionPortrait.VERT - fonts[fontsz].getsize("X")[1] - 4 * y_pad

        # Update Status & Device Name
        x_status_field = 15
        now = dt.datetime.now()
        time_str = f'{now.strftime("%-I:%M %p")}'
        update_str = "Updated: " + time_str
        self._draw.text(
            (x_status_field, y),
            update_str,
            font=fonts[fontsz],
            # fill=Color.GRAY_DARK,
            fill=Color.BLACK,
        )

        # Device IP field
        sz = fonts[fontsz].getbbox(device_ip)
        x_device_ip = round(width - sz[2]) / 2
        self._draw.text(
            (x_device_ip, y),
            device_ip,
            font=fonts[fontsz],
            # fill=Color.GRAY_LIGHT,
            fill=Color.BLACK,
        )

        # Device Name field
        device_field = f"Device Name: {device}"
        x_device_field = width
        x_device_field -= fonts[fontsz].getbbox(device_field)[2]
        x_device_field -= 4 * x_pad
        self._draw.text(
            (x_device_field, y),
            device_field,
            font=fonts[fontsz],
            # fill.Color.GRAY_DARK,
            fill=Color.BLACK,
        )


# ------------------------------------------------------------
# Tools
# ------------------------------------------------------------


def test_text() -> str:
    """
    Returns a string of test text for text_fill_box.
    """

    text = """Lorem ipsum dolor sit amet, consectetur
              adipiscing elit, sed do eiusmod tempor incididunt ut
              labore et dolore magna aliqua. Ut enim ad minim veniam,
              quis nostrud exercitation ullamco laboris nisi ut aliquip
              ex ea commodo consequat. Duis aute irure dolor in
              reprehenderit in voluptate velit esse cillum dolore eu
              fugiat nulla pariatur. Excepteur sint occaecat cupidatat
              non proident, sunt in culpa qui officia deserunt mollit
              anim id est laborum."""
    text = " ".join(text.split())

    return text


def text_fill_box(
    draw: ImageDraw = None,
    text: str = "",
    font: ImageFont.FreeTypeFont = None,
    width: int = 100,
    height: int = 50,
    spacing: int = 2,
):
    """
    Fills a box with left justified text, wrapping and truncating as necessary.
    Will write a minimum of 1 line and 1 word.
    All size information in image pixels.

    Args:
        draw (ImageDraw): Image drawing context.
        text (str): _description_. Defaults to ''.
        font (ImageFont.FreeTypeFont): Font object for text rendering. Defaults to None.
        width (int, optional): Box width. Defaults to 100.
        height (int, optional): Box height. Defaults to 50.
        spacing (int): Spacing between lines. Defaults to 2.
    """

    if draw is None or not isinstance(draw, ImageDraw.ImageDraw):
        raise ValueError("draw parameter must be of type ImageDraw")

    if font is None or not isinstance(font, ImageFont.FreeTypeFont):
        raise ValueError("font parameter must be of type ImageFont.FreeTypeFont")

    words = text.split()
    word_cnt_total = len(words)
    word_cnt_cur = 0
    line_cnt = 1
    fit_text = ""

    logger.debug(f"Box size: {width}x{height}")

    def multiline_textsz(text: str, font: ImageFont.FreeTypeFont, spacing: int):
        sz = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing)
        return (sz[2] - sz[0], sz[3] - sz[1])

    while word_cnt_cur < word_cnt_total:
        # Try to add words to this line.
        first_word_of_line = True
        # while draw.multiline_textsize(fit_text, font=font, spacing=spacing)[0] <= width:
        while multiline_textsz(fit_text, font=font, spacing=spacing)[0] <= width:
            if first_word_of_line:
                fit_text += words[word_cnt_cur]
                first_word_of_line = False
            else:
                fit_text += " " + words[word_cnt_cur]

            word_cnt_cur += 1

            logger.debug("")
            logger.debug(f"Fit text:|{fit_text}|")
            logger.debug(f"Word count: {word_cnt_cur}:{word_cnt_total}")
            logger.debug(
                f"Word add sz: {multiline_textsz(fit_text, font=font, spacing=spacing)}"
            )

            # If we added all the words, we're done.
            if word_cnt_cur == word_cnt_total:
                if multiline_textsz(fit_text, font=font, spacing=spacing)[0] <= width:
                    return fit_text

        # Drop the last word added & add a newline
        fit_text = fit_text.rsplit(" ", 1)[0]
        word_cnt_cur -= 1

        logger.debug(f"   Box size: {width}x{height}")
        logger.debug(
            f"   Accepted Line:{multiline_textsz(fit_text, font=font, spacing=spacing)} |{fit_text}|"
        )
        logger.debug(f"   Word count: {word_cnt_cur}:{word_cnt_total}")

        fit_text += "\n"
        line_cnt += 1

        if multiline_textsz(fit_text, font=font, spacing=spacing)[0] > width:
            raise ValueError("Text too long for box width.")

        # If we've exceeded the height, we're done.
        # print(
        #     f'Line add sz: {draw.multiline_textsize(fit_text, font=font, spacing=spacing)}')
        if multiline_textsz(fit_text, font=font, spacing=spacing)[1] > height:
            break

    return fit_text
