# devices.py
# Device related pages & routes

import asyncio
import datetime as dt
import logging
import traceback
import os
import glob

from db import DB, DeviceState
from fastapi import Request
from fastapi.responses import FileResponse, PlainTextResponse

from pydantic import BaseModel

from nicegui import APIRouter, ui, app
import paths

import theme
from plugin_base import PluginBase, TabItem, MenuItem


# Logger config
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)

# Device routes
router = APIRouter(tags=["devices"])


def battery_voltage_to_soc(voltage: float) -> int:
    """
    Convert battery voltage to state of charge percentage.
    Based on LiPo battery discharge curve.

    Args:
        voltage: Battery voltage in volts

    Returns:
        State of charge as percentage (0-100)
    """
    if voltage >= 3.65:
        return 100
    elif voltage >= 3.3:
        return 80
    elif voltage >= 3.2:
        return 50
    elif voltage >= 3.0:
        return 20
    else:
        return 5

ROUTE_DEVICE_DELAY_MGR = "/device_delay_manager"
ROUTE_DEVICE_MAIN_PAGE = "/"

# Tab
tab = TabItem("Devices", ROUTE_DEVICE_MAIN_PAGE)
tab.tooltip = "List of devices"

# Menu(s)
menu = MenuItem("Device Delay Manager", ROUTE_DEVICE_DELAY_MGR)
menu.sort_order = 10

# Plugin
plugin = PluginBase()
plugin += tab
plugin += menu


# State data
device_data = {}


# Function to pre-render images
async def image_render_schedule(device: str, delay: dt.timedelta):
    prefix = "*BG*:"
    logger.debug(f"{prefix} Background rendering scheduled for: {device} in {delay}")
    await asyncio.sleep(delay.total_seconds())

    logger.debug(f"{prefix} Background rendering image for: {device}")
    fn = f"image-{device}.png"

    # Get renderer
    renderer = app.plugin_manager.renderer_get(device)
    if renderer:
        renderer.render(device=device, filename=fn)
    else:
        logger.error(f"{prefix} Renderer not found for: {device}")
        return

    logger.debug(f"{prefix} Background image created for: {device}")


class StatePayload(BaseModel):
    device: str = ""
    temp: str = ""
    battery: str = ""
    battery_voltage: str = ""


@router.page(ROUTE_DEVICE_MAIN_PAGE, favicon=theme.PAGE_ICON)
async def index():
    # Pull in header & select tab header for current page
    with theme.header() as tabs:
        tabs.set_value("Devices")

        # DB holds devices that have been seen by this server.
        db = DB()
        for device in db.devices:
            data = db.device_latest(device)

            ui.markdown(f"### {device.title()}")
            t = data.time.strftime("%Y-%m-%d %H:%M:%S")
            ui.markdown(f"* Last Seen: {t}")
            ui.markdown(f"* Temperature: {data.temperature}")
            ui.markdown(f"* Battery Voltage: {data.battery_voltage} [V]")
            ui.markdown(f"* Battery SOC: {data.battery_soc}")
            ui.markdown(f"* IP Address: {data.ipaddr}")
            ui.link("Image", f"/image/{data.device}", new_tab=True)

        # Convert dict to tree
        tree = []
        for device in db.devices:
            data = db.device_latest(device)

            dev = {}
            dev["id"] = device.title()
            dev["children"] = []

            for key in data.dict():
                if key == "id":
                    continue

                child = {"id": f"{key}: {data.dict()[key]}"}
                dev["children"].append(child)

            tree.append(dev)

        # Device tree
        ui.markdown("### Device Tree")
        ui.tree(tree, label_key="id")  # , on_select=lambda e: ui.notify(e.value))

        # Clear cached images
        # TODO: Use butter to watch for files, enable/disable button accordingly: https://pypi.org/project/butter/
        logger.debug(f"Images: {glob.glob('image-*.png')}")
        ui.button("Clear Cached Images", on_click=lambda: os.system("rm image-*.png"))


# Kindle image screen
@router.get("/image/{device}")
async def get_image_for_device(device: str):
    # Generate a new image
    logger.debug(f"Retrieving image for: {device}")

    if device not in device_data.keys():
        device_data[device] = {}

    fn = f"image-{device}.png"
    # See if we have a recent image.
    # If we have an old one, delete it.
    age_max = dt.timedelta(minutes=5)
    if os.path.exists(fn):
        # Used recently cached image if we have one
        t_mod = os.path.getmtime(fn)
        t_mod = dt.datetime.fromtimestamp(t_mod)
        age = dt.datetime.now() - t_mod

        # If image is less than 5 minutes old, use it.
        if age < age_max:
            logger.debug(f"Using cached image for: {device}")
        else:
            # Delete expired image
            logger.debug(f"Deleting expired image for: {device}, age: {age}")
            os.remove(fn)

    # If we don't have an image, create one.
    if not os.path.exists(fn):
        # Draw it
        try:
            # Get renderer
            renderer = app.plugin_manager.renderer_get(device)
            if renderer:
                renderer.render(device=device, filename=fn)
            else:
                logger.error(f"Renderer not found for: {device}")
                return

            logger.debug(f"Image created for: {device}")
        except Exception as e:  # noqa: F841
            text = f"Error generating image for: {device}\n\n"
            text += traceback.format_exc()

            return PlainTextResponse(text)

    # Make sure we got a file
    if not os.path.exists(fn):
        return PlainTextResponse(f"Image for: {device} not generated.")

    # Replace "/path/to/image.png" with the actual path to your image file
    return FileResponse(fn, media_type="image/png")


# Return plain text with delay time
@router.get("/delay/{device}", response_class=PlainTextResponse)
async def get_delay_to_next_wake_time_for_device(device: str):
    logger.debug("Get delay called")
    logger.debug(f"Device: {device}")

    # Get the delay time for this device
    delay_update = app.plugin_manager.sleep_delay_get(device)
    if not delay_update:
        logger.error(f"Sleep delay not found for: {device}")
        return "0"

    # Message the delay
    now = dt.datetime.now()
    logger.debug(f"Current time     : {now}")
    logger.debug(f"Next update delay: {delay_update}")

    # Schedule an image pre-render
    timer_render_ahead = dt.timedelta(minutes=1)
    delay_prerender = delay_update - timer_render_ahead
    if delay_prerender.total_seconds() > 0:
        # If we'd get a negative delay, don't schedule a pre-render.
        asyncio.ensure_future(image_render_schedule(device, delay_prerender))

    return str(int(delay_update.total_seconds()))


@router.page(ROUTE_DEVICE_DELAY_MGR, favicon=theme.PAGE_ICON)
async def device_delay_manager():
    devices = app.plugin_manager.devices

    device_dicts = [dev.to_dict() for dev in devices]

    with theme.header():
        ui.markdown("### Device Delay Manager")

        grid = ui.aggrid(
            {
                "columnDefs": [
                    {"headerName": "Device", "field": "text", "sortable": "true"},
                    {
                        "headerName": "Delay Time",
                        "field": "sleep_delay",
                        "sortable": "true",
                    },
                    {
                        "headerName": "Delay Enabled",
                        "field": "sleep_delay_enabled",
                        "sortable": "true",
                    },
                    {
                        "headerName": "Delay Function",
                        "field": "sleep_delay_fcn",
                        "sortable": "true",
                    },
                ],
                "rowData": device_dicts,
                "rowSelection": "single",
            }
        )

        async def on_click(celldata):
            # Only handle clicks on the "Delay Enabled" column
            celldata = celldata["args"]
            if celldata["colId"] != "sleep_delay_enabled":
                return

            # Toggle device state
            device_name = celldata["data"]["text"]
            logger.debug(f"Toggling device: {device_name}")
            device = app.plugin_manager.device_get(device_name)
            device.sleep_delay_enabled = not device.sleep_delay_enabled

            # Update the grid
            row = celldata["rowIndex"]
            col = "sleep_delay_enabled"
            grid.options["rowData"][row][col] = device.sleep_delay_enabled
            grid.update()

        grid.on("cellClicked", handler=on_click)


# Allow Kindle to post state data
# Proper curl call:
# curl -X POST http://192.168.0.120:8000/state -H "Content-Type: application/json"  -d '{"temp":"72F","battery":"84%"}'  # noqa: E501
# per: https://stackoverflow.com/questions/64057445/fast-api-post-does-not-recgonize-my-parameter
@router.post("/state", status_code=200)
def post_state(payload: StatePayload = None, request: Request = None):
    logger.debug("POST called")
    logger.debug(f"Device     : {payload.device}")
    logger.debug(f"Result type: {type(payload)}")
    logger.debug(f"Result     : {payload}")
    logger.debug(f"Temperature: {payload.temp}")
    logger.debug(f"Battery SOC: {payload.battery}")
    logger.debug(f"Battery Voltage: {payload.battery_voltage}")

    # Track data in from devices.
    db = DB()

    # Calculate SoC from voltage if provided, otherwise use legacy battery field
    battery_soc = -1
    battery_voltage = -1.0

    if payload.battery_voltage:
        battery_voltage = float(payload.battery_voltage)
        battery_soc = battery_voltage_to_soc(battery_voltage)
        logger.debug(f"Calculated SoC from voltage: {battery_voltage}V -> {battery_soc}%")
    elif payload.battery:
        battery_soc = int(payload.battery.replace("%", ""))

    # Temperature handling
    temperature = 99
    if payload.temp:
        temperature = int(payload.temp.replace("F", ""))

    data = DeviceState(
        device=payload.device,
        time=dt.datetime.now(),
        temperature=temperature,
        battery_soc=battery_soc,
        battery_voltage=battery_voltage,
        ipaddr=request.client.host,
    )
    db.store(data)
    logger.debug(data)

    # Call post callback handlers
    handler = app.plugin_manager.state_post_handler_get(payload.device)
    if handler:
        handler(payload)
