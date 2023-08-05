# plugin_manager.py
# Plugin manager.

import os
from glob import glob
import importlib
import datetime as dt
from fastapi import APIRouter
import paths
from plugin_base import PluginBase, DeviceItem
from renderer import RendererBase


class PluginManager:
    """
    Handles plugin discovery and management.
    """

    def __init__(self, dir: str = "plugins") -> None:
        # Defaults
        self.dir = dir

    @property
    def dir(self) -> str:
        """
        Returns the plugin directory.
        """
        return self._dir

    @dir.setter
    def dir(self, dir: str) -> None:
        """
        Sets the plugin directory.
        """

        if not isinstance(dir, str):
            raise TypeError("Plugin directory must be a string.")

        # Verify dir is a valid directory
        if not os.path.isdir(dir):
            raise ValueError(f"Plugin directory must be a valid directory: {dir}")

        self._dir = dir

        # Discover plugins
        self.discover()

    def discover(self) -> None:
        """
        Discovers plugins in the plugin directory.

        Sets the following properties:
        - plugins: list of plugins
        - routers: list of routers
        """

        # List of python files.
        files = glob(os.path.join(self.dir, "*.py"))
        files = [file.replace(self.dir + "/", "") for file in files]
        files = [file.replace(".py", "") for file in files]

        # Load files looking for plugins.
        self._plugins = []
        self._routers = []
        for file in files:
            mod = importlib.import_module(file)

            var_dict = vars(mod)
            for var in var_dict.keys():
                # Skip dunders
                if var.startswith("__"):
                    continue

                # Plugins.
                if isinstance(var_dict[var], PluginBase):
                    self._plugins.append(var_dict[var])

                # Routers
                if isinstance(var_dict[var], APIRouter):
                    self._routers.append(var_dict[var])

    @property
    def plugins(self) -> list:
        """
        Returns the list of PluginBase objects from plugins.

        Returns:
            list: List of PluginBase derived objects.
        """
        return self._plugins

    @property
    def routers(self) -> list:
        """
        Returns the list of routers from plugins.

        Returns:
            list: List of routers.
        """

        return self._routers

    @property
    def devices(self) -> list:
        """
        List of devices registered with PluginManager.

        Returns:
            list: Device list.
        """

        devices = []
        for plugin in self.plugins:
            if plugin.device:
                devices.append(plugin.device)

        return devices

    @property
    def menuitems(self) -> list:
        """
        Returns a sorted list of all MenuItem objects for all plugins.

        Returns:
            list: Sorted list of MenuItem objects.
        """

        menus = []
        for plugin in self.plugins:
            for menu in plugin.menuitems:
                menus.append(menu)

        def sorted_order(menu):
            return menu.sort_order

        menus.sort(key=sorted_order)

        return menus

    def device_get(self, name: str) -> DeviceItem:
        """
        Returns the device item for the device name.

        Args:
            name (str): Device name.

        Returns:
            DeviceItem: Device with given name.
        """

        if not isinstance(name, str):
            raise TypeError("Device name must be a string.")

        for device in self.devices:
            if device.text == name:
                return device

    def renderer_get(self, device: str) -> RendererBase:
        """
        Returns the renderer for the device.

        Args:
            device (str): Device name

        Returns:
            RendererBase: Renderer object
        """
        for plugin in self.plugins:
            if plugin.device:
                if plugin.device.text == device:
                    return plugin.device.renderer

        return None

    def state_post_handler_get(self, device: str) -> callable:
        """
        Returns the state post handler function for the device.

        Args:
            device (str): Device name

        Returns:
            callable: State post handler
        """
        for plugin in self.plugins:
            if plugin.device:
                if plugin.device.text == device:
                    return plugin.device.state_post_handler

        return None

    def sleep_delay_get(self, device: str) -> dt.timedelta:
        """
        Returns the sleep delay time for the device.

        Args:
            device (str): Device name

        Returns:
            datetime.timedelta: Sleep delay time.
        """
        for plugin in self.plugins:
            if plugin.device:
                if plugin.device.text == device:
                    return plugin.device.sleep_delay

        return None


if __name__ == "__main__":
    import paths

    pm = PluginManager()

    for plugin in pm.plugins:
        print(f"Plugin: {plugin.name}")
        if plugin.device:
            if plugin.device.renderer:
                print(
                    f"   Device: {plugin.device.text} -> {type(plugin.device.renderer)}"
                )
            else:
                print(f"   Device: {plugin.device.text}")

        for menu in plugin.menuitems:
            print(f"   Menu: {menu.text} -> {menu.route}")
        for tab in plugin.tabitems:
            print(f"   Tab : {tab.text} -> {tab.route}")

    print("")
    print(f"Routers [{len(pm.routers)}]:")
    for i, router in enumerate(pm.routers):
        for route in router.routes:
            print(f"   Router [{i}]: {route.path}")

    # Find specific device.
    print(pm.device_get("kitchen"))
