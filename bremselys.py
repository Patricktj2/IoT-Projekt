from machine import I2C
from machine import Pin, PWM
from time import sleep
from mpu6050 import MPU6050
import sys


i2c = I2C(0)

imu = MPU6050(i2c)
Bremselys = Pin(15, Pin.OUT)
Bremse_tænd_G = -0.4



while True:
    vals = imu.get_values()
    gy =(vals["acceleration y"] / 16384)
    print (gy)
    sleep (0.2)
    if gy < Bremse_tænd_G:
        Bremselys.on()
        sleep(.5)
    else:
        Bremselys.off()
    

   