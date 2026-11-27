import M5,time
def ejecutar():
    M5.begin()
    lcd=M5.Lcd
    lcd.fillScreen(0x102638)
    lcd.setTextSize(1)
    lcd.setTextColor(0xffffff,0x102638)
    try:
        import m5lib_test as a
        import m5lib_test2 as b
        x=a.sumar(2,3); y=b.cuadrado(x)
        lcd.drawString("2+3 = "+str(x),5,25)
        lcd.drawString("5 al cuadrado = "+str(y),5,45)
        ok=x==5 and y==25
        lcd.setTextColor(0x76f2ab if ok else 0xff5555,0x102638)
        lcd.drawString("DEPENDENCIAS OK" if ok else "ERROR RESULTADOS",5,80)
    except Exception as e:
        lcd.drawString(str(e)[:35],5,45)
    lcd.drawString("G0: volver",5,115)
    while True:
        M5.update()
        if M5.BtnA.wasPressed(): break
        time.sleep_ms(30)
if __name__=='__main__': ejecutar()
