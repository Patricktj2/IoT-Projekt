from machine import Pin
from neopixel import NeoPixel
from time import sleep

no_of_pixels = 12

np = NeoPixel(Pin(12, Pin.OUT), no_of_pixels) #Definere neopixel på pin med no_of_pixels


for led in range(no_of_pixels): #Intitiater lys på dioderne
    np[led] = (0,0,0)
np[1] = (0,0,0)
np.write()
sleep(0.3)

pcounter = 0

while True: #Tænder NeoPixel dioderne en af gangen
    for i in range(no_of_pixels):
        np[i] = (0,0,0)
    np[pcounter] = (255,255,255)
    np.write()
    pcounter +=1 #fjern + og indsæt speed value
    if pcounter == 12:
        pcounter = 0
    sleep(0.3) #Sleep skal nok fjernes
