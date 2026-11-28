# SDHC/SDXC block device, single-sector transactions, bounded waits.
import time
VERSION='0.1'
def crc16(data):
    c=0
    for b in data:
        c^=b<<8
        for _ in range(8):
            c=((c<<1)^0x1021)&65535 if c&32768 else (c<<1)&65535
    return c
class SDCard:
    def __init__(self,spi,cs):
        self.spi=spi; self.cs=cs; self.writable=False
        cs(1); spi.write(b'\xff'*16)
        for _ in range(5):
            if self.command(0,0,0x95)[0]==1: break
        else: raise OSError('CMD0')
        r,d=self.command(8,0x1aa,0x87,4)
        if r!=1 or d[-2:]!=b'\x01\xaa': raise OSError('CMD8')
        for _ in range(100):
            if self.command(55,0)[0] not in (0,1): raise OSError('CMD55')
            r,_=self.command(41,0x40000000)
            if r==0: break
            if r!=1: raise OSError('ACMD41')
            time.sleep_ms(50)
        else: raise OSError('ACMD41 timeout')
        r,d=self.command(58,0,extra=4)
        if r!=0 or d[0]&192!=192: raise OSError('SDHC required')
        csd=bytearray(16)
        self.read_data(9,0,csd)
        if csd[0]>>6!=1: raise OSError('CSD version')
        self.sectors=(((csd[7]&63)<<16 | csd[8]<<8 | csd[9])+1)*1024
    def release(self):
        self.cs(1); self.spi.write(b'\xff')
    def ready(self,ms=2000):
        t=time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(),t)<ms:
            if self.spi.read(1,255)[0]==255: return
        raise OSError('SD busy timeout')
    def send(self,n,arg,crc=1):
        self.cs(0); self.ready()
        self.spi.write(bytes([64+n,(arg>>24)&255,(arg>>16)&255,(arg>>8)&255,arg&255,crc]))
        for _ in range(100):
            r=self.spi.read(1,255)[0]
            if r<128: return r
        raise OSError('CMD%d timeout'%n)
    def command(self,n,arg,crc=1,extra=0):
        try:
            r=self.send(n,arg,crc)
            return r,self.spi.read(extra,255) if extra else b''
        finally: self.release()
    def read_data(self,n,arg,buf):
        try:
            if self.send(n,arg)!=0: raise OSError('CMD%d read'%n)
            t=time.ticks_ms()
            while time.ticks_diff(time.ticks_ms(),t)<1000:
                token=self.spi.read(1,255)[0]
                if token==254: break
                if token!=255: raise OSError('Read token')
            else: raise OSError('Read timeout')
            self.spi.readinto(buf,255)
            c=self.spi.read(2,255)
            if crc16(buf)!=(c[0]<<8|c[1]): raise OSError('Read CRC')
        finally: self.release()
    def bounds(self,n,buf):
        if len(buf)%512 or n<0 or n+len(buf)//512>self.sectors: raise OSError(22)
    def readblocks(self,n,buf):
        self.bounds(n,buf)
        mv=memoryview(buf)
        for i in range(len(buf)//512): self.read_data(17,n+i,mv[i*512:(i+1)*512])
        return 0
    def writeblocks(self,n,buf):
        if not self.writable: raise OSError(30)
        self.bounds(n,buf)
        mv=memoryview(buf)
        for i in range(len(buf)//512):
            b=mv[i*512:(i+1)*512]
            try:
                if self.send(24,n+i)!=0: raise OSError('CMD24')
                self.spi.write(b'\xff\xfe'); self.spi.write(b)
                c=crc16(b); self.spi.write(bytes([c>>8,c&255]))
                for _ in range(100):
                    r=self.spi.read(1,255)[0]
                    if r!=255: break
                if r&31!=5: raise OSError('Write rejected')
                self.ready(3000)
            finally: self.release()
            r,d=self.command(13,0,extra=1)
            if r or d[0]: raise OSError('Write status')
        return 0
    def ioctl(self,op,arg):
        if op in (1,2,3): return 0
        if op==4: return self.sectors
        if op==5: return 512
        return None
