import M5,time
from m5lib_storage import Storage,exists,join,read
from m5lib_datalogger import Logger,csvrow
from hardware import MatrixKeyboard
def show(*rows):
    M5.Lcd.fillScreen(0x102638); M5.Lcd.setTextSize(1)
    M5.Lcd.setTextColor(0xffffff,0x102638)
    M5.Lcd.drawString('DATALOGGER V0.1',4,4)
    for i,s in enumerate(rows): M5.Lcd.drawString(s,4,22+i*16)
def main():
    st=None; log=None; kb=MatrixKeyboard()
    try:
        show('1: Memoria interna','2: microSD','G0: salir')
        while True:
            M5.update(); kb.tick()
            if M5.BtnA.wasPressed(): return
            if kb.is_pressed():
                k=kb.get_key()
                if k in (49,50): break
            time.sleep_ms(20)
        medium='flash' if k==49 else 'sd'
        st=Storage(); root=st.root(medium)
        for i in range(1000):
            name='test_log_%03d.csv'%i
            if not exists(join(root,name)): break
        else: raise OSError('Sin nombre libre')
        log=Logger(st,medium,name,('indice','valor_simulado'),1000)
        expected=csvrow(('elapsed_ms','indice','valor_simulado'))
        while log.count<10:
            M5.update()
            if M5.BtnA.wasPressed(): return
            if log.due():
                i=log.count
                log.record((i,i*10))
                expected+=csvrow((log.elapsed,i,i*10))
                show(medium,name,'Registros: %d/10'%log.count,'G0: detener')
            time.sleep_ms(20)
        log.close()
        if read(log.path)!=expected: raise OSError('CSV diferente')
        st.close()
        show('10 REGISTROS OK',name,'CSV verificado','Archivo conservado','G0: salir')
    except Exception as e:
        show('ERROR',str(e)[:36],'G0: salir')
    finally:
        if log is not None: log.close()
        if st is not None: st.close()
        kb.deinit()
    while True:
        M5.update()
        if M5.BtnA.wasPressed(): return
        time.sleep_ms(20)
main()
