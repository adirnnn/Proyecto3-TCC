"""Pruebas de la MT reconocedora de { ww : w ∈ {a,b}* } (Parte 3)."""

import random
import unittest

from simulador_mt import cargar_maquina
from simulador_mt.motor import Terminacion, ejecutar

from tests.oraculos import es_ww, todas_las_cadenas
from tests.test_motor import RAIZ, verificar_traza

MAQUINA = cargar_maquina(RAIZ / "maquinas" / "reconocedora.yaml")
LONGITUD_EXHAUSTIVA = 10  # 2 047 cadenas
TERMINA = (Terminacion.ACEPTADA, Terminacion.RECHAZADA)


def cota_de_pasos(n: int) -> int:
    # Cota del argumento de terminación del README: fase 1 ≤ (n+2)²,
    # fase 2 ≤ n/2 + 2, fase 3 ≤ n(n+2); en total menos de 2(n+2)².
    return 2 * (n + 2) ** 2


class Definicion(unittest.TestCase):
    def test_carga_sin_advertencias(self):
        self.assertEqual(MAQUINA.formato, "escalar")
        self.assertEqual(MAQUINA.advertencias, ())
        self.assertEqual(len(MAQUINA.estados), 10)
        self.assertEqual(len(MAQUINA.transiciones), 34)


class CasosDelVideo(unittest.TestCase):
    ESPERADO = {
        "abbabb": (Terminacion.ACEPTADA, 54),
        "bbabbbab": (Terminacion.ACEPTADA, 87),
        "aabab": (Terminacion.RECHAZADA, 20),
        "abaabb": (Terminacion.RECHAZADA, 49),
    }

    def test_entradas_del_yaml_cumplen_la_rubrica(self):
        self.assertEqual(MAQUINA.entradas, tuple(self.ESPERADO))
        aceptadas = [e for e in MAQUINA.entradas if es_ww(e)]
        rechazadas = [e for e in MAQUINA.entradas if not es_ww(e)]
        self.assertEqual((len(aceptadas), len(rechazadas)), (2, 2))
        for entrada in MAQUINA.entradas:
            self.assertGreaterEqual(len(entrada), 5)
            self.assertLessEqual(set(entrada), {"a", "b"})  # rechazos por estructura

    def test_resultados_pasos_y_traza(self):
        for entrada, (terminacion, pasos) in self.ESPERADO.items():
            with self.subTest(entrada=entrada):
                r = ejecutar(MAQUINA, entrada)
                self.assertIs(r.terminacion, terminacion)
                self.assertEqual(r.pasos, pasos)
                verificar_traza(self, r)

    def test_motivos_de_rechazo(self):
        # Longitud impar: en q2 no queda símbolo libre a la derecha.
        # El símbolo central (b) quedó marcado como Y.
        r = ejecutar(MAQUINA, "aabab")
        self.assertEqual((r.final.estado, r.final.leer(r.final.cabezal)), ("q2", "Y"))
        # aba ≠ abb: lleva a (q6) y encuentra V en la tercera comparación.
        r = ejecutar(MAQUINA, "abaabb")
        self.assertEqual((r.final.estado, r.final.leer(r.final.cabezal)), ("q6", "V"))
        self.assertEqual(r.final.simbolos, tuple("ZZZWWV"))


class ComparacionConOraculo(unittest.TestCase):
    def test_exhaustivo_hasta_longitud_10(self):
        for cadena in todas_las_cadenas("ab", LONGITUD_EXHAUSTIVA):
            r = ejecutar(MAQUINA, cadena)
            self.assertIn(r.terminacion, TERMINA, cadena)
            self.assertEqual(r.terminacion is Terminacion.ACEPTADA, es_ww(cadena), cadena)
            self.assertLessEqual(r.pasos, cota_de_pasos(len(cadena)), cadena)

    def test_cadenas_largas_aleatorias(self):
        azar = random.Random(20251)  # semilla fija: resultado reproducible
        for _ in range(200):
            w = "".join(azar.choice("ab") for _ in range(azar.randint(6, 20)))
            # Un cambio en una sola posición de la segunda mitad rompe ww.
            i = azar.randrange(len(w))
            cambiada = w[:i] + ("a" if w[i] == "b" else "b") + w[i + 1:]
            for cadena, esperado in ((w + w, True), (w + cambiada, False), (w + w[:-1], False)):
                r = ejecutar(MAQUINA, cadena)
                self.assertIs(r.terminacion,
                              Terminacion.ACEPTADA if esperado else Terminacion.RECHAZADA, cadena)


if __name__ == "__main__":
    unittest.main()
