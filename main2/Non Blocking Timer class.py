from time import ticks_ms

class timer:
    def __init__(self, delay_period_ms):
        self.start_time = ticks_ms()
        self.delay_period_ms = delay_period_ms
    
    def non_blocking_timer(self, func):
        if ticks_ms() - self.start_time > self.delay_period_ms:
            func() # Starter funktionen når tiden er gået
            self.start_time = ticks_ms() # Genstarter tiden
            
test_timer = timer(1000) #Laver en timer til en function

def time_test(): # Functionen som bruger timeren
    print("epic")

while True:
    test_timer.non_blocking_timer(time_test) # Bruger timeren med functionen