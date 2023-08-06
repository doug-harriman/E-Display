# E-Display Server

## Software Installation

* `sudo apt install libvips`
    * [PyVips](https://libvips.github.io/pyvips/index.html) to load and render SVG into Pillow images.
* `pip install -r requirements.txt` (in server directory)

## Configuration

* Copy `google-credentials.json` and `google-token.json` to server.
* Google Calendar
    * When token expires the token file will be deleted if it cannot be refreshed.
    * Manually run the `calendar_google.py` script.
    * Follow the link it provides & confirm access.
    * `google-token.json` will be created.

## Run

```bash
cd server
./serve.sh
```