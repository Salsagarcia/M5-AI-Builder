# M5-AI Builder - reloj_core2 v0.1
# Hora del reloj interno del Core2; no sincroniza NTP.
import M5
import time

FONDO = 0x172333
BLANCO = 0xFFFFFF
GRIS = 0x9FB0C1
AZUL = 0x315875

def _texto(s, x, y, tam=1, color=BLANCO):
    M5.Lcd.setTextSize(tam)
    M5.Lcd.setTextColor(color, FONDO)
    M5.Lcd.drawString(str(s), x, y)

def ejecutar():
    M5.begin()
    M5.Lcd.fillScreen(FONDO)
    _texto('RELOJ CORE2', 16, 15, 2)
    _texto('Hora del dispositivo (sin NTP)', 16, 55, 1, GRIS)
    M5.Lcd.fillRect(12, 202, 296, 33, AZUL)
    _texto('VOLVER', 130, 213)
    anterior = M5.Touch.getCount() > 0
    ultima = None
    while True:
        M5.update()
        ahora = time.localtime()
        fecha = '%04d-%02d-%02d' % (ahora[0], ahora[1], ahora[2])
        hora = '%02d:%02d:%02d' % (ahora[3], ahora[4], ahora[5])
        if (fecha, hora) != ultima:
            M5.Lcd.fillRect(12, 91, 296, 95, FONDO)
            _texto(hora, 35, 99, 3)
            _texto(fecha, 102, 160, 1, GRIS)
            ultima = (fecha, hora)
        pulsado = M5.Touch.getCount() > 0
        if pulsado and not anterior:
            try:
                p = M5.Touch.getTouchPointRaw(0)
                if 12 <= p[0] <= 308 and 202 <= p[1] <= 239:
                    while M5.Touch.getCount() > 0:
                        M5.update()
                        time.sleep_ms(40)
                    return True
            except Exception as e:
                print('Touch reloj:', repr(e))
        anterior = pulsado
        time.sleep_ms(100)
