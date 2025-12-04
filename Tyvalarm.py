from machine import Pin, PWM
from time import sleep
from machine import UART
from gps_simple import GPS_SIMPLE
from math import sin, cos, sqrt, atan2, radians   # added

gpsPort = 2                                 # ESP32 UART port, Educaboard ESP32 default UART port
gpsSpeed = 9600                             # UART speed, defauls u-blox speed
gpsEcho = False                             # Echo NMEA frames: True or False
gpsAllNMEA = False                          # Enable all NMEA frames: True or False
uart = UART(gpsPort, gpsSpeed)              # UART object creation
led = Pin(12, Pin.OUT)
buzz = PWM(Pin(21))
buzz.freq(3000)       # loud frequency
buzz.duty_u16(0)      # start silent
gps = GPS_SIMPLE(uart, gpsAllNMEA)          # GPS object creation
threaded = False                            # Use threaded (True) or loop (False)

# reference position (set once when we get first good fix)
ref_lat = None
ref_lon = None

def alarm():
    while True:
        led.value(1)
        buzz.duty_u16(40000)   # loud volume (max ~65535)
        sleep(1)

        led.value(0)
        buzz.duty_u16(0)       # off
        sleep(0.5)

def distance_m(lat1, lon1, lat2, lon2):
    
    R = 6371000 
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)

    a = sin(dphi/2)**2 + cos(phi1) * cos(phi2) * sin(dlambda/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c
    #Bliver brugt til at udregne distancen mellem to punkter (lon og lat)
while True:
    if (gps.receive_nmea_data(gpsEcho)):
        gps.get_latitude()
        gps.get_longitude()

    Location = {
        "Latitude": gps.get_latitude(),
        "Longitude": gps.get_longitude()
    }
#Starter ikke programmet hvis ingen lokation er fundet
    if Location["Latitude"] == -999 or Location["Longitude"] == -999:
        print("Uh oh no sattelite found oopsie woopsie")
        sleep(0.5)
        continue

    # Set reference position once (on first valid fix)
    if ref_lat is None:
        ref_lat = Location["Latitude"]
        ref_lon = Location["Longitude"]
        print("Reference set to:", ref_lat, ref_lon)
        sleep(0.5)
        continue

    dist = distance_m(ref_lat, ref_lon,
                      Location["Latitude"], Location["Longitude"])

    print("Current:", Location.values(), "Distance (m):", dist)
    sleep(0.5)

    # Her kan der indstilles hvor langt cyklen må flytte sig i meter
    if dist > 10:
        alarm()
        
