import M5
import math
import time

def ejecutar():
    M5.begin()
    lcd=M5.Lcd
    bg=0x101D2B
    white=0xFFFFFF
    blue=0x54C9FF
    amber=0xFFC46B
    green=0x76F2AB
    cx,cy=229,121
    radii=(21,42,63,84)
    colors=(green,blue,amber,0xE06D65)
    def text(s,x,y,color=white,size=1):
        lcd.setTextSize(size)
        lcd.setTextColor(color,bg)
        lcd.drawString(s,x,y)
    def target():
        for i in range(4):
            lcd.drawCircle(cx,cy,radii[i],colors[i])
        lcd.drawLine(cx-84,cy,cx+84,cy,0x62798D)
        lcd.drawLine(cx,cy-84,cx,cy+84,0x62798D)
        for i in range(4):
            text(('2.5','5','7.5','10')[i],cx+4,cy-radii[i]+3,colors[i])
    def restore(x,y):
        lcd.fillCircle(x,y,8,bg)
        d=math.sqrt((x-cx)**2+(y-cy)**2)
        for i in range(4):
            if abs(d-radii[i])<=9:
                lcd.drawCircle(cx,cy,radii[i],colors[i])
        if abs(y-cy)<=9:
            lcd.drawLine(cx-84,cy,cx+84,cy,0x62798D)
        if abs(x-cx)<=9:
            lcd.drawLine(cx,cy-84,cx,cy+84,0x62798D)
        if abs(x-cx)<=32:
            for i in range(4):
                if abs(y-(cy-radii[i]+7))<=16:
                    text(('2.5','5','7.5','10')[i],cx+4,cy-radii[i]+3,colors[i])
    lcd.fillScreen(bg)
    text('INCLINOMETRO V0.2',8,6,white,2)
    text('X LONGITUDINAL',8,48,blue)
    text('Y TRANSVERSAL',8,122,amber)
    text('A CERO',8,220,blue)
    text('B RETENER',112,220,amber)
    text('C VOLVER',232,220)
    target()
    filt=None
    zero=(0.0,0.0)
    hold=False
    shown=None
    old=None
    status=None
    values=None
    last=time.ticks_ms()
    lastnum=last
    while True:
        M5.update()
        if M5.BtnC.wasPressed(): return True
        try:
            a=M5.Imu.getAccel()
            x,y,z=float(a[0]),float(a[1]),float(a[2])
            norm=math.sqrt(x*x+y*y+z*z)
            valid=0.85<norm<1.15 and abs(z)>0.17
            if valid:
                if filt is None: filt=(x,y,z)
                else: filt=(0.90*filt[0]+0.10*x,0.90*filt[1]+0.10*y,0.90*filt[2]+0.10*z)
                x,y,z=filt
                angles=(math.atan2(x,abs(z))*180/math.pi,math.atan2(y,abs(z))*180/math.pi)
            else: filt=None
        except Exception as e:
            lcd.fillScreen(bg)
            text('Error IMU',8,50)
            text(str(e)[:38],8,80)
            while True:
                M5.update()
                if M5.BtnC.wasPressed(): return False
                time.sleep_ms(30)
        if M5.BtnA.wasPressed() and valid and not hold: zero=angles
        if M5.BtnB.wasPressed() and shown is not None: hold=not hold
        if valid and not hold: shown=(angles[0]-zero[0],angles[1]-zero[1])
        now=time.ticks_ms()
        if time.ticks_diff(now,last)>=33:
            last=now
            st='RETENIDO' if hold else ('ESTATICO' if valid else 'NO VALIDO')
            if st!=status:
                lcd.fillRect(8,27,130,16,bg)
                text(st,8,27,amber if hold or not valid else green)
                status=st
            point=None
            if shown is not None and (valid or hold):
                p,q=shown
                dx,dy=p*8.4,q*8.4
                d=math.sqrt(dx*dx+dy*dy)
                scale=max(1.0,d/84)
                point=(cx+int(dx/scale),cy-int(dy/scale),green if d<=21 else blue if d<=42 else amber if d<=63 else colors[3])
            if point!=old:
                if old is not None: restore(old[0],old[1])
                if point is not None: lcd.fillCircle(point[0],point[1],7,point[2])
                old=point
            if time.ticks_diff(now,lastnum)>=100:
                lastnum=now
                v=None if point is None else ('%+.2f deg'%p,'%+.2f %%'%(100*math.tan(p*math.pi/180)) if abs(p)<89 else '---','%+.2f deg'%q,'%+.2f %%'%(100*math.tan(q*math.pi/180)) if abs(q)<89 else '---')
                if v!=values:
                    for i in range(4):
                        yy=(68,88,142,162)[i]
                        if values is None or v is None or v[i]!=values[i]:
                            lcd.fillRect(8,yy,124,16,bg)
                            text(v[i] if v is not None else '---',8,yy,blue if i<2 else amber)
                    values=v
        time.sleep_ms(20)
