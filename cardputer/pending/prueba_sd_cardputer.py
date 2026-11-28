import M5,time,os
from machine import Pin,SoftSPI
def show(*rows):
    M5.Lcd.fillScreen(0x102638)
    M5.Lcd.setTextSize(1)
    M5.Lcd.setTextColor(0xffffff,0x102638)
    M5.Lcd.drawString('MICROSD V0.8',4,4)
    for i,s in enumerate(rows): M5.Lcd.drawString(s,4,22+i*16)
    M5.update()
def main():
    spi=None; cs=None; stage='Inicio'
    try:
        if 'sd' in os.listdir('/'):
            show('SD ya montada','G0: salir')
        else:
            stage='SoftSPI'; show(stage)
            cs=Pin(12,Pin.OUT,value=1)
            spi=SoftSPI(baudrate=100000,polarity=0,phase=0,sck=Pin(40),miso=Pin(39),mosi=Pin(14))
            def cmd(n,arg,crc=1,extra=0,block=False):
                cs(0)
                try:
                    spi.write(bytes([64+n,(arg>>24)&255,(arg>>16)&255,(arg>>8)&255,arg&255,crc]))
                    for i in range(100):
                        r=spi.read(1,255)[0]
                        if r<128: break
                    else: return 255,b''
                    if block and r==0:
                        t=time.ticks_ms()
                        while time.ticks_diff(time.ticks_ms(),t)<1000:
                            token=spi.read(1,255)[0]
                            if token==254:
                                data=spi.read(512,255)
                                spi.read(2,255)
                                return r,data
                            if token!=255: raise OSError('Token %02X'%token)
                        raise OSError('Timeout sector')
                    return r,spi.read(extra,255) if extra else b''
                finally:
                    cs(1); spi.write(b'\xff')
            spi.write(b'\xff'*16)
            stage='CMD0'; show(stage)
            for i in range(5):
                r,_=cmd(0,0,0x95)
                if r==1: break
            if r!=1: raise OSError('CMD0 %02X'%r)
            stage='CMD8'; show(stage)
            r,d=cmd(8,0x1aa,0x87,4)
            if r!=1 or d[-2:]!=b'\x01\xaa': raise OSError('CMD8 %02X'%r)
            stage='ACMD41'; show(stage)
            for i in range(100):
                r,_=cmd(55,0)
                if r not in (0,1): raise OSError('CMD55 %02X'%r)
                r,_=cmd(41,0x40000000)
                if r==0: break
                if r!=1: raise OSError('ACMD41 %02X'%r)
                time.sleep_ms(50)
            if r!=0: raise OSError('Timeout ACMD41')
            stage='CMD58'; show(stage)
            r,d=cmd(58,0,1,4)
            if r!=0 or not d[0]&128: raise OSError('OCR invalido')
            if not d[0]&64: raise OSError('No SDHC/SDXC')
            stage='CMD17 sector 0'; show(stage)
            r,d=cmd(17,0,block=True)
            if r!=0 or len(d)!=512: raise OSError('CMD17 %02X'%r)
            show('SDHC INICIALIZADA','Sector 0: 512 bytes OK','Firma: %02X%02X'%(d[510],d[511]),'Sin escritura','G0: salir')
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
