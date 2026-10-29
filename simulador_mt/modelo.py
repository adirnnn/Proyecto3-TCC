"""Representación formal e inmutable de una Máquina de Turing de una cinta.

M = (Q, Σ, Γ, δ, q0, B, F). La máquina es determinista: δ es una función
parcial Q × Γ → Q × Γ × {L, R, S}. Si δ no está definida para el par
(estado, símbolo) actual, la máquina se detiene.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

# S (quedarse) es una extensión documentada del modelo clásico con solo L y R.
MOVIMIENTOS = ("L", "R", "S")


class EntradaInvalida(ValueError):
    """La cadena contiene símbolos fuera del alfabeto de entrada.

    Es distinta de un rechazo: la máquina ni siquiera llega a ejecutarse.
    """


@dataclass(frozen=True)
class Transicion:
    estado: str
    lee: str
    escribe: str
    mueve: str
    siguiente: str
    # Posición (desde 1) en la lista `transitions` del YAML, para poder
    # rastrear cada paso de la traza hasta la regla que lo produjo.
    indice: int

    def __str__(self) -> str:
        return (f"δ({self.estado}, {self.lee}) = "
                f"({self.siguiente}, {self.escribe}, {self.mueve})")


@dataclass(frozen=True)
class MaquinaTuring:
    nombre: str
    estados: tuple[str, ...]
    alfabeto_entrada: tuple[str, ...]
    alfabeto_cinta: tuple[str, ...]
    blanco: str
    estado_inicial: str
    estados_aceptacion: frozenset[str]
    # Clave (estado, símbolo leído). El cargador entrega un MappingProxyType
    # para que nadie pueda alterar δ después de validarla.
    transiciones: Mapping[tuple[str, str], Transicion]
    entradas: tuple[str, ...]
    # "escalar" (read: a) o "memoria" (read: [a, B], estados [q, m]).
    formato: str = "escalar"
    advertencias: tuple[str, ...] = ()

    def transicion(self, estado: str, simbolo: str) -> Optional[Transicion]:
        return self.transiciones.get((estado, simbolo))

    def es_aceptacion(self, estado: str) -> bool:
        return estado in self.estados_aceptacion


def problemas_de_entrada(maquina: MaquinaTuring, cadena: str) -> list[str]:
    """Devuelve los problemas de la cadena; lista vacía si es válida.

    Cada carácter es un símbolo (todos los símbolos miden un carácter), la
    comparación distingue mayúsculas y la cadena vacía es válida. No se
    recortan espacios ni se cambia nada: o la cadena es válida tal cual,
    o se informa por qué no.
    """
    permitidos = set(maquina.alfabeto_entrada)
    return [
        f"símbolo {simbolo!r} en la posición {i} no pertenece al alfabeto "
        f"de entrada {{{', '.join(maquina.alfabeto_entrada)}}}"
        for i, simbolo in enumerate(cadena)
        if simbolo not in permitidos
    ]


def tokenizar_entrada(maquina: MaquinaTuring, cadena: str) -> tuple[str, ...]:
    problemas = problemas_de_entrada(maquina, cadena)
    if problemas:
        raise EntradaInvalida(f"entrada {cadena!r} inválida: " + "; ".join(problemas))
    return tuple(cadena)
