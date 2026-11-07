# Simulador de Máquinas de Turing

Proyecto 3 de Teoría de la Computación. Simula Máquinas de Turing (MT)
deterministas de **una sola cinta** descritas en un archivo YAML y muestra
todas las descripciones instantáneas (IDs) de cada ejecución.

Incluye la carga y validación del YAML, el motor, las IDs, la interfaz de
terminal y dos máquinas de demostración: una **reconocedora** de
L = { ww : w ∈ {a,b}* } y una **alteradora** que suma dos números binarios
`x+y` y deja solo el resultado en la cinta.

## Requisitos e instalación

- Python 3.10 o superior.
- [PyYAML](https://pypi.org/project/PyYAML/) 6.x (única dependencia).

Todos los comandos de este documento se ejecutan desde la **raíz del
repositorio** (la carpeta que contiene este README).

```bash
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Linux / macOS:        source .venv/bin/activate
python -m pip install -r requirements.txt
```

Si PowerShell no permite ejecutar `Activate.ps1` ("la ejecución de scripts
está deshabilitada"), habilítelo solo para la ventana actual con
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` y vuelva a
activar el entorno.

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

Debe terminar con `Ran 88 tests ... OK` (unos segundos). Las pruebas usan
solo `unittest` de la biblioteca estándar:

| Archivo | Pruebas | Qué cubre |
|---|---|---|
| `test_cargador.py` | 38 | Validación del YAML: claves, tipos, alfabetos, estados, determinismo, formato con memoria, lectura de escalares como texto, entradas inválidas. |
| `test_motor.py` | 17 | Cinta infinita en ambos sentidos, cada tipo de terminación, frontera del límite de pasos, aislamiento entre ejecuciones e inmutabilidad de las configuraciones. |
| `test_presentacion.py` | 16 | Notación de las IDs, alineación de la traza y de la cinta, resumen y CLI (archivo de traza y códigos de salida). |
| `test_reconocedora.py` | 6 | MT de ww: casos del video y comparación exhaustiva y aleatoria con un oráculo. |
| `test_alteradora.py` | 11 | MT de suma binaria: casos del video, casos particulares, comparación exhaustiva y aleatoria (resultado y pasos exactos), entradas mal formadas, uso de todas las transiciones. |

Además, cada traza probada se **reproduce paso a paso**: desde cada
configuración y la regla registrada se recalcula la siguiente y se compara
celda por celda.

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

## MT alteradora: suma binaria x+y

Archivo: [`maquinas/alteradora.yaml`](maquinas/alteradora.yaml).

```bash
python -m simulador_mt maquinas/alteradora.yaml
```

**Transformación.** La entrada es `x+y`, con x, y ∈ {0,1}⁺ escritos en
binario (el bit más significativo a la izquierda). Al terminar, la cinta
contiene **solo la suma x + y en binario**: sin `+`, sin restos de y y sin
marcadores. Por ejemplo, `1011+110` (11 + 6) → `10001` (17). El cabezal queda
sobre el primer símbolo del resultado, que termina en la celda |x|−1 y puede
empezar en celdas negativas, porque la suma puede ser más larga que x.

- El resultado tiene el ancho del operando más largo, o una cifra más si
  queda un acarreo final. Si los operandos no tienen ceros a la izquierda,
  la suma tampoco: `111+1` → `1000`. Si los tienen, se conserva el ancho:
  `1+0010` → `0011`. Se admite el operando `0` (`0+0` → `0`).
- Una entrada que no tiene la forma x+y (`+1`, `1+`, `1++1`, `11`, la
  cadena vacía) se detiene **sin aceptar** en la fase de validación, sin
  modificar la cinta.
- En esta MT, "ACEPTADA" significa que la suma terminó.

**Por qué es más que el ejemplo del enunciado.** La máquina valida la forma
de la entrada, recorre los bits de y del menos al más significativo, propaga
acarreos en cadena, maneja operandos de distinta longitud, extiende la cinta
hacia la izquierda (posiciones negativas) cuando la suma crece y, al final,
borra el operando y y todos los marcadores. Tiene 13 estados y 43
transiciones, frente a las 33 de una reversa in situ.

**Definición formal.** M = (Q, Σ, Γ, δ, q0, B, F) con
Q = {q0, …, q11, qf}, Σ = {0, 1, +}, Γ = {0, 1, +, C, U, B} y F = {qf}.

| Marcador | Significado |
|---|---|
| `C` / `U` | bit `0` / `1` definitivo del resultado (columna ya sumada); puede estar a la izquierda de x si y es más largo |

Se usan `C` (cero) y `U` (uno) en lugar de `O` e `I` para que no se
confundan con `0` y `1` en la traza.

**Fases y estados.**

| Fase | Estado | Papel |
|---|---|---|
| 1. Validar | `q0` | x debe empezar con un bit. |
| | `q1` | Recorre x hasta el `+`. |
| | `q2` | y debe empezar con un bit. |
| | `q3` | Recorre y hasta el blanco; un segundo `+` no tiene transición. |
| 2. Sumar | `q4` | En el extremo derecho: borra el último bit de y y lo lleva en el estado (`0` → q5, `1` → q6). Si lee `+`, y ya se acabó y pasa a limpiar. |
| | `q5` / `q6` | Llevan 0 / 1 a la izquierda sobre lo que queda de y hasta pasar el `+`. |
| | `q7` | Suma 0: pasa las posiciones ya sumadas (C/U) y marca la primera sin marcar. Si x se acabó (B), escribe una posición nueva. |
| | `q8` | Suma 1: igual que q7, pero 1 + 1 escribe `C` y genera acarreo. |
| | `q11` | Propaga el acarreo a la izquierda: `1` → `0` y sigue; `0` o B → `1` y termina. |
| | `q9` | Regresa al extremo derecho para tomar el siguiente bit de y. |
| 3. Limpiar | `q10` | Borra el `+` (lo hace q4) y regresa cambiando C → 0, U → 1 hasta el blanco; termina en `qf` sobre el primer símbolo. |

**Transiciones** (celda = `siguiente, escribe, mueve`; `—` = no definida,
la máquina se detiene; `qf` no tiene transiciones):

| δ | 0 | 1 | + | C | U | B |
|---|---|---|---|---|---|---|
| q0 | q1,0,R | q1,1,R | — | — | — | — |
| q1 | q1,0,R | q1,1,R | q2,+,R | — | — | — |
| q2 | q3,0,R | q3,1,R | — | — | — | — |
| q3 | q3,0,R | q3,1,R | — | — | — | q4,B,L |
| q4 | q5,B,L | q6,B,L | q10,B,L | — | — | — |
| q5 | q5,0,L | q5,1,L | q7,+,L | — | — | — |
| q6 | q6,0,L | q6,1,L | q8,+,L | — | — | — |
| q7 | q9,C,R | q9,U,R | — | q7,C,L | q7,U,L | q9,C,R |
| q8 | q9,U,R | q11,C,L | — | q8,C,L | q8,U,L | q9,U,R |
| q9 | q9,0,R | q9,1,R | q9,+,R | q9,C,R | q9,U,R | q4,B,L |
| q10 | q10,0,L | q10,1,L | — | q10,0,L | q10,1,L | qf,B,R |
| q11 | q9,1,R | q11,0,L | — | — | — | q9,1,R |

**IDs seleccionadas de `1011+110` → `10001`** (49 pasos):

```
 0  [q0]1011+110    inicio
 9  1011+11[q4]0    validada; toma el último bit de y (0)
13  101[q7]1+11     lleva 0 hasta la posición 2⁰ de x
14  101U[q9]+11     1 + 0 = 1, sin acarreo: marca U
23  1[q11]0CU+1     posición 2¹: 1 + 1 = 0 (C), lleva acarreo
24  11[q9]CU+1      el acarreo convierte el 0 de 2² en 1
34  [q11]1CCU+      posición 2²: 1 + 1 = 0 (C), otro acarreo
36  1[q9]0CCU+      el acarreo cruza el 1 de 2³ y crea la celda −1
43  10CC[q10]U      y se acabó: borró el + y empieza a limpiar
49  [qf]10001       resultado 10001 en las celdas −1..3
```

**Por qué funciona.** Sean a = |x|, b = |y|, n = a + b + 1, y sea
y = y_{b−1}…y₁y₀ (y₀ el bit menos significativo). La posición de peso 2ʲ de
la suma es la celda a−1−j; para j ≥ a está a la izquierda de la entrada.

- *Validación.* q0–q3 aceptan exactamente las cadenas de la forma
  `{0,1}⁺ + {0,1}⁺`, de izquierda a derecha y sin escribir nada distinto. Con
  cualquier otra cadena se detienen sin transición en esa misma pasada.
- *Invariante de la fase 2.* Al entrar en `q4` por (k+1)-ésima vez
  (k = 0, …, b), con el cabezal en el último símbolo no blanco:
  1. las celdas a+1 … a+b−k contienen y_{b−1}…y_k, el `+` sigue en la
     celda a y los k bits menores de y ya se borraron;
  2. a la izquierda del `+` hay una palabra sin blancos interiores, formada
     por bits sin marcar seguidos de exactamente k marcas C/U (las posiciones
     2⁰ … 2^{k−1});
  3. leída como número (C = 0, U = 1), esa palabra vale x + (y mod 2ᵏ).
- *Una ronda.* q4 borra y_k. q5/q6 cruzan lo que queda de y y el `+`, y
  q7/q8 cruzan las k marcas, así que se detienen justo en la posición 2ᵏ.
  Si es B, x ya no tiene esa cifra y vale 0. Sumar y_k ahí y marcarla deja
  k+1 marcas. Si 1 + 1, se escribe C y se suma 2ᵏ⁺¹ incrementando la parte
  sin marcar (q11): los `1` finales pasan a `0` y el primer `0` o B pasa a
  `1`. Como todo lo que está a la izquierda de la posición 2ᵏ está sin
  marcar, el acarreo nunca toca una marca. El valor aumenta exactamente
  y_k·2ᵏ, y q9 vuelve al último símbolo no blanco: el invariante se cumple
  para k+1.
- *Limpieza.* Con k = b, q4 lee el `+`, lo borra y q10 cambia cada marca por
  su bit hasta el blanco; luego avanza una celda. La cinta contiene
  x + y y nada más.
- *Ancho.* Se escriben celdas a la izquierda de x solo para una posición 2ʲ
  con j < b (q7/q8 leen B) o para un acarreo que la suma realmente necesita.
  Por eso el ancho es max(a, b), o uno más si la suma no cabe.
- *Ninguna lectura inesperada.* q5/q6 solo encuentran bits de y y el `+`;
  q7/q8, marcas, bits sin marcar o B; q11, solo bits sin marcar o B; q9 nunca
  lee un `1` sin marcar dentro de x (a la derecha de lo que acaba de escribir
  hay una marca, un `0` dejado por el acarreo o el `+`).

**Terminación.** La validación hace n + 1 pasos. La ronda k hace
2b + 3 + 2jₖ pasos, donde jₖ es lo que avanza su acarreo (0 si no hay). La
limpieza hace w + 2, con w el ancho del resultado. En total:

**pasos = n + 3 + b(2b + 3) + 2J + w**, con J = Σ jₖ.

Cada acarreo convierte jₖ − 1 unos sin marcar en ceros y crea a lo sumo uno
nuevo, así que J ≤ a + 2b. De ahí sale que **pasos ≤ 2n² + n**: la máquina se
detiene con toda entrada sobre {0, 1, +}, en tiempo O(n²). Las entradas mal
formadas se detienen en a lo sumo n pasos. Por ejemplo, en `1011+110` hay
acarreos de 1 y 2 celdas (J = 3) y w = 5: 8 + 3 + 27 + 6 + 5 = 49 pasos. El
peor caso medido es `1+11…1`, con 2n² − n pasos.

Como el límite por defecto es de 10 000 pasos, una suma de unas 71 cifras o
más puede terminar como LÍMITE ALCANZADO aunque la máquina sí se detendría.
Por ejemplo, `1+` seguido de 69 unos necesita 10 011 pasos; en ese caso hay
que usar, por ejemplo, `--max-pasos 20000`.

**Casos del video** (las entradas de `inputs` del YAML):

| Entrada | Longitud | Salida esperada | Pasos | Qué muestra |
|---|---|---|---|---|
| `1011+110` | 8 | `10001` | 49 | acarreos encadenados, operandos de distinta longitud |
| `111+1` | 5 | `1000` | 23 | un acarreo recorre todo x y crea una celda a la izquierda |
| `1+1111` | 6 | `10000` | 66 | x más corto que y: la cinta crece hasta la celda −4 |
| `1001+1001` | 9 | `10010` | 65 | operandos de igual longitud |

En todos los casos la salida es distinta de la entrada y nunca es una cinta
en blanco.

**Verificación.** `tests/test_alteradora.py` comprueba los casos del video
(salida, número exacto de pasos y reproducción de la traza) y lo siguiente:

- Las **29 524 cadenas sobre {0, 1, +} de longitud 0 a 9**. Las bien formadas
  terminan con exactamente la suma que da un oráculo independiente
  (`tests/oraculos.py`, con `int(x, 2) + int(y, 2)`), sin nada más en la
  cinta, el resultado terminando en la celda |x|−1, el cabezal sobre su
  primer símbolo y **exactamente** el número de pasos de la fórmula (con J
  calculado aparte, con aritmética de enteros), que nunca supera 2n² + n.
  Las mal formadas se rechazan en la validación sin cambiar la cinta.
- 200 sumas aleatorias con operandos de 1 a 25 bits y semilla fija.
- Casos particulares: operandos `0`, ceros a la izquierda y entradas mal
  formadas.
- Las 43 transiciones se ejecutan al menos una vez, y los marcadores C y U
  aparecen durante la ejecución pero no al final.

Además, durante el desarrollo se cambió cada transición, una por una, por
cada alternativa posible (otro símbolo, otro movimiento, otro estado, o
eliminarla) y se comprobaron los 860 mutantes con estos mismos criterios
sobre las cadenas hasta longitud 7. Se detectan 858. Los 2 restantes cambian
`δ(q9, 1)` o `δ(q9, +)` para que vayan a `q3` en lugar de `q9`. Ese cambio no
se nota porque q9 solo lee `1` o `+` dentro de y, donde q3 hace exactamente
lo mismo: escribe igual, se mueve igual y gasta los mismos pasos.

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
