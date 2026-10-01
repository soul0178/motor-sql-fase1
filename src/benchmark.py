"""Benchmark: Index Scan (B+Tree) vs Full Table Scan, con tiempo e I/O de páginas."""
import os, random, tempfile, time

from storage.table import Table
from storage.tuple_serializer import Schema, Column, INT, VARCHAR

SCHEMA = Schema([Column("id", INT), Column("name", VARCHAR, 50), Column("email", VARCHAR, 80)])


def make_rows(n, seed=1):
    ids = list(range(1, n + 1))
    random.Random(seed).shuffle(ids)          # orden físico != orden de clave
    return [(i, f"usuario_{i}", f"usuario_{i}@ejemplo.com") for i in ids]


def run(sizes=(1_000, 10_000, 100_000), t=50, index_queries=2000, scan_queries=10):
    print(f"Grado t = {t}  (máx. {2*t-1} claves/nodo) | página = 4096 B\n")
    print(f"{'filas':>8} {'págs':>6} {'altura':>6} | {'carga':>9} {'bulk':>9} | "
          f"{'Index ms':>9} {'nodos':>6} {'págs':>5} | {'Scan ms':>9} {'págs':>7} | {'speedup':>8}")
    print("-" * 105)
    for n in sizes:
        rows = make_rows(n)
        with tempfile.TemporaryDirectory() as d:
            # carga fila a fila (con splits)
            tb = Table(os.path.join(d, "a.heap"), SCHEMA, "id", t=t)
            t0 = time.perf_counter()
            for r in rows: tb.insert(r)
            tb.flush(); t_ins = time.perf_counter() - t0
            tb.close()
            # carga masiva (bulk load)
            tb = Table(os.path.join(d, "b.heap"), SCHEMA, "id", t=t)
            t0 = time.perf_counter(); tb.bulk_insert(rows); t_bulk = time.perf_counter() - t0

            rnd = random.Random(99)
            keys = [rnd.randint(1, n) for _ in range(index_queries)]
            # Index Scan
            tb.heap.reset_counters(); tb.index.node_reads = 0
            t0 = time.perf_counter()
            for k in keys: assert tb.find_by_index(k)[0] == k
            t_idx = (time.perf_counter() - t0) / index_queries
            idx_nodes = tb.index.node_reads / index_queries
            idx_pages = tb.heap.reads / index_queries
            # Full Table Scan
            tb.heap.reset_counters()
            t0 = time.perf_counter()
            for k in keys[:scan_queries]: assert tb.find_by_full_scan(k)[0] == k
            t_scan = (time.perf_counter() - t0) / scan_queries
            scan_pages = tb.heap.reads / scan_queries
            pages, height = tb.heap.num_pages, tb.index.height
            tb.close()
        print(f"{n:>8} {pages:>6} {height:>6} | {t_ins:>8.2f}s {t_bulk:>8.2f}s | "
              f"{t_idx*1e3:>9.4f} {idx_nodes:>6.1f} {idx_pages:>5.1f} | "
              f"{t_scan*1e3:>9.2f} {scan_pages:>7.0f} | {t_scan/t_idx:>7.0f}x")
    print("\nNotas: tiempos y páginas son PROMEDIO por consulta (claves aleatorias existentes).")
    print("El Full Scan se detiene al encontrar la clave (en promedio recorre ~la mitad de la tabla).")
