"""Cinta infinita en ambos sentidos.

Convención: la entrada ocupa las celdas 0..n-1 y el cabezal empieza en 0.
Las posiciones negativas son válidas. Solo se guardan las celdas que no
contienen el blanco, así que leer una celda nunca escrita devuelve el blanco
y la cinta "crece" sin reservar memoria ni desplazar índices.
"""

from __future__ import annotations

from typing import Iterable


class Cinta:
    def __init__(self, blanco: str, simbolos: Iterable[str] = ()):
        self.blanco = blanco
        self._celdas: dict[int, str] = {}
        for posicion, simbolo in enumerate(simbolos):
            self.escribir(posicion, simbolo)

    def leer(self, posicion: int) -> str:
        return self._celdas.get(posicion, self.blanco)

    def escribir(self, posicion: int, simbolo: str) -> None:
        # Escribir el blanco equivale a borrar la celda; así el contenido
        # guardado es siempre exactamente el conjunto de celdas no blancas.
        if simbolo == self.blanco:
            self._celdas.pop(posicion, None)
        else:
            self._celdas[posicion] = simbolo

    def contenido(self) -> tuple[int, tuple[str, ...]]:
        """(posición inicial, símbolos) desde la primera hasta la última celda
        no blanca, con los blancos interiores incluidos. Cinta vacía: (0, ())."""
        if not self._celdas:
            return 0, ()
        inicio, fin = min(self._celdas), max(self._celdas)
        return inicio, tuple(self.leer(p) for p in range(inicio, fin + 1))
