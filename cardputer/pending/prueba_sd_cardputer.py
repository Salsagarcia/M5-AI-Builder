import M5,time,os
from hardware import MatrixKeyboard
from machine import Pin,SoftSPI
BG=0x102638
def show(rows):
    lcd=M5.Lcd
    lcd.fillScreen(BG); lcd.setTextSize(1)
    lcd.setTextColor(0x54c9ff,BG); lcd.drawString('MICROSD V0.4',4,4)
    lcd.setTextColor(0xffffff,BG)
    for i,s in enumerate(rows): lcd.drawString(s,4,22+i*16)
    M5.update()
def cmd(spi,cs,n,arg,crc):
    cs(0)
    try:
        spi.write(bytes([64+n,(arg>>24)&255,(arg>>16)&255,(arg>>8)&255,arg&255,crc]))
        for i in range(100):
            v=spi.read(1,255)[0]
            if v<128:
                extra=spi.read(4,255) if n in (8,58) else b''
                return v,extra
        return 255,b''
    finally:
        cs(1); spi.write(b'\xff')
def main():
    kb=MatrixKeyboard()
    spi=None; cs=None
    try:
        show(['Diagnostico solo lectura','Comprobando /sd'])
        if 'sd' in os.listdir('/'):
            show(['SD ya montada','Sin reinicializar SPI','G0: salir'])
        else:
            show(['SoftSPI 100 kHz','ENTER: iniciar prueba','G0: salir'])
            while True:
                M5.update(); kb.tick()
                if M5.BtnA.wasPressed(): return
                if kb.is_pressed() and kb.get_key() in (10,13): break
                time.sleep_ms(20)
            try:
                cs=Pin(4,Pin.OUT,value=1)
                spi=SoftSPI(baudrate=100000,polarity=0,phase=0,sck=Pin(36),mosi=Pin(37),miso=Pin(35))
                spi.write(b'\xff'*16)
                show(['CMD0: reset tarjeta'])
                for i in range(5):
                    r,_=cmd(spi,cs,0,0,0x95)
                    if r==1: break
                if r!=1: raise OSError('CMD0: 0x%02X'%r)
                show(['CMD0 OK','CMD8: comprobar SDHC'])
                r,data=cmd(spi,cs,8,0x1aa,0x87)
                if r!=1 or data[-2:]!=b'\x01\xaa': raise OSError('CMD8: 0x%02X'%r)
                show(['CMD0/CMD8 OK','ACMD41: inicializar'])
                for i in range(100):
                    cmd(spi,cs,55,0,1)
                    r,_=cmd(spi,cs,41,0x40000000,1)
                    if r==0: break
                    time.sleep_ms(50)
                if r!=0: raise OSError('ACMD41: 0x%02X'%r)
                r,data=cmd(spi,cs,58,0,1)
                if r!=0: raise OSError('CMD58: 0x%02X'%r)
                show(['COMUNICACION SD OK','CMD0/8/41/58 OK','SDHC/SDXC' if data[0]&64 else 'SDSC','Sin escritura ni montaje','G0: salir'])
            except Exception as e:
                show(['ERROR SOFTSPI',str(e)[:36],'G0: salir'])
        while True:
            M5.update(); kb.tick()
            if M5.BtnA.wasPressed(): return
            time.sleep_ms(20)
    finally:
        if cs is not None: cs(1)
        if spi is not None: spi.deinit()
        kb.deinit()
main()
