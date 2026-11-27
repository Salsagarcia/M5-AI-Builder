import M5,time,os
from hardware import MatrixKeyboard
import machine
BG=0x102638
stage='Inicio'
card=None
def test():
    global stage, card
    stage='Detectar montaje'
    if 'sd' in os.listdir('/'):
        os.listdir('/sd')
        source='SD YA MONTADA'
    else:
        stage='Inicializar SPI slot 3'
        card=machine.SDCard(slot=3,width=1,sck=36,miso=35,mosi=37,cs=4,freq=2000000)
        stage='Leer tarjeta'
        card.info()
        stage='Montar FAT'
        os.mount(card,'/sd')
        source='SD MONTADA SLOT 3'
    stage='Consultar capacidad'
    s=os.statvfs('/sd')
    rows=[source,'Total: %.1f MiB'%(s[0]*s[2]/1048576),'Libre: %.1f MiB'%(s[0]*s[3]/1048576)]
    stage='Escritura/lectura'
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
        except Exception as e: rows=['ERROR MICROSD',stage,str(e)[:36]]
        lcd=M5.Lcd; lcd.fillScreen(BG); lcd.setTextSize(1)
        lcd.setTextColor(0x54c9ff,BG); lcd.drawString('MICROSD V0.2',4,4)
        lcd.setTextColor(0xffffff,BG)
        for i,s in enumerate(rows): lcd.drawString(s,4,22+i*16)
        lcd.drawString('G0: salir',4,122)
        while True:
            M5.update(); kb.tick()
            if M5.BtnA.wasPressed(): return
            time.sleep_ms(20)
    finally:
        kb.deinit()
        if card is not None:
            try:
                if 'sd' in os.listdir('/'): os.umount('/sd')
                card.deinit()
            except Exception as e: print(repr(e))
main()
