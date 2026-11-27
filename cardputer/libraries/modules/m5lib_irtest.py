# GPIO IR activity test; no capture or replay of remote codes.
from machine import Pin,PWM
import time
VERSION='0.1'

class IRTest:
    def __init__(self,rx,tx):
        self.rx=Pin(rx,Pin.IN)
        self.tx=Pin(tx,Pin.OUT,value=0)
        self.edges=0
        self.rx.irq(trigger=Pin.IRQ_FALLING,handler=self._edge)
    def _edge(self,pin):
        self.edges=(self.edges+1)&0x3fffffff
    def pulse(self):
        pwm=PWM(self.tx,freq=38000,duty_u16=21845)
        try:
            time.sleep_ms(20)
        finally:
            pwm.deinit()
            self.tx.init(Pin.OUT,value=0)
    def close(self):
        self.rx.irq(handler=None)
        self.tx.init(Pin.OUT,value=0)
