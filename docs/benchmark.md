# Resultados del benchmark

Comando: `python src/main.py bench` (t = 50, páginas de 4 KB)

```text
Grado t = 50  (máx. 99 claves/nodo) | página = 4096 B

   filas   págs altura |     carga      bulk |  Index ms  nodos  págs |   Scan ms    págs |  speedup
---------------------------------------------------------------------------------------------------------
    1000     12      2 |     0.01s     0.00s |    0.0053    2.0   1.0 |      1.22       7 |     230x
   10000    118      3 |     0.06s     0.04s |    0.0046    3.0   1.0 |     10.43      73 |    2278x
  100000   1220      3 |     0.48s     0.39s |    0.0060    3.0   1.0 |     89.90     752 |   15078x

Notas: tiempos y páginas son PROMEDIO por consulta (claves aleatorias existentes).
El Full Scan se detiene al encontrar la clave (en promedio recorre ~la mitad de la tabla).
```

**Lectura:** el Index Scan visita `altura` nodos y **1** página de heap por consulta, mientras que el Full Scan lee, en promedio, ~la mitad de las páginas de la tabla. La ventaja crece con n (O(log n) vs O(n)).

_Los tiempos dependen de la máquina; ejecútalo para obtener tus propias cifras._
