from time import ticks_ms

# Laver en class som hedder timer 
class timer:
    def __init__(self, delay_period_ms): # Laver selve classen til en der fungere med tid
        self.start_time = ticks_ms() 
        self.delay_period_ms = delay_period_ms
    
    def non_blocking_timer(self, func): # Selve den non blocking timer
        if ticks_ms() - self.start_time > self.delay_period_ms:
            func() # Starter funktionen når tiden er gået
            self.start_time = ticks_ms() # Genstarter tiden
            
test_timer = timer(1000) # Laver en timer 

def time_test(): # Functionen som bruger timeren
    print("epic")

while True:
    test_timer.non_blocking_timer(time_test) # Bruger timeren med functionen
# Den non blocking timer skrives sådan her = "timer_du_har_lavet".non_blocking_timer.("function som skal bruge timeren")
