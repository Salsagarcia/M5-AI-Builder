# Read-only hardware profiles, schema 1.
import json
VERSION='0.1'
DEFAULT={'tof':{'mode':'pahub','hub':112,'channel':0,'address':41},'rfid':{'mode':'pahub','hub':112,'channel':1,'address':40},'gps':{'baud':115200,'rx':2,'tx':1},'ir':{'rx':2,'tx':1},'i2c_freq':100000}

def load(path='/flash/m5_hardware.json', defaults=None):
    if defaults is None: defaults=DEFAULT
    for p in (path,path+'.bak'):
        try:
            with open(p) as f: d=json.load(f)
            if d.get('schema')!=1: continue
            c=d['profiles']
            for n in ('tof','rfid'):
                a=c[n]
                if a['mode'] not in ('direct','pahub') or type(a['hub'])!=int or a['hub'] not in range(112,120) or type(a['channel'])!=int or a['channel'] not in range(6) or a['address']!=defaults[n]['address']: raise ValueError('I2C')
            for n in ('gps','ir'):
                if (c[n]['rx'],c[n]['tx']) not in ((defaults[n]['rx'],defaults[n]['tx']),(defaults[n]['tx'],defaults[n]['rx'])): raise ValueError('GPIO')
            if c['gps']['baud'] not in (9600,115200) or c['i2c_freq'] not in (100000,400000): raise ValueError('Frequency')
            return c,p
        except (OSError,ValueError,KeyError,TypeError,AttributeError): pass
    return json.loads(json.dumps(defaults)), 'defaults'

def profile(name,path='/flash/m5_hardware.json',defaults=None):
    return load(path,defaults)[0][name]
