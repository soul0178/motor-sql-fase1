import os, random, tempfile, time, unittest
from tests import _path  # noqa
from storage.table import Table
from storage.tuple_serializer import Schema, Column, INT, VARCHAR

SCHEMA = Schema([Column("id", INT), Column("name", VARCHAR, 50)])


class TestIndexVsFullScan(unittest.TestCase):
    """Criterio de aceptación: el Index Scan supera claramente al Full Table Scan."""

    def test_io_and_time(self):
        n = 20000
        rows = [(i, f"usuario_{i}") for i in range(n)]
        random.Random(1).shuffle(rows)
        with tempfile.TemporaryDirectory() as d:
            tb = Table(os.path.join(d, "b.heap"), SCHEMA, "id", t=50)
            tb.bulk_insert(rows)
            keys = random.Random(2).sample(range(n), 100)

            tb.heap.reset_counters(); tb.index.node_reads = 0
            t0 = time.perf_counter()
            for k in keys: self.assertEqual(tb.find_by_index(k)[0], k)
            t_idx = (time.perf_counter() - t0) / len(keys)
            pages_idx = tb.heap.reads / len(keys)

            tb.heap.reset_counters()
            t0 = time.perf_counter()
            for k in keys[:5]: self.assertEqual(tb.find_by_full_scan(k)[0], k)
            t_scan = (time.perf_counter() - t0) / 5
            pages_scan = tb.heap.reads / 5

            self.assertEqual(pages_idx, 1)                     # 1 página de heap por búsqueda
            self.assertGreater(pages_scan, 10 * pages_idx)     # el scan lee muchas más páginas
            self.assertGreater(t_scan, 10 * t_idx)             # y es al menos 10x más lento
            tb.close()

    def test_bulk_insert_requires_empty_table(self):
        with tempfile.TemporaryDirectory() as d:
            tb = Table(os.path.join(d, "t.heap"), SCHEMA, "id", t=2)
            tb.insert((1, "a"))
            before = tb.heap.num_pages
            with self.assertRaises(ValueError): tb.bulk_insert([(2, "b")])
            self.assertEqual(sum(1 for _ in tb.heap.scan()), 1)   # el heap no se tocó
            self.assertEqual(tb.heap.num_pages, before)
            tb.close()


if __name__ == "__main__":
    unittest.main()
