import requests
from machine import Pin
from time import sleep
import esp32
from neopixel import NeoPixel
from gpio_lcd import GpioLcd

try:
    import ujson as json
except ImportError:
    import json
RL = Pin(14, Pin.OUT)
np = NeoPixel(Pin(26, Pin.OUT),2)
rgb = [0, 255] 
lcd = GpioLcd(rs_pin=Pin(27), enable_pin=Pin(25),
              d4_pin=Pin(33), d5_pin=Pin(32), d6_pin=Pin(21), d7_pin=Pin(22),
              num_lines=4, num_columns=20)


while True:
    CO2_response = requests.get(url='https://api.energidataservice.dk/dataset/CO2Emis?limit=2')
    CO2_result = CO2_response.json()
    PENGE_response = requests.get(url='https://api.energidataservice.dk/dataset/DayAheadPrices?limit=5')
    PENGE_result = PENGE_response.json()

    CO2_records = CO2_result.get('records', [])
    PENGE_records = PENGE_result.get('records', [])
    
#  
    for record in CO2_records:
#         El_pris = 600
#         co2_emission = 40
        co2_emission = CO2_result["records"][0]["CO2Emission"]
        El_pris = PENGE_result["records"][1]['DayAheadPriceDKK']
        sleep(5)
        if co2_emission <= 50 and El_pris <= 500:
            lcd.clear()
            lcd.putstr('Strommen er gron')
            np.fill ((0,100,0))
            np.write()
            RL.on()
            
        else:
            lcd.clear()
            lcd.putstr('Strommen er beskidt')
            np.fill ((100,0,0))
            np.write()
            RL.off()
        
        

                
                
            
            
            
   
   