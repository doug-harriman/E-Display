# plugin_base.py
# Plugin base class.

from __future__ import annotations
import inspect
import logging
import datetime as dt

from nicegui import ui
from typing import Union

import paths
from renderer import RendererBase
from db import DB, DeviceState

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)


class ItemBase:
    def __init__(self, text: str, route: str, sort_order: int = 1000):
        self.text = text
        self.route = route
        self.sort_order = sort_order

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, text: str) -> None:
        if not isinstance(text, str):
            raise TypeError("Menu text must be a string.")

        self._text = text

    @property
    def route(self) -> str:
        """
        URL route to open on click.

        Returns:
            str: URL. Can be relative.
        """

        return self._route

    @route.setter
    def route(self, route: str) -> None:
        """
        URL route to open on click.

        Args:
            route (str): URL. Can be relative.
        """

        if route is None:
            self._route = None
            return

        if not isinstance(route, str):
            raise TypeError("Route must be a string.")

        self._route = route

    @property
    def sort_order(self) -> int:
        """
        Sort order value for item.
        Items will be sorted from low to high based on this value.

        Returns:
            int: Sort order value.
        """

        return self._sort_order

    @sort_order.setter
    def sort_order(self, value: int) -> None:
        """
        Sort order value for item.
        Items will be sorted from low to high based on this value.

        Args:
            value (int): Sort order value.
        """

        if not isinstance(value, int):
            raise TypeError(f"Sort order must be an integer: {type(value)}")

        self._sort_order = value


class MenuItem(ItemBase):
    def __init__(self, text: str, route: str):
        super().__init__(text, route)

    def to_menu_item(self) -> ui.menu_item:
        """
        Returns a MenuItem as a NiceGUI ui.menu_item.
        """

        return ui.menu_item(self.text, on_click=lambda: ui.navigate.to(self.route))


class TabItem(ItemBase):
    def __init__(self, text: str, route: str, tooltip: str = None):
        super().__init__(text, route)

        self.tooltip = tooltip

    @property
    def tooltip(self) -> str:
        return self._tooltip

    @tooltip.setter
    def tooltip(self, text: str) -> None:
        if text is None:
            self._tooltip = None
            return

        if not isinstance(text, str):
            raise TypeError("Tooltip text must be a string.")

        self._tooltip = text

    def to_tab(self) -> ui.tab:
        tab = ui.tab(self.text).on("click", lambda: ui.navigate.to(self.route))

        if self.tooltip is not None:
            tab.tooltip(self.tooltip)

        return tab


class DeviceItem(ItemBase):
    def __init__(self, name: str = "Default"):
        super().__init__(name, route=None)

        self._renderer = None
        self._state_post_handler = None

        self._sleep_delay_enabled = True
        self._sleep_delay = dt.timedelta(hours=1)
        self._sleep_delay_fcn = None

        self._name = name

        # If no DB entry for this device, add one.
        # Get device info.
        db = DB()
        if name not in db.devices:
            # Default data since none pushed to server yet.
            data = {"device": name, "battery_soc": 101, "temperature": 99, "ipaddr": "000.000.0.000"}
            data = DeviceState(**data)
            db.store(data)

    def to_dict(self):
        fcn = self.sleep_delay_fcn
        if fcn:
            fcn = f"{fcn.__module__}.{fcn.__name__}"
        else:
            fcn = str(fcn)

        return {
            "text": self.text,
            "route": self.route,
            "sleep_delay_enabled": self.sleep_delay_enabled,
            "sleep_delay": int(self.sleep_delay.total_seconds()),
            "sleep_delay_fcn": fcn,
        }

    @property
    def renderer(self) -> RendererBase:
        """
        Renderer object for device.

        Returns:
            RendererBase: Renderer object or derived class.
        """

        return self._renderer

    @renderer.setter
    def renderer(self, renderer: RendererBase) -> None:
        if renderer is None:
            self._renderer = None
            return

        if not isinstance(renderer, RendererBase):
            raise TypeError("Renderer must be a RendererBase.")

        self._renderer = renderer

    @property
    def state_post_handler(self) -> callable:
        """
        Handler function called when device posts state data.

        Handler must accept a single argument of type StatePayload

        Returns:
            callable: State data handler.
        """

        return self._state_post_handler

    @state_post_handler.setter
    def state_post_handler(self, handler: callable) -> None:
        if handler is None:
            self._state_post_handler = None
            return

        if not callable(handler):
            raise TypeError("Handler must be a callable.")

        self._state_post_handler = handler

    @property
    def sleep_delay(self) -> dt.timedelta:
        """
        Device sleep delay.

        Returns:
            datetime.timedelta: Sleep time delay.
        """

        if not self._sleep_delay_enabled:
            return dt.timedelta(seconds=0)

        if self._sleep_delay_fcn:
            return self._sleep_delay_fcn()

        return self._sleep_delay

    @sleep_delay.setter
    def sleep_delay(self, value: dt.timedelta) -> None:
        if not isinstance(value, dt.timedelta):
            raise TypeError("Sleep delay must be a datetime.timedelta object.")

        if value.total_seconds <= 0:
            raise ValueError("Sleep delay must be greater than zero.")

        self._sleep_delay = value

    @property
    def sleep_delay_enabled(self) -> bool:
        """
        Device sleep delay enabled.

        Returns:
            bool: True if enabled, False otherwise.
        """

        return self._sleep_delay_enabled

    @sleep_delay_enabled.setter
    def sleep_delay_enabled(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise TypeError("Sleep delay enabled must be a boolean.")

        self._sleep_delay_enabled = value

    @property
    def sleep_delay_fcn(self) -> callable:
        """
        Device sleep delay function.

        Function takes no arguments and returns datetime.timedelta object.

        Returns:
            callable: Sleep delay function.
        """

        return self._sleep_delay_fcn

    @sleep_delay_fcn.setter
    def sleep_delay_fcn(self, value: callable) -> None:
        if not callable(value):
            raise TypeError("Sleep delay function must be a callable.")

        # Test the function
        ret = value()
        if not isinstance(ret, dt.timedelta):
            raise TypeError("Sleep delay function must return a datetime.timedelta.")

        self._sleep_delay_fcn = value


class PluginBase:
    """
    Base class for plugins.
    """

    def __init__(self, name: str = None) -> None:
        # Defaults
        self._device = None
        self._state_post_handler = None
        self._menuitems = []
        self._tabitems = []

        # Default name is calling file.
        if not name:
            frame = inspect.stack()[1]
            module = inspect.getmodule(frame[0])
            name = module.__file__
        self._name = name

    @property
    def name(self) -> str:
        """
        Returns the plugin name.
        Used for debugging
        """
        return self._name

    @property
    def device(self) -> DeviceItem:
        """
        Returns the device item.
        """
        return self._device

    @device.setter
    def device(self, device: DeviceItem) -> None:
        """
        Sets the device item.
        """

        if not isinstance(device, DeviceItem):
            raise TypeError("Device must be a DeviceItem.")

        self._device = device

    def menuitem_add(self, menuitem: MenuItem) -> None:
        """
        Adds a menu item to the header menu.

        Args:
            menuitem (MenuItem): Menu item to add.
        """

        if not isinstance(menuitem, MenuItem):
            raise TypeError("Menu item must be a MenuItem.")

        self._menuitems.append(menuitem)

    @property
    def menuitems(self) -> list:
        """
        Returns the list of menu items.
        """

        return self._menuitems

    def tabitem_add(self, tabitem: TabItem) -> None:
        """
        Adds a tab item to the header menu.

        Args:
            tabitem (TabItem): Tab item to add.
        """

        if not isinstance(tabitem, TabItem):
            raise TypeError("Menu item must be a TabItem.")

        self._tabitems.append(tabitem)

    @property
    def tabitems(self) -> list:
        """
        Returns the list of tab items.
        """

        return self._tabitems

    def __iadd__(self, item: Union[MenuItem, TabItem, DeviceItem]) -> PluginBase:
        """
        Adds a menu or tab item to the header menu.

        Args:
            item (MenuItem): New Menu Item.
        """

        if isinstance(item, MenuItem):
            self.menuitem_add(item)
            return self

        if isinstance(item, TabItem):
            self.tabitem_add(item)
            return self

        if isinstance(item, DeviceItem):
            self.device = item
            return self

        raise TypeError(f"Item must be a MenuItem or TabItem: {type(item)}")
