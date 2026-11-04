# Simulador de Máquinas de Turing

Proyecto 3 de Teoría de la Computación. Simula Máquinas de Turing (MT)
deterministas de **una sola cinta** descritas en un archivo YAML y muestra
todas las descripciones instantáneas (IDs) de cada ejecución.

> Estado: en desarrollo. Están listos la carga y validación del YAML, el
> motor, las IDs, la interfaz de terminal y las dos máquinas de
> demostración (reconocedora y alteradora). Falta la revisión final de
> documentación y la preparación del video.

## Requisitos e instalación

- Python 3.10 o superior.
- [PyYAML](https://pypi.org/project/PyYAML/) 6.x (única dependencia).

```bash
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Linux / macOS:        source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Uso

```bash
python -m simulador_mt maquinas/ejemplo_enunciado.yaml
```

Simula cada cadena de `inputs` y muestra la definición de la máquina, las
IDs de cada paso, la configuración final, el resultado y un resumen.

| Opción | Efecto |
|---|---|
| `--max-pasos N` | Límite de pasos por entrada (por defecto 10 000). |
| `--salida RUTA` | Guarda la traza completa en `RUTA` (UTF-8). |
| `--resumen` | No muestra las IDs en pantalla; el archivo de `--salida` siempre las contiene todas. |

```bash
python -m simulador_mt maquinas/ejemplo_enunciado.yaml --salida trazas/ejemplo.txt
```

Para guardar la traza conviene usar `--salida` en lugar de redirigir con `>`:
en Windows PowerShell la redirección puede cambiar la codificación de `δ` y `⊢`.
Código de salida: `0` si la máquina se cargó y se simularon las entradas
(sin importar si fueron aceptadas), `1` si el YAML es inválido o no se pudo
escribir la traza y `2` si las opciones son incorrectas.

Salida del ejemplo del enunciado para `"aabb"` (este ejemplo no tiene
transiciones hacia `qf`, así que solo demuestra el parsing):

```
Descripciones instantáneas (cabezal = posición de la celda leída):
  0   [q0,B]aabb   cabezal=0
  1 ⊢ [q1,a]abb    cabezal=1   por #1: δ([q0,B], a) = ([q1,a], B, R)
...
Resultado: RECHAZADA
Motivo: no hay transición para δ([q1,a], a) y [q1,a] no es de aceptación
Pasos: 1
```

## Pruebas

```bash
python -m unittest -v
```

Las pruebas usan solo `unittest` de la biblioteca estándar. Cubren la
validación del YAML, la cinta, cada tipo de terminación, la frontera del
límite de pasos, el aislamiento entre ejecuciones, la inmutabilidad de las
configuraciones, el formato de las IDs y la CLI. Además, cada traza probada
se **reproduce paso a paso**: desde cada configuración y la regla registrada
se recalcula la siguiente y se compara celda por celda.

## Formato del archivo YAML

Todo va dentro de la clave raíz `mt`:

```yaml
mt:
  states: [q0, q1, qf]          # Q
  input_alphabet: [a, b]        # Σ
  tape_alphabet: [a, b, X, B]   # Γ ⊇ Σ ∪ {blanco}
  blank: B                      # opcional; por defecto B
  initial_state: q0
  accept_states: [qf]           # F
  transitions:
    - {state: q0, read: a, write: X, move: R, next: q1}
    - state: q1                 # también se admite la forma expandida
      read: B
      write: B
      move: S
      next: qf
  inputs:
    - "ab"
    - ""                        # cadena vacía
```

| Clave | Obligatoria | Regla |
|---|---|---|
| `states` | sí | Lista sin repetidos. Nombres sin espacios ni `[`, `]`, `,`. |
| `input_alphabet` | sí | Símbolos de un carácter; no puede contener el blanco. |
| `tape_alphabet` | sí | Debe contener a `input_alphabet` y al blanco. |
| `blank` | no | Un símbolo de `tape_alphabet`; por defecto `B`. |
| `initial_state` | sí | Debe estar en `states`. |
| `accept_states` | sí | Subconjunto de `states` (vacío solo genera advertencia). |
| `transitions` | sí | Lista de mapeos con exactamente `state`, `read`, `write`, `move`, `next`. |
| `inputs` | sí | Lista de cadenas a simular. |

Una clave desconocida es un error (se sugiere la más parecida), igual que una
clave repetida dentro del mismo mapeo.

### Dos formatos de transición

**Escalar (formato principal, usado por nuestras máquinas):** `read` y
`write` son un símbolo. Representa δ(q, a) = (p, X, M).

**Con memoria en el estado (compatibilidad con el ejemplo del enunciado):**
el enunciado escribe

```yaml
- state: q0
  read: [a, B]
  write: [a, B]
  move: R
  next: q1
```

junto con la ecuación δ([q0, B], a) = ([q1, a], B, R). El documento no explica
las listas. La única lectura coherente con ambas transiciones del ejemplo es
la de una MT con **memoria en el control finito** (Hopcroft, Motwani y Ullman,
§8.3.1), que sigue siendo de una sola cinta:

- `read: [símbolo leído, memoria actual]`
- `write: [memoria nueva, símbolo escrito]`
- el estado efectivo es el par `[q,m]`; la memoria inicial es el blanco.

El cargador traduce este formato a estados compuestos `[q,m]` (Q' = Q × Γ),
de modo que el motor ejecuta una MT estándar. Las listas **no** se
interpretan como dos cintas ni como pistas ni como alternativas. No se pueden
mezclar ambos formatos en un mismo archivo. `maquinas/ejemplo_enunciado.yaml`
es el ejemplo copiado tal cual; solo sirve para comprobar el parsing, porque
no tiene transiciones hacia `qf` y no acepta ninguna de sus entradas.

## Decisiones y convenciones

| Tema | Decisión |
|---|---|
| Lectura del YAML | Carga segura (`SafeLoader`) en la que **todo escalar es texto**: `[0, 1]` son los símbolos `'0'` y `'1'`, `010` sigue siendo `'010'` y `yes` no es un booleano. |
| Símbolos | Exactamente un carácter, distingue mayúsculas. Espacios y `[`, `]`, `,` están reservados. |
| Entradas | Cada carácter es un símbolo. La cadena vacía se escribe `""`; un elemento vacío sin comillas (`-`) es un error, no se toma como cadena vacía. No se recortan espacios ni se cambia la cadena: si tiene un símbolo fuera de Σ es una **entrada inválida** (se informa la posición) y se continúa con las demás. |
| Movimientos | `L`, `R` y `S` (quedarse; extensión documentada). |
| Determinismo | Dos transiciones para la misma situación (estado, símbolo) son un error de carga, aunque sean idénticas. Nunca se sobrescribe una en silencio. |
| Transiciones desde un estado de aceptación | Se admiten con advertencia, porque nunca se ejecutan. |

## Semántica de ejecución

**Cinta.** Infinita en ambos sentidos. La entrada ocupa las celdas
`0..n-1`, el cabezal empieza en la celda 0 y las posiciones negativas son
válidas. Una celda nunca escrita contiene el blanco. Con la cadena vacía, el
cabezal empieza sobre un blanco.

**Paso.** Con estado `q` y símbolo leído `a`, si δ(q, a) = (p, X, M): se
escribe `X` en la celda actual, el cabezal se mueve (`L` −1, `R` +1, `S` 0)
y el estado pasa a `p`.

**Parada.** Antes de cada paso se comprueba, en este orden:

| Condición | Resultado |
|---|---|
| El estado actual es de aceptación | **ACEPTADA** (la máquina se detiene al entrar en él) |
| δ(estado, símbolo leído) no está definida | **RECHAZADA** |
| Ya se hicieron `--max-pasos` pasos y aún hay una transición aplicable | **LÍMITE ALCANZADO / resultado no determinado** |

El límite es solo una protección operativa: alcanzarlo **no** significa que
la cadena sea rechazada, porque no se puede decidir en general si una MT se
detendrá. Una entrada con símbolos fuera de Σ es **ENTRADA INVÁLIDA**: la
máquina no se ejecuta y se continúa con la siguiente entrada.

**Descripciones instantáneas.** Se usa la notación α[q]β (Hopcroft): el
estado aparece entre corchetes justo antes del símbolo que lee el cabezal.
Por ejemplo, `XaY[q2]bZ` significa estado `q2`, cabezal sobre `b`. Se muestra
la ventana desde la primera celda no blanca hasta la última, ampliada para
incluir siempre la celda del cabezal; por eso los blancos relevantes
aparecen como `B`, por ejemplo `abcB[q]B` o `[q]BBabc` con el cabezal en la
posición −2. Los estados compuestos del formato con memoria ya llevan
corchetes y se muestran tal cual: `[q1,a]abb`. Cada línea de la traza indica
además la posición del cabezal y la regla aplicada (`por #1: δ(q0, a) = ...`).

**Configuración final.** Se muestra en tres filas (posiciones, símbolos y
cabezal), junto con la ID final y el contenido no blanco **real** de la
cinta. Si ese contenido incluye símbolos que no son de Σ (marcadores o
blancos interiores), se indica explícitamente en lugar de ocultarlos.

## MT reconocedora: L = { ww : w ∈ {a,b}* }

Archivo: [`maquinas/reconocedora.yaml`](maquinas/reconocedora.yaml).

```bash
python -m simulador_mt maquinas/reconocedora.yaml
```

**Lenguaje.** Cadenas sobre {a, b} formadas por una misma palabra escrita
dos veces, **sin separador**: `abbabb` (w = `abb`) pertenece a L, `abaabb`
no. Incluye la cadena vacía (ε = εε). L no es libre de contexto, así que
ningún autómata de pila lo reconoce. La dificultad está en que la máquina
tiene que encontrar por sí misma dónde termina la primera mitad.

**Definición formal.** M = (Q, Σ, Γ, δ, q0, B, F) con
Q = {q0, …, q8, qf}, Σ = {a, b}, Γ = {a, b, X, Y, U, V, Z, W, B} y F = {qf}.

| Marcador | Significado |
|---|---|
| `X` / `Y` | `a` / `b` de la primera mitad, aún sin comparar |
| `U` / `V` | `a` / `b` de la segunda mitad, aún sin comparar |
| `Z` | símbolo de la primera mitad ya comparado |
| `W` | símbolo de la segunda mitad ya comparado |

**Fases y estados.**

| Fase | Estado | Papel |
|---|---|---|
| 1. Encontrar la mitad | `q0` | En el símbolo libre más a la izquierda: lo marca X/Y. Si lee U/V, ya encontró la mitad. Si lee B, la entrada es ε y acepta. |
| | `q1` | Avanza a la derecha sobre a/b hasta U, V o B. |
| | `q2` | Marca U/V el símbolo libre más a la derecha. Si lee X/Y, la longitud es impar y rechaza. |
| | `q3` | Retrocede sobre a/b hasta la última X/Y. |
| 2. Rebobinar | `q4` | Va a la izquierda sobre X/Y hasta el blanco. |
| 3. Comparar | `q5` | En el primer X/Y: lo cambia por Z y pasa a q6 (lleva `a`) o q7 (lleva `b`). Si lee W, acepta. |
| | `q6` / `q7` | Avanzan sobre X, Y, W hasta el primer U/V. Si coincide, lo cambian por W; si no, rechazan. |
| | `q8` | Retrocede sobre W, X, Y hasta la última Z. |

**Transiciones** (celda = `siguiente, escribe, mueve`; `—` = no definida,
la máquina se detiene; `qf` no tiene transiciones):

| δ | a | b | X | Y | U | V | Z | W | B |
|---|---|---|---|---|---|---|---|---|---|
| q0 | q1,X,R | q1,Y,R | — | — | q4,U,L | q4,V,L | — | — | qf,B,S |
| q1 | q1,a,R | q1,b,R | — | — | q2,U,L | q2,V,L | — | — | q2,B,L |
| q2 | q3,U,L | q3,V,L | — | — | — | — | — | — | — |
| q3 | q3,a,L | q3,b,L | q0,X,R | q0,Y,R | — | — | — | — | — |
| q4 | — | — | q4,X,L | q4,Y,L | — | — | — | — | q5,B,R |
| q5 | — | — | q6,Z,R | q7,Z,R | — | — | — | qf,W,S | — |
| q6 | — | — | q6,X,R | q6,Y,R | q8,W,L | — | — | q6,W,R | — |
| q7 | — | — | q7,X,R | q7,Y,R | — | q8,W,L | — | q7,W,R | — |
| q8 | — | — | q8,X,L | q8,Y,L | — | — | q5,Z,R | q8,W,L | — |

**Algunas IDs de `abbabb`** (54 pasos):

```
 0  [q0]abbabb      inicio
 7  Xbbab[q2]b      marcará la última b como V
13  X[q0]bbabV      segunda ronda de la fase 1
26  XY[q3]YUVV      la mitad quedó marcada: XYY | UVV
31  [q4]BXYYUVV     rebobinado completo
40  ZZ[q7]YWVV      lleva b para la tercera comparación
54  ZZZ[qf]WWW      todo coincidió: aceptada
```

**Por qué funciona.** Sea n la longitud de la entrada.

- *Invariante de la fase 1.* Tras k rondas, las celdas `0..k-1` son X/Y, las
  últimas k son U/V y entre ellas solo hay a/b libres; cada marca conserva la
  letra original (X/U = a, Y/V = b). Cada ronda marca un símbolo de cada
  extremo. Si n es par, tras n/2 rondas `q0` lee U/V exactamente en la celda
  n/2. Si n es impar, en la ronda (n+1)/2 `q0` marca el símbolo central y `q2`
  ya no encuentra ninguno libre: lee X/Y, que no tiene transición, y rechaza.
- *Invariante de la fase 3.* Con m = n/2, al entrar en `q5` por j-ésima vez la
  cinta es Z^j (X|Y)^(m−j) W^j (U|V)^(m−j), con el cabezal en la celda j. La
  ronda j+1 lleva la letra de la celda j (en el estado q6 o q7) hasta el
  primer U/V, que está en la celda m+j. Si las letras coinciden la convierte
  en W; si no, se detiene sin transición. Por eso `q5` lee W (con j = m) si y
  solo si las letras de las posiciones i y m+i coinciden para todo i, es
  decir, si la cadena es ww.
- *Ninguna lectura inesperada.* `q6`/`q7` nunca leen B, porque quedan tantos
  U/V como X/Y. `q8` nunca lee B, porque siempre hay al menos una Z a su
  izquierda. `q4` nunca lee U/V, porque empieza a la izquierda de la mitad.

**Terminación.** Cada ronda marca permanentemente una celda nueva o detiene
la máquina, y cada recorrido avanza en un solo sentido dentro de las n celdas
más un blanco. La fase 1 hace a lo sumo ⌈n/2⌉ rondas de a lo sumo 2n+4
pasos, es decir, ≤ (n+2)²; la fase 2 hace ≤ n/2 + 2; la fase 3 hace n/2
rondas de ≤ 2n+4 pasos, es decir, ≤ n(n+2). En total hay **menos de
2(n+2)² pasos**: la máquina se detiene con toda entrada sobre {a, b}, en
tiempo O(n²).

**Casos del video** (las entradas de `inputs` del YAML):

| Entrada | Longitud | Esperado | Pasos | Motivo |
|---|---|---|---|---|
| `abbabb` | 6 | ACEPTADA | 54 | w = `abb` |
| `bbabbbab` | 8 | ACEPTADA | 87 | w = `bbab` |
| `aabab` | 5 | RECHAZADA | 20 | longitud impar: `q2` lee `Y` (fase 1) |
| `abaabb` | 6 | RECHAZADA | 49 | `aba` ≠ `abb`: `q6` lleva `a` y encuentra `V` en la 3.ª comparación |

Las dos rechazadas usan solo símbolos válidos y fallan por estructura, en
fases distintas. Además se eligieron cadenas que no son palíndromos, para
que no se confunda L con el lenguaje de los palíndromos.

**Verificación.** `tests/test_reconocedora.py` comprueba los casos del video
(resultado, número exacto de pasos y reproducción paso a paso de la traza),
la definición (10 estados, 34 transiciones, sin advertencias) y lo siguiente:

- Las **2 047 cadenas de longitud 0 a 10** dan el mismo resultado que un
  oráculo independiente (`tests/oraculos.py`), sin alcanzar el límite y sin
  superar la cota de 2(n+2)² pasos.
- 600 cadenas aleatorias de longitud 11 a 40 con semilla fija: ww, ww con
  una letra cambiada en la segunda mitad y ww sin la última letra.

Estas pruebas dan evidencia y complementan el argumento anterior, pero no lo
sustituyen.

## MT alteradora: reversa sobre las mismas celdas

Archivo: [`maquinas/alteradora.yaml`](maquinas/alteradora.yaml).

```bash
python -m simulador_mt maquinas/alteradora.yaml
```

**Transformación.** f(w) = wᴿ para w ∈ {a, b}*. Si la entrada w ocupa las
celdas `0..n-1`, al terminar esas mismas celdas contienen wᴿ, el resto de la
cinta queda en blanco, **no queda ningún marcador** y el cabezal está en la
celda 0. Por ejemplo, `aabab` → `babaa`. La máquina termina en `qf` con toda
entrada válida; en esta MT, "ACEPTADA" significa que la transformación
terminó.

A diferencia de la reversa típica, que escribe una copia invertida después
de un separador, esta máquina **intercambia los extremos sobre la propia
cadena**. Para hacerlo lleva un símbolo en el estado en cada sentido, resuelve
el símbolo central cuando la longitud es impar y, al final, restaura las
letras originales.

**Definición formal.** M = (Q, Σ, Γ, δ, q0, B, F) con
Q = {q0, …, q8, qf}, Σ = {a, b}, Γ = {a, b, H, X, Y, B} y F = {qf}.

| Marcador | Significado |
|---|---|
| `H` | hueco: celda izquierda cuyo símbolo se está llevando a la derecha |
| `X` / `Y` | `a` / `b` ya colocado en su posición final |

**Fases y estados.**

| Fase | Estado | Papel |
|---|---|---|
| 1. Intercambiar extremos | `q0` | En el símbolo libre más a la izquierda: lo cambia por H y lo lleva a la derecha (`a` → q1, `b` → q2). Si lee X/Y, ya no quedan libres y pasa a limpiar. Si lee B, la entrada es ε. |
| | `q1` / `q2` | Llevan `a` / `b` a la derecha sobre a/b hasta X, Y o B, y retroceden una celda. |
| | `q3` / `q4` | En el símbolo libre más a la derecha: escriben X / Y (el símbolo llevado, ya en su lugar final) y recogen el que había (`a` → q5, `b` → q6). Si leen H, el hueco es el símbolo central: lo marcan y se quedan (`S`). |
| | `q5` / `q6` | Traen `a` / `b` a la izquierda hasta H, escriben X / Y y vuelven a q0. |
| 2. Limpiar | `q7` | Va a la derecha sobre X/Y hasta el blanco. |
| | `q8` | Regresa cambiando X → a, Y → b y termina en `qf` con el cabezal en la celda 0. |

**Transiciones** (celda = `siguiente, escribe, mueve`; `—` = no definida;
`qf` no tiene transiciones):

| δ | a | b | H | X | Y | B |
|---|---|---|---|---|---|---|
| q0 | q1,H,R | q2,H,R | — | q7,X,R | q7,Y,R | qf,B,S |
| q1 | q1,a,R | q1,b,R | — | q3,X,L | q3,Y,L | q3,B,L |
| q2 | q2,a,R | q2,b,R | — | q4,X,L | q4,Y,L | q4,B,L |
| q3 | q5,X,L | q6,X,L | q0,X,S | — | — | — |
| q4 | q5,Y,L | q6,Y,L | q0,Y,S | — | — | — |
| q5 | q5,a,L | q5,b,L | q0,X,R | — | — | — |
| q6 | q6,a,L | q6,b,L | q0,Y,R | — | — | — |
| q7 | — | — | — | q7,X,R | q7,Y,R | q8,B,L |
| q8 | — | — | — | q8,a,L | q8,b,L | qf,B,R |

**IDs seleccionadas de `aabab` → `babaa`** (31 pasos):

```
 0  [q0]aabab       inicio
 1  H[q1]abab       toma la primera a y deja el hueco H
 6  Haba[q3]b       extremo derecho: escribirá X (la a llevada) y recoge b
10  [q6]HabaX       trae la b hasta el hueco
11  Y[q0]abaX       primer intercambio hecho: a…b → Y…X
18  YX[q0]bXX       segundo intercambio hecho
20  YX[q4]HXX       el hueco es el símbolo central (longitud impar)
21  YX[q0]YXX       todo colocado; empieza la limpieza
24  YXYXX[q7]B      llegó al final
30  [q8]Bbabaa      letras restauradas
31  [qf]babaa       resultado: babaa, cabezal en la celda 0
```

**Por qué funciona.** Sea w = w₀…wₙ₋₁ y sea m(c) la marca final de la letra
c (m(a) = X, m(b) = Y).

- *Invariante de la fase 1.* Al entrar en `q0` tras k intercambios, la cinta
  es m(wₙ₋₁)…m(wₙ₋ₖ) · wₖ…wₙ₋ₖ₋₁ · m(wₖ₋₁)…m(w₀), con el cabezal en la
  celda k. Es decir, las k primeras y las k últimas celdas ya contienen
  (marcadas) las letras correctas de wᴿ, y el centro sigue intacto.
- *Un intercambio.* Desde `q0` en la celda k con wₖ = c, la máquina escribe H y
  lleva c (q1/q2) hasta la celda n−k−1, la última libre. Ahí escribe m(c),
  recoge d = wₙ₋ₖ₋₁ (q5/q6), vuelve hasta H y escribe m(d). Entre H y el
  extremo derecho solo hay letras libres, así que los recorridos se detienen
  en el lugar correcto. El invariante se cumple para k+1.
- *Centro.* Si n es impar, cuando k = (n−1)/2 el único símbolo libre es el
  central. `q1`/`q2` encuentran la marca de la celda siguiente, retroceden al
  propio hueco, y `q3`/`q4` leen H y escriben la marca de esa misma letra,
  que en wᴿ queda en el mismo lugar. El movimiento `S` deja a `q0` sobre esa
  marca. Si fuera `R`, con n = 1 `q0` caería en el blanco y la máquina
  terminaría sin limpiar (un mutante que lo hace es detectado por las
  pruebas).
- *Fin de la fase 1 y limpieza.* `q0` lee X/Y exactamente cuando no quedan
  letras libres; en ese momento toda la cadena es m(wᴿ). `q7` va al último
  marcador y `q8` cambia cada marcador por su letra hasta el blanco de la
  celda −1, y luego avanza a la celda 0. El resultado es wᴿ sin residuos.

**Terminación.** Cada ronda de la fase 1 fija permanentemente dos celdas
(una en la ronda del centro) y, sobre una región libre de m celdas, tarda
exactamente 2m + 1 pasos. Hay ⌈n/2⌉ rondas. La limpieza recorre la cadena una
vez en cada sentido. Para n ≥ 1 el número de pasos depende solo de n:
**(n² + 6n + 4)/2 si n es par y (n² + 6n + 7)/2 si n es impar**. Con la
cadena vacía hace 1 paso. Esto es O(n²) y siempre es menor o igual que
(n+2)² + 1, así que la máquina se detiene con toda entrada sobre {a, b}.

**Casos del video** (las entradas de `inputs` del YAML):

| Entrada | Longitud | Salida esperada | Pasos |
|---|---|---|---|
| `aabab` | 5 | `babaa` | 31 |
| `abbbb` | 5 | `bbbba` | 31 |
| `aaabbb` | 6 | `bbbaaa` | 38 |
| `abbabaa` | 7 | `aababba` | 49 |

Ninguna es un palíndromo, así que un error que dejara la cadena sin cambios
sería visible. Hay longitudes pares e impares. La salida nunca es una cinta
en blanco.

**Verificación.** `tests/test_alteradora.py` comprueba los casos del video
(salida, número exacto de pasos y reproducción de la traza) y lo siguiente:

- Las **2 047 cadenas de longitud 0 a 10** terminan con exactamente su
  reversa (`tests/oraculos.py`) en las celdas `0..n-1`, nada más escrito en
  la cinta, el cabezal en 0 y exactamente el número de pasos de la fórmula.
- 100 cadenas aleatorias de longitud 11 a 40 con semilla fija.
- Las 33 transiciones se ejecutan al menos una vez, y los marcadores H, X e
  Y aparecen durante la ejecución pero no al final.

## Arquitectura

```
simulador_mt/
  modelo.py        # Transicion y MaquinaTuring inmutables; validación de entradas
  cargador.py      # YAML seguro → validación completa → MaquinaTuring
  cinta.py         # Cinta dispersa: dict posición → símbolo (solo celdas no blancas)
  motor.py         # ejecutar(): aplica δ paso a paso; Configuracion y Resultado inmutables
  presentacion.py  # Texto de la máquina, las IDs, la cinta y el resumen
  __main__.py      # CLI: argumentos, salida UTF-8 y archivo de traza
maquinas/
  ejemplo_enunciado.yaml  reconocedora.yaml  alteradora.yaml
tests/
  test_cargador.py  test_motor.py  test_presentacion.py
  test_reconocedora.py  test_alteradora.py
  oraculos.py      # referencias independientes, solo para pruebas
```

El flujo es YAML → `cargador` → `MaquinaTuring` → `motor.ejecutar` (una vez
por entrada, cada una con su propia cinta) → `Resultado` con todas las
`Configuracion` → `presentacion` → terminal y archivo. El motor solo consulta
δ; no sabe qué lenguaje reconoce ni qué transformación hace la máquina. Cada
`Configuracion` es una copia inmutable de la cinta en ese paso, no una
referencia a la cinta viva, así que la traza no cambia aunque la ejecución
continúe.

`cargador.py` reúne **todos** los errores que encuentra en una pasada y los
reporta juntos con su ubicación (por ejemplo `transición #3.move: 'D' no es
válido; use uno de ['L', 'R', 'S']`).
