from machine import UART
from time import ticks_ms, sleep
import network
from umqtt.simple import MQTTClient

from gps_simple import GPS_SIMPLE
from lmt87 import LMT87
import secrets


# -----------------------------
# WiFi
# -----------------------------
def wifi_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(secrets.SSID, secrets.PASSWORD)
        while not wlan.isconnected():
            sleep(0.5)

    print("WiFi connected:", wlan.ifconfig())
    return wlan


# -----------------------------
# Non-blocking timer
# -----------------------------
class Timer:
    def __init__(self, delay_ms):
        self.delay_ms = delay_ms
        self.last = ticks_ms()

    def run(self, func):
        now = ticks_ms()
        if now - self.last >= self.delay_ms:
            self.last = now
            func()


# -----------------------------
# MQTT settings (Home Assistant / Mosquitto)
# -----------------------------
MQTT_CLIENT_ID = b"esp32_cykel"
MQTT_BROKER = secrets.MQTT_SERVER
MQTT_PORT = 1883
MQTT_USER = secrets.MQTT_USER
MQTT_PASSWORD = secrets.MQTT_PASSWORD

# State topics (værdier)
TOPIC_SPEED = b"cykel/hastighed"
TOPIC_LAT = b"cykel/latitude"
TOPIC_LON = b"cykel/longitude"
TOPIC_COURSE = b"cykel/course"
TOPIC_TEMP = b"cykel/temperature"

# Discovery config topics (opretter sensorer i HA)
CFG_SPEED = b"homeassistant/sensor/cykel_hastighed/config"
CFG_LAT = b"homeassistant/sensor/cykel_latitude/config"
CFG_LON = b"homeassistant/sensor/cykel_longitude/config"
CFG_COURSE = b"homeassistant/sensor/cykel_course/config"
CFG_TEMP = b"homeassistant/sensor/cykel_temperature/config"


def mqtt_connect():
    client = MQTTClient(
        client_id=MQTT_CLIENT_ID,
        server=MQTT_BROKER,
        port=MQTT_PORT,
        user=MQTT_USER,
        password=MQTT_PASSWORD,
        keepalive=60
    )
    client.connect()
    print("MQTT connected:", MQTT_BROKER)
    return client


def publish_discovery(mqtt_client):
    # Speed (km/h)
    mqtt_client.publish(
        CFG_SPEED,
        b'{"name":"Cykel Hastighed","state_topic":"cykel/hastighed",'
        b'"unit_of_measurement":"km/h","device_class":"speed","state_class":"measurement"}',
        retain=True
    )

    # Temperature (°C)
    mqtt_client.publish(
        CFG_TEMP,
        b'{"name":"Cykel Temperatur","state_topic":"cykel/temperature",'
        b'"unit_of_measurement":"\xc2\xb0C","device_class":"temperature","state_class":"measurement"}',
        retain=True
    )

    # Latitude / Longitude (bare tal, measurement)
    mqtt_client.publish(
        CFG_LAT,
        b'{"name":"Cykel Latitude","state_topic":"cykel/latitude","state_class":"measurement"}',
        retain=True
    )
    mqtt_client.publish(
        CFG_LON,
        b'{"name":"Cykel Longitude","state_topic":"cykel/longitude","state_class":"measurement"}',
        retain=True
    )

    # Course (grader, typisk 0-359)
    mqtt_client.publish(
        CFG_COURSE,
        b'{"name":"Cykel Course","state_topic":"cykel/course",'
        b'"unit_of_measurement":"\xc2\xb0","state_class":"measurement"}',
        retain=True
    )

    print("Home Assistant discovery configs sent (retain=true)")


# -----------------------------
# GPS setup
# -----------------------------
gpsPort = 2
gpsSpeed = 9600
gpsEcho = False
gpsAllNMEA = False

uart = UART(gpsPort, gpsSpeed)
gps = GPS_SIMPLE(uart, gpsAllNMEA)

# -----------------------------
# Temperature sensor setup
# -----------------------------
temp_sensor = LMT87(35)  # pin 35 som i jeres gamle kode


# -----------------------------
# Senders
# -----------------------------
def make_gps_sender(mqtt_client):
    def send_gps():
        if not gps.receive_nmea_data(gpsEcho):
            return

        speed_ms = gps.get_speed()
        lat = gps.get_latitude()
        lon = gps.get_longitude()
        course = gps.get_course()

        # Hvis jeres GPS_SIMPLE bruger -999 for "ingen fix"
        if lat == -999 or lon == -999:
            print("No valid GPS fix yet")
            return

        # speed kan også være -999, så beskyt den
        if speed_ms != -999:
            speed_kmh = speed_ms * 3.6
            mqtt_client.publish(TOPIC_SPEED, "{:.1f}".format(speed_kmh))

        mqtt_client.publish(TOPIC_LAT, "{:.6f}".format(lat))
        mqtt_client.publish(TOPIC_LON, "{:.6f}".format(lon))

        # course kan være float/int afhængigt af bibliotek
        try:
            mqtt_client.publish(TOPIC_COURSE, "{:.0f}".format(course))
        except Exception:
            mqtt_client.publish(TOPIC_COURSE, str(course))

        print("GPS sent:", lat, lon, "speed(ms):", speed_ms, "course:", course)

    return send_gps


def make_temp_sender(mqtt_client):
    def send_temp():
        temperature = temp_sensor.get_temperature()
        mqtt_client.publish(TOPIC_TEMP, str(temperature))
        print("Temp sent:", temperature)

    return send_temp


# -----------------------------
# Main
# -----------------------------
def main():
    wifi_connect()
    mqtt_client = mqtt_connect()

    # Opret sensorerne i HA (1 gang)
    publish_discovery(mqtt_client)

    # Timers: GPS hvert 10. sekund, temp hvert 10. sekund (ændr hvis du vil)
    gps_timer = Timer(10000)
    temp_timer = Timer(10000)

    send_gps = make_gps_sender(mqtt_client)
    send_temp = make_temp_sender(mqtt_client)

    try:
        while True:
            gps_timer.run(send_gps)
            temp_timer.run(send_temp)
            sleep(0.1)
    except KeyboardInterrupt:
        print("Stopped")


if __name__ == "__main__":
    main()
