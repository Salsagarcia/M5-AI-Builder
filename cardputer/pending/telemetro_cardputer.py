import M5, time
from machine import Pin, SoftI2C
from hardware import MatrixKeyboard
from m5lib_hardware import load
from m5lib_pahub import PaHub
from m5lib_vl53l0x import RangeSensor

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

def draw(value, low, high, history, label, error):
    lcd=M5.Lcd
    lcd.fillScreen(BG)
    lcd.setTextSize(1); lcd.setTextColor(0x54c9ff,BG)
    lcd.drawString('TELEMETRO 0.2 '+label,4,3)
    lcd.setTextSize(3); lcd.setTextColor(FG,BG)
    lcd.drawString('%d mm'%value if value is not None else '--- mm',20,19)
    lcd.setTextSize(1); lcd.setTextColor(GREEN,BG)
    lcd.drawString('MIN:'+str(low if low is not None else '--'),4,48)
    lcd.drawString('MAX:'+str(high if high is not None else '--'),125,48)
    for y,t in ((65,'1200'),(87,'600'),(109,'0')):
        lcd.setTextColor(0xaabfd0,BG); lcd.drawString(t,1,y-4)
        lcd.drawLine(30,y,236,y,0x354d60)
    last=None
    for i,v in enumerate(history):
        if v is None:
            last=None; continue
        x=30+(60-len(history)+i)*206//59
        y=109-v*44//1200
        if last is not None: lcd.drawLine(last[0],last[1],x,y,GREEN)
        else: lcd.fillRect(x,y,2,2,GREEN)
        last=(x,y)
    lcd.setTextColor(FG,BG)
    lcd.drawString(error[:37] if error else 'ENTER: Reset   G0: Salir',3,122)

def main():
    bus=None; hub=None; kb=None
    try:
        kb=MatrixKeyboard()
        profiles,_=load()
        cfg=profiles['tof']
        bus=SoftI2C(sda=Pin(2),scl=Pin(1),freq=profiles['i2c_freq'],timeout=50000)
        label='DIRECTO'
        if cfg['mode']=='pahub':
            hub=PaHub(bus,cfg['hub'])
            hub.disable()
            if cfg['address'] in bus.scan(): raise ValueError('Conflicto bus directo')
            hub.select(cfg['channel'])
            label='CH%d'%cfg['channel']
        if cfg['address'] not in bus.scan(): raise ValueError('Revisar perfil y conexion')
        sensor=RangeSensor(bus,cfg['address'])
        low=high=None; history=[]; next_read=time.ticks_ms(); errors=0
        while True:
            M5.update(); kb.tick()
            if M5.BtnA.wasPressed(): return
            if kb.is_pressed():
                k=kb.get_key()
                if k in (10,13):
                    low=high=None; history=[]
            if time.ticks_diff(time.ticks_ms(),next_read)>=0:
                next_read=time.ticks_add(time.ticks_ms(),200)
                error=''
                try:
                    value=sensor.read_mm(); errors=0
                    if value is None: error='Fuera de rango / invalido'
                except Exception as e:
                    value=None; errors+=1; error='Error ToF: '+str(e)
                if value is not None:
                    low=value if low is None else min(low,value)
                    high=value if high is None else max(high,value)
                history.append(value)
                if len(history)>60: history.pop(0)
                draw(value,low,high,history,label,error)
                if errors>=3: raise RuntimeError('Tres errores de lectura')
            time.sleep_ms(10)
    except Exception as e:
        print(repr(e))
        if kb is not None: choose(kb,'ERROR TELEMETRO',[str(e)[:36],'Volver'])
    finally:
        if hub is not None:
            try: hub.disable()
            except Exception: pass
        if kb is not None: kb.deinit()
        if bus is not None and hasattr(bus,'deinit'): bus.deinit()

main()
