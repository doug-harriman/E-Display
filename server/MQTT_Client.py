# MQTT_Client.py
# MQTT client for subscribing to device messages and storing to database.

import json
import logging
import datetime as dt
from typing import Optional

import paho.mqtt.client as mqtt

from db import DB, DeviceState


# Logging config
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)


class MQTTClient:
    """
    MQTT client for subscribing to device temperature messages.

    Connects to MQTT broker, subscribes to device topics, and stores
    received temperature data to the database using the DB class.
    """

    def __init__(
        self,
        broker_ip: str = "192.168.0.120",
        broker_port: int = 1885,
        topic: str = "device/home-office-tmp",
        db_filename: str = "device-data.db",
    ) -> None:
        """
        Initialize MQTT client and subscribe to device topic.

        Args:
            broker_ip: MQTT broker IP address
            broker_port: MQTT broker port
            topic: MQTT topic to subscribe to
            db_filename: Database filename for storing device data

        Example:
            >>> client = MQTTClient()
            >>> client.connect()
            >>> client.client_loop_start()
        """
        self._broker_ip = broker_ip
        self._broker_port = broker_port
        self._topic = topic
        self._db = DB(filename=db_filename)
        self._client: Optional[mqtt.Client] = None

        logger.info(
            f"MQTTClient initialized for broker {broker_ip}:{broker_port}, topic '{topic}'"
        )

    @property
    def broker_ip(self) -> str:
        """MQTT broker IP address (read-only)."""
        return self._broker_ip

    @property
    def broker_port(self) -> int:
        """MQTT broker port (read-only)."""
        return self._broker_port

    @property
    def topic(self) -> str:
        """MQTT topic to subscribe to (read-only)."""
        return self._topic

    @property
    def db(self) -> DB:
        """Database instance (read-only)."""
        return self._db

    def _message_on_connect(
        self, client: mqtt.Client, userdata, flags, rc: int
    ) -> None:
        """
        Callback for when the client receives a CONNACK response from the server.

        Args:
            client: The client instance for this callback
            userdata: The private user data as set in Client() or userdata_set()
            flags: Response flags sent by the broker
            rc: The connection result (0 = success)

        Example:
            This is an internal callback method called automatically by the MQTT client.
        """
        if rc == 0:
            logger.info("Connected")
            client.subscribe(self._topic)
            logger.info(f"Subscribed to topic '{self._topic}'")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")

    def _message_on_message(
        self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage
    ) -> None:
        """
        Callback for when a PUBLISH message is received from the server.

        Parses the message payload, extracts device name from topic,
        and stores the data to the database.

        Args:
            client: The client instance for this callback
            userdata: The private user data as set in Client() or userdata_set()
            msg: An instance of MQTTMessage containing topic and payload

        Example:
            This is an internal callback method called automatically by the MQTT client.
            Message format: '{"id": 1,"temperature": 65,"battery_soc": 100}'
            Topic format: 'device/home-office-tmp'
        """
        try:
            # Parse JSON payload
            payload = json.loads(msg.payload.decode("utf-8"))
            logger.debug(f"Received message on topic '{msg.topic}': {payload}")

            # Extract device name from topic (e.g., "device/home-office-tmp" -> "home-office-tmp")
            device_name = self._topic_to_device_name(msg.topic)

            # Create DeviceState object
            device_state = DeviceState(
                device=device_name,
                time=dt.datetime.now(),
                temperature=payload.get("temperature", -40),
                battery_soc=payload.get("battery_soc", -1),
            )

            # Store to database
            self._db.store(device_state)
            logger.info(
                f"Stored data for device '{device_name}': temp={device_state.temperature}°, "
                f"battery={device_state.battery_soc}%"
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON payload: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _topic_to_device_name(self, topic: str) -> str:
        """
        Extract device name from MQTT topic.

        Args:
            topic: MQTT topic string

        Returns:
            Device name extracted from topic

        Example:
            >>> client = MQTTClient()
            >>> client._topic_to_device_name("device/home-office-tmp")
            'home-office-tmp'
            >>> client._topic_to_device_name("device/kitchen-sensor")
            'kitchen-sensor'
        """
        # Remove "device/" prefix if present
        if topic.startswith("device/"):
            return topic[7:]  # len("device/") = 7
        return topic

    def connect(self) -> None:
        """
        Connect to MQTT broker, set up callbacks and start the message handler thread.

        Example:
            >>> client = MQTTClient()
            >>> client.connect()
        """
        self._client = mqtt.Client()
        self._client.on_connect = self._message_on_connect
        self._client.on_message = self._message_on_message

        try:
            self._client.connect(self._broker_ip, self._broker_port, keepalive=60)
            logger.info(f"Connecting to MQTT broker at {self._broker_ip}:{self._broker_port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise

        self._client.loop_start()

    def disconnect(self) -> None:
        """
        Stop the message thread and disconnect from MQTT broker.

        Example:
            >>> client = MQTTClient()
            >>> client.connect()
            >>> # ... do work ...
            >>> client.disconnect()
        """

        if self._client is not None:
            self._client.loop_stop()

        if self._client is not None:
            self._client.disconnect()
            logger.info("Disconnected from MQTT broker")


if __name__ == "__main__":
    # Test code
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create MQTT client and connect
    client = MQTTClient()
    client.connect()

    # Keep running (in production, this would be part of a larger application)
    try:
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        client.disconnect()
