import M5,time,os
from machine import Pin,SoftSPI
from m5lib_sdcard import SDCard
def show(*rows):
    M5.Lcd.fillScreen(0x102638); M5.Lcd.setTextSize(1)
    M5.Lcd.setTextColor(0xffffff,0x102638)
    M5.Lcd.drawString('MICROSD V0.9',4,4)
    for i,s in enumerate(rows): M5.Lcd.drawString(s,4,22+i*16)
    M5.update()
def main():
    spi=None; cs=None; mounted=False; folder=None; stage='Inicio'
    try:
        if 'sd' in os.listdir('/'): raise OSError('SD ya montada; reiniciar')
        stage='Inicializar SD'; show(stage)
        cs=Pin(12,Pin.OUT,value=1)
        spi=SoftSPI(baudrate=100000,polarity=0,phase=0,sck=Pin(40),miso=Pin(39),mosi=Pin(14))
        sd=SDCard(spi,cs)
        stage='Montar FAT lectura'; show(stage)
        os.mount(sd,'/sd',readonly=True); mounted=True
        s=os.statvfs('/sd'); count=len(os.listdir('/sd'))
        total=s[0]*s[2]/1073741824
        os.umount('/sd'); mounted=False
        stage='Montar escritura'; show(stage)
        sd.writable=True
        os.mount(sd,'/sd'); mounted=True
        stage='Crear temporal'; show(stage)
        for i in range(100):
            p='/sd/m5test_%02d'%i
            try: os.mkdir(p); folder=p; break
            except OSError as e:
                if e.args[0]!=17: raise
        if folder is None: raise OSError('Sin nombre libre')
        path=folder+'/test.csv'
        data=b't,valor\n0,123\n1,456\n'
        stage='Escribir CSV'; show(stage)
        with open(path,'wb') as f:
            if f.write(data)!=len(data): raise OSError('Escritura parcial')
        if hasattr(os,'sync'): os.sync()
        stage='Leer CSV'; show(stage)
        with open(path,'rb') as f:
            if f.read()!=data: raise OSError('Datos diferentes')
        stage='Eliminar temporal'; show(stage)
        os.remove(path); os.rmdir(folder); folder=None
        stage='Desmontar'; show(stage)
        if hasattr(os,'sync'): os.sync()
        os.umount('/sd'); mounted=False
        show('FAT OK: %.2f GiB'%total,'Entradas: %d'%count,'CSV escritura/lectura OK','Desmontaje OK','TODAS LAS PRUEBAS OK','G0: salir')
    except Exception as e:
        show('ERROR',stage,str(e)[:36],'Temporal puede quedar','G0: salir')
    finally:
        if mounted:
            try: os.umount('/sd'); mounted=False
            except Exception: show('ERROR DESMONTAJE','No retirar SD','Apagar tras finalizar')
        if not mounted:
            if cs is not None: cs(1)
            if spi is not None: spi.deinit()
    while True:
        M5.update()
        if M5.BtnA.wasPressed(): return
        time.sleep_ms(20)
main()
