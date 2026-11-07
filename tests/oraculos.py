"""Implementaciones de referencia independientes del simulador.

Solo se usan en las pruebas para comparar resultados; nunca sustituyen a la
MT. No importan nada de simulador_mt.
"""

from itertools import product


def es_ww(cadena: str) -> bool:
    """¿La cadena es una palabra repetida dos veces?"""
    mitad, resto = divmod(len(cadena), 2)
    return resto == 0 and cadena[:mitad] == cadena[mitad:]


def suma_binaria(cadena: str):
    """Resultado esperado de la MT alteradora, o None si la cadena no
    tiene la forma x+y con x, y binarios no vacíos.

    La suma conserva el ancho del operando más largo (ceros a la
    izquierda incluidos) y crece una cifra si queda un acarreo final.
    """
    partes = cadena.split("+")
    if len(partes) != 2 or not all(p and set(p) <= {"0", "1"} for p in partes):
        return None
    x, y = partes
    return format(int(x, 2) + int(y, 2), "b").zfill(max(len(x), len(y)))


def todas_las_cadenas(alfabeto: str, longitud_maxima: int):
    """Todas las cadenas sobre el alfabeto, de longitud 0 a longitud_maxima."""
    for n in range(longitud_maxima + 1):
        for simbolos in product(alfabeto, repeat=n):
            yield "".join(simbolos)
