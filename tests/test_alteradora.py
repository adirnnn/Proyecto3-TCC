"""Pruebas de la MT alteradora que invierte la cadena in situ (Parte 4)."""

import random
import unittest

from simulador_mt import cargar_maquina
from simulador_mt.motor import Terminacion, ejecutar

from tests.oraculos import invertir, todas_las_cadenas
from tests.test_motor import RAIZ, verificar_traza

MAQUINA = cargar_maquina(RAIZ / "maquinas" / "alteradora.yaml")
LONGITUD_EXHAUSTIVA = 10  # 2 047 cadenas


def pasos_exactos(n: int) -> int:
    # Fórmula del argumento de terminación del README: solo depende de n.
    # La cadena vacía es un caso aparte: q0 lee B y acepta en un paso.
    if n == 0:
        return 1
    return (n * n + 6 * n + (4 if n % 2 == 0 else 7)) // 2


class Definicion(unittest.TestCase):
    def test_carga_sin_advertencias(self):
        self.assertEqual(MAQUINA.formato, "escalar")
        self.assertEqual(MAQUINA.advertencias, ())
        self.assertEqual(len(MAQUINA.estados), 10)
        self.assertEqual(len(MAQUINA.transiciones), 33)


class Salida(unittest.TestCase):
    def assertInvierte(self, cadena):
        """La cinta final es exactamente w^R en 0..n-1, sin marcadores ni
        nada más escrito, con el cabezal en 0 y la máquina en qf."""
        r = ejecutar(MAQUINA, cadena)
        final = r.final
        self.assertIs(r.terminacion, Terminacion.ACEPTADA, cadena)
        self.assertEqual("".join(final.simbolos), invertir(cadena), cadena)
        self.assertEqual(final.inicio, 0, cadena)  # Cinta.contenido ya excluye blancos externos
        self.assertEqual((final.estado, final.cabezal), ("qf", 0), cadena)
        self.assertEqual(r.pasos, pasos_exactos(len(cadena)), cadena)
        self.assertLessEqual(r.pasos, (len(cadena) + 2) ** 2 + 1, cadena)
        return r


class CasosDelVideo(Salida):
    ESPERADO = {
        "aabab": ("babaa", 31),
        "abbbb": ("bbbba", 31),
        "aaabbb": ("bbbaaa", 38),
        "abbabaa": ("aababba", 49),
    }

    def test_entradas_del_yaml_cumplen_la_rubrica(self):
        self.assertEqual(MAQUINA.entradas, tuple(self.ESPERADO))
        for entrada in MAQUINA.entradas:
            self.assertGreaterEqual(len(entrada), 5)
            self.assertNotEqual(entrada, invertir(entrada))  # no son palíndromos

    def test_resultado_pasos_y_traza(self):
        for entrada, (salida, pasos) in self.ESPERADO.items():
            with self.subTest(entrada=entrada):
                r = self.assertInvierte(entrada)
                self.assertEqual("".join(r.final.simbolos), salida)
                self.assertEqual(r.pasos, pasos)
                verificar_traza(self, r)

    def test_marcadores_aparecen_durante_la_ejecucion_y_desaparecen_al_final(self):
        r = ejecutar(MAQUINA, "aabab")
        usados = {s for c in r.configuraciones for s in c.simbolos}
        self.assertLessEqual({"H", "X", "Y"}, usados)
        self.assertLessEqual(set(r.final.simbolos), {"a", "b"})


class ComparacionConOraculo(Salida):
    def test_exhaustivo_hasta_longitud_10(self):
        for cadena in todas_las_cadenas("ab", LONGITUD_EXHAUSTIVA):
            self.assertInvierte(cadena)

    def test_cadena_vacia_y_longitud_uno(self):
        self.assertEqual(self.assertInvierte("").pasos, 1)
        self.assertEqual(self.assertInvierte("b").final.simbolos, ("b",))

    def test_cadenas_largas_aleatorias(self):
        azar = random.Random(20252)  # semilla fija: resultado reproducible
        for _ in range(100):
            self.assertInvierte("".join(azar.choice("ab") for _ in range(azar.randint(11, 40))))

    def test_todas_las_transiciones_se_usan(self):
        usadas = set()
        for cadena in todas_las_cadenas("ab", 4):
            usadas |= {c.transicion.indice for c in ejecutar(MAQUINA, cadena).configuraciones[1:]}
        self.assertEqual(usadas, {t.indice for t in MAQUINA.transiciones.values()})


if __name__ == "__main__":
    unittest.main()
