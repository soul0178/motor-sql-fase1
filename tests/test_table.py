import os, random, tempfile, unittest
from tests import _path  # noqa
from index.btree import DuplicateKeyError
from storage.table import Table
from storage.tuple_serializer import Schema, Column, INT, VARCHAR

SCHEMA = Schema([Column("id", INT), Column("name", VARCHAR, 50)])


class TestTable(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.path = os.path.join(self.d.name, "t.heap")
    def tearDown(self): self.d.cleanup()

    def test_index_scan_equals_full_scan(self):
        t = Table(self.path, SCHEMA, "id", t=3)
        ids = random.Random(3).sample(range(10**6), 3000)
        for i in ids: t.insert((i, f"user{i}"))
        t.flush()
        for i in ids[:50] + [-1, 10**6 + 5]:
            self.assertEqual(t.find_by_index(i), t.find_by_full_scan(i))
        self.assertEqual(t.find_by_index(ids[0]), (ids[0], f"user{ids[0]}"))
        t.close()

    def test_bulk_insert(self):
        t = Table(self.path, SCHEMA, "id", t=10)
        rows = [(i, f"n{i}") for i in range(5000)]; random.Random(0).shuffle(rows)
        t.bulk_insert(rows); t.index.check_invariants()
        self.assertEqual(t.find_by_index(4321), (4321, "n4321"))
        self.assertEqual(t.range_by_index(10, 13), [(i, f"n{i}") for i in range(10, 14)])
        t.close()

    def test_duplicate_key_leaves_heap_untouched(self):
        t = Table(self.path, SCHEMA, "id", t=2); t.insert((1, "a"))
        with self.assertRaises(DuplicateKeyError): t.insert((1, "b"))
        self.assertEqual(sum(1 for _ in t.heap.scan()), 1); t.close()

    def test_varchar_key(self):
        t = Table(self.path, SCHEMA, "name", t=2)
        for i in range(300): t.insert((i, f"nombre{i:04d}"))
        self.assertEqual(t.find_by_index("nombre0123"), (123, "nombre0123"))
        self.assertIsNone(t.find_by_index("nada")); t.close()

    def test_index_reads_one_page_per_lookup(self):
        t = Table(self.path, SCHEMA, "id", t=10)
        t.bulk_insert([(i, "x" * 30) for i in range(20000)])
        t.heap.reset_counters(); t.find_by_index(777)
        self.assertEqual(t.heap.reads, 1)
        t.heap.reset_counters(); t.find_by_full_scan(19999)
        self.assertEqual(t.heap.reads, t.heap.num_pages); t.close()


if __name__ == "__main__":
    unittest.main()
