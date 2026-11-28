import M5,time,os
from hardware import MatrixKeyboard
from machine import Pin,SoftSPI
from m5lib_sdcard import SDCard
BG=0x102638
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


def exists(p):
    try: os.stat(p); return True
    except OSError as e:
        if e.args[0]==2: return False
        raise
def notice(s):
    elegir('INFORMACION',[str(s)[:36],'Volver'])
def name_input():
    # Restricted portable names, selected with existing keyboard menu.
    s=''
    chars='abcdefghijklmnopqrstuvwxyz0123456789_-.' 
    while True:
        k=elegir('Nombre: '+s,['Aceptar','Borrar','Cancelar']+list(chars))
        if k is None or k==2: return None
        if k==0:
            if s and s not in ('.','..'): return s
        elif k==1: s=s[:-1]
        elif len(s)<32: s+=chars[k-3]
def join(p,n): return p+'/'+n
def preview(p):
    with open(p,'rb') as f:
        while True:
            b=f.read(144)
            if not b: notice('Fin de archivo'); return
            s=''.join(chr(c) if 32<=c<127 else ' ' for c in b)
            rows=[s[i:i+30] for i in range(0,len(s),30)]
            if elegir('VISTA TEXTO',rows+['Siguiente','Volver'])!=len(rows): return
def copyfile(src,dst):
    if exists(dst): raise ValueError('Destino ya existe')
    tmp=dst+'.m5part'
    if exists(tmp): raise ValueError('Temporal ya existe')
    created=False
    try:
        with open(src,'rb') as f:
            with open(tmp,'wb') as g:
                created=True
                while True:
                    b=f.read(1024)
                    if not b: break
                    if g.write(b)!=len(b): raise OSError('Escritura parcial')
        with open(src,'rb') as f:
            with open(tmp,'rb') as g:
                while True:
                    b=f.read(1024)
                    if b!=g.read(1024): raise OSError('Copia diferente')
                    if not b: break
        if hasattr(os,'sync'): os.sync()
        os.rename(tmp,dst); created=False
        if hasattr(os,'sync'): os.sync()
    finally:
        if created: os.remove(tmp)
def browse(root,other):
    path=root
    while True:
        try:
            names=sorted(os.listdir(path))
            dirs=[bool(os.stat(join(path,n))[0]&0x4000) for n in names]
            k=elegir(path,['Subir / salir','Nueva carpeta']+[('[D] ' if d else '[F] ')+n for n,d in zip(names,dirs)])
            if k is None or k==0:
                if path==root: return
                path=path.rsplit('/',1)[0]; continue
            if k==1:
                n=name_input()
                if n: os.mkdir(join(path,n))
                continue
            n=names[k-2]; src=join(path,n)
            if dirs[k-2]:
                path=src; continue
            a=elegir(n,['Ver texto','Informacion','Renombrar','Copiar a otro medio','Mover a otro medio','Eliminar','Volver'])
            if a==0: preview(src)
            elif a==1: notice('%d bytes'%os.stat(src)[6])
            elif a==2:
                nn=name_input()
                if nn:
                    dst=join(path,nn)
                    if exists(dst): raise ValueError('Destino ya existe')
                    os.rename(src,dst)
            elif a in (3,4):
                if other is None: raise ValueError('Otro medio no disponible')
                dst=join(other,n)
                if elegir('Destino: '+dst,['Cancelar','Confirmar'])==1:
                    copyfile(src,dst)
                    if a==4:
                        os.remove(src)
                        if hasattr(os,'sync'): os.sync()
                    notice('Operacion OK')
            elif a==5 and elegir('BORRAR '+n,['Cancelar','Confirmar'])==1:
                os.remove(src)
            if hasattr(os,'sync'): os.sync()
        except Exception as e: notice(str(e))
def main():
    spi=None; cs=None; mounted=False
    flash='/flash/m5_data'; sdroot='/sd/m5_data'
    try:
        if not exists(flash): os.mkdir(flash)
        while True:
            k=elegir('ARCHIVOS V0.2',['Memoria interna','Tarjeta microSD','Espacio disponible','Desmontar microSD','Volver'])
            if k is None or k==4: return
            stage='Menu archivos'
            try:
                if k==1 and not mounted:
                    stage='Detectar montaje'
                    if 'sd' in os.listdir('/'): raise OSError('SD externa ya montada')
                    stage='Inicializar SPI'
                    cs=Pin(12,Pin.OUT,value=1)
                    spi=SoftSPI(baudrate=100000,polarity=0,phase=0,sck=Pin(40),miso=Pin(39),mosi=Pin(14))
                    try:
                        stage='Inicializar tarjeta'
                        sd=SDCard(spi,cs); sd.writable=True
                        stage='Montar FAT'
                        os.mount(sd,'/sd'); mounted=True
                        stage='Crear m5_data SD'
                        if not exists(sdroot): os.mkdir(sdroot)
                    except Exception:
                        if not mounted: cs(1); spi.deinit(); spi=None
                        raise
                if k==0: browse(flash,sdroot if mounted else None)
                elif k==1: browse(sdroot,flash)
                elif k==2:
                    rows=[]
                    for label,path in [('Flash',flash),('SD','/sd')]:
                        if label=='SD' and not mounted: continue
                        s=os.statvfs(path); rows.append('%s libre %.1f MiB'%(label,s[0]*s[3]/1048576))
                    elegir('ESPACIO LIBRE',rows+['Volver'])
                elif k==3:
                    if mounted:
                        if hasattr(os,'sync'): os.sync()
                        os.umount('/sd'); mounted=False
                        cs(1); spi.deinit(); spi=None
                    notice('SD desmontada')
            except Exception as e: elegir('ERROR: '+stage,[str(e)[:36],'Volver'])
    finally:
        if mounted:
            if hasattr(os,'sync'): os.sync()
            os.umount('/sd')
        if spi is not None: cs(1); spi.deinit()
main()
