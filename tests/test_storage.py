import os, tempfile, unittest
from tests import _path  # noqa
from storage.tuple_serializer import Schema, Column, INT, VARCHAR
from storage.page import SlottedPage, PAGE_SIZE, MAX_RECORD
from storage.heap_file import HeapFile, RowID

SCHEMA = Schema([Column("id", INT), Column("name", VARCHAR, 20)])


class TestSerializer(unittest.TestCase):
    def test_roundtrip(self):
        for row in [(1, "ana"), (-5, ""), (2**31 - 1, "ñandú ✓"), (-2**31, "x" * 20)]:
            if len(row[1].encode()) <= 20:
                self.assertEqual(SCHEMA.deserialize(SCHEMA.serialize(row)), row)

    def test_binary_layout(self):
        self.assertEqual(SCHEMA.serialize((1, "ab")), b"\x00\x00\x00\x01\x00\x02ab")

    def test_errors(self):
        with self.assertRaises(TypeError): SCHEMA.serialize(("1", "a"))
        with self.assertRaises(TypeError): SCHEMA.serialize((True, "a"))
        with self.assertRaises(TypeError): SCHEMA.serialize((1, 2))
        with self.assertRaises(ValueError): SCHEMA.serialize((2**31, "a"))
        with self.assertRaises(ValueError): SCHEMA.serialize((1, "x" * 21))
        with self.assertRaises(ValueError): SCHEMA.serialize((1,))
        with self.assertRaises(ValueError): Schema([Column("a", "FLOAT")])
        with self.assertRaises(ValueError): Schema([Column("a", INT), Column("a", INT)])


class TestPage(unittest.TestCase):
    def test_insert_get_until_full(self):
        p, stored = SlottedPage(), []
        while True:
            rec = bytes([len(stored) % 251]) * 37
            s = p.insert(rec)
            if s is None:
                break
            stored.append(rec)
        self.assertGreater(len(stored), 50)
        for i, rec in enumerate(stored):
            self.assertEqual(p.get(i), rec)
        self.assertLess(p.free_space(), 37 + 4)

    def test_limits(self):
        p = SlottedPage()
        with self.assertRaises(ValueError): p.insert(b"x" * (MAX_RECORD + 1))
        self.assertEqual(p.insert(b"x" * MAX_RECORD), 0)
        with self.assertRaises(IndexError): p.get(5)

    def test_persist_bytes(self):
        p = SlottedPage(); p.insert(b"hola")
        self.assertEqual(SlottedPage(bytes(p.data)).get(0), b"hola")
        with self.assertRaises(ValueError): SlottedPage(b"short")


class TestHeapFile(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.path = os.path.join(self.d.name, "t.heap")
    def tearDown(self): self.d.cleanup()

    def test_rowids_and_reads(self):
        h = HeapFile(self.path)
        ids = [h.insert(SCHEMA.serialize((i, f"n{i}"))) for i in range(2000)]
        self.assertGreater(h.num_pages, 1)
        self.assertEqual(len(set(ids)), 2000)
        h.flush()
        for i in (0, 999, 1999):
            self.assertEqual(SCHEMA.deserialize(h.get(ids[i])), (i, f"n{i}"))
        h.close()

    def test_scan_counts_every_page(self):
        h = HeapFile(self.path)
        for i in range(2000): h.insert(SCHEMA.serialize((i, "x")))
        h.flush(); h.reset_counters()
        rows = [SCHEMA.deserialize(r)[0] for _, r in h.scan()]
        self.assertEqual(rows, list(range(2000)))
        self.assertEqual(h.reads, h.num_pages)
        h.close()

    def test_reopen(self):
        h = HeapFile(self.path)
        rid = h.insert(SCHEMA.serialize((7, "persist"))); h.close()
        h2 = HeapFile(self.path, create=False)
        self.assertEqual(SCHEMA.deserialize(h2.get(rid)), (7, "persist"))
        rid2 = h2.insert(SCHEMA.serialize((8, "more")))   # continúa en la última página
        self.assertEqual(rid2, RowID(0, 1)); h2.close()

    def test_bad_rowid(self):
        h = HeapFile(self.path)
        with self.assertRaises(IndexError): h.get(RowID(3, 0))
        h.close()


if __name__ == "__main__":
    unittest.main()
