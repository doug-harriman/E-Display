from plugin_base import PluginBase, DeviceItem
from renderer_calendar_outlook import RendererCalendarOutlook
from device_sleep_workweek import delay_get
from mqtt import state_post_handler

# Device registration
device = DeviceItem("home-office")
device.renderer = RendererCalendarOutlook()
device.sleep_delay_fcn = delay_get
device.state_post_handler = state_post_handler

plugin = PluginBase()
plugin += device
