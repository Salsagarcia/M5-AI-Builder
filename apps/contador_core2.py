# M5-AI Builder - contador tactil Core2
VERSION = "0.1"

def ejecutar():
    import M5
    import time
    M5.begin()
    fondo = 0x172333
    blanco = 0xFFFFFF
    M5.Lcd.fillScreen(fondo)
    M5.Lcd.setTextColor(blanco, fondo)
    M5.Lcd.setTextSize(2)
    M5.Lcd.drawString("CONTADOR", 72, 20)
    cuenta = 0
    def pintar():
        M5.Lcd.fillRect(40, 70, 240, 60, fondo)
        M5.Lcd.drawString(str(cuenta), 130, 90)
    pintar()
    M5.Lcd.fillRect(35, 155, 250, 40, 0x205030)
    M5.Lcd.drawString("+1", 138, 165)
    M5.Lcd.fillRect(35, 205, 250, 30, 0x46566C)
    M5.Lcd.drawString("SALIR", 115, 210)
    anterior = False
    while True:
        M5.update()
        pulsado = M5.Touch.getCount() > 0
        if pulsado and not anterior:
            x, y = M5.Touch.getTouchPointRaw(0)[:2]
            if 35 <= x <= 285 and 155 <= y <= 195:
                cuenta += 1
                pintar()
            elif 35 <= x <= 285 and 205 <= y <= 235:
                while M5.Touch.getCount() > 0:
                    M5.update()
                    time.sleep_ms(30)
                return
        anterior = pulsado
        time.sleep_ms(40)
