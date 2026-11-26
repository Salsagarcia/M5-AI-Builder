import M5
import time

def ejecutar():
    M5.begin()
    lcd=M5.Lcd
    lcd.fillScreen(0x102638)
    lcd.setTextSize(2)
    lcd.setTextColor(0x54c9ff,0x102638)
    lcd.drawString("M5 AI BUILDER",5,12)
    lcd.setTextSize(1)
    lcd.setTextColor(0xffffff,0x102638)
    lcd.drawString("Cardputer: instalacion OK",5,50)
    lcd.drawString("G0: volver",5,105)
    while True:
        M5.update()
        if M5.BtnA.wasPressed(): break
        time.sleep_ms(30)

if __name__=="__main__":
    ejecutar()
