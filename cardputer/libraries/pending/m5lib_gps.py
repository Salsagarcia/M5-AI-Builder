# Portable NMEA receiver, no background threads.
import time
VERSION='0.1'

class GPS:
    def __init__(self, uart):
        self.uart=uart
        self.buf=bytearray()
        self.frames=0
        self.last=None
        self.gga_time=None
        self.rmc_time=None
        self.fix=False
        self.sats=0
        self.lat=self.lon=self.alt=self.speed=None
        self.utc='--:--:--'

    def coord(self,s,h):
        v=float(s)
        d=int(v/100)
        return (d+(v-d*100)/60)*(-1 if h in ('S','W') else 1)

    def parse(self,line):
        try:
            if not line.startswith(b'$'): return
            body,check=line[1:].strip().split(b'*')
            c=0
            for b in body: c^=b
            if len(check)!=2 or c!=int(check,16): return
            f=body.decode().split(',')
            kind=f[0][-3:]
            self.frames+=1
            self.last=time.ticks_ms()
            if kind=='GGA':
                self.gga_time=self.last
                self.fix=int(f[6] or '0')>0
                self.sats=int(f[7] or '0')
                self.utc=f[1][:2]+':'+f[1][2:4]+':'+f[1][4:6] if f[1] else '--:--:--'
                if self.fix:
                    self.lat=self.coord(f[2],f[3])
                    self.lon=self.coord(f[4],f[5])
                    self.alt=float(f[9]) if f[9] else None
                else:
                    self.lat=self.lon=self.alt=None
            elif kind=='RMC':
                self.rmc_time=self.last
                self.speed=float(f[7])*1.852 if f[2]=='A' and f[7] else None
        except (ValueError,IndexError,UnicodeError):
            return

    def poll(self):
        n=self.uart.any()
        if n:
            data=self.uart.read(min(n,512))
            if data:
                for b in data:
                    if b==36: self.buf=bytearray(b'$')
                    elif b==10:
                        self.parse(bytes(self.buf)); self.buf=bytearray()
                    elif len(self.buf)<160: self.buf.append(b)
                    else: self.buf=bytearray()
        now=time.ticks_ms()
        if self.gga_time is None or time.ticks_diff(now,self.gga_time)>3000:
            self.fix=False; self.lat=self.lon=self.alt=None; self.sats=0
        if self.rmc_time is None or time.ticks_diff(now,self.rmc_time)>3000:
            self.speed=None
        return self.last is not None and time.ticks_diff(now,self.last)<3000
