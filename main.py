# -*- coding: utf-8 -*-
#
# Copyright 2024 Kevin Lindemark
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from uthingsboard.client import TBDeviceMqttClient
from time import sleep
from machine import reset, UART, Pin, PWM
import gc
import secrets
from gps_simple import GPS_SIMPLE
from math import sin, cos, sqrt, atan2, radians

alarm_enabled = False

gpsPort = 2                                 # ESP32 UART port, Educaboard ESP32 default UART port
gpsSpeed = 9600                             # UART speed, defauls u-blox speed
gpsEcho = False                             # Echo NMEA frames: True or False
gpsAllNMEA = False                          # Enable all NMEA frames: True or False
uart = UART(gpsPort, gpsSpeed)              # UART object creation
led = Pin(12, Pin.OUT)
buzz = PWM(Pin(21))
buzz.freq(1000)       # loud frequency
buzz.duty_u16(0)      # start silent
gps = GPS_SIMPLE(uart, gpsAllNMEA)          # GPS object creation
threaded = False                            # Use threaded (True) or loop (False)

ref_lat = None
ref_lon = None

def rpc_request(req_id, method, params):
    """handler callback to recieve RPC from server """
    global alarm_enabled
    print(f'Response {req_id}: {method}, params {params}')
    print(params, "params type:", type(params))
    try:
        # check if the method is "toggle_led1" (needs to be configured on thingsboard dashboard)
        if method == "alarmtrigger":
            # check if the value is is "led1 on"
            alarm_enabled = params
    except Exception as e:
        print("RPC handler error:", e)

def alarm():
    while alarm_enabled:
        led.value(1)
        buzz.duty_u16(40000)   # loud volume (max ~65535)
        sleep(1)

        led.value(0)
        buzz.duty_u16(0)       # off
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
    #Bliver brugt til at udregne distancen mellem to punkter (lon og lat)


def alarmtrigger_step():
    global ref_lat, ref_lon
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
        return False

    # Set reference position once (on first valid fix)
    if ref_lat is None:
        ref_lat = Location["Latitude"]
        ref_lon = Location["Longitude"]
        print("Reference set to:", ref_lat, ref_lon)
        sleep(0.5)
        return False

    dist = distance_m(ref_lat, ref_lon,
                      Location["Latitude"], Location["Longitude"])

    print("Current:", Location.values(), "Distance (m):", dist)
    sleep(0.5)

    # Her kan der indstilles hvor langt cyklen må flytte sig i meter
    if dist > 1:
        alarm()
    
        
    
    return False




client = TBDeviceMqttClient(secrets.SERVER_IP_ADDRESS, access_token = secrets.ACCESS_TOKEN)
client.connect()                           # Connecting to ThingsBoard 
print("connected to thingsboard, starting to send and receive data")

while True:
    client.check_msg()
    client.set_server_side_rpc_request_handler(rpc_request)
    
    if alarm_enabled:
        triggered = alarmtrigger_step()
        if triggered:
            print("ALARM TRIGGERED") 
        alarmtrigger_step()
        continue
        
    
    sleep(0.1)
    
    try:
        print(f"free memory: {gc.mem_free()}") # monitor memory left
        sleep(1)
        
        if gc.mem_free() < 2000:          # free memory if below 2000 bytes left
            print("Garbage collected!")
            gc.collect()                  # free memory
        
    except KeyboardInterrupt:
        print("Disconnected!")
        client.disconnect()               # Disconnecting from ThingsBoard
        reset()                           # reset ESP32

        