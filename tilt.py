from machine import I2C
from machine import Pin, PWM
from time import sleep
from mpu6050 import MPU6050
import sys
buzz = PWM(Pin(21))
buzz.freq(3000)       # loud frequency
buzz.duty_u16(0)
i2c = I2C(0)

imu = MPU6050(i2c)




while True:
    imu.get_values()
    vals = imu.get_values()   
    print(vals["acceleration z"])
    tilt = (vals["acceleration z"])
    Gforce =(vals["acceleration y"] / 16384)
    print (vals["acceleration y"] / 16384)

    sleep(.1)
    
    if tilt <6000 and  Gforce >1:
        while True:
            imu.get_values()
            vals = imu.get_values()   
            tilt = (vals["acceleration z"])
            print ("oh crap")
            buzz.duty_u16(40000)   # loud volume (max ~65535)
            sleep(0.2)
            buzz.duty_u16(0)       # off
            sleep(0.1)
            
            if tilt >6000:
                break 
            
        
    
        