"""Página con directorio de slots (slotted page) de 4 KB.

  [ header | slot0 slot1 ... -> (espacio libre) <- ... datos1 datos0 ]
header = (num_slots:uint16, free_end:uint16); cada slot = (offset, length).
"""
import struct

PAGE_SIZE = 4096
_HEADER = struct.Struct(">HH")
_SLOT = struct.Struct(">HH")
MAX_RECORD = PAGE_SIZE - _HEADER.size - _SLOT.size


class SlottedPage:
    def __init__(self, data=None):
        if data is None:
            self.data = bytearray(PAGE_SIZE)
            _HEADER.pack_into(self.data, 0, 0, PAGE_SIZE)
        else:
            if len(data) != PAGE_SIZE:
                raise ValueError("Tamaño de página inválido")
            self.data = bytearray(data)

    @property
    def num_slots(self):
        return _HEADER.unpack_from(self.data, 0)[0]

    @property
    def free_end(self):
        return _HEADER.unpack_from(self.data, 0)[1]

    def free_space(self):
        return self.free_end - (_HEADER.size + self.num_slots * _SLOT.size)

    def insert(self, record: bytes):
        """Devuelve el número de slot, o None si no hay espacio."""
        if len(record) > MAX_RECORD:
            raise ValueError("Registro mayor que una página")
        if len(record) + _SLOT.size > self.free_space():
            return None
        n, end = _HEADER.unpack_from(self.data, 0)
        start = end - len(record)
        self.data[start:end] = record
        _SLOT.pack_into(self.data, _HEADER.size + n * _SLOT.size, start, len(record))
        _HEADER.pack_into(self.data, 0, n + 1, start)
        return n

    def get(self, slot: int) -> bytes:
        if not 0 <= slot < self.num_slots:
            raise IndexError(f"Slot inexistente: {slot}")
        off, ln = _SLOT.unpack_from(self.data, _HEADER.size + slot * _SLOT.size)
        return bytes(self.data[off:off + ln])
