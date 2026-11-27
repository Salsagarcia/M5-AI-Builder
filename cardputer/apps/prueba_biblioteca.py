import M5
import time
def ejecutar():
    M5.begin()
    lcd=M5.Lcd
    lcd.fillScreen(0x102638)
    lcd.setTextSize(1)
    lcd.setTextColor(0xffffff,0x102638)
    try:
        import m5lib_test as lib
        lcd.drawString("Biblioteca "+lib.VERSION,5,8)
        resultados=[("2+3",lib.sumar(2,3),5),("Media 2,4,6",lib.media([2,4,6]),4),("Limitar 12 a 0..10",lib.limitar(12,0,10),10)]
        for i,(n,r,e) in enumerate(resultados):
            lcd.drawString(n+": "+str(r),5,30+i*18)
        ok=all(r==e for n,r,e in resultados)
        lcd.setTextColor(0x76f2ab if ok else 0xff5555,0x102638)
        lcd.drawString("PRUEBA OK" if ok else "ERROR RESULTADOS",5,90)
    except Exception as e:
        lcd.drawString("Error biblioteca",5,25)
        lcd.drawString(str(e)[:35],5,45)
    lcd.setTextColor(0xffffff,0x102638)
    lcd.drawString("G0: volver",5,115)
    while True:
        M5.update()
        if M5.BtnA.wasPressed(): break
        time.sleep_ms(30)
if __name__=="__main__": ejecutar()
