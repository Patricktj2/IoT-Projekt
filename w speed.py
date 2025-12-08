from time import sleep
from machine import UART
from gps_simple import GPS_SIMPLE
from lmt87 import LMT87
gpsPort = 2                                 # ESP32 UART port, Educaboard ESP32 default UART port
gpsSpeed = 9600                             # UART speed, defauls u-blox speed
gpsEcho = False                             # Echo NMEA frames: True or False
gpsAllNMEA = False                          # Enable all NMEA frames: True or False
uart = UART(gpsPort, gpsSpeed)              # UART object creation
gps = GPS_SIMPLE(uart, gpsAllNMEA)          # GPS object creation
threaded = False
pin_lmt87 = 35
average = 1
t1 = 25.2
adc1 = 2659
t2 = 24.2
adc2 = 2697
temperature = LMT87(pin_lmt87)
print("LMT87 test\n")
print(temperature.calibrate(t1, adc1, t2, adc2))
a = (t2 - t1) / (adc2 - adc1)
b = t1 - a * adc1

def get_temperature_celsius():
    raw = temperature.get_adc_value()
    temp_c = a * raw + b
    return temp_c

while True:
    if (gps.receive_nmea_data(gpsEcho)):
        print("Speed         : %.1f m/s" % gps.get_speed())
        print("Latitude      : %.8f" % gps.get_latitude())
        print("Longitude     : %.8f" % gps.get_longitude())
        print("Course        : %.1f°" % gps.get_course())
        print("Temp          : %.2f °C" % get_temperature_celsius())
        
    sleep (1)