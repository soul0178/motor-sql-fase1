"""Tabla = HeapFile (tuplas) + BTree (índice sobre la columna clave)."""
from index.btree import BTree, DuplicateKeyError
from .heap_file import HeapFile
from .tuple_serializer import Schema


class Table:
    def __init__(self, path, schema: Schema, key_column, t=50, logger=None):
        self.schema = schema
        self.key_idx = schema.index_of(key_column)
        self.heap = HeapFile(path, create=True)
        self.index = BTree(t=t, logger=logger)

    # ---------------- inserción ----------------
    def insert(self, values):
        key = values[self.key_idx]
        if self.index.search(key) is not None:
            raise DuplicateKeyError(key)
        rowid = self.heap.insert(self.schema.serialize(values))
        self.index.insert(key, rowid)
        return rowid

    def bulk_insert(self, rows):
        """Escribe todas las filas al heap y construye el índice con bulk load.
        Requiere una tabla vacía (se valida ANTES de escribir en el heap)."""
        if self.index.size:
            raise ValueError("bulk_insert requiere una tabla vacía")
        pairs = []
        for values in rows:
            rowid = self.heap.insert(self.schema.serialize(values))
            pairs.append((values[self.key_idx], rowid))
        self.index.bulk_load(pairs)
        self.heap.flush()

    # ---------------- consultas ----------------
    def find_by_index(self, key):
        """Index Scan: B+Tree -> RowID -> 1 página del heap."""
        rowid = self.index.search(key)
        if rowid is None:
            return None
        return self.schema.deserialize(self.heap.get(rowid))

    def find_by_full_scan(self, key):
        """Full Table Scan: recorre todas las páginas hasta encontrar la clave."""
        for _, raw in self.heap.scan():
            row = self.schema.deserialize(raw)
            if row[self.key_idx] == key:
                return row
        return None

    def range_by_index(self, lo, hi):
        return [self.schema.deserialize(self.heap.get(r)) for _, r in self.index.range_search(lo, hi)]

    def flush(self):
        self.heap.flush()

    def close(self):
        self.heap.close()
