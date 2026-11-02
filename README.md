# Simulador de Máquinas de Turing

Proyecto 3 de Teoría de la Computación. Simula Máquinas de Turing (MT)
deterministas de **una sola cinta** descritas en un archivo YAML y muestra
todas las descripciones instantáneas (IDs) de cada ejecución.

> Estado: en desarrollo. Están listos la carga y validación del YAML, el
> motor, las IDs y la interfaz de terminal. Las máquinas de demostración
> (reconocedora y alteradora) se agregan en las siguientes partes.

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
  ejemplo_enunciado.yaml
tests/
  test_cargador.py  test_motor.py  test_presentacion.py
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
