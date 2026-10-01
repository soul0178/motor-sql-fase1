"""Árbol B+ (claves únicas) con grado mínimo t.

 - Cada nodo tiene como máximo 2t-1 claves.
 - Nodos no raíz: >= t-1 claves (hojas) / >= t hijos (internos).
 - Las hojas guardan (clave -> RowID) y están enlazadas (range scan).
 - Convención de separadores: hijo[i] < keys[i] <= hijo[i+1].
"""
from bisect import bisect_left, bisect_right


class DuplicateKeyError(KeyError):
    pass


class BTreeNode:
    _next_id = 0
    __slots__ = ("id", "leaf", "keys", "children", "values", "next")

    def __init__(self, leaf):
        BTreeNode._next_id += 1
        self.id = BTreeNode._next_id
        self.leaf = leaf
        self.keys = []
        self.children = [] if not leaf else None
        self.values = [] if leaf else None
        self.next = None  # siguiente hoja


def _partition(n, cap):
    """Reparte n elementos en ceil(n/cap) grupos de tamaño casi igual."""
    g = -(-n // cap)
    base, rem = divmod(n, g)
    return [base + 1 if i < rem else base for i in range(g)]


class BTree:
    def __init__(self, t=50, logger=None):
        if t < 2:
            raise ValueError("El grado mínimo t debe ser >= 2")
        self.t = t
        self.max_keys = 2 * t - 1
        self.root = BTreeNode(leaf=True)
        self.height = 1
        self.size = 0
        self.splits = 0
        self.node_reads = 0      # nodos visitados (métrica de I/O del índice)
        self.logger = logger     # callable(str) opcional para ver los splits

    def _log(self, msg):
        if self.logger:
            self.logger(msg)

    # ------------------------------------------------------------ búsqueda
    def _find_leaf(self, key):
        node = self.root
        self.node_reads += 1
        while not node.leaf:
            node = node.children[bisect_right(node.keys, key)]
            self.node_reads += 1
        return node

    def search(self, key):
        """Devuelve el RowID asociado a key, o None. O(log n)."""
        leaf = self._find_leaf(key)
        i = bisect_left(leaf.keys, key)
        if i < len(leaf.keys) and leaf.keys[i] == key:
            return leaf.values[i]
        return None

    def range_search(self, lo, hi):
        """Genera (clave, RowID) con lo <= clave <= hi, en orden."""
        leaf = self._find_leaf(lo)
        i = bisect_left(leaf.keys, lo)
        while leaf is not None:
            while i < len(leaf.keys):
                if leaf.keys[i] > hi:
                    return
                yield leaf.keys[i], leaf.values[i]
                i += 1
            leaf, i = leaf.next, 0
            if leaf is not None:
                self.node_reads += 1

    # ----------------------------------------------------------- inserción
    def insert(self, key, rowid):
        res = self._insert(self.root, key, rowid)
        self.size += 1
        if res is not None:
            sep, right = res
            old = self.root
            self.root = BTreeNode(leaf=False)
            self.root.keys = [sep]
            self.root.children = [old, right]
            self.height += 1
            self._log(f"  >> La raíz se dividió: nueva raíz #{self.root.id}, altura = {self.height}")

    def _insert(self, node, key, rowid):
        if node.leaf:
            i = bisect_left(node.keys, key)
            if i < len(node.keys) and node.keys[i] == key:
                raise DuplicateKeyError(key)
            node.keys.insert(i, key)
            node.values.insert(i, rowid)
            return self._split_leaf(node) if len(node.keys) > self.max_keys else None
        i = bisect_right(node.keys, key)
        res = self._insert(node.children[i], key, rowid)
        if res is None:
            return None
        sep, right = res
        node.keys.insert(i, sep)
        node.children.insert(i + 1, right)
        return self._split_internal(node) if len(node.keys) > self.max_keys else None

    def _split_leaf(self, node):
        mid = self.t
        right = BTreeNode(leaf=True)
        right.keys, right.values = node.keys[mid:], node.values[mid:]
        node.keys, node.values = node.keys[:mid], node.values[:mid]
        right.next, node.next = node.next, right
        self.splits += 1
        self._log(f"SPLIT hoja #{node.id} -> #{node.id} | #{right.id}  (sube clave {right.keys[0]})")
        return right.keys[0], right

    def _split_internal(self, node):
        mid = self.t
        sep = node.keys[mid]
        right = BTreeNode(leaf=False)
        right.keys, right.children = node.keys[mid + 1:], node.children[mid + 1:]
        node.keys, node.children = node.keys[:mid], node.children[:mid + 1]
        self.splits += 1
        self._log(f"SPLIT interno #{node.id} -> #{node.id} | #{right.id}  (sube clave {sep})")
        return sep, right

    # ---------------------------------------------------------- bulk load
    def bulk_load(self, items):
        """Construye el árbol desde cero a partir de pares (clave, RowID).
        Ordena, empaqueta hojas al máximo y construye los niveles hacia arriba: O(n)."""
        if self.size:
            raise ValueError("bulk_load requiere un árbol vacío")
        items = sorted(items, key=lambda kv: kv[0])
        for a, b in zip(items, items[1:]):
            if a[0] == b[0]:
                raise DuplicateKeyError(a[0])
        if not items:
            return
        level, pos, prev = [], 0, None
        for s in _partition(len(items), self.max_keys):
            leaf = BTreeNode(leaf=True)
            chunk = items[pos:pos + s]
            leaf.keys = [k for k, _ in chunk]
            leaf.values = [v for _, v in chunk]
            pos += s
            if prev:
                prev.next = leaf
            prev = leaf
            level.append((leaf, leaf.keys[0]))   # (nodo, clave mínima del subárbol)
        height = 1
        while len(level) > 1:
            nxt, pos = [], 0
            for s in _partition(len(level), self.max_keys + 1):
                group = level[pos:pos + s]
                pos += s
                node = BTreeNode(leaf=False)
                node.children = [g[0] for g in group]
                node.keys = [g[1] for g in group[1:]]
                nxt.append((node, group[0][1]))
            level = nxt
            height += 1
        self.root, self.height, self.size = level[0][0], height, len(items)
        self._log(f"BULK LOAD: {len(items)} claves, altura = {height}")

    # --------------------------------------------------------- utilidades
    def level_sizes(self):
        """Cantidad de nodos por nivel (raíz primero)."""
        out, level = [], [self.root]
        while level:
            out.append(len(level))
            level = [c for n in level if not n.leaf for c in n.children]
        return out

    def check_invariants(self):
        """Verifica las propiedades del árbol; lanza AssertionError si alguna falla."""
        leaf_depths, leaves = set(), []

        def walk(node, depth, lo, hi, is_root):
            ks = node.keys
            assert ks == sorted(ks) and len(set(ks)) == len(ks), "claves desordenadas"
            assert len(ks) <= self.max_keys, "nodo desbordado"
            for k in ks:
                assert (lo is None or k >= lo) and (hi is None or k < hi), "clave fuera de rango"
            if node.leaf:
                assert len(node.values) == len(ks)
                assert is_root or len(ks) >= self.t - 1, "hoja subocupada"
                leaf_depths.add(depth)
                leaves.append(node)
                return
            assert len(node.children) == len(ks) + 1
            assert len(node.children) >= (2 if is_root else self.t), "interno subocupado"
            bounds = [lo] + ks + [hi]
            for i, c in enumerate(node.children):
                walk(c, depth + 1, bounds[i], bounds[i + 1], False)

        walk(self.root, 1, None, None, True)
        assert len(leaf_depths) == 1, "hojas a distinta profundidad"
        assert leaf_depths == {self.height}, "altura inconsistente"
        for a, b in zip(leaves, leaves[1:]):
            assert a.next is b, "enlace entre hojas roto"
        assert leaves[-1].next is None
        assert sum(len(l.keys) for l in leaves) == self.size, "size inconsistente"
        return True
