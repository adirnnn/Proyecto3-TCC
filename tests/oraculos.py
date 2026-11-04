"""Implementaciones de referencia independientes del simulador.

Solo se usan en las pruebas para comparar resultados; nunca sustituyen a la
MT. No importan nada de simulador_mt.
"""

from itertools import product


def es_ww(cadena: str) -> bool:
    """¿La cadena es una palabra repetida dos veces?"""
    mitad, resto = divmod(len(cadena), 2)
    return resto == 0 and cadena[:mitad] == cadena[mitad:]


def invertir(cadena: str) -> str:
    return cadena[::-1]


def todas_las_cadenas(alfabeto: str, longitud_maxima: int):
    """Todas las cadenas sobre el alfabeto, de longitud 0 a longitud_maxima."""
    for n in range(longitud_maxima + 1):
        for simbolos in product(alfabeto, repeat=n):
            yield "".join(simbolos)
