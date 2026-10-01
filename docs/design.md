# Diseño técnico — Fase 1

## Formato de tupla
`INT` = 4 bytes big-endian con signo. `VARCHAR` = 2 bytes de longitud + bytes UTF-8.
Ejemplo: `(1, "ab")` → `00 00 00 01 | 00 02 | 61 62`.

## Página (4096 B) con directorio de slots
```
| num_slots(2) free_end(2) | slot0(off,len) slot1 ... |  espacio libre  | ... tupla1 tupla0 |
```
Los slots crecen hacia adelante y los datos hacia atrás. Un **RowID = (page_id, slot)**
identifica una tupla de forma única y estable.

## HeapFile
Archivo de páginas contiguas. Mantiene en memoria solo la última página (buffer de inserción);
toda lectura de otra página incrementa `reads`, lo que da la métrica de I/O del benchmark.

## Árbol B+ (grado mínimo t)
- Máx. 2t−1 claves por nodo; hojas ≥ t−1 claves; internos ≥ t hijos; raíz ≥ 2 hijos (o es hoja).
- Las hojas guardan `clave → RowID` y se enlazan en una lista (consultas por rango).
- **Split**: al superar 2t−1 claves, la hoja se parte en t | t y la primera clave de la derecha
  *sube copiada*; un nodo interno se parte con la clave central *subiendo movida*.
  Si la raíz se divide, la altura crece en 1.
- **Bulk load**: ordena, reparte las claves en hojas casi iguales (siempre cumplen el mínimo de
  ocupación) y construye los niveles superiores de abajo hacia arriba en O(n).
- `check_invariants()` verifica orden, ocupación, profundidad uniforme y enlaces de hojas;
  se usa en las pruebas.

## Diagramas

### Arquitectura
```mermaid
flowchart LR
    Q[Consulta por clave] --> T[Table]
    T -->|Index Scan| B[BTree B+ en memoria]
    B -->|RowID page_id, slot| H[HeapFile]
    T -->|Full Table Scan| H
    H --> P[SlottedPage 4 KB]
    P --> D[(archivo .heap)]
    S[Schema / serializador] --> H
```

### Estructura del B+Tree (t = 2, máx. 3 claves por nodo)
```mermaid
flowchart TD
    R["[ 20 ]"] --> A["[ 6 | 10 ]"]
    R --> B["[ 30 | 50 ]"]
    A --> L1["1 3 5"]
    A --> L2["6 7"]
    A --> L3["10 12 17"]
    B --> L4["20 25"]
    B --> L5["30 40"]
    B --> L6["50 60 70 80"]
    L1 -.next.-> L2 -.next.-> L3 -.next.-> L4 -.next.-> L5 -.next.-> L6
```
_Esquema ilustrativo: los nodos internos guardan separadores y las hojas (enlazadas con `next`) guardan clave → RowID._

### Flujo de inserción con split
```mermaid
flowchart TD
    I[insert clave, RowID] --> F[Descender hasta la hoja]
    F --> G[Insertar ordenado en la hoja]
    G --> C{¿más de 2t-1 claves?}
    C -- no --> E[Fin]
    C -- sí --> S[Split: hoja en t y t, sube la 1a clave de la derecha]
    S --> U{¿el padre se desborda?}
    U -- no --> E
    U -- sí --> V[Split interno, la clave central sube]
    V --> W{¿era la raíz?}
    W -- sí --> X[Nueva raíz, altura + 1]
    W -- no --> U
```

## Limitaciones conocidas (para mencionar o mejorar)
- El índice vive en memoria; solo el heap se guarda en disco. Para persistirlo habría que
  serializar los nodos a páginas.
- No hay `DELETE` ni `UPDATE` (fuera del alcance de la Fase 1: solo SELECT).
- Claves únicas; no hay índices secundarios con duplicados.
