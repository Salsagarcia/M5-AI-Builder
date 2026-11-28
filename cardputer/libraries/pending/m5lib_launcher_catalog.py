import M5,time,gc,os,esp32,machine
VERSION='0.1'
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




