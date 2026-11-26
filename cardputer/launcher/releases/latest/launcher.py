import M5, time, gc, os, esp32, machine
import cp_wifi_v08a as cp_wifi
from hardware import MatrixKeyboard
BG=0x102638

def modo(n):
    nv=esp32.NVS('uiflow'); nv.set_u8('boot_option',n); nv.commit()

def temporal():
    nv=esp32.NVS('cp_launcher')
    nv.set_u8('once',1); nv.commit()
    modo(1); machine.reset()

# Cursor Cardputer: teclas fisicas ; (arriba) y . (abajo).
# Alternativas sin Fn y W/S; Enter ASCII 10/13.
def elegir(titulo, opciones, inicial=0):
    if not opciones: return None
    lcd=M5.Lcd; kb=MatrixKeyboard(); sel=max(0,min(inicial,len(opciones)-1)); top=max(0,sel-5)
    try:
        while True:
            lcd.fillScreen(BG); lcd.setTextSize(1)
            lcd.setTextColor(0x54c9ff,BG); lcd.drawString(titulo[:37],5,5)
            for i in range(top,min(top+6,len(opciones))):
                y=22+(i-top)*16; bg=0x23618a if i==sel else BG
                lcd.fillRect(2,y-2,230,15,bg); lcd.setTextColor(0xffffff,bg)
                lcd.drawString(('%d. '%(i+1)+opciones[i])[:36],5,y)
            if len(opciones)>6:
                lcd.fillRect(235,20,3,96,0x354b5d)
                h=max(5,96*6//len(opciones)); y=20+(96-h)*top//(len(opciones)-6)
                lcd.fillRect(235,y,3,h,0x54c9ff)
            lcd.setTextColor(0xffffff,BG); lcd.drawString(';/.: mover ENTER G0 %d/%d'%(sel+1,len(opciones)),3,125)
            while True:
                M5.update(); kb.tick()
                if M5.BtnA.wasPressed(): return None
                if kb.is_pressed():
                    k=kb.get_key()
                    if isinstance(k,int) and (k in (59,46,119,115,87,83,10,13) or 49<=k<=57):
                        while kb.is_key_pressed(k):
                            M5.update(); kb.tick()
                            while kb.is_pressed(): kb.get_key()
                            time.sleep_ms(5)
                        if k in (10,13): return sel
                        if 49<=k<=57:
                            if k-49<len(opciones): return k-49
                            continue
                        sel=max(0,min(len(opciones)-1,sel+(-1 if k in (59,119,87) else 1)))
                        if sel<top: top=sel
                        if sel>=top+6: top=sel-5
                        break
                time.sleep_ms(20)
    finally: kb.deinit()

def ejecutar_app(ruta):
    try:
        with open(ruta) as f: codigo=f.read()
        exec(compile(codigo,ruta,'exec'),{'__name__':'__main__','__file__':ruta})
    except Exception as e:
        print('Error app:',repr(e)); M5.Lcd.fillScreen(BG)
        M5.Lcd.drawString('Error: '+str(e)[:30],5,30); time.sleep_ms(2500)
    finally: gc.collect()
    M5.update(); time.sleep_ms(350)

def apps():
    p=0
    while True:
        try: nombres=sorted(n for n in os.listdir('/flash/apps') if n.endswith('.py') and not n.startswith('_') and not os.stat('/flash/apps/'+n)[0]&0x4000)
        except OSError: nombres=[]
        k=elegir('APPS LOCALES',[n[:30] for n in nombres] or ['Sin aplicaciones'],p)
        if k is None or not nombres: return
        p=k
        n=nombres[k]; ruta='/flash/apps/'+n
        c=elegir(n[:30],['Ejecutar','Informacion','Desinstalar','Volver'])
        if c==0: ejecutar_app(ruta)
        elif c==1:
            elegir(n[:30],['Tamano: %d bytes'%os.stat(ruta)[6],'Volver'])
        elif c==2:
            if elegir('BORRAR '+n[:22],['Cancelar','Confirmar borrado'])==1:
                try:
                    if ruta+'.bak' in ['/flash/apps/'+x for x in os.listdir('/flash/apps')]: os.remove(ruta+'.bak')
                    os.remove(ruta)
                except OSError as e: print('Error borrado:',e); elegir('ERROR AL BORRAR',['Volver'])

def ejecutar():
    M5.begin()
    # Ventana de recuperacion: G0 mantenido durante el inicio.
    M5.Lcd.fillScreen(BG); M5.Lcd.drawString('G0: recuperar UIFlow2',5,25)
    inicio=time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(),inicio)<2000:
        M5.update()
        if M5.BtnA.isPressed(): modo(1); machine.reset()
        time.sleep_ms(20)
    try:
        with open('/flash/launcher_mode.txt') as f: directo=f.read().strip()=='keyboard'
    except OSError: directo=False
    if directo: ejecutar_app('/flash/remote_keyboard.py')
    import cp_catalogo_v08a
    cp_catalogo_v08a.recuperar()
    cp_wifi.auto()
    import cp_bootstrap
    if cp_bootstrap.en_prueba():
        if elegir("CONFIRMAR NUEVO LAUNCHER",["Conservar version","Restaurar anterior"])==0:
            cp_bootstrap.confirmar()
        else: machine.reset()
    seleccion=0
    while True:
        k=elegir('V0.8d '+cp_wifi.status(),['Remote Keyboard','Aplicaciones locales','UIFlow2 temporal','UIFlow2 permanente','Configuracion','Catalogo GitHub','Configuracion WiFi','Actualizar Launcher'],seleccion)
        if k is None: return
        seleccion=k
        if k==0:
            ejecutar_app('/flash/remote_keyboard.py')
            cp_wifi.auto()
        elif k==1: apps()
        elif k==2: temporal()
        elif k==3: modo(1); machine.reset()
        elif k==7:
            import cp_selfupdate
            cp_selfupdate.menu(elegir)
        elif k==6: cp_wifi.menu(elegir)
        elif k==5:
            import cp_catalogo_v08a
            cp_catalogo_v08a.menu(elegir)
        elif k==4:
            c=elegir('ARRANQUE',['Mostrar Launcher','Remote Keyboard','UIFlow2 (reiniciar)'])
            if c in (0,1):
                with open('/flash/launcher_mode.txt','w') as f: f.write('keyboard' if c==1 else 'menu')
                modo(0)
            elif c==2: modo(1); machine.reset()

if __name__=='__main__': ejecutar()
