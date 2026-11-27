import M5,time
from machine import UART,Pin
from hardware import MatrixKeyboard
from m5lib_hardware import load
from m5lib_gps import GPS

BG=0x102638
def draw(g,online,baud,rx):
    lcd=M5.Lcd
    lcd.fillScreen(BG); lcd.setTextSize(1)
    lcd.setTextColor(0x54c9ff,BG)
    lcd.drawString('GPS V0.3  UART %d'%baud,4,4)
    lcd.setTextColor(0x76f2ab if g.fix else 0xffbc65,BG)
    lcd.drawString('POSICION VALIDA' if g.fix else 'BUSCANDO SATELITES' if online else 'SIN DATOS UART',4,20)
    lcd.setTextColor(0xffffff,BG)
    def val(v,fmt): return '--' if v is None else fmt%v
    rows=['Lat: '+val(g.lat,'%.6f'),'Lon: '+val(g.lon,'%.6f'),'Alt: '+val(g.alt,'%.1f')+' m','Vel: '+val(g.speed if g.fix else None,'%.1f')+' km/h','Sat: %d  UTC: %s'%(g.sats,g.utc),'NMEA: %d  RX: GPIO%d'%(g.frames,rx)]
    for i,s in enumerate(rows): lcd.drawString(s,4,36+13*i)
    lcd.drawString('B: baud  G0: salir',4,122)

def main():
    uart=None; kb=None
    cfg=load()[0]['gps']
    baud=cfg['baud']; rx=cfg['rx']; tx=cfg['tx']
    try:
        kb=MatrixKeyboard()
        uart=UART(1,baudrate=baud,bits=8,parity=None,stop=1,rx=Pin(rx),tx=Pin(tx),rxbuf=2048,timeout=0)
        g=GPS(uart); next_draw=time.ticks_ms()
        while True:
            M5.update(); kb.tick()
            if M5.BtnA.wasPressed(): return
            if kb.is_pressed():
                k=kb.get_key()
                if k in (98,66):
                    baud=115200 if baud==9600 else 9600
                    uart.init(baudrate=baud,bits=8,parity=None,stop=1,rx=Pin(rx),tx=Pin(tx),rxbuf=2048,timeout=0)
                    g=GPS(uart)
            online=g.poll()
            if time.ticks_diff(time.ticks_ms(),next_draw)>=0:
                draw(g,online,baud,rx)
                next_draw=time.ticks_add(time.ticks_ms(),500)
            time.sleep_ms(20)
    finally:
        if uart is not None: uart.deinit()
        if kb is not None: kb.deinit()

main()
