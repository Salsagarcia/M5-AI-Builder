import os, json, hashlib, re
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

PUBLIC = bytes.fromhex('04acb5836c64274024f7905abe43aa880ba9e4cd653223e7854e3f455697944a61b7100c09fd07a2396e7e91a5485ca474a811bac2ba5b7a2e699be49e26035181')

def check(condition):
    if not condition:
        raise ValueError('Validacion de publicacion fallida')

def verify(pub, raw, sig):
    check(len(sig)==64)
    pub.verify(utils.encode_dss_signature(int.from_bytes(sig[:32],'big'),int.from_bytes(sig[32:],'big')),raw,ec.ECDSA(hashes.SHA256()))

def main():
    name=os.environ['APP_NAME']; version=os.environ['APP_VERSION']
    check(re.fullmatch(r'[a-z][a-z0-9_]{0,39}',name) and re.fullmatch(r'[0-9][a-zA-Z0-9.]{0,19}',version))
    root=Path('releases/latest'); raw=(root/'manifest.json').read_bytes()
    pub=ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),PUBLIC)
    verify(pub,raw,bytes.fromhex((root/'manifest.sig').read_text().strip()))
    m=json.loads(raw); check(m['schema_version']==2 and type(m['revision']) is int)
    seen=set()
    for a in m['applications']:
        n=a['name']; check(re.fullmatch(r'[a-z][a-z0-9_]{0,39}',n) and n not in seen and a['path']=='apps/'+n+'.py'); seen.add(n)
        p=Path(a['path']); check(not p.is_symlink()); b=p.read_bytes(); check(len(b)==a['bytes'] and hashlib.sha256(b).hexdigest()==a['sha256'])
    previous=next((a for a in m['applications'] if a['name']==name),None)
    if previous is not None:
        def numeric(v):
            check(re.fullmatch(r'[0-9]+(?:\.[0-9]+)*',v))
            parts=[int(x) for x in v.split('.')]
            while len(parts)>1 and parts[-1]==0: parts.pop()
            return tuple(parts)
        check(numeric(version)>numeric(previous['version']))
    p=Path('pending')/(name+'.py'); check(not p.is_symlink()); b=p.read_bytes(); check(0<len(b)<=32768); b.decode('utf-8'); compile(b,str(p),'exec')
    import ast
    check(any(isinstance(n,ast.FunctionDef) and n.name=='ejecutar' for n in ast.parse(b).body))
    dest=Path('apps')/(name+'.py'); check(not dest.is_symlink() and dest.exists()==(previous is not None))
    entry=dict(name=name,version=version,path=dest.as_posix(),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
    if previous is None: m['applications'].append(entry)
    else: m['applications'][m['applications'].index(previous)]=entry
    m['revision']+=1
    raw=(json.dumps(m,ensure_ascii=False,indent=2)+'\n').encode()
    key=serialization.load_pem_private_key(os.environ['M5_SIGNING_KEY'].encode(),password=os.environ['M5_SIGNING_PASSWORD'].encode())
    check(isinstance(key,ec.EllipticCurvePrivateKey) and isinstance(key.curve,ec.SECP256R1))
    check(key.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)==PUBLIC)
    r,s=utils.decode_dss_signature(key.sign(raw,ec.ECDSA(hashes.SHA256()))); sig=r.to_bytes(32,'big')+s.to_bytes(32,'big'); verify(pub,raw,sig)
    dest.write_bytes(b); (root/'manifest.json').write_bytes(raw); (root/'manifest.sig').write_text(sig.hex()+'\n',encoding='ascii')
    print('Revision preparada:',m['revision'])
if __name__=='__main__': main()
