import M5, time
from machine import Pin, SoftI2C
from hardware import MatrixKeyboard
from m5lib_pahub import PaHub
from m5lib_rfid import RFIDReader

BG=0x102638
FG=0xffffff
GREEN=0x76f2ab

def choose(kb, title, labels):
    sel=0
    while True:
        M5.Lcd.fillScreen(BG)
        M5.Lcd.setTextSize(1)
        M5.Lcd.setTextColor(0x54c9ff,BG)
        M5.Lcd.drawString(title,4,4)
        top=max(0,sel-5)
        for i in range(top,min(top+6,len(labels))):
            y=22+16*(i-top)
            M5.Lcd.fillRect(2,y-2,236,14,0x23618a if i==sel else BG)
            M5.Lcd.setTextColor(FG,0x23618a if i==sel else BG)
            M5.Lcd.drawString(labels[i],5,y)
        while True:
            M5.update(); kb.tick()
            if M5.BtnA.wasPressed(): return None
            if kb.is_pressed():
                k=kb.get_key()
                if k in (59,46,119,115,87,83,10,13):
                    while kb.is_key_pressed(k):
                        M5.update(); kb.tick()
                        while kb.is_pressed(): kb.get_key()
                        if M5.BtnA.wasPressed(): return None
                        time.sleep_ms(5)
                    if k in (10,13): return sel
                    sel=max(0,min(len(labels)-1,sel+(-1 if k in (59,119,87) else 1)))
                    break
            time.sleep_ms(20)

def draw(uid,count,label,present,error):
    lcd=M5.Lcd
    lcd.fillScreen(BG)
    lcd.setTextSize(1); lcd.setTextColor(0x54c9ff,BG)
    lcd.drawString('RFID 2 V0.1 '+label,4,4)
    lcd.setTextColor(GREEN if present else FG,BG)
    lcd.drawString('Tarjeta detectada' if present else 'Acerca una tarjeta',4,24)
    lcd.setTextSize(2)
    if uid:
        parts=['%02X'%b for b in uid]
        lcd.drawString(' '.join(parts[:6]),4,44)
        lcd.drawString(' '.join(parts[6:]),4,65)
    else:
        lcd.drawString('UID: --',4,44)
    lcd.setTextSize(1); lcd.setTextColor(FG,BG)
    lcd.drawString('Lecturas: %d'%count,4,95)
    lcd.drawString(error[:37] if error else 'ENTER: Reset   G0: Salir',4,122)

def main():
    bus=None; hub=None; kb=None
    try:
        kb=MatrixKeyboard()
        bus=SoftI2C(sda=Pin(2),scl=Pin(1),freq=100000,timeout=50000)
        mode=choose(kb,'CONEXION RFID',['Directo (sin PaHub)','PaHub 0x70'])
        if mode is None: return
        label='DIRECTO'
        if mode==1:
            hub=PaHub(bus)
            direct,channels=hub.scan()
            if 0x28 in direct: raise ValueError('RFID directo: conflicto')
            found=[i for i,c in enumerate(channels) if 0x28 in c]
            if not found: raise ValueError('RFID no detectado')
            k=choose(kb,'CANAL RFID',['CH%d'%i for i in found])
            if k is None: return
            hub.select(found[k]); label='CH%d'%found[k]
        if 0x28 not in bus.scan(): raise ValueError('RFID no detectado')
        reader=RFIDReader(bus)
        last=None; active=None; count=0; misses=0; errors=0
        next_read=time.ticks_ms()
        draw(last,count,label,False,'')
        while True:
            M5.update(); kb.tick()
            if M5.BtnA.wasPressed(): return
            if kb.is_pressed():
                if kb.get_key() in (10,13):
                    count=0; last=None
                    draw(last,count,label,active is not None,'')
            if time.ticks_diff(time.ticks_ms(),next_read)>=0:
                next_read=time.ticks_add(time.ticks_ms(),200)
                try:
                    uid=reader.read_uid(); errors=0
                    if uid:
                        misses=0
                        if uid!=active:
                            count+=1; last=uid; active=uid
                            draw(last,count,label,True,'')
                    else:
                        misses+=1
                        if misses>=3 and active is not None:
                            active=None; draw(last,count,label,False,'')
                except Exception as e:
                    errors+=1; draw(last,count,label,False,str(e))
                    if errors>=3: raise
            time.sleep_ms(10)
    except Exception as e:
        print(repr(e))
        if kb is not None: choose(kb,'ERROR RFID',[str(e)[:36],'Volver'])
    finally:
        if hub is not None:
            try: hub.disable()
            except Exception: pass
        if kb is not None: kb.deinit()
        if bus is not None and hasattr(bus,'deinit'): bus.deinit()

main()
