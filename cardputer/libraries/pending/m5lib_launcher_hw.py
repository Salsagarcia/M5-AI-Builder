import M5,time,gc,os,esp32,machine
VERSION='0.1'
class PaHub:
    def __init__(self, bus, address=0x70):
        if not 0x70 <= address <= 0x77:
            raise ValueError('Direccion PaHub invalida')
        self.bus = bus
        self.address = address

    def disable(self):
        self.bus.writeto(self.address, b'\x00')

    def select(self, channel):
        if type(channel) != int or not 0 <= channel < 6:
            raise ValueError('Canal invalido')
        self.bus.writeto(self.address, bytes([1 << channel]))

    def scan(self):
        self.disable()
        try:
            direct = self.bus.scan()
            channels = []
            for ch in range(6):
                self.select(ch)
                channels.append([a for a in self.bus.scan() if a not in direct])
            return direct, channels
        finally:
            self.disable()

# Persistent module profiles. Configuration only; never drives pins.
HWFILE='/flash/m5_hardware.json'
HWDEFAULT={'tof':{'mode':'pahub','hub':112,'channel':0,'address':41},'rfid':{'mode':'pahub','hub':112,'channel':1,'address':40},'gps':{'baud':115200,'rx':2,'tx':1},'ir':{'rx':2,'tx':1},'i2c_freq':100000}
def hwload():
    import json
    for path in (HWFILE,HWFILE+'.bak'):
        try:
            with open(path) as f: d=json.load(f)
            if d.get('schema')!=1: continue
            c=d['profiles']
            for n in ('tof','rfid'):
                a=c[n]
                if a['mode'] not in ('direct','pahub') or a['hub'] not in range(112,120) or a['channel'] not in range(6) or a['address']!=HWDEFAULT[n]['address']: raise ValueError('I2C')
            for n in ('gps','ir'):
                if (c[n]['rx'],c[n]['tx']) not in ((1,2),(2,1)): raise ValueError('GPIO')
            if c['gps']['baud'] not in (9600,115200) or c['i2c_freq'] not in (100000,400000): raise ValueError('Frecuencia')
            return c
        except (OSError,ValueError,KeyError,TypeError,AttributeError): pass
    return json.loads(json.dumps(HWDEFAULT))

def hwsave(c):
    import json
    from cp_catalogo_v08a import existe
    with open(HWFILE+'.new','w') as f: json.dump({'schema':1,'profiles':c},f)
    if hasattr(os,'sync'): os.sync()
    if existe(HWFILE):
        if existe(HWFILE+'.bak'): os.remove(HWFILE+'.bak')
        os.rename(HWFILE,HWFILE+'.bak')
    os.rename(HWFILE+'.new',HWFILE)
    if hasattr(os,'sync'): os.sync()

def hwprofiles():
    c=hwload()
    while True:
        k=elegir('PERFILES DE MODULOS',['Mini ToF','RFID 2','GPS UART','IR GPIO','Frecuencia I2C','Guardar perfiles','Restaurar defaults','Volver sin guardar'])
        if k is None or k==7: return
        if k==5:
            hwsave(c); elegir('PERFILES GUARDADOS',['Volver']); return
        if k==6:
            if elegir('RESTAURAR DEFAULTS',['Cancelar','Restaurar'])==1:
                import json
                c=json.loads(json.dumps(HWDEFAULT))
            continue
        if k==4:
            i=elegir('FRECUENCIA I2C',['100 kHz','400 kHz'],int(c['i2c_freq']==400000))
            if i is not None: c['i2c_freq']=(100000,400000)[i]
            continue
        n=('tof','rfid','gps','ir')[k]; a=c[n]
        while True:
            if k<2:
                i=elegir(n.upper(),['Modo: '+a['mode'],'PaHub: 0x%02X'%a['hub'],'Canal: %d'%a['channel'],'Direccion: 0x%02X'%a['address'],'Volver'])
                if i is None or i>=3: break
                if i==0:
                    j=elegir('CONEXION',['Directo','PaHub'],int(a['mode']=='pahub'))
                    if j is not None: a['mode']=('direct','pahub')[j]
                elif i==1:
                    j=elegir('DIRECCION PAHUB',['0x%02X'%x for x in range(112,120)],a['hub']-112)
                    if j is not None: a['hub']=112+j
                else:
                    j=elegir('CANAL',['CH%d'%x for x in range(6)],a['channel'])
                    if j is not None: a['channel']=j
            else:
                opts=['RX G%d TX G%d'%(a['rx'],a['tx'])]
                if k==2: opts.append('Baudios: %d'%a['baud'])
                i=elegir(n.upper(),opts+['Volver'])
                if i is None or i==len(opts): break
                if i==0:
                    j=elegir('PINES',['RX G2 TX G1','RX G1 TX G2'],int(a['rx']==1))
                    if j is not None: a['rx'],a['tx']=((2,1),(1,2))[j]
                else:
                    j=elegir('BAUDIOS',['9600','115200'],int(a['baud']==115200))
                    if j is not None: a['baud']=(9600,115200)[j]

def hardware_menu():
    from machine import Pin, SoftI2C
    freq=hwload()['i2c_freq']
    hints={0x28:'RFID2?',0x29:'ToF?',0x23:'BH1750?',0x38:'AHT20?',0x44:'SHT3x?',0x48:'ADS1115?',0x68:'IMU/RTC?'}
    def describe(a):
        return '0x%02X %d %s'%(a,a,hints.get(a,''))
    while True:
        k=elegir('MODULOS EXTERNOS',['Escanear I2C','Escanear PaHub','Probar canal PaHub','Frecuencia: %d kHz'%(freq//1000),'Pines Grove','Perfiles de modulos','Volver'])
        if k is None or k==6: return
        if k==5:
            try: hwprofiles(); freq=hwload()['i2c_freq']
            except Exception as e: elegir('ERROR PERFILES',[str(e)[:30],'Volver'])
            continue
        if k==3:
            v=elegir('FRECUENCIA I2C',['100 kHz','400 kHz'])
            if v is not None: freq=(100000,400000)[v]
            continue
        if k==4:
            elegir('GROVE CARDPUTER V1.1',['Negro: GND','Rojo: 5V','Amarillo: SDA G2','Blanco: SCL G1','Logica 3.3V','Volver'])
            continue
        bus=None
        hub=None
        try:
            bus=SoftI2C(sda=Pin(2),scl=Pin(1),freq=freq,timeout=50000)
            addresses=bus.scan()
            if k==0:
                elegir('I2C: %d dispositivos'%len(addresses),[describe(a) for a in addresses] or ['Ningun dispositivo'])
                continue
            candidates=[a for a in addresses if 0x70<=a<=0x77]
            if not candidates:
                elegir('PAHUB NO DETECTADO',['Volver'])
                continue
            i=elegir('CONFIRMAR DIRECCION PAHUB',['PaHub 0x%02X'%a for a in candidates]+['Cancelar'])
            if i is None or i==len(candidates): continue
            hub=PaHub(bus,candidates[i])
            if k==1:
                direct,channels=hub.scan()
                while True:
                    labels=['CH%d: '%j+(','.join('%02X'%a for a in c) if c else 'Libre') for j,c in enumerate(channels)]
                    i=elegir('PAHUB 0x%02X'%hub.address,labels+['Bus directo','Volver'])
                    if i is None or i==7: break
                    data=direct if i==6 else channels[i]
                    elegir('BUS DIRECTO' if i==6 else 'CANAL %d'%i,[describe(a) for a in data] or ['Sin dispositivos'])
            else:
                i=elegir('PROBAR CANAL',['CH%d'%j for j in range(6)])
                if i is not None:
                    hub.disable()
                    direct=bus.scan()
                    hub.select(i)
                    data=[a for a in bus.scan() if a not in direct]
                    hub.disable()
                    elegir('CANAL %d'%i,[describe(a) for a in data] or ['Sin dispositivos'])
        except Exception as e:
            print(repr(e)); elegir('ERROR I2C',[str(e)[:30],'Volver'])
        finally:
            try:
                if hub is not None: hub.disable()
            except Exception as e: print('PaHub cierre:',repr(e))
            if bus is not None and hasattr(bus,'deinit'): bus.deinit()

