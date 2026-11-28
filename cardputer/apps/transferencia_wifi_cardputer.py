import M5,time,os,network,socket
from m5lib_storage import Storage,entries,join
def show(*rows):
    M5.Lcd.fillScreen(0x102638); M5.Lcd.setTextSize(1)
    M5.Lcd.setTextColor(0xffffff,0x102638)
    M5.Lcd.drawString('TRANSFERENCIA V0.1',4,4)
    for i,s in enumerate(rows): M5.Lcd.drawString(s,4,22+i*16)
def esc(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
def send(c,b):
    v=memoryview(b)
    while len(v):
        n=c.send(v)
        if not n: raise OSError('Conexion cerrada')
        v=v[n:]
def reply(c,status,body):
    b=body.encode()
    send(c,('HTTP/1.1 '+status+'\r\nContent-Type: text/html; charset=utf-8\r\nCache-Control: no-store\r\nConnection: close\r\nContent-Length: %d\r\n\r\n'%len(b)).encode())
    send(c,b)
def serve(c,token,roots):
    c.settimeout(3)
    req=b''
    while b'\r\n\r\n' not in req:
        b=c.recv(256)
        if not b: return
        req+=b
        if len(req)>4096: return
    line=req.split(b'\r\n',1)[0].decode().split()
    if len(line)!=3 or line[0]!='GET':
        reply(c,'405 Method Not Allowed','Solo lectura'); return
    parts=line[1].split('/')
    if len(parts)<2 or parts[1]!=token:
        reply(c,'404 Not Found','No disponible'); return
    base='/'+token
    head='<meta name="viewport" content="width=device-width, initial-scale=1"><h2>Cardputer - Archivos</h2>'
    if len(parts)==2 or parts[2]=='':
        reply(c,'200 OK',head+''.join('<p><a href="'+base+'/'+str(i)+'">'+esc(label)+'</a></p>' for i,(label,p) in enumerate(roots))); return
    try:
        if not parts[2].isdigit(): raise ValueError()
        idx=int(parts[2])
        if idx>=len(roots): raise ValueError()
        label,p=roots[idx]; url=base+'/'+str(idx)
        for part in parts[3:]:
            if not part.isdigit(): raise ValueError()
            items=entries(p); n,d=items[int(part)]
            p=join(p,n); url+='/'+part
        isdir=bool(os.stat(p)[0]&0x4000)
    except (ValueError,IndexError,OSError):
        reply(c,'404 Not Found','Archivo no disponible'); return
    if isdir:
        body=head+'<p><a href="'+base+'">Inicio</a> | <a href="'+url.rsplit('/',1)[0]+'">Subir</a></p>'
        for i,(n,d) in enumerate(entries(p)):
            body+='<p><a href="'+url+'/'+str(i)+'">'+('[DIR] ' if d else '')+esc(n)+'</a></p>'
        reply(c,'200 OK',body)
    else:
        n=p.rsplit('/',1)[-1]
        safe=''.join(ch if ch in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-' else '_' for ch in n)
        size=os.stat(p)[6]
        send(c,('HTTP/1.1 200 OK\r\nContent-Type: application/octet-stream\r\nContent-Disposition: attachment; filename="'+safe+'"\r\nContent-Length: %d\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n'%size).encode())
        with open(p,'rb') as f:
            while True:
                M5.update()
                if M5.BtnA.wasPressed(): raise KeyboardInterrupt()
                b=f.read(1024)
                if not b: break
                send(c,b)
def main():
    st=None; srv=None
    try:
        wlan=network.WLAN(network.STA_IF)
        if not wlan.isconnected(): raise OSError('Conectar WiFi en Launcher')
        ip=wlan.ifconfig()[0]
        st=Storage(); roots=[('Memoria interna',st.flash)]
        show('Montando microSD...')
        try: roots.append(('microSD',st.mount()))
        except Exception:
            st.close()
        token=''.join('%02x'%b for b in os.urandom(8))
        srv=socket.socket(); srv.bind((ip,8080)); srv.listen(1); srv.settimeout(0.25)
        show('Safari: http://'+ip+':8080','Ruta: /'+token,'SD: '+('OK' if len(roots)>1 else 'No disponible'),'Solo lectura - G0 salir')
        while True:
            M5.update()
            if M5.BtnA.wasPressed(): break
            try: c,a=srv.accept()
            except OSError: continue
            try: serve(c,token,roots)
            except KeyboardInterrupt: break
            except Exception: pass
            finally: c.close()
    except Exception as e:
        show('ERROR',str(e)[:36],'G0 salir')
        while True:
            M5.update()
            if M5.BtnA.wasPressed(): break
            time.sleep_ms(30)
    finally:
        if srv is not None: srv.close()
        if st is not None: st.close()
main()
