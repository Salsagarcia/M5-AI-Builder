# Adapter for the UIFlow2 built-in VL53L0X driver (M5Stack).
VERSION = '0.1'

class RangeSensor:
    def __init__(self, bus, address=0x29):
        from driver.vl53l0x import VL53L0X
        self.bus = bus
        self.address = address
        if bus.readfrom_mem(address, 0xC0, 1)[0] != 0xEE:
            raise ValueError('No es VL53L0X')
        self.sensor = VL53L0X(bus, address=address, io_timeout_ms=250)

    def read_mm(self):
        self.sensor.do_range_measurement()
        import time
        start = time.ticks_ms()
        while not self.sensor.get_data_ready():
            if time.ticks_diff(time.ticks_ms(), start) >= 250:
                raise RuntimeError('Timeout ToF')
            time.sleep_ms(2)
        status = (self.bus.readfrom_mem(self.address, 0x14, 1)[0] >> 3) & 15
        value = self.sensor.read_range()
        return value if status == 11 and 30 <= value <= 1200 else None
