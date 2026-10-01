import random, unittest
from tests import _path  # noqa
from index.btree import BTree, DuplicateKeyError
from storage.heap_file import RowID


def rid(k): return RowID(k // 100, k % 100)


class TestBTreeBasic(unittest.TestCase):
    def test_invalid_degree(self):
        with self.assertRaises(ValueError): BTree(t=1)

    def test_empty(self):
        t = BTree(t=2)
        self.assertIsNone(t.search(1))
        self.assertTrue(t.check_invariants())

    def test_insert_search_and_missing(self):
        t = BTree(t=2)
        for k in [5, 1, 9, 3, 7]: t.insert(k, rid(k))
        for k in [5, 1, 9, 3, 7]: self.assertEqual(t.search(k), rid(k))
        for k in [0, 2, 4, 10, -3]: self.assertIsNone(t.search(k))

    def test_duplicates_rejected(self):
        t = BTree(t=2); t.insert(1, rid(1))
        with self.assertRaises(DuplicateKeyError): t.insert(1, rid(1))
        self.assertEqual(t.size, 1)

    def test_string_keys(self):
        t = BTree(t=2)
        for w in ["pera", "manzana", "uva", "kiwi", "fresa", "mango", "limón"]: t.insert(w, rid(len(w)))
        self.assertIsNotNone(t.search("kiwi")); self.assertIsNone(t.search("sandía"))
        t.check_invariants()


class TestSplitAndGrowth(unittest.TestCase):
    def test_leaf_overflow_splits(self):
        t = BTree(t=2)                        # máx. 3 claves por nodo
        for k in (1, 2, 3): t.insert(k, rid(k))
        self.assertEqual((t.height, t.splits), (1, 0))   # justo en el límite: sin split
        t.insert(4, rid(4))                              # desborda -> split
        self.assertEqual((t.height, t.splits), (2, 1))
        t.check_invariants()

    def test_height_grows_logarithmically(self):
        t = BTree(t=2); heights = []
        for k in range(1, 1001):
            t.insert(k, rid(k)); heights.append(t.height)
        self.assertEqual(heights, sorted(heights))        # nunca decrece
        self.assertLessEqual(t.height, 10)                # ~log2(1000)
        t.check_invariants()

    def test_split_log(self):
        msgs = []; t = BTree(t=2, logger=msgs.append)
        for k in range(1, 12): t.insert(k, rid(k))
        self.assertTrue(any("SPLIT hoja" in m for m in msgs))
        self.assertTrue(any("raíz se dividió" in m for m in msgs))

    def test_orders_and_degrees(self):
        for deg in (2, 3, 4, 10):
            for order in ("asc", "desc", "rand"):
                keys = list(range(500))
                if order == "desc": keys.reverse()
                if order == "rand": random.Random(deg).shuffle(keys)
                t = BTree(t=deg)
                for k in keys: t.insert(k, rid(k))
                t.check_invariants()
                self.assertEqual(t.size, 500)
                self.assertTrue(all(t.search(k) == rid(k) for k in range(500)))



    def test_search_cost_is_height(self):
        t = BTree(t=2)
        for k in range(1000): t.insert(k, rid(k))
        t.node_reads = 0; t.search(500)
        self.assertEqual(t.node_reads, t.height)


class TestMassInsertion(unittest.TestCase):
    def test_50k_random_matches_dict(self):
        t, ref = BTree(t=5), {}
        for k in random.Random(42).sample(range(10**7), 50000):
            t.insert(k, rid(k)); ref[k] = rid(k)
        t.check_invariants()
        probe = random.Random(7)
        for k in random.sample(list(ref), 2000): self.assertEqual(t.search(k), ref[k])
        for _ in range(2000):
            k = probe.randrange(10**7)
            self.assertEqual(t.search(k), ref.get(k))


if __name__ == "__main__":
    unittest.main()
