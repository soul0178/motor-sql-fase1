# Motor de Base de Datos SQL — Fase 1: Almacenamiento e Índice B+Tree

Módulo de almacenamiento de tuplas (INT, VARCHAR) y un índice **Árbol B+** para búsquedas por clave en O(log n).

## Requisitos
- Python 3.9 o superior. Sin dependencias externas.

## Pruebas
```bash
python -m unittest discover -s tests -t . -v
```

## Estado del proyecto
- [x] Serializador de tuplas y página con slots
- [x] HeapFile, RowIDs y contadores de I/O
- [ ] Árbol B+
- [ ] Balanceo y bulk load
- [ ] Benchmarks
