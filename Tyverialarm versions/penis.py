from machine import Pin, PWM
from time import sleep
from machine import UART
from gps_simple import GPS_SIMPLE

gpsPort = 2                                 # ESP32 UART port, Educaboard ESP32 default UART port
gpsSpeed = 9600                             # UART speed, defauls u-blox speed
gpsEcho = True                              # Echo NMEA frames: True or False
gpsAllNMEA = False                          # Enable all NMEA frames: True or False
uart = UART(gpsPort, gpsSpeed)              # UART object creation

gps = GPS_SIMPLE(uart, gpsAllNMEA)          # GPS object creation
threaded = False                            # Use threaded (True) or loop (False)

import _thread
import time
led = Pin(12, Pin.OUT)
buzz = PWM(Pin(21))
buzz.freq(3000)       # loud frequency
buzz.duty_u16(0)      # start silent

def alarm():
    while True:
        led.value(1)
        buzz.duty_u16(40000)   # loud volume (max ~65535)
        sleep(0.5)

        led.value(0)
        buzz.duty_u16(0)       # off
        sleep(0.5)


while True:
    print("Longitude     : %.8f" % gps.get_longitude())
    print("Altitude      : %.1f m" % gps.get_altitude())


