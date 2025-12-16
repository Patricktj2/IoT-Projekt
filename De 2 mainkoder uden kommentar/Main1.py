from uthingsboard.client import TBDeviceMqttClient
from time import sleep, ticks_ms
from machine import UART, Pin, PWM
from neopixel import NeoPixel
from gps_simple import GPS_SIMPLE
from math import sin, cos, sqrt, atan2, radians
from gpio_lcd import GpioLcd
from lmt87 import LMT87
from adc_sub import ADC_substitute
from umqtt.simple import MQTTClient
import secrets, random, network, esp32, gc
import urequests as requests

import random
import network
import esp32

mqtt_client = None

ref_lat = None
ref_lon = None

pin_lmt87 = 35
alarm_enabled = False
temp = LMT87(pin_lmt87)

afk_timer = 180

gpsPort = 2                                 
gpsSpeed = 9600                             
gpsEcho = False                             
gpsAllNMEA = False                         
uart = UART(gpsPort, gpsSpeed)             
gps = GPS_SIMPLE(uart, gpsAllNMEA)          
led = Pin(19, Pin.OUT)
buzz = PWM(Pin(15))
buzz.freq(1000)      
buzz.duty_u16(0)      
adc = ADC_substitute(34)

lcd = GpioLcd(rs_pin=Pin(27), enable_pin=Pin(25), d4_pin=Pin(33),
               d5_pin=Pin(32), d6_pin=Pin(21), d7_pin=Pin(22), num_lines=4,
              num_columns=20)

np = NeoPixel(Pin(26, Pin.OUT),2)
rgb = [0, 255]
green_led = Pin(18, Pin.OUT)
yellow_led = Pin(19, Pin.OUT)
red_led = Pin(26, Pin.OUT)
RL = Pin(14, Pin.OUT)

lcd.backlight_on()
lcd.display_on()
lcd.clear()

client = TBDeviceMqttClient(secrets.SERVER_IP_ADDRESS, access_token = secrets.ACCESS_TOKEN)
client.connect()
print("Forbundet til thingsboard")

x1=1670
y1=0
x2=2440
y2=100

a= (y2-y1)/(x2-x1)
b = y2 - a*x2

class timer:
    def __init__(self, delay_period_ms):
        self.start_time = ticks_ms()
        self.delay_period_ms = delay_period_ms
    
    def non_blocking_timer(self, func):
        if ticks_ms() - self.start_time > self.delay_period_ms:
            func() 
            self.start_time = ticks_ms()
            
main_timer = timer(10000)
temp_display_timer = timer(1000)
gps_module_timer = timer(1000)
batteri_måler_timer = timer(1000)
afk_warning_timer = timer(1000)
groen_energi_timer = timer(5000)

def rpc_request(req_id, method, params):
    """handler callback to recieve RPC from server """
    global alarm_enabled, afk_timer
    print(f'Response {req_id}: {method}, params {params}')
    print(params, "params type:", type(params))
  
    try:
        if method == "alarmtrigger":
            alarm_enabled = params
            
            if not alarm_enabled:
                print("Genstarter alarm")
                np.fill((0,0,0))
                np.write()
                buzz.duty_u16(0)
                if afk_timer >=0:
                    afk_timer = 180
                
        elif method == "disable_afk":
            print("Slukker afk alarm")
            alarm_enabled = False
            afk_timer = -1
            
    except Exception as e:
        print("RPC handler error:", e)

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

MQTT_CLIENT_ID = b"esp32_cykel"
MQTT_BROKER = secrets.MQTT_SERVER
MQTT_PORT = 1883
MQTT_USER = secrets.MQTT_USER
MQTT_PASSWORD = secrets.MQTT_PASSWORD

TOPIC_SPEED = b"cykel/hastighed"
TOPIC_LAT = b"cykel/latitude"
TOPIC_LON = b"cykel/longitude"
TOPIC_COURSE = b"cykel/course"
TOPIC_TEMP = b"cykel/temperature"

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

    mqtt_client.publish(
        CFG_SPEED,
        b'{"name":"Cykel Hastighed","state_topic":"cykel/hastighed",'
        b'"unit_of_measurement":"km/h","device_class":"speed","state_class":"measurement"}',
        retain=True
    )

    mqtt_client.publish(
        CFG_TEMP,
        b'{"name":"Cykel Temperatur","state_topic":"cykel/temperature",'
        b'"unit_of_measurement":"\xc2\xb0C","device_class":"temperature","state_class":"measurement"}',
        retain=True
    )

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

    mqtt_client.publish(
        CFG_COURSE,
        b'{"name":"Cykel Course","state_topic":"cykel/course",'
        b'"unit_of_measurement":"\xc2\xb0","state_class":"measurement"}',
        retain=True
    )

    print("Home Assistant discovery configs sent (retain=true)")

def make_gps_sender(mqtt_client):
    def send_gps():
        if not gps.receive_nmea_data(gpsEcho):
            return

        speed_ms = gps.get_speed()
        lat = gps.get_latitude()
        lon = gps.get_longitude()
        course = gps.get_course()

        
        if lat == -999 or lon == -999:
            print("No valid GPS fix yet")
            return
        
        if speed_ms != -999:
            speed_kmh = speed_ms * 3.6
            mqtt_client.publish(TOPIC_SPEED, "{:.1f}".format(speed_kmh))

        mqtt_client.publish(TOPIC_LAT, "{:.6f}".format(lat))
        mqtt_client.publish(TOPIC_LON, "{:.6f}".format(lon))

        try:
            mqtt_client.publish(TOPIC_COURSE, "{:.0f}".format(course))
        except Exception:
            mqtt_client.publish(TOPIC_COURSE, str(course))

        print("GPS sent:", lat, lon, "speed(ms):", speed_ms, "course:", course)

    return send_gps


def make_temp_sender(mqtt_client):
    def send_temp():
        temperature = temp.get_temperature()
        mqtt_client.publish(TOPIC_TEMP, str(temperature))
        print("Temp sent:", temperature)

    return send_temp

def main():
    global mqtt_client
    
    wifi_connect()
    mqtt_client = mqtt_connect()
    publish_discovery(mqtt_client)
    print("Connected to MQTT")

def send_mqtt_data():
    global mqtt_client
    
    if mqtt_client is None:
        return
    
    try: 
        send_gps = make_gps_sender(mqtt_client)
        send_temp = make_temp_sender(mqtt_client)
        send_gps()
        send_temp()
        
    except Exception as e:
        print("MQTT send error:", e)

def formel_batt(x):
    y= a*x+b 
    return int(y)

def batteri_måler():
    adc_val = adc.read_adc()
    batt_percentage = formel_batt(adc_val)
    
    custom_chr = bytearray([0b01110,
                            0b11111,
                            0b10101,
                            0b11001,
                            0b10011,
                            0b10101,
                            0b11001,
                            0b11111])
    lcd.move_to(19, 0)
    lcd.custom_char(1, custom_chr)
    lcd.putchar(chr(1))
    
    lcd.move_to(15,0)
    lcd.putstr(f'{batt_percentage}%')
    
    client.send_telemetry({"Batteri": batt_percentage})

def groen_energi():
    gc.collect()  

    try:
        CO2_response = requests.get('https://api.energidataservice.dk/dataset/CO2Emis?limit=1')
        CO2_result = CO2_response.json()
        CO2_response.close()  
        gc.collect()

        PENGE_response = requests.get('https://api.energidataservice.dk/dataset/DayAheadPrices?limit=1')
        PENGE_result = PENGE_response.json()
        PENGE_response.close()  
        gc.collect()

        co2_emission = CO2_result["records"][0]["CO2Emission"]
        el_pris = PENGE_result["records"][0]["DayAheadPriceDKK"]

        if co2_emission <= 50 and el_pris <= 500:
            lcd.move_to(0, 3)
            lcd.putstr('Strommen er gron   ')
            green_led.on()
            red_led.off()
            RL.on()
        else:
            lcd.move_to(0, 3)
            lcd.putstr('Strommen er beskidt')
            green_led.off()
            red_led.on()
            RL.off()

    except Exception as e:
        print("groen_energi fejl:", e)

def speed_display():
    if (gps.receieve_nmea_data(gpsEcho)):
        lcd.move_to(0,0)
        lcd.putstr(gps.get_speed())

def gps_module():
    if (gps.receive_nmea_data(gpsEcho)):
        lcd.move_to(0, 0)
        lcd.putstr("%d m/s" % gps.get_speed())

        lcd.move_to(0,1)
        lcd.putstr("Lat: %d" % gps.get_latitude())

        lcd.move_to(0,2)
        lcd.putstr("Long: %d" % gps.get_longitude())
      
        client.send_telemetry({
        "speed": gps.get_speed(),
        "latitude": gps.get_latitude(),
        "longitude": gps.get_longitude(),
        "course": gps.get_course()
        })
        
def temp_display():
    custom_chr = bytearray([0b00010,
                            0b00101,
                            0b00010,
                            0b00000,
                            0b00000,
                            0b00000,
                            0b00000,
                            0b00000])

    temperature = temp.get_temperature()
    
    client.send_telemetry({"temperature": temperature})
    
    lcd.move_to(16, 1)
    lcd.putstr("%d C" % (temperature))
    lcd.move_to(18, 1)
    lcd.custom_char(0, custom_chr)
    lcd.putchar(chr(0))

def alarm():
    while alarm_enabled:
        np.fill((255, 0, 0))
        np.write()
        buzz.duty_u16(40000)   
        sleep(1)

        np.fill((0,0,0))
        np.write()
        buzz.duty_u16(0)    
        sleep(0.5)
        client.check_msg()
        client.set_server_side_rpc_request_handler(rpc_request)

def distance_m(lat1, lon1, lat2, lon2):
    
    R = 6371000 
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)

    a = sin(dphi/2)**2 + cos(phi1) * cos(phi2) * sin(dlambda/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def distance():
    global ref_lat, ref_lon, dist
    if (gps.receive_nmea_data(gpsEcho)):
        gps.get_latitude()
        gps.get_longitude()
    
    Location = {
        "Latitude": gps.get_latitude(),
        "Longitude": gps.get_longitude()
    }

    if Location["Latitude"] == -999 or Location["Longitude"] == -999:
        print("Uh oh no sattelite found oopsie woopsie")
        return None

    if ref_lat is None:
        ref_lat = Location["Latitude"]
        ref_lon = Location["Longitude"]
        print("Reference set to:", ref_lat, ref_lon)
        return None

    dist = distance_m(ref_lat, ref_lon,
                      Location["Latitude"], Location["Longitude"])
    return dist

def alarmtrigger_step():
    current_dist = distance()
    print(f"Dist:{current_dist}m")
    if current_dist == None:
        return False
    
    if current_dist > 10:
        alarm()
        return True
        
    return False

def afk_warning():
    global afk_timer, alarm_enabled, ref_lat, ref_lon
    
    if afk_timer < 0:
        return
    
    try:
        if not alarm_enabled:
            current_dist = distance()
            
            if current_dist == None:
                print("Damn, no sattelite 🙁")
                return
            
            print(f"Dist:{current_dist}m, Timer:{afk_timer}")
            
            if current_dist <= 10:
                if afk_timer > 0:
                    mins, secs = divmod(afk_timer, 60)
                    timeformat = "{:02d}:{:02d}".format(mins, secs)
                    afk_timer -= 1
                    
                if afk_timer <= 0:
                    print("Timer alarm enabled")
                    alarm_enabled = True
             
            else:
                ref_lat = None
                ref_lon = None
    except NameError:
        pass
      
    client.send_telemetry({"Alarm_timer": afk_timer})

main()

try:
    while True:
        temp_display_timer.non_blocking_timer(temp_display)
        gps_module_timer.non_blocking_timer(gps_module)
        batteri_måler_timer.non_blocking_timer(batteri_måler)
        afk_warning_timer.non_blocking_timer(afk_warning)
        main_timer.non_blocking_timer(send_mqtt_data)
        groen_energi_timer.non_blocking_timer(groen_energi)
        
        client.check_msg()
        client.set_server_side_rpc_request_handler(rpc_request)
        sleep(0.01)
        if alarm_enabled:
            triggered = alarmtrigger_step()
            if triggered:
                print("ALARM TRIGGERED") 
            continue
        
            
except KeyboardInterrupt:
    print("No more banana 🙁")
    np.fill((0,0,0))
    np.write()
    
finally:
    lcd.display_off()
    lcd.backlight_off()
    



