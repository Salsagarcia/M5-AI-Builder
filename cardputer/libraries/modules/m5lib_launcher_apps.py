import M5,time,gc,os,esp32,machine
VERSION='0.1'
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


