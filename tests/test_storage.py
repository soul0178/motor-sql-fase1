import unittest
from tests import _path  # noqa
from storage.tuple_serializer import Schema, Column, INT, VARCHAR
from storage.page import SlottedPage, PAGE_SIZE, MAX_RECORD

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


if __name__ == "__main__":
    unittest.main()
