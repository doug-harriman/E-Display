# Simple MQTT publisher

import logging
import datetime as dt
from paho.mqtt import client as mqtt_client
from db import DeviceState

# Logging config
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)


class MQTT:
    def __init__(self, host: str = None, port: int = 1883) -> None:
        """
        Creat MQTT object.

        Args:
            host (str, optional): Host IP address. Defaults to None.
            port (int, optional): Host IP port number. Defaults to 1883.
        """
        if host is not None:
            self.host = host
        self.port = port

        self._client = None

    @property
    def host(self) -> str:
        return self._host

    @host.setter
    def host(self, value: str) -> None:
        self._host = value

    @property
    def port(self) -> int:
        return self._port

    @port.setter
    def port(self, value: int) -> None:
        self._port = value

    @property
    def client(self) -> mqtt_client.Client:
        return self._client

    def connect(self):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.debug("Connected to MQTT Broker!")
            else:
                self._client = None
                logger.debug("Failed to connect to MQTT broker, return code %d\n", rc)

        # Error checks
        if self.host is None:
            msg = "Host IP address is not set."
            logger.debug(msg)
            raise ValueError(msg)

        # Set Connecting Client ID
        # NOTE: Can pass in a client ID to identified sender.
        client = mqtt_client.Client()
        client.on_connect = on_connect
        client.connect(self.host, self.port)

        self._client = client

    def publish(self, topic: str, message: str) -> None:
        if self._client is None:
            raise ValueError("MQTT client is not connected.")

        logger.debug(f"Topic  : {topic}")
        logger.debug(f"Message: {message}")

        result = self._client.publish(topic, message)
        status = result[0]
        if status != 0:
            logger.debug(f"Failed to send message to topic {topic}")


def state_post_handler(state: DeviceState):
    # Forward the state to the MQTT broker
    MQTT_IP = "192.168.0.120"
    MQTT_PORT = 1885
    publisher = MQTT(MQTT_IP, MQTT_PORT)
    publisher.connect()

    # MQTT
    topic = f"device/{state.device}"
    msg = state.to_mqtt_message()
    publisher.publish(topic, msg)


if __name__ == "__main__":
    HOST = "192.168.0.120"
    PORT = 1885

    mqtt = MQTT(host=HOST, port=PORT)
    mqtt.connect()
    mqtt.publish("test", "Hello World")
