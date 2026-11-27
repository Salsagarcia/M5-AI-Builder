import M5,time
from hardware import MatrixKeyboard
from m5lib_hardware import load

def main():
    kb=MatrixKeyboard()
    try:
        c,source=load()
        lcd=M5.Lcd; bg=0x102638
        lcd.fillScreen(bg); lcd.setTextSize(1)
        lcd.setTextColor(0x54c9ff,bg)
        lcd.drawString('PERFILES HW V0.1',4,4)
        lcd.setTextColor(0xffffff,bg)
        rows=['Origen: '+('DEFAULTS' if source=='defaults' else 'BACKUP' if source.endswith('.bak') else 'GUARDADO')]
        for n in ('tof','rfid'):
            a=c[n]
            rows.append(n.upper()+': '+('Directo' if a['mode']=='direct' else 'CH%d HUB %02X'%(a['channel'],a['hub']))+' @%02X'%a['address'])
        for n in ('gps','ir'):
            a=c[n]
            rows.append(n.upper()+': RX%d TX%d'%(a['rx'],a['tx'])+(' %d'%a['baud'] if n=='gps' else ''))
        rows.append('I2C: %d kHz'%(c['i2c_freq']//1000))
        for i,s in enumerate(rows): lcd.drawString(s,4,22+i*15)
        lcd.drawString('G0: salir',4,122)
        while True:
            M5.update(); kb.tick()
            if M5.BtnA.wasPressed(): return
            time.sleep_ms(20)
    finally: kb.deinit()
main()
