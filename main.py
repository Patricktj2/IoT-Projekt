from uthingsboard.client import TBDeviceMqttClient
from time import sleep, ticks_ms
from machine import UART, Pin, PWM
from neopixel import NeoPixel
from gps_simple import GPS_SIMPLE
from math import sin, cos, sqrt, atan2, radians
from gpio_lcd import GpioLcd
from lmt87 import LMT87
from adc_sub import ADC_substitute
import secrets
import random

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
          
display_test_timer = timer(200)
temp_display_timer = timer(1000)
gps_module_timer = timer(10000)
batteri_måler_timer = timer(1000)
afk_warning_timer = timer(1000)

def rpc_request(req_id, method, params):
    """handler callback to recieve RPC from server """
    global alarm_enabled
    print(f'Response {req_id}: {method}, params {params}')
    print(params, "params type:", type(params))
  
    try:
        if method == "alarmtrigger":
            alarm_enabled = params
    except Exception as e:
        print("RPC handler error:", e)

def formel_batt(x):
    y= a*x+b 
    return int(y)

def batteri_måler():
    adc_val = adc.read_adc()
    v = adc.read_voltage()
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
  
def speed_display():
    if (gps.receieve_nmea_data(gpsEcho)):
        lcd.move_to(0,0)
        lcd.putstr(gps.get_speed())

# Display test function
def display_test():
    numbers = [0,1,2,3,4,5,6,7,8,9]
    lcd.move_to(19,3)
    lcd.putstr(str(random.choice(numbers)))

# Gps modul function med speed, lat, long og course
def gps_module():
    if (gps.receive_nmea_data(gpsEcho)):
        lcd.move_to(0, 0)
        lcd.putstr("%d m/s" % gps.get_speed())
        
        print("Speed:", gps.get_speed(), "Lat:", gps.get_latitude(), "Lon:", gps.get_longitude(), "Course:", gps.get_course())
        
        
        client.send_telemetry({
        "speed": gps.get_speed(),
        "latitude": gps.get_latitude(),
        "longitude": gps.get_longitude(),
        "course": gps.get_course()
        })
        
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

    temperature = temp.get_temperature()
    
    client.send_telemetry({"temperature": temperature})
    
    lcd.move_to(16, 1)
    lcd.putstr("%d C" % (temperature))
    lcd.move_to(18, 1)
    lcd.custom_char(0, custom_chr)
    lcd.putchar(chr(0))

## Tyverialarm functions ##

# Selve alarm funktionen
def alarm():
    while alarm_enabled:
        np.fill((255, 0, 0))
        np.write()
        buzz.duty_u16(40000)   # loud volume (max ~65535)
        sleep(1)

        np.fill((0,0,0))
        np.write()
        buzz.duty_u16(0)       # off
        sleep(0.5)
        client.check_msg()
        client.set_server_side_rpc_request_handler(rpc_request)

# Udregner distance 
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

# Funktion som trigger alarmen
def alarmtrigger_step():
    global ref_lat, ref_lon, dist
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
    if dist > 3:
        alarm()
        return True
        
    return False

# Function til hvis cykel er afk i 3 min
def afk_warning():
    global dist, afk_timer, alarm_enabled
    if gps.get_latitude() and gps.get_longitude() == ref_lat and ref_lon:
        try: 
            if dist <= 10 and alarm_enabled == False:
                if afk_timer > 0:
                    mins, secs = divmod(afk_timer, 60)
                    timeformat = "{02d}:{:02d}".format(mins, secs)
                    print(timeformat, end="/r")
                    afk_timer -= 1
                    
                if afk_timer <= 0:
                    alarm_enabled = True
            
        except NameError:
            pass
        client.send_telemetry({"Alarm_timer": afk_timer})
    
# Intiater functions og sender data til thingsboard
try:
    while True:
        temp_display_timer.non_blocking_timer(temp_display)
        display_test_timer.non_blocking_timer(display_test)
        gps_module_timer.non_blocking_timer(gps_module)
        batteri_måler_timer.non_blocking_timer(batteri_måler)
        afk_warning_timer.non_blocking_timer(afk_warning)
        
        
        client.check_msg()
        client.set_server_side_rpc_request_handler(rpc_request)
        
        if alarm_enabled:
            triggered = alarmtrigger_step()
            if triggered:
                print("ALARM TRIGGERED") 
            alarmtrigger_step()
            continue
            
except KeyboardInterrupt:
    print("No more banana :(")
    
finally:
    lcd.display_off()
    lcd.backlight_off()

