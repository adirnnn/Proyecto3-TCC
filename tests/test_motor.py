"""Pruebas de la cinta y del motor de ejecución (Parte 2)."""

import textwrap
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from simulador_mt import cargar_desde_texto, cargar_maquina
from simulador_mt.cinta import Cinta
from simulador_mt.motor import DESPLAZAMIENTO, Terminacion, ejecutar

RAIZ = Path(__file__).resolve().parent.parent


def maquina(transiciones: str, aceptacion: str = "qf", inicial: str = "q0"):
    return cargar_desde_texto(textwrap.dedent(f"""\
        mt:
          states: [q0, q1, q2, qf]
          input_alphabet: [a, b]
          tape_alphabet: [a, b, X, Y, Z, B]
          initial_state: {inicial}
          accept_states: [{aceptacion}]
          transitions:
        """) + textwrap.indent(textwrap.dedent(transiciones), "    ") + "  inputs: []\n")


# Recorre a la derecha cambiando a por X; acepta en el primer blanco. No
# tiene regla para b, así que rechaza cualquier cadena con b.
DERECHA = maquina("""\
    - {state: q0, read: a, write: X, move: R, next: q0}
    - {state: q0, read: B, write: B, move: S, next: qf}
    """)

# Escribe Y y Z a la izquierda de la entrada (posiciones -1 y -2).
IZQUIERDA = maquina("""\
    - {state: q0, read: a, write: a, move: L, next: q1}
    - {state: q1, read: B, write: Y, move: L, next: q2}
    - {state: q2, read: B, write: Z, move: S, next: qf}
    """)

# Nunca se detiene sobre blancos: avanza a la derecha para siempre.
BUCLE = maquina("""\
    - {state: q0, read: a, write: a, move: R, next: q0}
    - {state: q0, read: B, write: B, move: R, next: q0}
    """)


def verificar_traza(prueba: unittest.TestCase, resultado):
    """Reproduce cada paso desde la configuración anterior y la regla
    registrada; comprueba que la traza no omite ni inventa cambios."""
    configs = resultado.configuraciones
    prueba.assertEqual([c.paso for c in configs], list(range(len(configs))))
    for previa, actual in zip(configs, configs[1:]):
        t = actual.transicion
        prueba.assertEqual(previa.estado, t.estado)
        prueba.assertEqual(previa.leer(previa.cabezal), t.lee)
        prueba.assertEqual(actual.estado, t.siguiente)
        prueba.assertEqual(actual.cabezal, previa.cabezal + DESPLAZAMIENTO[t.mueve])
        celdas = set(previa.ventana()) | set(actual.ventana())
        for p in celdas:
            esperado = t.escribe if p == previa.cabezal else previa.leer(p)
            prueba.assertEqual(actual.leer(p), esperado, f"celda {p} en el paso {actual.paso}")


class PruebasCinta(unittest.TestCase):
    def test_celda_no_escrita_es_blanco_en_ambos_sentidos(self):
        cinta = Cinta("B", "ab")
        self.assertEqual([cinta.leer(p) for p in (-5, -1, 0, 1, 2, 100)], ["B", "B", "a", "b", "B", "B"])

    def test_crece_a_ambos_lados(self):
        cinta = Cinta("B", "a")
        cinta.escribir(-3, "X")
        cinta.escribir(2, "Y")
        self.assertEqual(cinta.contenido(), (-3, ("X", "B", "B", "a", "B", "Y")))

    def test_escribir_blanco_borra_y_conserva_blancos_interiores(self):
        cinta = Cinta("B", "abc")
        cinta.escribir(1, "B")
        self.assertEqual(cinta.contenido(), (0, ("a", "B", "c")))
        cinta.escribir(0, "B")
        cinta.escribir(2, "B")
        self.assertEqual(cinta.contenido(), (0, ()))

    def test_entrada_que_contiene_el_blanco_no_ocupa_celdas(self):
        self.assertEqual(Cinta("B", "").contenido(), (0, ()))


class PruebasMotor(unittest.TestCase):
    def test_paso_conocido_configuracion_exacta(self):
        r = ejecutar(DERECHA, "aa")
        c = r.configuraciones[1]
        self.assertEqual((c.paso, c.estado, c.cabezal, c.inicio, c.simbolos),
                         (1, "q0", 1, 0, ("X", "a")))
        self.assertEqual(c.transicion.indice, 1)

    def test_aceptacion(self):
        r = ejecutar(DERECHA, "aaaaa")
        self.assertIs(r.terminacion, Terminacion.ACEPTADA)
        self.assertEqual(r.pasos, 6)
        self.assertEqual(r.final.simbolos, tuple("XXXXX"))
        self.assertEqual((r.final.estado, r.final.cabezal), ("qf", 5))
        self.assertIn("estado de aceptación qf", r.motivo)
        verificar_traza(self, r)

    def test_rechazo_por_transicion_inexistente(self):
        r = ejecutar(DERECHA, "aab")
        self.assertIs(r.terminacion, Terminacion.RECHAZADA)
        self.assertEqual(r.pasos, 2)
        self.assertIn("δ(q0, b)", r.motivo)
        verificar_traza(self, r)

    def test_movimiento_izquierda_y_posiciones_negativas(self):
        r = ejecutar(IZQUIERDA, "a")
        self.assertIs(r.terminacion, Terminacion.ACEPTADA)
        self.assertEqual((r.final.inicio, r.final.simbolos, r.final.cabezal), (-2, ("Z", "Y", "a"), -2))
        verificar_traza(self, r)

    def test_movimiento_quedarse(self):
        r = ejecutar(DERECHA, "a")
        self.assertEqual(r.configuraciones[-1].cabezal, r.configuraciones[-2].cabezal)

    def test_entrada_vacia(self):
        r = ejecutar(DERECHA, "")
        self.assertIs(r.terminacion, Terminacion.ACEPTADA)
        inicial = r.configuraciones[0]
        self.assertEqual((inicial.simbolos, inicial.cabezal, inicial.leer(0)), ((), 0, "B"))
        self.assertEqual(r.pasos, 1)

    def test_estado_inicial_de_aceptacion_acepta_sin_pasos(self):
        r = ejecutar(maquina("- {state: q1, read: a, write: a, move: R, next: q1}\n", aceptacion="q0"), "ab")
        self.assertIs(r.terminacion, Terminacion.ACEPTADA)
        self.assertEqual(r.pasos, 0)

    def test_limite_alcanzado_no_es_rechazo(self):
        r = ejecutar(BUCLE, "aa", max_pasos=50)
        self.assertIs(r.terminacion, Terminacion.LIMITE)
        self.assertEqual(r.pasos, 50)
        self.assertEqual(len(r.configuraciones), 51)  # no se pierden pasos
        self.assertIn("no se sabe", r.motivo)
        verificar_traza(self, r)

    def test_frontera_del_limite(self):
        # "aa" necesita exactamente 3 pasos.
        self.assertIs(ejecutar(DERECHA, "aa", max_pasos=3).terminacion, Terminacion.ACEPTADA)
        self.assertIs(ejecutar(DERECHA, "aa", max_pasos=2).terminacion, Terminacion.LIMITE)
        self.assertIs(ejecutar(DERECHA, "aab", max_pasos=2).terminacion, Terminacion.RECHAZADA)
        self.assertIs(ejecutar(DERECHA, "", max_pasos=0).terminacion, Terminacion.LIMITE)
        with self.assertRaises(ValueError):
            ejecutar(DERECHA, "a", max_pasos=-1)

    def test_entrada_invalida_no_se_ejecuta(self):
        for cadena in ("ac", "a a", "A", "aX", "aB"):
            with self.subTest(cadena=cadena):
                r = ejecutar(DERECHA, cadena)
                self.assertIs(r.terminacion, Terminacion.INVALIDA)
                self.assertEqual((r.configuraciones, r.pasos, r.final), ((), 0, None))

    def test_configuraciones_son_instantaneas_inmutables(self):
        r = ejecutar(DERECHA, "aa")
        self.assertEqual(r.configuraciones[0].simbolos, ("a", "a"))  # no refleja las X posteriores
        self.assertEqual(r.configuraciones[1].simbolos, ("X", "a"))
        with self.assertRaises(FrozenInstanceError):
            r.configuraciones[0].estado = "qf"
        self.assertIsInstance(r.configuraciones, tuple)

    def test_ejecuciones_aisladas(self):
        primera = ejecutar(DERECHA, "aaa")
        segunda = ejecutar(DERECHA, "a")
        self.assertEqual(segunda.configuraciones[0].simbolos, ("a",))
        self.assertEqual(segunda.final.simbolos, ("X",))
        self.assertEqual(primera, ejecutar(DERECHA, "aaa"))  # repetir da lo mismo

    def test_ejemplo_del_enunciado(self):
        mt = cargar_maquina(RAIZ / "maquinas" / "ejemplo_enunciado.yaml")
        for entrada in mt.entradas:
            r = ejecutar(mt, entrada)
            # Solo comprueba el parsing: sin transiciones hacia qf, rechaza.
            self.assertIs(r.terminacion, Terminacion.RECHAZADA)
            self.assertEqual(r.pasos, 1)
            self.assertEqual(r.final.estado, "[q1,a]")
            self.assertEqual(r.final.leer(0), "B")
            verificar_traza(self, r)


if __name__ == "__main__":
    unittest.main()
