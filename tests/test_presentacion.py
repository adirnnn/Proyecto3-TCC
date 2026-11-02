"""Pruebas del formato de IDs, la salida y la CLI (Parte 2)."""

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from simulador_mt.__main__ import main
from simulador_mt.motor import Configuracion, ejecutar
from simulador_mt.presentacion import (formatear_cinta, formatear_ejecucion, formatear_id,
                                       formatear_resumen)

from tests.test_motor import BUCLE, DERECHA, IZQUIERDA, RAIZ

EJEMPLO = str(RAIZ / "maquinas" / "ejemplo_enunciado.yaml")


def config(cabezal, simbolos="abc", inicio=0, estado="q"):
    return Configuracion(0, estado, cabezal, inicio, tuple(simbolos), "B")


def correr(*argv):
    salida, errores = io.StringIO(), io.StringIO()
    with redirect_stdout(salida), redirect_stderr(errores):
        codigo = main(list(argv))
    return codigo, salida.getvalue(), errores.getvalue()


class PruebasID(unittest.TestCase):
    def test_estado_antes_del_simbolo_leido(self):
        self.assertEqual(formatear_id(config(0)), "[q]abc")
        self.assertEqual(formatear_id(config(2)), "ab[q]c")

    def test_cabezal_fuera_del_contenido_muestra_blancos(self):
        self.assertEqual(formatear_id(config(4)), "abcB[q]B")
        self.assertEqual(formatear_id(config(-2)), "[q]BBabc")
        self.assertEqual(formatear_id(config(0, "")), "[q]B")

    def test_blanco_interior_visible(self):
        self.assertEqual(formatear_id(config(1, "aBb")), "a[q]Bb")

    def test_estado_compuesto_no_se_duplica_corchete(self):
        self.assertEqual(formatear_id(config(1, "abb", 1, "[q1,a]")), "[q1,a]abb")

    def test_vista_de_cinta_alinea_el_cabezal(self):
        for cabezal in (-2, 0, 3, 11):
            with self.subTest(cabezal=cabezal):
                c = config(cabezal, "abXYZbaabab", inicio=-1)
                posiciones, cinta, flecha = formatear_cinta(c, sangria="")
                columna = flecha.index("^")
                self.assertEqual(cinta[columna], c.leer(cabezal))
                self.assertEqual(posiciones[columna], str(cabezal)[-1])


class PruebasSalida(unittest.TestCase):
    def test_traza_tiene_una_id_por_configuracion(self):
        r = ejecutar(IZQUIERDA, "a")
        texto = formatear_ejecucion(IZQUIERDA, r, 1, 1)
        for c in r.configuraciones:
            self.assertIn(formatear_id(c), texto)
        self.assertEqual(texto.count(" ⊢ "), r.pasos)
        self.assertIn("ID final: [qf]ZYa", texto)
        self.assertIn("Resultado: ACEPTADA", texto)
        self.assertIn("Pasos: 3", texto)

    def test_traza_larga_no_se_trunca(self):
        r = ejecutar(BUCLE, "a", max_pasos=500)
        texto = formatear_ejecucion(BUCLE, r, 1, 1)
        self.assertEqual(texto.count(" ⊢ "), 500)
        self.assertIn("LÍMITE ALCANZADO / resultado no determinado", texto)

    def test_contenido_final_avisa_simbolos_ajenos_a_sigma(self):
        texto = formatear_ejecucion(DERECHA, ejecutar(DERECHA, "aaaaa"), 1, 1)
        self.assertIn('Contenido no blanco de la cinta: "XXXXX" (celdas 0..4)', texto)
        self.assertIn("símbolos que no son de Σ: X", texto)
        limpio = formatear_ejecucion(BUCLE, ejecutar(BUCLE, "a", max_pasos=3), 1, 1)
        self.assertNotIn("Aviso", limpio)

    def test_entrada_invalida(self):
        texto = formatear_ejecucion(DERECHA, ejecutar(DERECHA, "a c"), 2, 3)
        self.assertIn("Entrada 2/3", texto)
        self.assertIn("ENTRADA INVÁLIDA", texto)
        self.assertIn("símbolo ' ' en la posición 1", texto)
        self.assertIn("La máquina no se ejecutó", texto)

    def test_resumen_distingue_entrada_invalida(self):
        texto = formatear_resumen([ejecutar(DERECHA, "ac"), ejecutar(DERECHA, "aa")])
        self.assertIn('"ac"  ENTRADA INVÁLIDA  (no se ejecutó)', texto)
        self.assertIn('"aa"  ACEPTADA   pasos=3  cinta: "XX"', texto)


class PruebasCLI(unittest.TestCase):
    def test_ejecuta_todas_las_entradas_del_yaml(self):
        codigo, salida, errores = correr(EJEMPLO)
        self.assertEqual((codigo, errores), (0, ""))
        self.assertIn("δ([q0,B], a) = ([q1,a], B, R)", salida)
        for n, entrada in enumerate(("aabb", "ab", "aaabbb"), start=1):
            self.assertIn(f'Entrada {n}/3: "{entrada}"', salida)
        self.assertEqual(salida.count("Resultado: RECHAZADA"), 3)
        self.assertIn("Resumen", salida)

    def test_salida_a_archivo_completa_y_modo_resumen(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "trazas" / "ejemplo.txt"
            codigo, salida, _ = correr(EJEMPLO, "--salida", str(ruta), "--resumen")
            archivo = ruta.read_text(encoding="utf-8")
        self.assertEqual(codigo, 0)
        self.assertNotIn("Descripciones instantáneas", salida)
        self.assertIn("traza omitida en pantalla; pasos: 1", salida)
        self.assertEqual(archivo.count("Descripciones instantáneas"), 3)
        self.assertIn("[q1,a]aabbb", archivo)

    def test_archivo_igual_a_la_pantalla_sin_resumen(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "t.txt"
            _, salida, _ = correr(EJEMPLO, "--salida", str(ruta))
            archivo = ruta.read_text(encoding="utf-8")
        self.assertTrue(salida.startswith(archivo.rstrip("\n")))

    def test_configuracion_invalida_devuelve_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "mala.yaml"
            ruta.write_text("mt: {states: [q0]}", encoding="utf-8")
            codigo, salida, errores = correr(str(ruta))
        self.assertEqual((codigo, salida), (1, ""))
        self.assertIn("falta la clave obligatoria 'mt.initial_state'", errores)

    def test_max_pasos_invalido(self):
        for valor in ("-1", "diez"):
            with self.subTest(valor=valor), self.assertRaises(SystemExit) as ctx:
                correr(EJEMPLO, "--max-pasos", valor)
            self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
