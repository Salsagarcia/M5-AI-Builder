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
                    from cp_catalogo_v08a import existe
                    if existe(ruta+'.deps.json'): os.remove(ruta+'.deps.json')
                except OSError as e: print('Error borrado:',e); elegir('ERROR AL BORRAR',['Volver'])


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

def libcatalog():
    import json,binascii
    from cp_catalogo_v08a import descarga,KEY
    from cp_ecdsa import verificar
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

def versionnum(v):
    if not isinstance(v,str) or not 1<=len(v)<=20: raise ValueError('Version invalida')
    parts=v.split('.')
    if any(not x or any(c not in '0123456789' for c in x) for x in parts): raise ValueError('Version invalida')
    nums=[int(x) for x in parts]
    while len(nums)>1 and nums[-1]==0: nums.pop()
    return tuple(nums)

def depcatalog():
    import cp_catalogo_v08a as cat
    apps=cat.validar(cat.descarga('releases/latest/manifest.json',8192),cat.descarga('releases/latest/manifest.sig',256))
    for a in apps:
        deps=a.get('dependencies',[])
        if not isinstance(deps,list) or len(deps)>16: raise ValueError('Dependencias invalidas')
        seen=set()
        for d in deps:
            if not isinstance(d,dict) or not libname(d['name']) or d['name'] in seen: raise ValueError('Dependencia invalida')
            seen.add(d['name']); versionnum(d['min_version'])
    return apps

def depmenu():
    import cp_catalogo_v08a as cat
    try:
        apps=depcatalog(); sel=0
        while True:
            k=elegir('CATALOGO CARDPUTER',[a['name'][:19]+' '+cat.situacion(a) for a in apps] or ['Sin apps'],sel)
            if k is None or not apps: return
            sel=k; a=apps[k]; deps=a.get('dependencies',[])
            plan=[]
            if deps:
                libs={b['name']:b for b in libcatalog()}
                for d in deps:
                    b=libs.get(d['name'])
                    if b is None or versionnum(b['version'])<versionnum(d['min_version']): raise ValueError('Falta '+d['name'])
                    p=LIBDIR+'/'+b['name']+'.py'
                    if not cat.existe(p) or cat.hash_archivo(p)!=b['sha256']: plan.append(b)
            st=cat.situacion(a)
            if elegir(a['name'][:30],[st+' '+a['version'],'Dependencias: %d'%len(deps),'Volver'])!=0: continue
            if plan:
                if elegir('DEPENDENCIAS NECESARIAS',[b['name']+' '+b['version'] for b in plan]+['Continuar'])!=len(plan): continue
                if elegir('CONFIRMAR INSTALACION',['Cancelar','Instalar conjunto'])!=1: continue
                for b in plan: libinstall(b)
            if st!='OK': cat.instalar(a)
            receipt(a)
            elegir('Instalacion correcta',['Volver'])
    except Exception as e:
        print(repr(e)); elegir('ERROR CATALOGO',[str(e)[:30],'Volver'])

# Local dependency receipts bound to installed application hashes.
def receipt(a):
    import json
    from cp_catalogo_v08a import hash_archivo,existe
    p='/flash/apps/'+a['name']+'.py'
    if not existe(p) or hash_archivo(p)!=a['sha256']: return False
    if 'dependencies' not in a: return False
    q=p+'.deps.json'
    with open(q+'.new','w') as f:
        json.dump({'sha256':a['sha256'],'dependencies':a['dependencies']},f)
    if hasattr(os,'sync'): os.sync()
    if existe(q): os.remove(q)
    os.rename(q+'.new',q)
    if hasattr(os,'sync'): os.sync()
    return True

def localdeps(p):
    import json
    from cp_catalogo_v08a import hash_archivo
    try:
        with open(p+'.deps.json') as f: d=json.load(f)
        if d['sha256']!=hash_archivo(p): return None
        deps=d['dependencies']
        if not isinstance(deps,list) or len(deps)>16: return None
        for a in deps:
            if not libname(a['name']): return None
            versionnum(a['min_version'])
        return deps
    except Exception: return None

def depstatus():
    from cp_catalogo_v08a import existe
    rows=[]
    for f in sorted(os.listdir('/flash/apps')):
        if not f.endswith('.py'): continue
        deps=localdeps('/flash/apps/'+f)
        if deps is None: rows.append(f+': sin ficha')
        else:
            missing=[d['name'] for d in deps if not existe(LIBDIR+'/'+d['name']+'.py')]
            rows.append(f+(': faltan %d'%len(missing) if missing else ': OK presencia'))
    elegir('DEPENDENCIAS LOCALES',rows or ['Sin apps'])

def depmigrate():
    try:
        count=0
        for a in depcatalog():
            if receipt(a): count+=1
        elegir('FICHAS ACTUALIZADAS',[str(count)+' aplicaciones','Volver'])
    except Exception as e: elegir('ERROR FICHAS',[str(e)[:30],'Volver'])

def libcanremove(n):
    for f in os.listdir('/flash/apps'):
        if not f.endswith('.py'): continue
        deps=localdeps('/flash/apps/'+f)
        if deps is None or any(d['name']==n for d in deps): return False
    return True


def libmenu():
    import json,binascii,sys
    from cp_catalogo_v08a import descarga,sha,hash_archivo,existe,KEY
    from cp_ecdsa import verificar
    try:
        libinit()
        k=elegir('BIBLIOTECAS',['Catalogo GitHub','Bibliotecas locales','Registrar apps existentes','Diagnostico local','Volver'])
        if k==2: depmigrate(); return
        if k==3: depstatus(); return
        if k==1:
            names=sorted(f[:-3] for f in os.listdir(LIBDIR) if f.endswith('.py') and libname(f[:-3]))
            i=elegir('BIBLIOTECAS LOCALES',names or ['Sin bibliotecas'])
            if i is None or not names: return
            n=names[i]; p=LIBDIR+'/'+n+'.py'
            if elegir(n,['Volver','Desinstalar'])==1 and elegir('CONFIRMAR BORRADO',['Cancelar','Borrar'])==1:
                if not libcanremove(n):
                    elegir('Biblioteca protegida',['En uso o app sin ficha','Volver']); return
                if existe(p+'.bak'): os.remove(p+'.bak')
                os.remove(p)
                sys.modules.pop(n,None)
            return
        if k!=0: return
        entries=libcatalog()
        labels=[]
        for a in entries:
            p=LIBDIR+'/'+a['name']+'.py'
            status='INSTALAR' if not existe(p) else ('OK' if hash_archivo(p)==a['sha256'] else 'ACTUALIZAR')
            labels.append(a['name']+' '+status)
        i=elegir('CATALOGO BIBLIOTECAS',labels or ['Sin bibliotecas'])
        if i is None or not entries: return
        a=entries[i]; n=a['name']; p=LIBDIR+'/'+n+'.py'; h=a['sha256']
        if existe(p) and hash_archivo(p)==h: return
        if elegir(n+' '+a['version'],['Cancelar','Instalar / actualizar'])!=1: return
        libinstall(a)
        elegir('BIBLIOTECA INSTALADA',['Volver'])
    except Exception as e:
        print(repr(e)); elegir('ERROR BIBLIOTECAS',[str(e)[:30],'Volver'])




class PaHub:
    def __init__(self, bus, address=0x70):
        if not 0x70 <= address <= 0x77:
            raise ValueError('Direccion PaHub invalida')
        self.bus = bus
        self.address = address

    def disable(self):
        self.bus.writeto(self.address, b'\x00')

    def select(self, channel):
        if type(channel) != int or not 0 <= channel < 6:
            raise ValueError('Canal invalido')
        self.bus.writeto(self.address, bytes([1 << channel]))

    def scan(self):
        self.disable()
        try:
            direct = self.bus.scan()
            channels = []
            for ch in range(6):
                self.select(ch)
                channels.append([a for a in self.bus.scan() if a not in direct])
            return direct, channels
        finally:
            self.disable()

# Persistent module profiles. Configuration only; never drives pins.
HWFILE='/flash/m5_hardware.json'
HWDEFAULT={'tof':{'mode':'pahub','hub':112,'channel':0,'address':41},'rfid':{'mode':'pahub','hub':112,'channel':1,'address':40},'gps':{'baud':115200,'rx':2,'tx':1},'ir':{'rx':2,'tx':1},'i2c_freq':100000}
def hwload():
    import json
    for path in (HWFILE,HWFILE+'.bak'):
        try:
            with open(path) as f: d=json.load(f)
            if d.get('schema')!=1: continue
            c=d['profiles']
            for n in ('tof','rfid'):
                a=c[n]
                if a['mode'] not in ('direct','pahub') or a['hub'] not in range(112,120) or a['channel'] not in range(6) or a['address']!=HWDEFAULT[n]['address']: raise ValueError('I2C')
            for n in ('gps','ir'):
                if (c[n]['rx'],c[n]['tx']) not in ((1,2),(2,1)): raise ValueError('GPIO')
            if c['gps']['baud'] not in (9600,115200) or c['i2c_freq'] not in (100000,400000): raise ValueError('Frecuencia')
            return c
        except (OSError,ValueError,KeyError,TypeError,AttributeError): pass
    return json.loads(json.dumps(HWDEFAULT))

def hwsave(c):
    import json
    from cp_catalogo_v08a import existe
    with open(HWFILE+'.new','w') as f: json.dump({'schema':1,'profiles':c},f)
    if hasattr(os,'sync'): os.sync()
    if existe(HWFILE):
        if existe(HWFILE+'.bak'): os.remove(HWFILE+'.bak')
        os.rename(HWFILE,HWFILE+'.bak')
    os.rename(HWFILE+'.new',HWFILE)
    if hasattr(os,'sync'): os.sync()

def hwprofiles():
    c=hwload()
    while True:
        k=elegir('PERFILES DE MODULOS',['Mini ToF','RFID 2','GPS UART','IR GPIO','Frecuencia I2C','Guardar perfiles','Restaurar defaults','Volver sin guardar'])
        if k is None or k==7: return
        if k==5:
            hwsave(c); elegir('PERFILES GUARDADOS',['Volver']); return
        if k==6:
            if elegir('RESTAURAR DEFAULTS',['Cancelar','Restaurar'])==1:
                import json
                c=json.loads(json.dumps(HWDEFAULT))
            continue
        if k==4:
            i=elegir('FRECUENCIA I2C',['100 kHz','400 kHz'],int(c['i2c_freq']==400000))
            if i is not None: c['i2c_freq']=(100000,400000)[i]
            continue
        n=('tof','rfid','gps','ir')[k]; a=c[n]
        while True:
            if k<2:
                i=elegir(n.upper(),['Modo: '+a['mode'],'PaHub: 0x%02X'%a['hub'],'Canal: %d'%a['channel'],'Direccion: 0x%02X'%a['address'],'Volver'])
                if i is None or i>=3: break
                if i==0:
                    j=elegir('CONEXION',['Directo','PaHub'],int(a['mode']=='pahub'))
                    if j is not None: a['mode']=('direct','pahub')[j]
                elif i==1:
                    j=elegir('DIRECCION PAHUB',['0x%02X'%x for x in range(112,120)],a['hub']-112)
                    if j is not None: a['hub']=112+j
                else:
                    j=elegir('CANAL',['CH%d'%x for x in range(6)],a['channel'])
                    if j is not None: a['channel']=j
            else:
                opts=['RX G%d TX G%d'%(a['rx'],a['tx'])]
                if k==2: opts.append('Baudios: %d'%a['baud'])
                i=elegir(n.upper(),opts+['Volver'])
                if i is None or i==len(opts): break
                if i==0:
                    j=elegir('PINES',['RX G2 TX G1','RX G1 TX G2'],int(a['rx']==1))
                    if j is not None: a['rx'],a['tx']=((2,1),(1,2))[j]
                else:
                    j=elegir('BAUDIOS',['9600','115200'],int(a['baud']==115200))
                    if j is not None: a['baud']=(9600,115200)[j]

def hardware_menu():
    from machine import Pin, SoftI2C
    freq=hwload()['i2c_freq']
    hints={0x28:'RFID2?',0x29:'ToF?',0x23:'BH1750?',0x38:'AHT20?',0x44:'SHT3x?',0x48:'ADS1115?',0x68:'IMU/RTC?'}
    def describe(a):
        return '0x%02X %d %s'%(a,a,hints.get(a,''))
    while True:
        k=elegir('MODULOS EXTERNOS',['Escanear I2C','Escanear PaHub','Probar canal PaHub','Frecuencia: %d kHz'%(freq//1000),'Pines Grove','Perfiles de modulos','Volver'])
        if k is None or k==6: return
        if k==5:
            try: hwprofiles(); freq=hwload()['i2c_freq']
            except Exception as e: elegir('ERROR PERFILES',[str(e)[:30],'Volver'])
            continue
        if k==3:
            v=elegir('FRECUENCIA I2C',['100 kHz','400 kHz'])
            if v is not None: freq=(100000,400000)[v]
            continue
        if k==4:
            elegir('GROVE CARDPUTER V1.1',['Negro: GND','Rojo: 5V','Amarillo: SDA G2','Blanco: SCL G1','Logica 3.3V','Volver'])
            continue
        bus=None
        hub=None
        try:
            bus=SoftI2C(sda=Pin(2),scl=Pin(1),freq=freq,timeout=50000)
            addresses=bus.scan()
            if k==0:
                elegir('I2C: %d dispositivos'%len(addresses),[describe(a) for a in addresses] or ['Ningun dispositivo'])
                continue
            candidates=[a for a in addresses if 0x70<=a<=0x77]
            if not candidates:
                elegir('PAHUB NO DETECTADO',['Volver'])
                continue
            i=elegir('CONFIRMAR DIRECCION PAHUB',['PaHub 0x%02X'%a for a in candidates]+['Cancelar'])
            if i is None or i==len(candidates): continue
            hub=PaHub(bus,candidates[i])
            if k==1:
                direct,channels=hub.scan()
                while True:
                    labels=['CH%d: '%j+(','.join('%02X'%a for a in c) if c else 'Libre') for j,c in enumerate(channels)]
                    i=elegir('PAHUB 0x%02X'%hub.address,labels+['Bus directo','Volver'])
                    if i is None or i==7: break
                    data=direct if i==6 else channels[i]
                    elegir('BUS DIRECTO' if i==6 else 'CANAL %d'%i,[describe(a) for a in data] or ['Sin dispositivos'])
            else:
                i=elegir('PROBAR CANAL',['CH%d'%j for j in range(6)])
                if i is not None:
                    hub.disable()
                    direct=bus.scan()
                    hub.select(i)
                    data=[a for a in bus.scan() if a not in direct]
                    hub.disable()
                    elegir('CANAL %d'%i,[describe(a) for a in data] or ['Sin dispositivos'])
        except Exception as e:
            print(repr(e)); elegir('ERROR I2C',[str(e)[:30],'Volver'])
        finally:
            try:
                if hub is not None: hub.disable()
            except Exception as e: print('PaHub cierre:',repr(e))
            if bus is not None and hasattr(bus,'deinit'): bus.deinit()

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
        k=elegir('V0.13a '+cp_wifi.status(),['Remote Keyboard','Aplicaciones locales','UIFlow2 temporal','UIFlow2 permanente','Configuracion','Catalogo GitHub','Configuracion WiFi','Actualizar Launcher','Bibliotecas','Modulos externos'],seleccion)
        if k is None: return
        seleccion=k
        if k==0:
            ejecutar_app('/flash/remote_keyboard.py')
            cp_wifi.auto()
        elif k==1: apps()
        elif k==2: temporal()
        elif k==3: modo(1); machine.reset()
        elif k==9: hardware_menu()
        elif k==8: libmenu()
        elif k==7:
            import cp_selfupdate
            cp_selfupdate.menu(elegir)
        elif k==6: cp_wifi.menu(elegir)
        elif k==5:
            import cp_catalogo_v08a
            depmenu()
        elif k==4:
            c=elegir('ARRANQUE',['Mostrar Launcher','Remote Keyboard','UIFlow2 (reiniciar)'])
            if c in (0,1):
                with open('/flash/launcher_mode.txt','w') as f: f.write('keyboard' if c==1 else 'menu')
                modo(0)
            elif c==2: modo(1); machine.reset()

if __name__=='__main__': ejecutar()
