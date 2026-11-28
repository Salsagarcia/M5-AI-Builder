import M5,time,os
from hardware import sdcard
BG=0x102638
def show(rows):
    lcd=M5.Lcd
    lcd.fillScreen(BG); lcd.setTextSize(1)
    lcd.setTextColor(0x54c9ff,BG); lcd.drawString('MICROSD V0.6',4,4)
    lcd.setTextColor(0xffffff,BG)
    for i,s in enumerate(rows): lcd.drawString(s,4,22+i*16)
    M5.update()
def main():
    stage='Detectar montaje'
    try:
        show([stage])
        if 'sd' not in os.listdir('/'):
            stage='Montar SPI 40/39/14/12'
            show([stage]); time.sleep_ms(300)
            sdcard.SDCard(slot=2,width=1,sck=40,miso=39,mosi=14,cs=12,freq=2000000)
        stage='Consultar capacidad'
        show([stage])
        s=os.statvfs('/sd')
        stage='Leer directorio'
        show([stage])
        files=os.listdir('/sd')
        show(['SD MONTADA /sd','Total: %.1f MiB'%(s[0]*s[2]/1048576),'Libre: %.1f MiB'%(s[0]*s[3]/1048576),'Entradas: %d'%len(files),'Lectura OK - G0 salir'])
    except Exception as e:
        show(['ERROR MICROSD',stage,str(e)[:36],'G0: salir'])
    while True:
        M5.update()
        if M5.BtnA.wasPressed(): return
        time.sleep_ms(20)
main()
