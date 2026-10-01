# Motor de Base de Datos SQL — Fase 1: Almacenamiento e Índice B+Tree

Módulo de almacenamiento de tuplas (INT, VARCHAR) y un índice **Árbol B+** que permite
búsquedas por clave en O(log n), comparadas contra un Full Table Scan O(n).

## Requisitos
- Python 3.9 o superior. **Sin dependencias externas** (solo biblioteca estándar).

## Ejecución
```bash
python src/main.py demo                 # inserciones con log de splits + bulk load
python src/main.py bench                # Index Scan vs Full Scan (1k, 10k, 100k filas)
python src/main.py bench --rows 500000 --t 50
```

## Pruebas
```bash
python -m unittest discover -s tests -t . -v
```

## Estructura
```
src/storage/   tuple_serializer.py (Schema, formato binario) · page.py (página de 4 KB con slots)
               heap_file.py (archivo de páginas, RowIDs, contadores de I/O) · table.py (heap + índice)
src/index/     btree.py (BTreeNode, BTree: search, insert, split, bulk_load, range_search)
src/main.py    demo y benchmark          src/benchmark.py   comparativa de rendimiento
tests/         32 pruebas unitarias e integración
docs/design.md decisiones de diseño
```

## Grado t seleccionado
Se usa **t = 50 por defecto**: cada nodo guarda hasta 2t−1 = 99 claves y 100 hijos.
Con 100 000 filas el árbol tiene altura 3, es decir, **3 nodos visitados + 1 página de heap** por búsqueda.
Un grado alto reduce la altura (menos accesos), y 99 claves enteras con sus RowIDs ocupan del orden
de 1 KB, cercano al tamaño de una página. Para la demostración de splits se usa t = 2, donde se ven
los desbordamientos con pocos datos.
