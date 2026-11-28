import M5,time,os
from hardware import MatrixKeyboard
from m5lib_storage import Storage, exists, join, copyfile, movefile, mkdir, remove, rename, space, entries, sync
from m5lib_textinput import read_text
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


def notice(s):
    elegir('INFORMACION',[str(s)[:36],'Volver'])
def name_input(initial=''):
    return read_text('Nombre',initial,32,'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-. ',lambda s: bool(s.strip()) and s not in ('.','..') and not s.endswith((' ','.')))
def preview(p):
    with open(p,'rb') as f:
        while True:
            b=f.read(144)
            if not b: notice('Fin de archivo'); return
            s=''.join(chr(c) if 32<=c<127 else ' ' for c in b)
            rows=[s[i:i+30] for i in range(0,len(s),30)]
            if elegir('VISTA TEXTO',rows+['Siguiente','Volver'])!=len(rows): return
def browse(root,other):
    path=root
    while True:
        try:
            items=entries(path)
            names=[n for n,d in items]; dirs=[d for n,d in items]
            k=elegir(path,['Subir / salir','Nueva carpeta']+[('[D] ' if d else '[F] ')+n for n,d in zip(names,dirs)])
            if k is None or k==0:
                if path==root: return
                path=path.rsplit('/',1)[0]; continue
            if k==1:
                n=name_input()
                if n: mkdir(join(path,n))
                continue
            n=names[k-2]; src=join(path,n)
            if dirs[k-2]:
                path=src; continue
            a=elegir(n,['Ver texto','Informacion','Renombrar','Copiar a otro medio','Mover a otro medio','Eliminar','Volver'])
            if a==0: preview(src)
            elif a==1: notice('%d bytes'%os.stat(src)[6])
            elif a==2:
                nn=name_input(n)
                if nn and nn!=n:
                    dst=join(path,nn)
                    if exists(dst): raise ValueError('Destino ya existe')
                    rename(src,dst)
            elif a in (3,4):
                if other is None: raise ValueError('Otro medio no disponible')
                dst=join(other,n)
                if elegir('Destino: '+dst,['Cancelar','Confirmar'])==1:
                    if a==4: movefile(src,dst)
                    else: copyfile(src,dst)
                    notice('Operacion OK')
            elif a==5 and elegir('BORRAR '+n,['Cancelar','Confirmar'])==1:
                remove(src)
            sync()
        except Exception as e: notice(str(e))
def main():
    st=Storage()
    try:
        while True:
            k=elegir('ARCHIVOS V0.4',['Memoria interna','Tarjeta microSD','Espacio disponible','Desmontar microSD','Volver'])
            if k is None or k==4: return
            try:
                if k==0: browse(st.flash,st.sdroot if st.mounted else None)
                elif k==1: browse(st.mount(),st.flash)
                elif k==2:
                    rows=['Flash libre %.1f MiB'%(space(st.flash)[1]/1048576)]
                    if st.mounted: rows.append('SD libre %.1f MiB'%(space(st.sdroot)[1]/1048576))
                    elegir('ESPACIO LIBRE',rows+['Volver'])
                elif k==3:
                    st.close(); notice('SD desmontada')
            except Exception as e: notice(str(e))
    finally: st.close()
main()
