import os,gc,json
from m5lib_storage import Storage,exists,join,mkdir,copyfile,sync
from cp_catalogo_v08a import hash_archivo
VERSION='0.1'
ROOTS={'apps':'/flash/apps','libs':'/flash/m5_libs','data':'/flash/m5_data','config':'/flash'}
CONFIG=('m5_hardware.json','launcher_mode.txt')
def allowed(group,n):
    if not n or n in ('.','..') or '/' in n or chr(92) in n or chr(0) in n: return False
    if group=='config': return n in CONFIG
    if group=='apps': return n.endswith('.py') or n.endswith('.py.deps.json')
    if group=='libs': return n.startswith('m5lib_') and n.endswith('.py')
    return not n.endswith(('.m5part','.new'))
def walk(path,prefix='',depth=0):
    if depth>12: raise ValueError('Demasiados niveles')
    for n in sorted(os.listdir(path)):
        p=join(path,n); rel=prefix+n
        if os.stat(p)[0]&0x4000:
            yield from walk(p,rel+'/',depth+1)
        elif allowed('data',n): yield rel
def target(root,rel,create=False):
    parts=rel.split('/')
    if len(parts)>13: raise ValueError('Ruta larga')
    for i,n in enumerate(parts):
        root=join(root,n)
        if create and i<len(parts)-1 and not exists(root): mkdir(root)
    return root
def backup(root):
    i=0
    while exists(root+'/backup_%03d'%i): i+=1
    dst=root+'/backup_%03d'%i; mkdir(dst)
    count=0
    with open(dst+'/index.jsonl','w') as f:
        for group,src in ROOTS.items():
            mkdir(dst+'/'+group)
            if not exists(src): continue
            names=walk(src) if group=='data' else (n for n in os.listdir(src) if allowed(group,n))
            for n in names:
                p=target(src,n)
                if os.stat(p)[0]&0x4000: continue
                q=target(dst+'/'+group,n,True)
                copyfile(p,q)
                f.write(json.dumps([group,n,hash_archivo(q)])+'\n')
                count+=1
                gc.collect()
    sync()
    with open(dst+'/complete','w') as f: f.write(str(count))
    sync()
    elegir('COPIA COMPLETA',[dst.split('/')[-1],'%d archivos'%count,'Volver'])
def records(src):
    with open(src+'/index.jsonl') as f:
        for line in f:
            g,n,h=json.loads(line)
            if g not in ROOTS or (g!='data' and not allowed(g,n)) or not allowed(g,n.split('/')[-1]): raise ValueError('Ruta invalida')
            p=target(src+'/'+g,n)
            if hash_archivo(p)!=h: raise ValueError('Hash incorrecto')
            yield g,n,h,p
def restore(src):
    with open(src+'/complete') as f: expected=int(f.read())
    count=sum(1 for _ in records(src))
    if count!=expected: raise ValueError('Copia incompleta')
    if elegir('RESTAURAR DATOS',['Cancelar','Solo archivos ausentes'])!=1: return
    restored=0; skipped=0
    for g,n,h,p in records(src):
        # Executable files and configuration are retained in backup but not blindly trusted.
        if g!='data': skipped+=1; continue
        q=target(ROOTS[g],n,True)
        if exists(q): skipped+=1; continue
        copyfile(p,q); restored+=1
    elegir('RESTAURACION',['Nuevos: %d'%restored,'Omitidos: %d'%skipped,'Volver'])
def menu():
    s=Storage()
    try:
        s.mount()
        root='/sd/m5_backups'
        if not exists(root): mkdir(root)
        while True:
            k=elegir('COPIAS DE SEGURIDAD',['Crear copia','Verificar / restaurar datos','Volver'])
            if k is None or k==2: return
            if k==0: backup(root)
            else:
                names=sorted(n for n in os.listdir(root) if n.startswith('backup_') and exists(join(root,n)+'/complete'))
                i=elegir('COPIAS COMPLETAS',names or ['Sin copias'])
                if i is not None and names: restore(join(root,names[i]))
    except Exception as e: elegir('ERROR COPIA',[str(e)[:30],'Volver'])
    finally: s.close()
