import os,json,hashlib,re
from pathlib import Path
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import ec,utils
PUBLIC=bytes.fromhex('04acb5836c64274024f7905abe43aa880ba9e4cd653223e7854e3f455697944a61b7100c09fd07a2396e7e91a5485ca474a811bac2ba5b7a2e699be49e26035181')
def check(ok):
    if not ok: raise ValueError('Validacion Launcher fallida')
def verify(pub,raw,sig):
    check(len(sig)==64)
    pub.verify(utils.encode_dss_signature(int.from_bytes(sig[:32],'big'),int.from_bytes(sig[32:],'big')),raw,ec.ECDSA(hashes.SHA256()))
def main():
    version=os.environ['LAUNCHER_VERSION']
    check(re.fullmatch(r'0\.[89][a-z]',version) is not None)
    base=Path('cardputer/launcher'); root=base/'releases/latest'
    mf=root/'manifest.json'; sf=root/'manifest.sig'; dest=root/'launcher.py'
    pub=ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),PUBLIC)
    check(mf.exists()==sf.exists()==dest.exists())
    rev=0
    if mf.exists():
        raw=mf.read_bytes(); verify(pub,raw,bytes.fromhex(sf.read_text().strip()))
        m=json.loads(raw); rev=m['revision']
        check(m['device']=='cardputer_v1_1' and m['schema']==1 and m['kind']=='launcher' and m['path']=='launcher/releases/latest/launcher.py')
        check(type(rev) is int and 1<=rev<2147483647 and version>m['version'])
        old=dest.read_bytes(); check(len(old)==m['bytes'] and hashlib.sha256(old).hexdigest()==m['sha256'])
    p=base/'pending'/'launcher.py'; check(not p.is_symlink() and not dest.is_symlink())
    b=p.read_bytes(); check(0<len(b)<=32768); compile(b.decode('utf-8'),str(p),'exec')
    check(('V'+version+' ') in b.decode('utf-8'))
    m=dict(device='cardputer_v1_1',schema=1,kind='launcher',revision=rev+1,version=version,path='launcher/releases/latest/launcher.py',bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
    raw=(json.dumps(m,indent=2)+'\n').encode(); check(len(raw)<=2048)
    key=serialization.load_pem_private_key(os.environ['M5_SIGNING_KEY'].encode(),password=os.environ['M5_SIGNING_PASSWORD'].encode())
    check(isinstance(key,ec.EllipticCurvePrivateKey) and isinstance(key.curve,ec.SECP256R1))
    check(key.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)==PUBLIC)
    r,s=utils.decode_dss_signature(key.sign(raw,ec.ECDSA(hashes.SHA256())))
    sig=r.to_bytes(32,'big')+s.to_bytes(32,'big'); verify(pub,raw,sig)
    root.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(b); mf.write_bytes(raw); sf.write_text(sig.hex()+'\n',encoding='ascii')
if __name__=='__main__': main()
