from machine import Pin, UART
from uthingsboard.client import TBDeviceMqttClient
from gpio_lcd import GpioLcd
from time import sleep, ticks_ms
from lmt87 import LMT87
from gps_simple import GPS_SIMPLE
import random
import secrets

pin_lmt87 = 35
temp = LMT87(pin_lmt87)

# Gps ting ting
gpsPort = 2                                 # ESP32 UART port, Educaboard ESP32 default UART port
gpsSpeed = 9600                             # UART speed, defauls u-blox speed
gpsEcho = False                             # Echo NMEA frames: True or False
gpsAllNMEA = False                          # Enable all NMEA frames: True or False
uart = UART(gpsPort, gpsSpeed)              # UART object creation
gps = GPS_SIMPLE(uart, gpsAllNMEA)          # GPS object creation
threaded = False
pin_lmt87 = 35
average = 1

# Laver lcd object
lcd = GpioLcd(rs_pin=Pin(27), enable_pin=Pin(25), d4_pin=Pin(33),
               d5_pin=Pin(32), d6_pin=Pin(21), d7_pin=Pin(22), num_lines=4,
              num_columns=20)

# Tænder og clearer displayet når koden starter
lcd.backlight_on()
lcd.display_on()
lcd.clear()

# En class til en non blocking timer
class timer:
    def __init__(self, delay_period_ms):
        self.start_time = ticks_ms()
        self.delay_period_ms = delay_period_ms
    
    def non_blocking_timer(self, func):
        if ticks_ms() - self.start_time > self.delay_period_ms:
            func() # Starter funktionen når tiden er gået
            self.start_time = ticks_ms() # Genstarter tiden

# Non blocking timers til de forskellige functions, skrives sådan: "selv lavet timer".non_blocking_timer("function man skal køre")
display_test_timer = timer(200)
temp_display_timer = timer(500)
gps_module_timer = timer(1000)

# Forbinder til thingsboard
client = TBDeviceMqttClient(secrets.SERVER_IP_ADDRESS, access_token = secrets.ACCESS_TOKEN)
client.connect()
print("Forbundet til thingsboard")

# Display test function
def display_test():
    numbers = [0,1,2,3,4,5,6,7,8,9]
    lcd.move_to(19,3)
    lcd.putstr(str(random.choice(numbers)))
 
# Hastighed display function
def speed_display():
    lcd.move_to(0,0)
    lcd.putstr("Test")

def gps_module():
    if (gps.receive_nmea_data(gpsEcho)):
        print("Speed         : %.1f m/s" % gps.get_speed())
        print("Latitude      : %.8f" % gps.get_latitude())
        print("Longitude     : %.8f" % gps.get_longitude())
        print("Course        : %.1f°" % gps.get_course())

#Program
print("LMT87 test\n")

# Temperatur display function
def temp_display():
    custom_chr = bytearray([0b00010,
                            0b00101,
                            0b00010,
                            0b00000,
                            0b00000,
                            0b00000,
                            0b00000,
                            0b00000])

    lcd.move_to(8, 1)
    lcd.custom_char(0, custom_chr)
    lcd.putchar(chr(0))

    
    adc_val = temp.get_adc_value()
    temperature = temp.get_temperature()
    
    client.send_telemetry({"temperature": temperature})
    
    lcd.move_to(0, 1)
    lcd.putstr("Temp: %d C" % (temperature))
    lcd.move_to(8, 1)
    lcd.custom_char(0, custom_chr)
    lcd.putchar(chr(0))

# Try loop som kører de forskellige functions, og slukker display når den stopper
try:
    while True:
        temp_display_timer.non_blocking_timer(temp_display)
        display_test_timer.non_blocking_timer(display_test)
        gps_module_timer.non_blocking_timer(gps_module)

except KeyboardInterrupt:
    print("No more banana :(")

finally:
    lcd.display_off()
    lcd.backlight_off()

