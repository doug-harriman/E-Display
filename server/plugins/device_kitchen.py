from plugin_base import PluginBase, DeviceItem
from renderer_calendar_google import RendererCalendarGoogle
from mqtt import state_post_handler

# Device registration
# Uses default sleep delay of 1 hour.
device = DeviceItem("kitchen")
device.renderer = RendererCalendarGoogle()
device.state_post_handler = state_post_handler

plugin = PluginBase()
plugin += device
