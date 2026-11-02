"""Motor de ejecución: aplica δ paso a paso y registra cada configuración.

Semántica de parada (en este orden, antes de cada paso):
1. Si el estado actual es de aceptación, la máquina se detiene y ACEPTA.
2. Si δ no está definida para (estado, símbolo leído), se detiene y RECHAZA.
3. Si ya se hicieron `max_pasos` pasos y aún habría uno más, se detiene
   con LÍMITE ALCANZADO: el resultado queda no determinado, no es rechazo.

El motor solo usa las transiciones de la máquina; no conoce el lenguaje
que reconoce ni la transformación que realiza.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .cinta import Cinta
from .modelo import EntradaInvalida, MaquinaTuring, Transicion, tokenizar_entrada

MAX_PASOS_POR_DEFECTO = 10_000
DESPLAZAMIENTO = {"L": -1, "R": 1, "S": 0}


class Terminacion(Enum):
    ACEPTADA = "ACEPTADA"
    RECHAZADA = "RECHAZADA"
    LIMITE = "LÍMITE ALCANZADO / resultado no determinado"
    INVALIDA = "ENTRADA INVÁLIDA"


@dataclass(frozen=True)
class Configuracion:
    """Descripción instantánea: una copia, no una vista de la cinta viva."""
    paso: int
    estado: str
    cabezal: int
    # Celdas no blancas desde `inicio` (ver Cinta.contenido).
    inicio: int
    simbolos: tuple[str, ...]
    blanco: str
    # Regla que produjo esta configuración; None en la configuración inicial.
    transicion: Optional[Transicion] = None

    def leer(self, posicion: int) -> str:
        indice = posicion - self.inicio
        if 0 <= indice < len(self.simbolos):
            return self.simbolos[indice]
        return self.blanco

    def ventana(self) -> range:
        """Celdas relevantes: el contenido no blanco y siempre la del cabezal."""
        if not self.simbolos:
            return range(self.cabezal, self.cabezal + 1)
        fin = self.inicio + len(self.simbolos) - 1
        return range(min(self.inicio, self.cabezal), max(fin, self.cabezal) + 1)


@dataclass(frozen=True)
class Resultado:
    entrada: str
    terminacion: Terminacion
    motivo: str
    # Configuración inicial seguida de una por cada paso; vacía si la
    # entrada es inválida, porque la máquina no llegó a ejecutarse.
    configuraciones: tuple[Configuracion, ...]

    @property
    def pasos(self) -> int:
        return max(len(self.configuraciones) - 1, 0)

    @property
    def final(self) -> Optional[Configuracion]:
        return self.configuraciones[-1] if self.configuraciones else None


def ejecutar(maquina: MaquinaTuring, entrada: str,
             max_pasos: int = MAX_PASOS_POR_DEFECTO) -> Resultado:
    if max_pasos < 0:
        raise ValueError("max_pasos no puede ser negativo")
    try:
        simbolos = tokenizar_entrada(maquina, entrada)
    except EntradaInvalida as exc:
        return Resultado(entrada, Terminacion.INVALIDA, str(exc), ())

    # Cada ejecución crea su propia cinta, estado e historial.
    cinta = Cinta(maquina.blanco, simbolos)
    estado, cabezal = maquina.estado_inicial, 0
    historial = [_instantanea(0, estado, cabezal, cinta, None)]

    while True:
        if maquina.es_aceptacion(estado):
            return Resultado(entrada, Terminacion.ACEPTADA,
                             f"entró al estado de aceptación {estado}", tuple(historial))
        leido = cinta.leer(cabezal)
        transicion = maquina.transicion(estado, leido)
        if transicion is None:
            return Resultado(entrada, Terminacion.RECHAZADA,
                             f"no hay transición para δ({estado}, {leido}) y {estado} "
                             f"no es de aceptación", tuple(historial))
        if len(historial) - 1 >= max_pasos:
            return Resultado(entrada, Terminacion.LIMITE,
                             f"se alcanzó el límite de {max_pasos} pasos con una transición "
                             f"aún aplicable; no se sabe si la máquina se detendría",
                             tuple(historial))

        cinta.escribir(cabezal, transicion.escribe)
        cabezal += DESPLAZAMIENTO[transicion.mueve]
        estado = transicion.siguiente
        historial.append(_instantanea(len(historial), estado, cabezal, cinta, transicion))


def _instantanea(paso: int, estado: str, cabezal: int, cinta: Cinta,
                 transicion: Optional[Transicion]) -> Configuracion:
    inicio, simbolos = cinta.contenido()
    return Configuracion(paso, estado, cabezal, inicio, simbolos, cinta.blanco, transicion)
