import M5
import time

def ejecutar():
    M5.begin()
    fondo=0x172333
    def texto(s,x,y,t=1):
        M5.Lcd.setTextSize(t)
        M5.Lcd.setTextColor(0xffffff,fondo)
        M5.Lcd.drawString(s,x,y)
    M5.Lcd.fillScreen(fondo)
    texto('CRONOMETRO',20,15,2)
    texto('A Inicio/Pausa   B Reset   C Volver',10,210)
    acumulado=0
    inicio=None
    anterior=None
    while True:
        M5.update()
        ahora=time.ticks_ms()
        if M5.BtnC.wasPressed(): return True
        if M5.BtnA.wasPressed():
            if inicio is None: inicio=ahora
            else:
                acumulado+=time.ticks_diff(ahora,inicio)
                inicio=None
        if M5.BtnB.wasPressed():
            acumulado=0
            if inicio is not None: inicio=ahora
        ms=acumulado+(time.ticks_diff(ahora,inicio) if inicio is not None else 0)
        s='%02d:%02d.%d'%(ms//60000,ms//1000%60,ms//100%10)
        if s!=anterior:
            M5.Lcd.fillRect(10,80,300,60,fondo)
            texto(s,25,95,3)
            anterior=s
        time.sleep_ms(40)
