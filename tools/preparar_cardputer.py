import os, json, hashlib, re
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

PUBLIC=bytes.fromhex('04acb5836c64274024f7905abe43aa880ba9e4cd653223e7854e3f455697944a61b7100c09fd07a2396e7e91a5485ca474a811bac2ba5b7a2e699be49e26035181')
def check(ok):
    if not ok: raise ValueError('Validacion Cardputer fallida')
def verify(pub,raw,sig):
    check(len(sig)==64)
    pub.verify(utils.encode_dss_signature(int.from_bytes(sig[:32],'big'),int.from_bytes(sig[32:],'big')),raw,ec.ECDSA(hashes.SHA256()))
def name_ok(n):
    return isinstance(n,str) and re.fullmatch(r'[a-z][a-z0-9_]{0,39}',n)
def version_ok(v):
    return isinstance(v,str) and re.fullmatch(r'[0-9]+(?:\.[0-9]+)*',v) and len(v)<=20
def main():
    name=os.environ['APP_NAME']; version=os.environ['APP_VERSION']
    check(name_ok(name) and version_ok(version))
    base=Path('cardputer'); root=base/'releases/latest'
    mf=root/'manifest.json'; sf=root/'manifest.sig'
    pub=ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),PUBLIC)
    check(mf.exists()==sf.exists())
    if mf.exists():
        raw=mf.read_bytes(); verify(pub,raw,bytes.fromhex(sf.read_text().strip()))
        m=json.loads(raw)
        check(m['device']=='cardputer_v1_1' and m['schema']==1 and type(m['revision']) is int and 1<=m['revision']<2147483647)
    else:
        check(not (base/'apps').exists() or not list((base/'apps').iterdir()))
        m=dict(device='cardputer_v1_1',schema=1,revision=0,applications=[])
    apps=m['applications']; check(isinstance(apps,list) and len(apps)<=40)
    seen=set()
    for a in apps:
        n=a['name']; check(name_ok(n) and n not in seen and a['path']=='apps/'+n+'.py' and version_ok(a['version']))
        seen.add(n); p=base/a['path']; check(not p.is_symlink())
        b=p.read_bytes(); check(0<len(b)<=32768 and len(b)==a['bytes'] and hashlib.sha256(b).hexdigest()==a['sha256'])
    previous=next((a for a in apps if a['name']==name),None)
    def numeric(v):
        parts=[int(x) for x in v.split('.')]
        while len(parts)>1 and parts[-1]==0: parts.pop()
        return tuple(parts)
    if previous is None:
        check(len(apps)<40)
    else:
        check(numeric(version)>numeric(previous['version']))
    p=base/'pending'/(name+'.py'); dest=base/'apps'/(name+'.py')
    check(not p.is_symlink() and dest.exists()==(previous is not None) and not dest.is_symlink())
    b=p.read_bytes(); check(0<len(b)<=32768); compile(b.decode('utf-8'),str(p),'exec')
    entry=dict(name=name,version=version,path='apps/'+name+'.py',bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
    # Dependencias declaradas junto al codigo; incluidas en la firma.
    dp=p.with_suffix('.deps.json')
    deps=json.loads(dp.read_text()) if dp.exists() else []
    check(isinstance(deps,list) and len(deps)<=16)
    names=set()
    for d in deps:
        check(isinstance(d,dict) and set(d)=={'name','min_version'})
        n=d['name']; check(name_ok(n) and n.startswith('m5lib_') and len(n)>6 and n not in names and version_ok(d['min_version']))
        names.add(n)
    if deps:
        lr=base/'libraries/releases/latest'
        rawlib=(lr/'manifest.json').read_bytes()
        verify(pub,rawlib,bytes.fromhex((lr/'manifest.sig').read_text().strip()))
        lm=json.loads(rawlib)
        check(lm['device']=='cardputer_v1_1' and lm['kind']=='libraries' and lm['schema']==1)
        libs={a['name']:a for a in lm['libraries']}
        for d in deps:
            a=libs[d['name']]
            check(numeric(a['version'])>=numeric(d['min_version']))
        entry['dependencies']=deps
    if previous is None: apps.append(entry)
    else: apps[apps.index(previous)]=entry
    m['revision']+=1
    raw=(json.dumps(m,indent=2)+'\n').encode(); check(len(raw)<=8192)
    key=serialization.load_pem_private_key(os.environ['M5_SIGNING_KEY'].encode(),password=os.environ['M5_SIGNING_PASSWORD'].encode())
    check(isinstance(key,ec.EllipticCurvePrivateKey) and isinstance(key.curve,ec.SECP256R1))
    check(key.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)==PUBLIC)
    r,s=utils.decode_dss_signature(key.sign(raw,ec.ECDSA(hashes.SHA256())))
    sig=r.to_bytes(32,'big')+s.to_bytes(32,'big'); verify(pub,raw,sig)
    root.mkdir(parents=True,exist_ok=True); dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(b); mf.write_bytes(raw); sf.write_text(sig.hex()+'\n',encoding='ascii')
    print('Cardputer revision:',m['revision'])
if __name__=='__main__': main()
