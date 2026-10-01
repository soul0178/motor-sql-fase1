"""Archivo de heap: secuencia de páginas en disco. Asigna RowIDs (page_id, slot)
y cuenta lecturas/escrituras de página para las métricas de I/O."""
import os
from collections import namedtuple

from .page import PAGE_SIZE, SlottedPage

RowID = namedtuple("RowID", ["page_id", "slot"])


class HeapFile:
    def __init__(self, path, create=True):
        self.path = path
        if create or not os.path.exists(path):
            self.f = open(path, "w+b")
        else:
            self.f = open(path, "r+b")
        self.num_pages = os.path.getsize(path) // PAGE_SIZE
        self.reads = 0
        self.writes = 0
        self._tail = None       # última página, en memoria (buffer de inserción)
        self._tail_id = None
        self._dirty = False

    # ---- I/O de bajo nivel ----
    def _read_page(self, pid):
        if pid == self._tail_id and self._tail is not None:
            return self._tail            # acierto de buffer: no cuenta I/O
        self.f.seek(pid * PAGE_SIZE)
        self.reads += 1
        return SlottedPage(self.f.read(PAGE_SIZE))

    def _write_tail(self):
        if self._tail is not None and self._dirty:
            self.f.seek(self._tail_id * PAGE_SIZE)
            self.f.write(self._tail.data)
            self.writes += 1
            self._dirty = False

    def flush(self):
        """Escribe la página pendiente y vacía el buffer (las lecturas posteriores cuentan I/O)."""
        self._write_tail()
        self.f.flush()
        self._tail, self._tail_id = None, None

    # ---- API ----
    def insert(self, record: bytes) -> RowID:
        if self._tail is None and self.num_pages > 0:
            self._tail_id = self.num_pages - 1
            self._tail = self._read_page(self._tail_id)
        slot = self._tail.insert(record) if self._tail is not None else None
        if slot is None:
            self._write_tail()
            self._tail_id = self.num_pages
            self.num_pages += 1
            self._tail = SlottedPage()
            slot = self._tail.insert(record)
        self._dirty = True
        return RowID(self._tail_id, slot)

    def get(self, rowid: RowID) -> bytes:
        if not 0 <= rowid.page_id < self.num_pages:
            raise IndexError("RowID fuera de rango")
        return self._read_page(rowid.page_id).get(rowid.slot)

    def scan(self):
        """Recorrido secuencial de toda la tabla (Full Table Scan)."""
        self.flush()
        for pid in range(self.num_pages):
            page = self._read_page(pid)
            for slot in range(page.num_slots):
                yield RowID(pid, slot), page.get(slot)

    def reset_counters(self):
        self.reads = self.writes = 0

    def close(self):
        self.flush()
        self.f.close()
