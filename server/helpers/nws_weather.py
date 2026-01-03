# Description: Get weather forecast from National Weather Service.

# NOTE: Image processing required install of libvips
#       sudo apt install libvips

import datetime as dt
import json
import os

import dateutil.parser
from dateutil import tz

import requests
from PIL import Image, ImageDraw
import pyvips

import logging

# Logging config
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

# Other good icon sets:
# https://erikflowers.github.io/weather-icons/
# https://github.com/erikflowers/weather-icons


def ForecastUrl(lat: float, lon: float) -> str:
    """
    Returns the National Weather Service forecast URL for the provided
    latitude and longitude.

    Args:
        lat (float): Latitude
        lon (float): Longitude

    Returns:
        str: Forcast URL for api.weather.gov
    """

    # Returns JSON w/
    # gridID = json['properties']['gridID']
    # gridX = json['properties']['gridX']
    # gridY = json['properties']['gridY']
    # and a bunch of endpoints identified

    # "forecast": "https://api.weather.gov/gridpoints/PQR/115,105/forecast",
    # "forecastHourly": "https://api.weather.gov/gridpoints/PQR/115,105/forecast/hourly",
    # "forecastGridData": "https://api.weather.gov/gridpoints/PQR/115,105",
    # Hourly is the one of interest

    url = f"https://api.weather.gov/points/{LAT},{LON}"
    res = requests.get(url)

    return res.json()["properties"]["forecastHourly"]


class Weather:
    def __init__(self, lat: float = None, lon: float = None):
        self._file_config = __file__.replace(".py", ".json")

        if (lat is None) or (lon is None):
            # Try to load URL from config file.

            # Load JSON file if exists.
            # If not, get from URL and save to file.
            if not os.path.exists(self._file_config):
                raise FileNotFoundError(
                    f"Config file {self._file_config} not found & lat/lon not provided."
                )

            with open(self._file_config) as fp:
                config = json.load(fp)
        else:
            # Get URL from lat/lon
            url = ForecastUrl(lat, lon)
            config = {"LAT": lat, "LON": lon, "URL_FORCAST": url}
            with open(self._file_config, "w") as fp:
                json.dump(config, fp)

        self._url_forecast = config["URL_FORCAST"]
        self._dt_next_update = None

        self._forecast = None
        self._time_read_delta = dt.timedelta(minutes=5)

        # Number of forecast periods to return
        self._periods = 12

        # Set up logging
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(level=logging.DEBUG)


    @property
    def forecast(self) -> dict:
        """
        Returns the current weather forecast from the National Weather Service.

        Returns:
            dict: Dictionary of forecast hour by hour, keyed by datetime hour.
        """

        # Throttle reads
        if self._dt_next_update is not None:
            if dt.datetime.now() < self._dt_next_update:
                # Return cached weather
                return self._forecast

        # Get current weather
        resp = requests.get(self._url_forecast)
        data = resp.json()
        self._dt_next_update = dt.datetime.now() + self._time_read_delta

        # Extract forecast fields
        data = data["properties"]["periods"][0 : self._periods]

        self._forecast = {}
        for record in data:
            t = dateutil.parser.parse(record["startTime"])
            t = t.astimezone(tz.tzlocal())
            # t = t.replace(tzinfo=None)
            self._forecast[t] = {
                key: record[key]
                for key in [
                    "isDaytime",
                    "temperature",
                    "windSpeed",
                    "windDirection",
                    "shortForecast",
                    "icon",
                ]
            }

        return self._forecast

    @property
    def temperature_current(self) -> int:
        """
        Returns the current temperature in degrees F.

        Returns:
            int: Temperature in degrees F.
        """

        # Get latest forecast
        forecast = self.forecast
        now = dt.datetime.now().astimezone(tz.tzlocal())
        now = now.replace(minute=0, second=0, microsecond=0)

        return forecast[now]["temperature"]

    def Render(
        self,
        hour: dt.datetime = None,
        draw: ImageDraw = None,
        x_base: int = 0,
        y_base: int = 0,
        width: int = 100,
        height: int = 100,
    ) -> None:
        from kindle import Color, fonts, ResolutionPortrait

        # Mapping from NWS icon names to icon files
        ICON_PATH = "./icons/"
        with open(ICON_PATH + "weather-icon-map.json") as fp:
            icons = json.load(fp)

        if draw is None:
            return ValueError("Image.Draw context must be provided.")

        if hour is None:
            hour = dt.datetime.now().astimezone(tz.tzlocal())
            hour = hour.replace(minute=0, second=0, microsecond=0)

        x_pad = 5
        y_pad = 5

        # Force forecast update if needed
        if not self._forecast:
            self.forecast

        # Add temperature string to bottom of image
        fontsz = "small"
        datastr = f"{self._forecast[hour]['temperature']}°F"
        datasz = fonts[fontsz].getbbox(datastr)
        x = x_base + round((width - datasz[2]) / 2)
        y = y_base + height - datasz[3] - 3 * y_pad
        draw.text((x, y), datastr, font=fonts[fontsz], fill=Color.BLACK)

        # Icon size
        height_remaining = height - datasz[1] - y_pad
        icon_space = (width - 2 * x_pad, int(round(height_remaining)))

        # Select icon image
        # https://api.weather.gov/icons
        url = self._forecast[hour]["icon"]
        data = url.rsplit("/", 2)[-2:]
        dn = data[0]  # Day or night
        forcast_short = data[1].split(",")[0]  # forecast short name
        if "?" in forcast_short:
            forcast_short = forcast_short.split("?")[0]
        self._logger.debug(f"Forecast icon: {forcast_short}, {dn}")
        self._logger.debug(f"URL     : {url}")
        # self._logger.debug(f"Forecast: {self._forecast}")
        icon_file = icons[forcast_short][dn]

        # Load icon and scale to fit
        icon_path_svg = os.path.join(ICON_PATH, icon_file)
        icon_path_png = icon_path_svg.replace(".svg", ".png")
        icon = pyvips.Image.new_from_file(
            icon_path_svg, dpi=ResolutionPortrait.PPI, scale=1
        )

        # Determine scale factor
        icon_size = (icon.width, icon.height)
        scale_x = icon_space[0] / icon_size[0]
        scale_y = icon_space[1] / icon_size[1]
        scale = min(scale_x, scale_y) * 0.8
        logger.debug(
            f"Icon space min dim: {icon_space}, Current size: {icon_size}, Scale: {scale}"
        )
        icon = icon.resize(scale)
        icon.write_to_file(icon_path_png)
        icon_png = Image.open(icon_path_png)
        logger.debug(f"   scaled size: ({icon.width},{icon.height})")
        logger.debug(f"   png    size: ({icon_png.width},{icon_png.height})")

        x = x_base + round((width - icon_png.width) / 2)
        y = y_base + 2 * y_pad  # round((height - icon_png.height)/2)
        y = round(y)
        draw._image.paste(icon_png, (x, y), icon_png)


if __name__ == "__main__":
    # Get NWS grid info.
    # Grid Lookup
    LAT = 41
    LON = -120

    # Get current weather info
    weather = Weather(lat=LAT, lon=LON)

    print(weather.forecast)

    import dill

    with open("weather.dill", "wb") as fp:
        dill.dump(weather, fp)

    print(f"Current temperature: {weather.temperature_current}°F")
