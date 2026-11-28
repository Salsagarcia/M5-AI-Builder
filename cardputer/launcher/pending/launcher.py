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

LIBDIR='/flash/m5_libs'
LIBROOT='libraries/releases/latest/'
def libname(n):
    return isinstance(n,str) and 7<=len(n)<=40 and n.startswith('m5lib_') and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in n)
def libinit():
    import sys
    try: os.mkdir(LIBDIR)
    except OSError:
        if not os.stat(LIBDIR)[0]&0x4000: raise
    if LIBDIR not in sys.path: sys.path.append(LIBDIR)
    from cp_catalogo_v08a import existe
    for f in os.listdir(LIBDIR):
        if f.endswith('.py.bak') and libname(f[:-7]):
            p=LIBDIR+'/'+f[:-4]
            if not existe(p): os.rename(p+'.bak',p)
        elif f.endswith('.py.new') and libname(f[:-7]):
            os.remove(LIBDIR+'/'+f)

def libcatalog(offline=False):
    import json,binascii
    from cp_catalogo_v08a import descarga,KEY
    from cp_ecdsa import verificar
    cache=LIBDIR+'/launcher_catalog.bin'
    if offline:
        with open(cache,'rb') as f:
            sig=f.read(128); raw=f.read(8193)
        if len(raw)>8192: raise ValueError('Catalogo demasiado grande')
    else:
        raw=descarga(LIBROOT+'manifest.json',8192)
        sig=descarga(LIBROOT+'manifest.sig',256)
    if not verificar(raw,KEY,binascii.unhexlify(sig.strip())): raise ValueError('Firma invalida')
    m=json.loads(raw.decode())
    if m['device']!='cardputer_v1_1' or m['schema']!=1 or m['kind']!='libraries': raise ValueError('Catalogo incompatible')
    rev=m['revision']; entries=m['libraries']
    if type(rev)!=int or not 1<=rev<=2147483647 or not isinstance(entries,list) or len(entries)>40: raise ValueError('Catalogo invalido')
    nv=esp32.NVS('cp_libs')
    try: old=nv.get_i32('revision')
    except OSError: old=0
    if rev<old: raise ValueError('Revision antigua')
    seen=set()
    for a in entries:
        n=a['name']; h=a['sha256']; size=a['bytes']; v=a['version']
        if not libname(n) or n in seen or a['path']!='libraries/modules/'+n+'.py' or type(size)!=int or not 1<=size<=32768 or not isinstance(h,str) or len(h)!=64 or any(c not in '0123456789abcdef' for c in h) or not isinstance(v,str) or not 1<=len(v)<=20: raise ValueError('Entrada invalida')
        seen.add(n)
    if not offline:
        from cp_catalogo_v08a import existe
        with open(cache+'.new','wb') as f:
            f.write(sig.strip()); f.write(raw)
        if hasattr(os,'sync'): os.sync()
        if existe(cache): os.remove(cache)
        os.rename(cache+'.new',cache)
        if hasattr(os,'sync'): os.sync()
        nv.set_i32('revision',rev); nv.commit()
    return entries

def libinstall(a):
    import sys
    from cp_catalogo_v08a import descarga,sha,hash_archivo,existe
    n=a['name']; p=LIBDIR+'/'+n+'.py'; h=a['sha256']
    data=descarga(a['path'],a['bytes'])
    if len(data)!=a['bytes'] or sha(data)!=h: raise ValueError('Hash incorrecto')
    compile(data.decode(),p,'exec')
    with open(p+'.new','wb') as f: f.write(data)
    if hash_archivo(p+'.new')!=h: raise ValueError('Error escritura')
    if hasattr(os,'sync'): os.sync()
    if existe(p):
        if existe(p+'.bak'): os.remove(p+'.bak')
        os.rename(p,p+'.bak')
    try:
        os.rename(p+'.new',p)
        if hash_archivo(p)!=h: raise ValueError('Error final')
        if hasattr(os,'sync'): os.sync()
    except Exception:
        if existe(p): os.remove(p)
        if existe(p+'.bak'): os.rename(p+'.bak',p)
        raise
    sys.modules.pop(n,None)


def module_run(name,entry):
    import sys
    try:
        libinit()
        p=LIBDIR+'/'+name+'.py'
        from cp_catalogo_v08a import existe,hash_archivo
        # Always verify against signed catalog before executing launcher modules.
        try:
            entries=libcatalog(True)
        except Exception:
            entries=libcatalog()
        a=next((x for x in entries if x['name']==name),None)
        if a is None: raise ValueError('Modulo no publicado')
        if not existe(p) or hash_archivo(p)!=a['sha256']:
            if existe(p+'.bak') and hash_archivo(p+'.bak')==a['sha256']:
                if existe(p): os.remove(p)
                os.rename(p+'.bak',p)
            else:
                entries=libcatalog()
                a=next((x for x in entries if x['name']==name),None)
                if a is None: raise ValueError('Modulo no publicado')
                libinstall(a)
        del entries,a
        gc.collect()
        m=__import__(name)
        m.elegir=elegir
        m.ejecutar_app=ejecutar_app
        getattr(m,entry)()
    except Exception as e:
        print(repr(e)); elegir('ERROR MODULO',[str(e)[:30],'Volver'])
    finally:
        sys.modules.pop(name,None)
        m=None
        gc.collect()

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
    libinit()
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
        k=elegir('V0.14a '+cp_wifi.status(),['Remote Keyboard','Aplicaciones locales','UIFlow2 temporal','UIFlow2 permanente','Configuracion','Catalogo GitHub','Configuracion WiFi','Actualizar Launcher','Bibliotecas','Modulos externos','Memoria RAM','Actualizar modulos','Copias de seguridad'],seleccion)
        if k is None: return
        seleccion=k
        if k==0:
            ejecutar_app('/flash/remote_keyboard.py')
            cp_wifi.auto()
        elif k==1: module_run('m5lib_launcher_apps','apps')
        elif k==2: temporal()
        elif k==3: modo(1); machine.reset()
        elif k==9: module_run('m5lib_launcher_hw','hardware_menu')
        elif k==8: module_run('m5lib_launcher_catalog','libmenu')
        elif k==7:
            import cp_selfupdate
            cp_selfupdate.menu(elegir)
        elif k==6: cp_wifi.menu(elegir)
        elif k==5:
            import cp_catalogo_v08a
            module_run('m5lib_launcher_catalog','depmenu')
        elif k==12:
            try:
                entries=libcatalog(True)
                for n in ('m5lib_sdcard','m5lib_storage'):
                    a=next(x for x in entries if x['name']==n)
                    from cp_catalogo_v08a import existe,hash_archivo
                    p=LIBDIR+'/'+n+'.py'
                    if not existe(p) or hash_archivo(p)!=a['sha256']: libinstall(a)
                del entries,a
                gc.collect()
                module_run('m5lib_launcher_backup','menu')
            except Exception as e: elegir('ERROR COPIA',[str(e)[:30],'Actualizar modulos'])
        elif k==11:
            try:
                libcatalog()
                elegir('CATALOGO VERIFICADO',['Volver'])
            except Exception as e: elegir('ERROR CATALOGO',[str(e)[:30],'Volver'])
        elif k==10:
            gc.collect()
            elegir('MEMORIA RAM',['Libre: %d bytes'%gc.mem_free(),'Usada: %d bytes'%gc.mem_alloc(),'Volver'])
        elif k==4:
            c=elegir('ARRANQUE',['Mostrar Launcher','Remote Keyboard','UIFlow2 (reiniciar)'])
            if c in (0,1):
                with open('/flash/launcher_mode.txt','w') as f: f.write('keyboard' if c==1 else 'menu')
                modo(0)
            elif c==2: modo(1); machine.reset()

if __name__=='__main__': ejecutar()
