import M5,time,os
from machine import Pin,SoftSPI
def show(*rows):
    M5.Lcd.fillScreen(0x102638)
    M5.Lcd.setTextSize(1)
    M5.Lcd.setTextColor(0xffffff,0x102638)
    M5.Lcd.drawString('MICROSD V0.7',4,4)
    for i,s in enumerate(rows): M5.Lcd.drawString(s,4,22+i*16)
    M5.update()
def main():
    spi=None
    cs=None
    stage='Inicio'
    try:
        if 'sd' in os.listdir('/'):
            show('SD ya montada','G0: salir')
        else:
            stage='Configurar CS12'
            show(stage)
            cs=Pin(12,Pin.OUT,value=1)
            stage='SoftSPI 40/39/14'
            show(stage)
            spi=SoftSPI(baudrate=100000,polarity=0,phase=0,sck=Pin(40),miso=Pin(39),mosi=Pin(14))
            stage='Reloj inicial'
            show(stage)
            spi.write(b'\xff'*16)
            stage='CMD0'
            show(stage)
            result=255
            for i in range(5):
                cs(0)
                spi.write(b'\x40\x00\x00\x00\x00\x95')
                for j in range(100):
                    result=spi.read(1,255)[0]
                    if result<128: break
                cs(1)
                spi.write(b'\xff')
                if result==1: break
            show('CMD0: 0x%02X'%result,'TARJETA RESPONDE' if result==1 else 'Sin respuesta valida','Sin escritura','G0: salir')
    except Exception as e:
        show('ERROR',stage,str(e)[:36],'G0: salir')
    finally:
        if cs is not None: cs(1)
        if spi is not None: spi.deinit()
    while True:
        M5.update()
        if M5.BtnA.wasPressed(): return
        time.sleep_ms(20)
main()
