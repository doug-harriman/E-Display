# trmnl_7_5in.py  Constants related to Seeed Studio 7.5in e-ink terminal.
# https://www.seeedstudio.com/XIAO-ePaper-EE04-DIY-Bundle-Kit.html

import os
from enum import IntEnum
from PIL import ImageFont


class ResolutionPortrait(IntEnum):
    # Kindle screen resolution, Paper White 1
    HORIZ = 480
    VERT = 800
    PPI = 110


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

# https://font.download/font/lucida-sans#google_vignette
FILE_FONT_REG = "LSANS.TTF"
FILE_FONT_BOLD = "LSANSD.TTF"
path_font_reg = os.path.join(os.curdir, DIR_FONT, FILE_FONT_REG)
path_font_bold = os.path.join(os.curdir, DIR_FONT, FILE_FONT_BOLD)
fonts = {}
fonts["large"] = ImageFont.truetype(path_font_reg, 32) #64)
fonts["medium"] = ImageFont.truetype(path_font_reg, 24) #48)
fonts["medium_small"] = ImageFont.truetype(path_font_reg, 18) #36)
fonts["small"] = ImageFont.truetype(path_font_bold, 14) #23)
fonts["tiny"] = ImageFont.truetype(path_font_reg, 9) #18)

