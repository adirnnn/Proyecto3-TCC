"""Pruebas de la MT alteradora que suma dos binarios x+y."""

import random
import unittest

from simulador_mt import cargar_maquina
from simulador_mt.motor import Terminacion, ejecutar

from tests.oraculos import suma_binaria, todas_las_cadenas
from tests.test_motor import RAIZ, verificar_traza

MAQUINA = cargar_maquina(RAIZ / "maquinas" / "alteradora.yaml")
LONGITUD_EXHAUSTIVA = 9  # 29 524 cadenas sobre {0, 1, +}


def cota_de_pasos(n: int) -> int:
    # Cota del argumento de terminación del README (n = |x| + |y| + 1).
    return 2 * n * n + n


def pasos_exactos(x: str, y: str) -> int:
    """Fórmula del README: n + 3 + b(2b + 3) + 2J + w.

    J (lo que avanzan en total los acarreos) se calcula con aritmética de
    enteros, sin mirar la máquina: al sumar el bit k de y, si el bit k del
    valor acumulado también es 1, el acarreo avanza 1 + (unos consecutivos
    desde el bit k+1).
    """
    valor, total_acarreo = int(x, 2), 0
    for k, bit in enumerate(reversed(y)):
        if bit == "1":
            if (valor >> k) & 1:
                unos = 0
                while (valor >> (k + 1 + unos)) & 1:
                    unos += 1
                total_acarreo += 1 + unos
            valor += 1 << k
    n, b = len(x) + len(y) + 1, len(y)
    ancho = len(format(valor, "b").zfill(max(len(x), len(y))))
    return n + 3 + b * (2 * b + 3) + 2 * total_acarreo + ancho


class Definicion(unittest.TestCase):
    def test_carga_sin_advertencias(self):
        self.assertEqual(MAQUINA.formato, "escalar")
        self.assertEqual(MAQUINA.advertencias, ())
        self.assertEqual(len(MAQUINA.estados), 13)
        self.assertEqual(len(MAQUINA.transiciones), 43)


class Salida(unittest.TestCase):
    def assertSuma(self, cadena):
        """Cadena bien formada: la cinta final es exactamente la suma, sin
        '+', sin y ni marcadores, el resultado termina en la celda |x|-1 y el
        cabezal está sobre su primer símbolo, en qf."""
        r = ejecutar(MAQUINA, cadena)
        final = r.final
        esperado = suma_binaria(cadena)
        self.assertIsNotNone(esperado, cadena)
        self.assertIs(r.terminacion, Terminacion.ACEPTADA, cadena)
        # Cinta.contenido ya excluye los blancos de los extremos.
        self.assertEqual("".join(final.simbolos), esperado, cadena)
        self.assertEqual(final.inicio + len(final.simbolos) - 1, cadena.index("+") - 1, cadena)
        self.assertEqual((final.estado, final.cabezal), ("qf", final.inicio), cadena)
        self.assertEqual(r.pasos, pasos_exactos(*cadena.split("+")), cadena)
        self.assertLessEqual(r.pasos, cota_de_pasos(len(cadena)), cadena)
        return r

    def assertRechaza(self, cadena):
        """Cadena mal formada: se detiene sin aceptar en la fase de
        validación, sin haber cambiado la cinta."""
        r = ejecutar(MAQUINA, cadena)
        self.assertIsNone(suma_binaria(cadena), cadena)
        self.assertIs(r.terminacion, Terminacion.RECHAZADA, cadena)
        self.assertIn(r.final.estado, {"q0", "q1", "q2", "q3"}, cadena)
        self.assertEqual("".join(r.final.simbolos), cadena, cadena)
        self.assertLessEqual(r.pasos, len(cadena), cadena)  # una sola pasada
        return r


class CasosDelVideo(Salida):
    ESPERADO = {
        "1011+110": ("10001", 49),
        "111+1": ("1000", 23),
        "1+1111": ("10000", 66),
        "1001+1001": ("10010", 65),
    }

    def test_entradas_del_yaml_cumplen_la_rubrica(self):
        self.assertEqual(MAQUINA.entradas, tuple(self.ESPERADO))
        for entrada in MAQUINA.entradas:
            self.assertGreaterEqual(len(entrada), 5)

    def test_resultado_pasos_y_traza(self):
        for entrada, (salida, pasos) in self.ESPERADO.items():
            with self.subTest(entrada=entrada):
                r = self.assertSuma(entrada)
                self.assertEqual("".join(r.final.simbolos), salida)
                self.assertEqual(r.pasos, pasos)
                verificar_traza(self, r)

    def test_marcadores_aparecen_durante_la_ejecucion_y_desaparecen_al_final(self):
        r = ejecutar(MAQUINA, "1011+110")
        usados = {s for c in r.configuraciones for s in c.simbolos}
        self.assertLessEqual({"C", "U"}, usados)
        self.assertLessEqual(set(r.final.simbolos), {"0", "1"})

    def test_la_cinta_crece_hacia_la_izquierda(self):
        # x más corto que y (y acarreo final): el resultado empieza en
        # posiciones negativas.
        self.assertEqual(self.assertSuma("1+1111").final.inicio, -4)


class CasosParticulares(Salida):
    def test_operandos_cero_y_un_bit(self):
        for cadena, esperado in (("0+0", "0"), ("0+1", "1"), ("1+0", "1"), ("1+1", "10")):
            with self.subTest(cadena=cadena):
                self.assertEqual("".join(self.assertSuma(cadena).final.simbolos), esperado)

    def test_ceros_a_la_izquierda_conservan_el_ancho(self):
        for cadena, esperado in (("01+1", "10"), ("1+0010", "0011"), ("0001+0", "0001")):
            with self.subTest(cadena=cadena):
                self.assertEqual("".join(self.assertSuma(cadena).final.simbolos), esperado)

    def test_entradas_mal_formadas_se_rechazan(self):
        for cadena in ("", "+", "1", "11", "+1", "1+", "1++1", "1+1+1", "++"):
            with self.subTest(cadena=cadena):
                self.assertRechaza(cadena)


class ComparacionConOraculo(Salida):
    def test_exhaustivo_hasta_longitud_9(self):
        for cadena in todas_las_cadenas("01+", LONGITUD_EXHAUSTIVA):
            if suma_binaria(cadena) is None:
                self.assertRechaza(cadena)
            else:
                self.assertSuma(cadena)

    def test_sumas_largas_aleatorias(self):
        azar = random.Random(20253)  # semilla fija: resultado reproducible
        for _ in range(200):
            x, y = ("".join(azar.choice("01") for _ in range(azar.randint(1, 25))) for _ in range(2))
            self.assertSuma(f"{x}+{y}")

    def test_todas_las_transiciones_se_usan(self):
        usadas = set()
        for cadena in todas_las_cadenas("01+", 5):
            usadas |= {c.transicion.indice for c in ejecutar(MAQUINA, cadena).configuraciones[1:]}
        self.assertEqual(usadas, {t.indice for t in MAQUINA.transiciones.values()})


if __name__ == "__main__":
    unittest.main()
