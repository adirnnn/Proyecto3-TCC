# Simulador de Máquinas de Turing

Proyecto 3 de Teoría de la Computación. Simula Máquinas de Turing (MT)
deterministas de **una sola cinta** descritas en un archivo YAML y muestra
todas las descripciones instantáneas (IDs) de cada ejecución.

> Estado: en desarrollo. Están listos el modelo formal y la carga/validación
> del YAML. El motor, las IDs, la interfaz de terminal y las máquinas de
> demostración se agregan en las siguientes partes.

## Requisitos e instalación

- Python 3.10 o superior.
- [PyYAML](https://pypi.org/project/PyYAML/) 6.x (única dependencia).

```bash
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Linux / macOS:        source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Pruebas

```bash
python -m unittest -v
```

Las pruebas usan solo `unittest` de la biblioteca estándar.

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

Las convenciones de cinta, aceptación, parada y formato de las IDs se
documentan con el motor (Parte 2).

## Arquitectura

```
simulador_mt/
  modelo.py     # Transicion y MaquinaTuring inmutables; validación de entradas
  cargador.py   # YAML seguro → validación completa → MaquinaTuring
maquinas/
  ejemplo_enunciado.yaml
tests/
  test_cargador.py
```

`cargador.py` reúne **todos** los errores que encuentra en una pasada y los
reporta juntos con su ubicación (por ejemplo `transición #3.move: 'D' no es
válido; use uno de ['L', 'R', 'S']`).
