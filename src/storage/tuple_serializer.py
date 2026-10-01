"""Esquema de tablas y serialización binaria de tuplas (INT, VARCHAR).

Formato de una tupla (columnas concatenadas, sin separadores):
  INT      -> 4 bytes, entero con signo, big-endian
  VARCHAR  -> 2 bytes de longitud (en bytes UTF-8) + los bytes del texto
"""
import struct
from dataclasses import dataclass

INT = "INT"
VARCHAR = "VARCHAR"

_INT = struct.Struct(">i")
_LEN = struct.Struct(">H")
INT_MIN, INT_MAX = -(2 ** 31), 2 ** 31 - 1


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    max_length: int = 255  # solo aplica a VARCHAR (en bytes UTF-8)


class Schema:
    def __init__(self, columns):
        self.columns = list(columns)
        if not self.columns:
            raise ValueError("El esquema necesita al menos una columna")
        names = [c.name for c in self.columns]
        if len(set(names)) != len(names):
            raise ValueError("Nombres de columna duplicados")
        for c in self.columns:
            if c.type not in (INT, VARCHAR):
                raise ValueError(f"Tipo no soportado: {c.type}")
        self._index = {c.name: i for i, c in enumerate(self.columns)}

    def index_of(self, name):
        if name not in self._index:
            raise KeyError(f"Columna inexistente: {name}")
        return self._index[name]

    def serialize(self, values) -> bytes:
        if len(values) != len(self.columns):
            raise ValueError("Cantidad de valores distinta a la de columnas")
        out = bytearray()
        for col, v in zip(self.columns, values):
            if col.type == INT:
                if not isinstance(v, int) or isinstance(v, bool):
                    raise TypeError(f"{col.name}: se esperaba INT")
                if not INT_MIN <= v <= INT_MAX:
                    raise ValueError(f"{col.name}: INT fuera de rango")
                out += _INT.pack(v)
            else:
                if not isinstance(v, str):
                    raise TypeError(f"{col.name}: se esperaba VARCHAR (str)")
                raw = v.encode("utf-8")
                if len(raw) > col.max_length:
                    raise ValueError(f"{col.name}: excede max_length={col.max_length}")
                out += _LEN.pack(len(raw)) + raw
        return bytes(out)

    def deserialize(self, data: bytes) -> tuple:
        values, off = [], 0
        for col in self.columns:
            if col.type == INT:
                values.append(_INT.unpack_from(data, off)[0])
                off += _INT.size
            else:
                (n,) = _LEN.unpack_from(data, off)
                off += _LEN.size
                values.append(data[off:off + n].decode("utf-8"))
                off += n
        return tuple(values)
