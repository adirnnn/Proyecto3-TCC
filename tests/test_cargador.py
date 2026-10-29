"""Pruebas de carga y validación del YAML (Parte 1)."""

import tempfile
import textwrap
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from simulador_mt import (EntradaInvalida, ErrorConfiguracion, cargar_desde_texto,
                          cargar_maquina, problemas_de_entrada, tokenizar_entrada)

RAIZ = Path(__file__).resolve().parent.parent

# Máquina escalar mínima y válida; cada prueba de error altera un fragmento.
BASE = textwrap.dedent("""\
    mt:
      states: [q0, q1, qf]
      input_alphabet: [a, b]
      tape_alphabet: [a, b, X, B]
      initial_state: q0
      accept_states: [qf]
      transitions:
        - {state: q0, read: a, write: X, move: R, next: q1}
        - {state: q1, read: b, write: b, move: L, next: q0}
        - {state: q1, read: B, write: B, move: S, next: qf}
      inputs:
        - "ab"
        - ""
    """)


def variante(original: str, nuevo: str) -> str:
    assert original in BASE, original
    return BASE.replace(original, nuevo, 1)


class EjemploDelEnunciado(unittest.TestCase):
    def setUp(self):
        self.mt = cargar_maquina(RAIZ / "maquinas" / "ejemplo_enunciado.yaml")

    def test_formato_memoria_y_estados_compuestos(self):
        self.assertEqual(self.mt.formato, "memoria")
        self.assertEqual(self.mt.nombre, "ejemplo_enunciado")
        self.assertEqual(self.mt.estado_inicial, "[q0,B]")
        self.assertEqual(len(self.mt.estados), 4 * 5)  # Q × Γ
        self.assertTrue(self.mt.es_aceptacion("[qf,a]"))
        self.assertFalse(self.mt.es_aceptacion("[q1,a]"))

    def test_transiciones_coinciden_con_las_ecuaciones(self):
        t = self.mt.transicion("[q0,B]", "a")
        self.assertEqual(str(t), "δ([q0,B], a) = ([q1,a], B, R)")
        t = self.mt.transicion("[q0,B]", "b")
        self.assertEqual(str(t), "δ([q0,B], b) = ([q1,b], B, R)")
        self.assertEqual(len(self.mt.transiciones), 2)
        self.assertIsNone(self.mt.transicion("[q1,a]", "a"))

    def test_entradas(self):
        self.assertEqual(self.mt.entradas, ("aabb", "ab", "aaabbb"))
        self.assertEqual(self.mt.alfabeto_cinta, ("a", "b", "B", "X", "Y"))


class MaquinaEscalarValida(unittest.TestCase):
    def setUp(self):
        self.mt = cargar_desde_texto(BASE)

    def test_componentes(self):
        mt = self.mt
        self.assertEqual(mt.formato, "escalar")
        self.assertEqual(mt.estados, ("q0", "q1", "qf"))
        self.assertEqual(mt.blanco, "B")
        self.assertEqual(mt.estado_inicial, "q0")
        self.assertEqual(mt.estados_aceptacion, frozenset({"qf"}))
        self.assertEqual(mt.entradas, ("ab", ""))
        self.assertEqual(mt.advertencias, ())

    def test_transicion_conserva_todos_los_campos(self):
        t = self.mt.transicion("q1", "b")
        self.assertEqual((t.estado, t.lee, t.escribe, t.mueve, t.siguiente, t.indice),
                         ("q1", "b", "b", "L", "q0", 2))

    def test_es_inmutable(self):
        with self.assertRaises(TypeError):
            self.mt.transiciones[("q0", "b")] = self.mt.transicion("q0", "a")
        with self.assertRaises(FrozenInstanceError):
            self.mt.blanco = "_"
        with self.assertRaises(FrozenInstanceError):
            self.mt.transicion("q0", "a").escribe = "a"

    def test_blanco_personalizado(self):
        texto = variante("tape_alphabet: [a, b, X, B]", "tape_alphabet: [a, b, X, _]\n  blank: _")
        texto = texto.replace("read: B, write: B", "read: _, write: _")
        self.assertEqual(cargar_desde_texto(texto).blanco, "_")

    def test_escalares_se_leen_como_texto(self):
        texto = textwrap.dedent("""\
            mt:
              states: [yes, no]
              input_alphabet: [0, 1]
              tape_alphabet: [0, 1, ~]
              blank: ~
              initial_state: yes
              accept_states: [no]
              transitions:
                - {state: yes, read: 0, write: 1, move: R, next: no}
              inputs:
                - 010
                - 0110
            """)
        mt = cargar_desde_texto(texto)
        self.assertEqual(mt.estados, ("yes", "no"))
        self.assertEqual(mt.alfabeto_entrada, ("0", "1"))
        self.assertEqual(mt.blanco, "~")
        self.assertEqual(mt.entradas, ("010", "0110"))  # 010 no se convierte en 8

    def test_advertencia_por_transicion_desde_aceptacion(self):
        texto = variante("  inputs:", "    - {state: qf, read: a, write: a, move: R, next: q0}\n  inputs:")
        mt = cargar_desde_texto(texto)
        self.assertEqual(len(mt.advertencias), 1)
        self.assertIn("transición #4", mt.advertencias[0])


class ErroresDeConfiguracion(unittest.TestCase):
    def assertError(self, texto, *fragmentos):
        with self.assertRaises(ErrorConfiguracion) as ctx:
            cargar_desde_texto(texto)
        mensaje = str(ctx.exception)
        for fragmento in fragmentos:
            self.assertIn(fragmento, mensaje)
        return ctx.exception

    def test_yaml_mal_formado(self):
        self.assertError("mt: [a, b", "YAML mal formado")

    def test_sin_clave_mt(self):
        self.assertError("states: [q0]", "clave 'mt'")
        self.assertError("", "clave 'mt'")

    def test_clave_obligatoria_faltante(self):
        self.assertError(variante("  initial_state: q0\n", ""), "falta la clave obligatoria 'mt.initial_state'")

    def test_clave_desconocida_con_sugerencia(self):
        self.assertError(variante("accept_states:", "accept_state:"),
                         "clave desconocida 'mt.accept_state'", "¿quiso decir 'accept_states'?")

    def test_clave_yaml_duplicada(self):
        self.assertError(variante("{state: q0, read: a,", "{state: q0, read: a, read: b,"), "clave duplicada 'read'")

    def test_estados_repetidos_e_inicial_no_declarado(self):
        error = self.assertError(variante("states: [q0, q1, qf]", "states: [q0, q1, qf, q1]")
                                 .replace("initial_state: q0", "initial_state: q9"),
                                 "elementos repetidos ['q1']", "initial_state: 'q9' no está declarado")
        self.assertEqual(len(error.errores), 2)  # se informan todos, no solo el primero

    def test_estado_de_aceptacion_no_declarado(self):
        self.assertError(variante("accept_states: [qf]", "accept_states: [qz]"), "accept_states: 'qz'")

    def test_nombre_de_estado_reservado(self):
        self.assertError(variante("states: [q0, q1, qf]", "states: [q0, q1, qf, 'q 2']"), "no puede contener espacios")

    def test_alfabeto_de_entrada_no_incluido_en_cinta(self):
        self.assertError(variante("input_alphabet: [a, b]", "input_alphabet: [a, b, c]"), "faltan ['c']")

    def test_simbolo_de_varios_caracteres(self):
        self.assertError(variante("tape_alphabet: [a, b, X, B]", "tape_alphabet: [a, b, X1, B]"),
                         "'X1' debe tener exactamente un carácter")

    def test_simbolo_espacio_reservado(self):
        self.assertError(variante("tape_alphabet: [a, b, X, B]", "tape_alphabet: [a, b, X, B, ' ']"),
                         "no puede usarse como símbolo")

    def test_blanco_fuera_de_cinta_o_en_entrada(self):
        self.assertError(variante("tape_alphabet: [a, b, X, B]", "tape_alphabet: [a, b, X]"),
                         "el blanco 'B' debe pertenecer a tape_alphabet")
        self.assertError(variante("input_alphabet: [a, b]", "input_alphabet: [a, b, B]"),
                         "input_alphabet: no puede contener el blanco 'B'")

    def test_movimiento_invalido(self):
        self.assertError(variante("move: R, next: q1", "move: D, next: q1"), "'D' no es válido")

    def test_simbolos_de_transicion_fuera_de_cinta(self):
        self.assertError(variante("read: a, write: X", "read: c, write: Z"),
                         "transición #1.read: el símbolo 'c'", "transición #1.write: el símbolo 'Z'")

    def test_estados_de_transicion_no_declarados(self):
        self.assertError(variante("{state: q0, read: a, write: X, move: R, next: q1}",
                                  "{state: p, read: a, write: X, move: R, next: r}"),
                         "transición #1.state: el estado 'p'", "transición #1.next: el estado 'r'")

    def test_transicion_duplicada_no_se_sobrescribe(self):
        self.assertError(variante("  inputs:", "    - {state: q0, read: a, write: a, move: L, next: qf}\n  inputs:"),
                         "transición #4: no determinismo", "(estado=q0, lee=a)", "transición #1")

    def test_transicion_con_claves_faltantes_o_extra(self):
        self.assertError(variante("move: R, next: q1}", "next: q1}"), "faltan las claves ['move']")
        self.assertError(variante("move: R, next: q1}", "move: R, next: q1, tape: 2}"),
                         "claves desconocidas ['tape']")

    def test_lista_de_tamano_incorrecto(self):
        self.assertError(variante("read: a, write: X", "read: [a, B, X], write: [a, X]"),
                         "'read' debe ser [símbolo, memoria]")

    def test_read_y_write_de_tipos_distintos(self):
        self.assertError(variante("read: a, write: X", "read: [a, B], write: X"),
                         "ambos símbolos o ambos listas")

    def test_formatos_mezclados(self):
        self.assertError(variante("read: a, write: X", "read: [a, B], write: [B, X]"),
                         "no se pueden mezclar formatos")

    def test_memoria_duplicada(self):
        texto = textwrap.dedent("""\
            mt:
              states: [q0, q1]
              input_alphabet: [a]
              tape_alphabet: [a, B]
              initial_state: q0
              accept_states: [q1]
              transitions:
                - {state: q0, read: [a, B], write: [a, B], move: R, next: q1}
                - {state: q0, read: [a, B], write: [B, a], move: L, next: q0}
              inputs: [a]
            """)
        self.assertError(texto, "(estado=q0, memoria=B, lee=a)", "transición #1")

    def test_inputs_mal_formados(self):
        self.assertError(variante('    - "ab"\n    - ""\n', "    - {x: 1}\n"), "inputs[0]: se esperaba una cadena")
        self.assertError(variante('  inputs:\n    - "ab"\n    - ""\n', "  inputs: ab\n"), "inputs: se esperaba una lista")

    def test_valor_vacio_sin_comillas_no_es_cadena_vacia(self):
        self.assertError(variante('    - ""\n', "    -\n"), 'inputs[1]: se esperaba una cadena', 'escriba ""')
        self.assertError(variante("tape_alphabet: [a, b, X, B]", "tape_alphabet: [a, b, X, B]\n  blank:"),
                         "blank: se esperaba un texto no vacío, se obtuvo nada")

    def test_etiquetas_explicitas_y_objetos_python(self):
        self.assertError(variante("input_alphabet: [a, b]", "input_alphabet: [a, !!int 1]"),
                         "input_alphabet[1]: se esperaba un texto no vacío, se obtuvo int 1")
        self.assertError("mt: !!python/object:os.system {}", "YAML mal formado")

    def test_archivo_inexistente(self):
        with self.assertRaises(ErrorConfiguracion) as ctx:
            cargar_maquina(RAIZ / "maquinas" / "no_existe.yaml")
        self.assertIn("el archivo no existe", str(ctx.exception))

    def test_archivo_no_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "latin1.yaml"
            ruta.write_bytes("mt: {states: [qñ]}".encode("latin-1"))
            with self.assertRaises(ErrorConfiguracion) as ctx:
                cargar_maquina(ruta)
        self.assertIn("UTF-8", str(ctx.exception))


class ValidacionDeEntradas(unittest.TestCase):
    def setUp(self):
        self.mt = cargar_desde_texto(BASE)

    def test_cadena_valida_y_vacia(self):
        self.assertEqual(tokenizar_entrada(self.mt, "abba"), ("a", "b", "b", "a"))
        self.assertEqual(tokenizar_entrada(self.mt, ""), ())

    def test_espacio_mayuscula_y_simbolo_de_cinta_son_invalidos(self):
        for cadena, malo, posicion in (("ab a", "' '", 2), ("aA", "'A'", 1),
                                       ("aX", "'X'", 1), ("aB", "'B'", 1)):
            with self.subTest(cadena=cadena):
                problemas = problemas_de_entrada(self.mt, cadena)
                self.assertEqual(len(problemas), 1)
                self.assertIn(f"símbolo {malo} en la posición {posicion}", problemas[0])
                with self.assertRaises(EntradaInvalida):
                    tokenizar_entrada(self.mt, cadena)

    def test_no_se_recortan_espacios(self):
        self.assertEqual(len(problemas_de_entrada(self.mt, " ab ")), 2)


if __name__ == "__main__":
    unittest.main()
