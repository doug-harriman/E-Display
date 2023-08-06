# E-Display Server

## Software Installation

* Server software was developed on an Ubuntu system (Windows WSL2 Ubuntu 20.04).
* All softare written in Python.  Minimum recommended version is Python 3.8.
* `sudo apt install libvips`
    * [PyVips](https://libvips.github.io/pyvips/index.html) to load and render SVG into Pillow images.
* `pip install -r requirements.txt` (in server directory)

## Configuration

By default, the system supports generation of two calendars:

* Google Calendar
    * A one week view of all events in all calendars for your Google account.
* Outlook 365 Daily Calendar with weather.
    * A one day view of all events in your Outlook 365 calendar with weather forecast for the day.
    * Weather is pulled from the United States National Weather Service.  No API key is required.

### Google Calendar

* Google Calendar
    * When token expires the token file will be deleted if it cannot be refreshed.
    * Manually run the `calendar_google.py` script.
    * Follow the link it provides & confirm access.
    * `google-token.json` will be created.

* Copy `google-credentials.json` and `google-token.json` to server.

### Outlook 365 Calendar

#### National Weather Service

The NWS API requires a few bits of information to retrieve the weather forecast data.  See: https://www.weather.gov/documentation/services-web-api for details.

You'll need to determine the latitude and longitude of the location for which you'd like the forecast, as well as the URL of for the forecast, which includes the office and grid X & Y data, per the link above.  If you point a web browser at the properly configured URL, you should see the forecast data in JSON format.

The information should be stored in the file: `server/helpers/nws_weather.json`.

File format is:

```json
{
    "LAT": <LATITUDE>, 
    "LON": <LONGITUDE>, 
    "URL_FORCAST": "<URL>"
}

```

#### Outlook API

### MQTT Bridge

## Run

Once configured the server can be started.  There are a variety of ways to run the server.  I have found it simplest to start a `tmux` session, then run the server from there.  You can then simply detach from the session and leave it running.

To start the server:

```bash
cd server
./serve.sh
```