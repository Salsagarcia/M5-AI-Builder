import M5
import math
import time

def ejecutar():
    M5.begin()
    lcd=M5.Lcd
    bg=0x172333
    white=0xffffff
    def text(s,x,y,size=1):
        lcd.setTextSize(size)
        lcd.setTextColor(white,bg)
        lcd.drawString(s,x,y)
    def read():
        return M5.Imu.getAccel()
    lcd.fillScreen(bg)
    text('INCLINOMETRO V0.1',10,8,2)
    text('A Cero  B Retener  C Volver',10,220)
    filt=None
    zero=(0.0,0.0)
    hold=False
    valid=False
    shown=None
    last=time.ticks_ms()
    while True:
        M5.update()
        if M5.BtnC.wasPressed():
            return True
        try:
            a=read()
            x,y,z=float(a[0]),float(a[1]),float(a[2])
            norm=math.sqrt(x*x+y*y+z*z)
            valid=0.85<norm<1.15 and abs(z)>0.17
            if valid:
                if filt is None: filt=(x,y,z)
                else: filt=tuple(0.85*filt[i]+0.15*v for i,v in enumerate((x,y,z)))
                x,y,z=filt
                angles=(math.atan2(x,abs(z))*180/math.pi,math.atan2(y,abs(z))*180/math.pi)
        except Exception as e:
            lcd.fillRect(0,40,320,170,bg)
            text('Error IMU',10,60,2)
            text(str(e)[:38],10,95)
            while True:
                M5.update()
                if M5.BtnC.wasPressed(): return False
                time.sleep_ms(50)
        if M5.BtnA.wasPressed() and valid and not hold:
            zero=angles
        if M5.BtnB.wasPressed():
            hold=not hold if shown is not None else False
        if valid and not hold:
            shown=(angles[0]-zero[0],angles[1]-zero[1])
        now=time.ticks_ms()
        if time.ticks_diff(now,last)>=200:
            last=now
            lcd.fillRect(0,30,320,185,bg)
            text('RETENIDO' if hold else ('ESTATICO' if valid else 'LECTURA NO VALIDA'),10,32)
            if shown is not None and (valid or hold):
                p,q=shown
                for i,v in enumerate((p,q)):
                    yy=56+i*68
                    text(('X Long.' if i==0 else 'Y Trans.'),10,yy)
                    text('%+.2f deg'%v,10,yy+15,2)
                    if abs(v)<89: text('%+.2f %%'%(100*math.tan(v*math.pi/180)),10,yy+36)
                cx,cy=250,125
                lcd.drawCircle(cx,cy,52,0x829bb0)
                lcd.drawCircle(cx,cy,26,0x829bb0)
                lcd.drawLine(cx-52,cy,cx+52,cy,0x829bb0)
                lcd.drawLine(cx,cy-52,cx,cy+52,0x829bb0)
                dx=p*4; dy=q*4
                scale=max(1,math.sqrt(dx*dx+dy*dy)/43)
                lcd.fillCircle(cx+int(dx/scale),cy-int(dy/scale),8,0x79dd9a)
            else: text('Colocar en reposo',10,80,2)
        time.sleep_ms(40)
