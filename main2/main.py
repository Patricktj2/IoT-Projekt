from time import ticks_ms
from machine import I2C
from machine import Pin, PWM
from time import sleep
from mpu6050 import MPU6050
import sys
from mpu6050 import MPU6050
buzz = PWM(Pin(12))
buzz.freq(3000)      
buzz.duty_u16(0)
i2c = I2C(0)
imu = MPU6050(i2c)
Bremselys = Pin(15, Pin.OUT)
Bremse_tænd_G = -0.17
from uthingsboard.client import TBDeviceMqttClient
faldet = False

class timer:
    def __init__(self, delay_period_ms):
        self.start_time = ticks_ms() 
        self.delay_period_ms = delay_period_ms
    
    def non_blocking_timer(self, func): 
        if ticks_ms() - self.start_time > self.delay_period_ms:
            func() 
            self.start_time = ticks_ms() 
            
test_timer = timer(1000) 

def rpc_callback(req_id, method, params):
    print(f"RPC request: {method}")
    if method == "faldet":

        client.send_rpc_reply(req_id, str(faldet).lower())

client = TBDeviceMqttClient(secrets.SERVER_IP_ADDRESS, access_token = secrets.ACCESS_TOKEN)
client.connect() 
print("Forbundet til thingsboard")

client.set_server_side_rpc_request_handler(rpc_callback)

def bremselys():
    vals = imu.get_values()
    gy =(vals["acceleration y"] / 16384)
    print (gy)
    sleep (0.2)
    if gy < Bremse_tænd_G:
        Bremselys.on()
        sleep(.3)
    else:
        Bremselys.off()
            
def faldalarm():
    global faldet
    imu.get_values()
    vals = imu.get_values()   
    print(vals["acceleration z"])
    tilt = (vals["acceleration z"])
    Gforce =(vals["acceleration y"] / 16384)
    print (vals["acceleration y"] / 16384)

    sleep(.1)

    if tilt <10000 and  Gforce >0.8:
        faldet=True
        client.send_attributes({"faldet": True})
        while True:
            imu.get_values()
            vals = imu.get_values()   
            tilt = (vals["acceleration z"])
            buzz.duty_u16(40000) 
            sleep(0.2)
            buzz.duty_u16(0)       
            sleep(0.1)
            
            if tilt >10000:
                client.send_attributes({"faldet": False})
                break 
while True:
    bremselys_timer.non_blocking_timer(bremselys)
    fald_timer.non_blocking_timer(faldalarm)
    
    client.check_msg()

