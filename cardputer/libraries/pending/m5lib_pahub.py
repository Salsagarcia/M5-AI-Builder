VERSION = '0.1'

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
