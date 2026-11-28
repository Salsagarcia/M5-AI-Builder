import time
from m5lib_storage import write_new,append,join
VERSION='0.1'
def csvrow(values):
    return (','.join('"'+str(v).replace('"','""')+'"' if v is not None else '' for v in values)+'\r\n').encode()
class Logger:
    def __init__(self,storage,medium,name,columns,interval_ms=1000):
        if not columns or interval_ms<100: raise ValueError('Configuracion invalida')
        self.path=join(storage.root(medium),name)
        self.columns=tuple(columns); self.interval=interval_ms
        self.count=0; self.elapsed=0; self.closed=False
        write_new(self.path,csvrow(('elapsed_ms',)+self.columns))
        self.last=time.ticks_ms(); self.next=self.last
    def due(self):
        return not self.closed and time.ticks_diff(time.ticks_ms(),self.next)>=0
    def record(self,values):
        if self.closed or len(values)!=len(self.columns): raise ValueError('Registro invalido')
        now=time.ticks_ms()
        self.elapsed+=time.ticks_diff(now,self.last); self.last=now
        try: append(self.path,csvrow((self.elapsed,)+tuple(values)))
        except Exception:
            self.closed=True; raise
        self.count+=1
        self.next=time.ticks_add(now,self.interval)
    def close(self):
        self.closed=True
