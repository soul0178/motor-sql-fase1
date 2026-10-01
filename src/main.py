"""Punto de entrada.   python src/main.py demo | bench [--rows N] [--t T]"""
import argparse, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.table import Table
from storage.tuple_serializer import Schema, Column, INT, VARCHAR
import benchmark


def demo(t):
    schema = Schema([Column("id", INT), Column("name", VARCHAR, 30)])
    with tempfile.TemporaryDirectory() as d:
        print(f"=== 1) Inserción con splits visibles (t={t}, máx. {2*t-1} claves/nodo) ===")
        tb = Table(os.path.join(d, "demo.heap"), schema, "id", t=t, logger=print)
        for k in [10, 20, 5, 6, 12, 30, 7, 17, 3, 1, 25, 40, 50, 60, 70, 80]:
            print(f"insert({k}) -> RowID {tb.insert((k, f'persona_{k}'))}")
        print(f"\nAltura: {tb.index.height} | splits: {tb.index.splits} | nodos por nivel: {tb.index.level_sizes()}")
        tb.index.check_invariants()
        tb.flush()
        print(f"Index scan  id=17  -> {tb.find_by_index(17)}")
        print(f"Rango 5..20        -> {tb.range_by_index(5, 20)}")
        tb.close()

        print("\n=== 2) Carga masiva (bulk load) de 20 000 filas, t=50 ===")
        tb = Table(os.path.join(d, "bulk.heap"), schema, "id", t=50, logger=print)
        tb.bulk_insert([(i, f"p{i}") for i in range(20000, 0, -1)])
        print(f"Altura: {tb.index.height} | nodos por nivel: {tb.index.level_sizes()} | páginas heap: {tb.heap.num_pages}")
        tb.index.check_invariants(); print("Invariantes del árbol: OK")
        tb.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("modo", choices=["demo", "bench"])
    ap.add_argument("--rows", type=int, nargs="+", default=[1000, 10000, 100000])
    ap.add_argument("--t", type=int, default=None)
    a = ap.parse_args()
    if a.modo == "demo":
        demo(a.t or 2)
    else:
        benchmark.run(sizes=a.rows, t=a.t or 50)
