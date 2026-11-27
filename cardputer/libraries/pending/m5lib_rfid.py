VERSION = '0.1'

class RFIDReader:
    def __init__(self, bus, address=0x28):
        from unit.rfid import RFIDUnit
        self.reader = RFIDUnit(bus, address)
    def read_uid(self):
        if not self.reader.is_new_card_present():
            return None
        uid = self.reader.read_card_uid()
        if uid is None:
            return None
        try:
            return bytes(uid)
        finally:
            self.reader.close()
