# kindle.py  Constants related to Kindle device.

import os
from enum import IntEnum
from PIL import ImageFont


class ResolutionPortrait(IntEnum):
    # Kindle screen resolution, Paper White 1
    HORIZ = 480
    VERT = 800
    PPI = 123


class ResolutionLandscape(IntEnum):
    HORIZ = ResolutionPortrait.VERT
    VERT = ResolutionPortrait.HORIZ
    PPI = ResolutionPortrait.PPI


class Color(IntEnum):
    # Image color names
    BLACK = 0
    WHITE = 255


# Fonts
DIR_FONT = "Fonts"

# https://www.fontsquirrel.com/fonts/aileron
FILE_FONT = "Aileron-Regular.otf"

# Load font(s)
path_font = os.path.join(os.curdir, DIR_FONT, FILE_FONT)
print(f"Loading font: {path_font}")
fonts = {}
fonts["large"] = ImageFont.FreeTypeFont(path_font, 32) #64)
fonts["medium"] = ImageFont.FreeTypeFont(path_font, 24) #48)
fonts["medium_small"] = ImageFont.FreeTypeFont(path_font, 18) #36)
fonts["small"] = ImageFont.FreeTypeFont(path_font, 11) #23)
fonts["tiny"] = ImageFont.FreeTypeFont(path_font, 9) #18)


# path_font = "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf"
# fonts = {}
# fonts["large"] = ImageFont.truetype(path_font, 32) #64)
# fonts["medium"] = ImageFont.truetype(path_font, 24) #48)
# fonts["medium_small"] = ImageFont.truetype(path_font, 18) #36)
# fonts["small"] = ImageFont.truetype(path_font, 11) #23)
# fonts["tiny"] = ImageFont.truetype(path_font, 9) #18)