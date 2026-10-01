# Motor de Base de Datos SQL — Fase 1: Almacenamiento e Índice B+Tree

Módulo de almacenamiento de tuplas (INT, VARCHAR) y un índice **Árbol B+** para búsquedas por clave en O(log n).

## Requisitos
- Python 3.9 o superior. Sin dependencias externas.

## Pruebas
```bash
python -m unittest discover -s tests -t . -v
```

## Estado del proyecto
- [x] Storage (serializador, páginas, HeapFile, RowIDs)
- [x] Árbol B+: search, insert, split de hojas e internos
- [ ] Bulk load y range scan
- [ ] Integración Table (heap + índice)
- [ ] Benchmarks
