import os
VERSION='0.1'
def sync():
    if hasattr(os,'sync'): os.sync()
def exists(p):
    try: os.stat(p); return True
    except OSError as e:
        if e.args[0]==2: return False
        raise
def join(p,n):
    if not n or n in ('.','..') or '/' in n or '\\' in n or '\x00' in n: raise ValueError('Nombre invalido')
    return p+'/'+n
def mkdir(p):
    os.mkdir(p); sync()
def remove(p):
    os.remove(p); sync()
def rename(src,dst):
    if exists(dst): raise ValueError('Destino ya existe')
    os.rename(src,dst); sync()
def space(p):
    s=os.statvfs(p)
    return s[0]*s[2],s[0]*s[3]
def entries(p):
    return [(n,bool(os.stat(join(p,n))[0]&0x4000)) for n in sorted(os.listdir(p))]
def append(p,data):
    with open(p,'ab') as f:
        if f.write(data)!=len(data): raise OSError('Escritura parcial')
    sync()
def read(p,size=4096):
    with open(p,'rb') as f: return f.read(size)
def write_new(p,data):
    if exists(p): raise ValueError('Destino ya existe')
    with open(p,'wb') as f:
        if f.write(data)!=len(data): raise OSError('Escritura parcial')
    sync()
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

def movefile(src,dst):
    copyfile(src,dst); remove(src)
def cardputer_backend():
    from machine import Pin,SoftSPI
    from m5lib_sdcard import SDCard
    cs=Pin(12,Pin.OUT,value=1)
    spi=SoftSPI(baudrate=100000,polarity=0,phase=0,sck=Pin(40),miso=Pin(39),mosi=Pin(14))
    def close():
        cs(1); spi.deinit()
    try:
        sd=SDCard(spi,cs); sd.writable=True
        return sd,close
    except Exception:
        close(); raise
class Storage:
    def __init__(self,backend=None,flash='/flash/m5_data'):
        self.flash=flash; self.sdroot='/sd/m5_data'
        self.backend=backend or cardputer_backend
        self.mounted=False; self.device=None; self.release=None
        if not exists(flash): mkdir(flash)
    def mount(self):
        if not self.mounted:
            if 'sd' in os.listdir('/'): raise OSError('SD externa ya montada')
            self.device,self.release=self.backend()
            try: os.mount(self.device,'/sd')
            except Exception:
                self.release(); self.device=None; self.release=None; raise
            self.mounted=True
        if not exists(self.sdroot): mkdir(self.sdroot)
        return self.sdroot
    def close(self):
        if self.mounted:
            sync(); os.umount('/sd'); self.mounted=False
            release=self.release; self.release=None; self.device=None
            release()
    def root(self,medium):
        if medium=='flash': return self.flash
        if medium=='sd': return self.mount()
        raise ValueError('Medio invalido')
