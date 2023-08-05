#!/usr/bin/python
#
# MQTT to InfuxDB bridge server.
# Subscribes to specific MQTT topics and writes the data to InfluxDB.
# Created as a learning project.

# Running a script as a Linux service:
# https://oxylabs.io/blog/python-script-service-guide

import datetime as dt
import ipaddress
import json
import logging
from paho.mqtt import client as mqtt_client
from influxdb import InfluxDBClient


class MapTopic2Sensor:
    """
    Map MQTT topic to InfluxDB sensor.
    """

    def __init__(self, topic: str = None, sensor: str = None) -> None:
        self._topic = None
        self._sensor = None

        if topic is not None:
            self.topic = topic
        if sensor is not None:
            self.sensor = sensor

    @property
    def topic(self) -> str:
        return self._topic

    @topic.setter
    def topic(self, value: str) -> None:
        self._topic = value

    @property
    def sensor(self) -> str:
        return self._sensor

    @sensor.setter
    def sensor(self, value: str) -> None:
        self._sensor = value


class Mqtt2InfluxDbBridge:
    def __init__(
        self,
        mqtt_host: str = "0.0.0.0",
        mqtt_port: int = 1883,  # Default Mosquitto port
        influx_host: str = "0.0.0.0",
        influx_port: int = 8086,  # Default InfluxDB port
        database: str = None,
    ) -> None:
        # Logging config
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(level=logging.DEBUG)

        # Defaults
        self._is_connected = False
        self._database = None
        self._maps = []

        # Setters
        if mqtt_host is not None:
            self.mqtt_host = mqtt_host
        if mqtt_port is not None:
            self.mqtt_port = mqtt_port
        if influx_host is not None:
            self.influx_host = influx_host
        if influx_port is not None:
            self.influx_port = influx_port
        if database is not None:
            self.database = database

    @property
    def mqtt_host(self) -> str:
        """
        MQTT Host IP Address.

        Returns:
            str: IP address.
        """
        return self._mqtt_host

    @mqtt_host.setter
    def mqtt_host(self, value: str) -> None:
        # Error checks
        if not isinstance(value, str):
            raise TypeError("MQTT host IP must be a string.")

        try:
            ipaddress.ip_address(value)
        except ValueError as e:
            self.logger.debug("Invalid IP address for MQTT server: %s", value)
            raise e

        self._mqtt_host = value

    @property
    def mqtt_port(self) -> int:
        """
        MQTT Host IP Port.

        Returns:
            int: Port number.
        """
        return self._mqtt_port

    @mqtt_port.setter
    def mqtt_port(self, value: int) -> None:
        # Error checks
        if not isinstance(value, int):
            raise TypeError("MQTT host port must be an integer.")

        self._mqtt_port = value

    @property
    def influx_host(self) -> str:
        """
        InfluxDB Host IP Address.

        Returns:
            str: IP address.
        """
        return self._influx_host

    @influx_host.setter
    def influx_host(self, value: str) -> None:
        # Error checks
        if not isinstance(value, str):
            raise TypeError("InfluxDB host IP must be a string.")

        try:
            ipaddress.ip_address(value)
        except ValueError as e:
            self.logger.debug("Invalid IP address for InfluxDB server: %s", value)
            raise e

        self._influx_host = value

    @property
    def influx_port(self) -> int:
        """
        InfluxDB Host IP Port.

        Returns:
            int: Port number.
        """
        return self._influx_port

    @influx_port.setter
    def influx_port(self, value: int) -> None:
        # Error checks
        if not isinstance(value, int):
            raise TypeError("InfluxDB host port must be an integer.")

        self._influx_port = value

    @property
    def database(self) -> str:
        """
        InfluxDB database name.

        Returns:
            str: Database name.
        """
        return self._database

    @database.setter
    def database(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("Database name must be a string.")

        self._database = value

    @property
    def maps(self) -> list:
        """
        List of topic to sensor mappings.

        Returns:
            list: List of topic to sensor mappings.
        """
        return self._maps

    @property
    def is_connected(self) -> bool:
        """
        MQTT and InfluxDB connection status.

        Returns:
            bool: True of connected to both MQTT and InfluxDB servers.
        """

        return self._is_connected

    def connect(self) -> None:
        """
        Connect to MQTT and InfluxDB servers.
        """

        self._is_connected = False

        # Error checks
        if self.mqtt_host is None:
            raise ValueError("MQTT host IP address is not set.")
        if self.mqtt_port is None:
            raise ValueError("MQTT host port is not set.")
        if self.influx_host is None:
            raise ValueError("InfluxDB host IP address is not set.")
        if self.influx_port is None:
            raise ValueError("InfluxDB host port is not set.")
        if self.database is None:
            raise ValueError("InfluxDB database name is not set.")

        # Connect to MQTT broker
        self._mqtt_client = mqtt_client.Client()
        self._mqtt_client.on_message = self._mqtt_on_message
        self._mqtt_client.connect(self.mqtt_host, self.mqtt_port)

        # Connect to InfluxDB
        self._influx_client = InfluxDBClient(
            host=self.influx_host, port=self.influx_port
        )

        # If database doesn't exist, create it
        dbs = [db["name"] for db in self._influx_client.get_list_database()]
        if self.database not in dbs:
            self._influx_client.create_database(self.database)
        self._influx_client.switch_database(self.database)

        self._is_connected = True

    def map_add(self, map: MapTopic2Sensor) -> None:
        """
        Add a topic to sensor mapping to the bridge.
        Must be connected to server to add mappings.

        Args:
            map (MapTopic2Sensor): Mapping object.
        """

        if not isinstance(map, MapTopic2Sensor):
            raise TypeError("Mapping must be of type MapTopic2Sensor.")

        # Add the map and subscribe to the topic
        self._maps.append(map)

        # Subscribe to the topic
        self._mqtt_client.subscribe(map.topic)

    def _mqtt_on_message(self, client, userdata, message, tmp=None) -> None:
        """
        MQTT subscription message handler.

        Args:
            client (_type_): _description_
            userdata (_type_): _description_
            message (_type_): _description_
            tmp (_type_, optional): _description_. Defaults to None.
        """

        # Convert topic to tag
        (tag_name, tag_value) = message.topic.split("/")[-2:]
        print(f"Tag: {tag_name}:{tag_value}")

        # Message payload is assumed to be JSON, convert to dict
        payload = json.loads(message.payload.decode("utf-8"))

        # If we don't have a timestamp, add one.
        if "timestamp" in payload:
            timestamp = payload["timestamp"]
            payload.pop("timestamp")
        else:
            timestamp = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Generate InfluxDB formatted dict
        data = {"measurement": "state"}
        data["tags"] = {tag_name: tag_value}
        data["time"] = timestamp
        data["fields"] = payload

        # Write to InfluxDB
        self._influx_client.write_points([data])

        print(f"Wrote to InfluxDB: {data}")

    def run(self):
        """
        Enters loop waiting for MQTT messages.
        """

        self._mqtt_client.loop_forever()


if __name__ == "__main__":
    # Create the bridge
    bridge = Mqtt2InfluxDbBridge()
    bridge.mqtt_host = "192.168.0.120"
    bridge.mqtt_port = 1885
    bridge.influx_host = bridge.mqtt_host
    bridge.database = "device_display"
    bridge.connect()

    # Create topic mapping and register it.
    map = MapTopic2Sensor(topic="device/#", sensor="state")
    bridge.map_add(map)

    # Listen for messages
    bridge.run()
