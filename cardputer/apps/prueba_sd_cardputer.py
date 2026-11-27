import M5,time,os
from hardware import MatrixKeyboard,sdcard
BG=0x102638
def test():
    # Official UIFlow2 Cardputer SPI wiring.
    sdcard.SDCard(slot=2,width=1,sck=36,miso=35,mosi=37,cs=4,freq=2000000)
    s=os.statvfs('/sd')
    rows=['SD MONTADA /sd','Total: %.1f MiB'%(s[0]*s[2]/1048576),'Libre: %.1f MiB'%(s[0]*s[3]/1048576)]
    path=None
    for i in range(100):
        p='/sd/m5test_%02d'%i
        try: os.mkdir(p); path=p; break
        except OSError as e:
            if e.args[0]!=17: raise
    if path is None: raise OSError('Sin nombre libre')
    fpath=path+'/test.txt'
    try:
        with open(fpath,'wb') as f: f.write(b'M5-AI SD TEST')
        if hasattr(os,'sync'): os.sync()
        with open(fpath,'rb') as f: ok=f.read()==b'M5-AI SD TEST'
        rows.append('Escritura/lectura: '+('OK' if ok else 'ERROR'))
    finally:
        try: os.remove(fpath)
        except OSError: pass
        os.rmdir(path)
        if hasattr(os,'sync'): os.sync()
    rows.append('Temporal eliminado')
    return rows

def main():
    kb=MatrixKeyboard()
    try:
        try: rows=test()
        except Exception as e: rows=['ERROR MICROSD',str(e)[:36],'Revisar tarjeta FAT32']
        lcd=M5.Lcd; lcd.fillScreen(BG); lcd.setTextSize(1)
        lcd.setTextColor(0x54c9ff,BG); lcd.drawString('MICROSD V0.1',4,4)
        lcd.setTextColor(0xffffff,BG)
        for i,s in enumerate(rows): lcd.drawString(s,4,22+i*16)
        lcd.drawString('G0: salir',4,122)
        while True:
            M5.update(); kb.tick()
            if M5.BtnA.wasPressed(): return
            time.sleep_ms(20)
    finally: kb.deinit()
main()
