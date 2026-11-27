import M5,time
from hardware import MatrixKeyboard
from m5lib_hardware import load
from m5lib_irtest import IRTest
BG=0x102638

def main():
    kb=None; ir=None
    try:
        kb=MatrixKeyboard()
        cfg=load()[0]['ir']
        rx=cfg['rx']; tx=cfg['tx']
        ir=IRTest(rx,tx)
        last=0; sent=0; next_draw=time.ticks_ms()
        while True:
            M5.update(); kb.tick()
            if M5.BtnA.wasPressed(): return
            if kb.is_pressed():
                k=kb.get_key()
                if k in (10,13):
                    ir.pulse(); sent+=1
                elif k in (114,82):
                    ir.edges=0; last=0; sent=0
            if time.ticks_diff(time.ticks_ms(),next_draw)>=0:
                n=ir.edges
                lcd=M5.Lcd
                lcd.fillScreen(BG); lcd.setTextSize(1)
                lcd.setTextColor(0x54c9ff,BG)
                lcd.drawString('IR GPIO V0.2',4,4)
                lcd.setTextColor(0x76f2ab if n!=last else 0xffffff,BG)
                lcd.drawString('ACTIVIDAD IR' if n!=last else 'Esperando senal IR',4,22)
                lcd.setTextColor(0xffffff,BG)
                lcd.drawString('Flancos RX: %d'%n,4,42)
                lcd.drawString('Pulsos TX: %d'%sent,4,58)
                lcd.drawString('RX GPIO%d  TX GPIO%d'%(rx,tx),4,76)
                lcd.drawString('ENTER: pulso 38 kHz',4,96)
                lcd.drawString('R: reset G0: salir',4,122)
                last=n
                next_draw=time.ticks_add(time.ticks_ms(),250)
            time.sleep_ms(20)
    finally:
        if ir is not None: ir.close()
        if kb is not None: kb.deinit()

main()
