import M5,time
from hardware import MatrixKeyboard
VERSION='0.1'
def read_text(title,initial='',maxlen=32,allowed=None,validate=None):
    s=initial[:maxlen]; kb=MatrixKeyboard(); lcd=M5.Lcd; bg=0x102638
    try:
        while True:
            lcd.fillScreen(bg); lcd.setTextSize(1)
            lcd.setTextColor(0x54c9ff,bg); lcd.drawString(title[:36],4,4)
            lcd.setTextColor(0xffffff,bg)
            lcd.drawString(s[-30:]+'_',4,35)
            lcd.drawString('%d/%d'%(len(s),maxlen),4,55)
            lcd.drawString('ENTER aceptar / DEL borrar',4,90)
            lcd.drawString('G0 cancelar',4,110)
            while True:
                M5.update(); kb.tick()
                if M5.BtnA.wasPressed(): return None
                if kb.is_pressed():
                    k=kb.get_key()
                    if not isinstance(k,int): continue
                    while kb.is_key_pressed(k):
                        M5.update(); kb.tick()
                        if M5.BtnA.wasPressed(): return None
                        while kb.is_pressed(): kb.get_key()
                        time.sleep_ms(5)
                    if k in (10,13):
                        if validate is None or validate(s): return s
                        lcd.drawString('Nombre no valido',4,72)
                        continue
                    if k in (8,127): s=s[:-1]; break
                    if 32<=k<=126 and len(s)<maxlen:
                        ch=chr(k)
                        if allowed is None or ch in allowed: s+=ch; break
                time.sleep_ms(20)
    finally: kb.deinit()
