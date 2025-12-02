from machine import Pin
from neopixel import NeoPixel
from time import sleep

no_of_pixels = 12
np = NeoPixel(Pin(12, Pin.OUT), no_of_pixels)

def speed_level(speed_value): #Definere hvad der skal gøres med speed_value fra IMU
    for i in range(no_of_pixels):
        if i < speed_value:
            np[i] = (255,255,255)
        else:
            np[i] = (0,0,0)
    np.write()

value = 0
direction = 1

while True:
    speed_level(value)
    value += direction

    if value >= no_of_pixels:
        direction = -1
    if value <= 0:
        direction = 1

    sleep(0.2)

