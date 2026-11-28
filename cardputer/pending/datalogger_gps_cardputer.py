import M5,time
from machine import UART,Pin
from m5lib_hardware import profile
from m5lib_gps import GPS
from m5lib_storage import Storage
from m5lib_datalogger import Logger
from m5lib_textinput import read_text
def show(*rows):
    lcd=M5.Lcd; lcd.fillScreen(0x102638); lcd.setTextSize(1)
    lcd.setTextColor(0xffffff,0x102638)
    lcd.drawString('GPS LOGGER V0.1',4,4)
    for i,s in enumerate(rows): lcd.drawString(s,4,22+i*16)
def main():
    st=None; uart=None; log=None
    try:
        medium=read_text('Medio: 1 Flash / 2 SD','2',1,'12',lambda s:s in ('1','2'))
        if medium is None: return
        interval=read_text('Intervalo segundos','1',4,'0123456789',lambda s:bool(s) and 1<=int(s)<=3600)
        if interval is None: return
        name=read_text('Nombre CSV (sin extension)','gps_001',24,'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-',lambda s:bool(s))
        if name is None: return
        st=Storage()
        cfg=profile('gps')
        uart=UART(1,baudrate=cfg['baud'],bits=8,parity=None,stop=1,rx=Pin(cfg['rx']),tx=Pin(cfg['tx']),rxbuf=2048,timeout=0)
        g=GPS(uart)
        log=Logger(st,'flash' if medium=='1' else 'sd',name+'.csv',('utc','fix','lat_deg','lon_deg','alt_m','speed_kmh','satellites'),int(interval)*1000)
        next_draw=time.ticks_ms()
        while True:
            M5.update()
            if M5.BtnA.wasPressed(): break
            online=g.poll()
            valid=online and g.fix and g.lat is not None and g.lon is not None
            if log.due():
                log.record((g.utc if online and g.gga_time is not None and time.ticks_diff(time.ticks_ms(),g.gga_time)<3000 else None,int(valid),g.lat if valid else None,g.lon if valid else None,g.alt if valid else None,g.speed if valid else None,g.sats if online else None))
            if time.ticks_diff(time.ticks_ms(),next_draw)>=0:
                show('POSICION VALIDA' if valid else 'BUSCANDO GPS' if online else 'SIN DATOS UART','Lat: %.6f'%g.lat if valid else 'Lat: --','Lon: %.6f'%g.lon if valid else 'Lon: --','Sat: %d UTC: %s'%(g.sats,g.utc),'Registros: %d'%log.count,'G0: detener y guardar')
                next_draw=time.ticks_add(time.ticks_ms(),500)
            time.sleep_ms(20)
        log.close(); st.close()
        show('REGISTRO FINALIZADO',name+'.csv','Registros: %d'%log.count,'G0: salir')
    except Exception as e:
        show('ERROR',str(e)[:36],'G0: salir')
    finally:
        if log is not None: log.close()
        if uart is not None: uart.deinit()
        if st is not None: st.close()
    while True:
        M5.update()
        if M5.BtnA.wasPressed(): return
        time.sleep_ms(20)
main()
