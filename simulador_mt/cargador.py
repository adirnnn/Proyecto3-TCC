"""Carga segura del YAML y validación de la Máquina de Turing.

Se aceptan dos formatos de transición (no se pueden mezclar en un archivo):

* escalar:  read: a        write: X        → δ(q, a) = (p, X, M)
* memoria:  read: [a, m]   write: [m', X]  → δ([q,m], a) = ([p,m'], X, M)

El formato de memoria es la interpretación adoptada para el ejemplo del
enunciado, el único que concuerda con sus ecuaciones δ([q0,B], a) =
([q1,a], B, R): el segundo elemento de `read` es la memoria guardada en el
estado y el primero de `write` es la memoria nueva. Sigue siendo una sola
cinta; la memoria vive en el control finito, así que se traduce a estados
compuestos [q,m] y el motor no necesita saber nada de ella.
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from types import MappingProxyType
from typing import Any, Optional, Union

import yaml

from .modelo import MOVIMIENTOS, MaquinaTuring, Transicion

BLANCO_POR_DEFECTO = "B"
CLAVES_OBLIGATORIAS = ("states", "input_alphabet", "tape_alphabet",
                       "initial_state", "accept_states", "transitions", "inputs")
CLAVES_OPCIONALES = ("blank",)
CLAVES_TRANSICION = ("state", "read", "write", "move", "next")
# Reservados porque la notación de las IDs y de los estados compuestos los usa.
CARACTERES_RESERVADOS = "[],"


class ErrorConfiguracion(Exception):
    """El archivo no describe una MT válida. Reúne todos los errores hallados."""

    def __init__(self, errores: list[str], origen: str = "<texto>"):
        self.errores = list(errores)
        self.origen = origen
        super().__init__(str(self))

    def __str__(self) -> str:
        lineas = "\n".join(f"  - {e}" for e in self.errores)
        return f"Configuración inválida en {self.origen}:\n{lineas}"


class _CargadorTexto(yaml.SafeLoader):
    """SafeLoader en el que todo escalar se lee como texto.

    YAML 1.1 convierte `0` y `1` en enteros, `010` en 8, `yes`/`no` en
    booleanos y `~` en null; eso alteraría símbolos y cadenas sin avisar.
    Al quitar la resolución implícita de tipos, `[0, 1]` sigue siendo
    ['0', '1'] y `- 010` sigue siendo '010'.
    """


_CargadorTexto.yaml_implicit_resolvers = {}
# Excepción deliberada: un valor vacío sin comillas (`-` o `blank:`) es
# "nada", no la cadena vacía, para que un olvido no se convierta en "" en
# silencio. La cadena vacía se escribe explícitamente como "".
_CargadorTexto.add_implicit_resolver("tag:yaml.org,2002:null", re.compile(r"^$"), [""])


def _construir_mapeo_sin_duplicados(cargador, nodo):
    # PyYAML sobrescribe en silencio una clave repetida (p. ej. dos `read:`
    # en la misma transición); aquí se convierte en un error con su línea.
    resultado = {}
    for nodo_clave, nodo_valor in nodo.value:
        clave = cargador.construct_object(nodo_clave, deep=True)
        if not isinstance(clave, str):
            raise yaml.constructor.ConstructorError(
                None, None, f"clave no textual {clave!r}", nodo_clave.start_mark)
        if clave in resultado:
            raise yaml.constructor.ConstructorError(
                None, None, f"clave duplicada {clave!r}", nodo_clave.start_mark)
        resultado[clave] = cargador.construct_object(nodo_valor, deep=True)
    return resultado


_CargadorTexto.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                               _construir_mapeo_sin_duplicados)


def cargar_maquina(ruta: Union[str, Path]) -> MaquinaTuring:
    ruta = Path(ruta)
    try:
        texto = ruta.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ErrorConfiguracion(["el archivo no existe"], str(ruta)) from None
    except UnicodeDecodeError:
        raise ErrorConfiguracion(["el archivo no está codificado en UTF-8"], str(ruta)) from None
    except OSError as exc:
        raise ErrorConfiguracion([f"no se pudo leer el archivo: {exc.strerror}"], str(ruta)) from None
    return cargar_desde_texto(texto, origen=str(ruta), nombre=ruta.stem)


def cargar_desde_texto(texto: str, origen: str = "<texto>", nombre: str = "mt") -> MaquinaTuring:
    try:
        datos = yaml.load(texto, Loader=_CargadorTexto)
    except yaml.YAMLError as exc:
        raise ErrorConfiguracion([f"YAML mal formado: {exc}"], origen) from None
    return _Validador(origen, nombre).construir(datos)


class _Validador:
    def __init__(self, origen: str, nombre: str):
        self.origen = origen
        self.nombre = nombre
        self.errores: list[str] = []
        self.advertencias: list[str] = []

    def _fallar_si_hay_errores(self) -> None:
        if self.errores:
            raise ErrorConfiguracion(self.errores, self.origen)

    # ---- utilidades de tipo ---------------------------------------------

    def _texto(self, valor: Any, donde: str) -> Optional[str]:
        if not isinstance(valor, str) or valor == "":
            self.errores.append(f"{donde}: se esperaba un texto no vacío, se obtuvo {_describir(valor)}")
            return None
        return valor

    def _lista_textos(self, valor: Any, donde: str) -> Optional[list[str]]:
        if not isinstance(valor, list):
            self.errores.append(f"{donde}: se esperaba una lista, se obtuvo {_describir(valor)}")
            return None
        elementos = [self._texto(v, f"{donde}[{i}]") for i, v in enumerate(valor)]
        if any(e is None for e in elementos):
            return None
        repetidos = sorted({e for e in elementos if elementos.count(e) > 1})
        if repetidos:
            self.errores.append(f"{donde}: elementos repetidos {repetidos}")
        return elementos

    def _simbolo(self, valor: str, donde: str) -> bool:
        if len(valor) != 1:
            self.errores.append(f"{donde}: el símbolo {valor!r} debe tener exactamente un carácter")
            return False
        if valor.isspace() or valor in CARACTERES_RESERVADOS:
            self.errores.append(f"{donde}: {valor!r} no puede usarse como símbolo "
                                f"(espacios y {CARACTERES_RESERVADOS!r} están reservados)")
            return False
        return True

    def _nombre_estado(self, valor: str, donde: str) -> None:
        if any(c.isspace() or c in CARACTERES_RESERVADOS for c in valor):
            self.errores.append(f"{donde}: el estado {valor!r} no puede contener espacios "
                                f"ni los caracteres {CARACTERES_RESERVADOS!r}")

    # ---- estructura general ---------------------------------------------

    def construir(self, datos: Any) -> MaquinaTuring:
        if not isinstance(datos, dict) or "mt" not in datos:
            raise ErrorConfiguracion(["la raíz del archivo debe ser un mapeo con la clave 'mt'"], self.origen)
        sobrantes = [k for k in datos if k != "mt"]
        if sobrantes:
            self.errores.append(f"claves raíz desconocidas {sobrantes}; todo va dentro de 'mt'")
        mt = datos["mt"]
        if not isinstance(mt, dict):
            raise ErrorConfiguracion([f"'mt' debe ser un mapeo, se obtuvo {_describir(mt)}"], self.origen)

        for clave in CLAVES_OBLIGATORIAS:
            if clave not in mt:
                self.errores.append(f"falta la clave obligatoria 'mt.{clave}'")
        validas = CLAVES_OBLIGATORIAS + CLAVES_OPCIONALES
        for clave in mt:
            if clave not in validas:
                parecida = difflib.get_close_matches(clave, validas, n=1)
                pista = f" (¿quiso decir '{parecida[0]}'?)" if parecida else ""
                self.errores.append(f"clave desconocida 'mt.{clave}'{pista}")
        self._fallar_si_hay_errores()

        estados, entrada, cinta, blanco, inicial, aceptacion = self._componentes(mt)
        self._fallar_si_hay_errores()

        transiciones, formato = self._transiciones(mt["transitions"], estados, cinta, aceptacion)
        entradas = self._entradas(mt["inputs"])
        self._fallar_si_hay_errores()

        if formato == "memoria":
            # Q' = Q × Γ; la memoria inicial es el blanco, como en [q0,B].
            estados = [_compuesto(q, m) for q in estados for m in cinta]
            inicial = _compuesto(inicial, blanco)
            aceptacion = [_compuesto(q, m) for q in aceptacion for m in cinta]

        return MaquinaTuring(
            nombre=self.nombre,
            estados=tuple(estados),
            alfabeto_entrada=tuple(entrada),
            alfabeto_cinta=tuple(cinta),
            blanco=blanco,
            estado_inicial=inicial,
            estados_aceptacion=frozenset(aceptacion),
            transiciones=MappingProxyType(transiciones),
            entradas=tuple(entradas),
            formato=formato,
            advertencias=tuple(self.advertencias),
        )

    def _componentes(self, mt: dict):
        estados = self._lista_textos(mt["states"], "states") or []
        if not estados and isinstance(mt["states"], list):
            self.errores.append("states: debe declarar al menos un estado")
        for i, q in enumerate(estados):
            self._nombre_estado(q, f"states[{i}]")

        entrada = self._lista_textos(mt["input_alphabet"], "input_alphabet") or []
        cinta = self._lista_textos(mt["tape_alphabet"], "tape_alphabet") or []
        for nombre, alfabeto in (("input_alphabet", entrada), ("tape_alphabet", cinta)):
            for i, s in enumerate(alfabeto):
                self._simbolo(s, f"{nombre}[{i}]")

        blanco = self._texto(mt.get("blank", BLANCO_POR_DEFECTO), "blank")
        if blanco is not None and self._simbolo(blanco, "blank"):
            if cinta and blanco not in cinta:
                self.errores.append(f"blank: el blanco {blanco!r} debe pertenecer a tape_alphabet")
            if blanco in entrada:
                self.errores.append(f"input_alphabet: no puede contener el blanco {blanco!r}")

        faltantes = [s for s in entrada if s not in cinta]
        if cinta and faltantes:
            self.errores.append(f"tape_alphabet debe contener a input_alphabet; faltan {faltantes}")

        inicial = self._texto(mt["initial_state"], "initial_state")
        if inicial is not None and estados and inicial not in estados:
            self.errores.append(f"initial_state: {inicial!r} no está declarado en states")

        aceptacion = self._lista_textos(mt["accept_states"], "accept_states") or []
        for q in aceptacion:
            if estados and q not in estados:
                self.errores.append(f"accept_states: {q!r} no está declarado en states")
        if isinstance(mt["accept_states"], list) and not mt["accept_states"]:
            self.advertencias.append("accept_states está vacío: ninguna cadena podrá ser aceptada")

        return estados, entrada, cinta, blanco, inicial, aceptacion

    # ---- transiciones ---------------------------------------------------

    def _transiciones(self, valor: Any, estados: list[str], cinta: list[str], aceptacion: list[str]):
        if not isinstance(valor, list):
            self.errores.append(f"transitions: se esperaba una lista, se obtuvo {_describir(valor)}")
            return {}, "escalar"
        if not valor:
            self.advertencias.append("transitions está vacío: la máquina se detiene en el primer paso")

        transiciones: dict[tuple[str, str], Transicion] = {}
        definida_en: dict[tuple, int] = {}
        formatos: dict[str, int] = {}

        for i, t in enumerate(valor, start=1):
            donde = f"transición #{i}"
            if not isinstance(t, dict):
                self.errores.append(f"{donde}: se esperaba un mapeo, se obtuvo {_describir(t)}")
                continue
            faltan = [c for c in CLAVES_TRANSICION if c not in t]
            sobran = [c for c in t if c not in CLAVES_TRANSICION]
            if faltan:
                self.errores.append(f"{donde}: faltan las claves {faltan}")
            if sobran:
                self.errores.append(f"{donde}: claves desconocidas {sobran} "
                                    f"(se admiten {list(CLAVES_TRANSICION)})")
            if faltan or sobran:
                continue

            formato = self._formato(t["read"], t["write"], donde)
            if formato is None:
                continue
            formatos.setdefault(formato, i)

            n_errores = len(self.errores)
            estado = self._referencia_estado(t["state"], estados, f"{donde}.state")
            siguiente = self._referencia_estado(t["next"], estados, f"{donde}.next")
            mueve = self._texto(t["move"], f"{donde}.move")
            if mueve is not None and mueve not in MOVIMIENTOS:
                self.errores.append(f"{donde}.move: {mueve!r} no es válido; use uno de {list(MOVIMIENTOS)}")
            if formato == "escalar":
                lee = self._simbolo_cinta(t["read"], cinta, f"{donde}.read")
                escribe = self._simbolo_cinta(t["write"], cinta, f"{donde}.write")
                mem, mem_nueva = None, None
            else:
                lee = self._simbolo_cinta(t["read"][0], cinta, f"{donde}.read[0] (símbolo leído)")
                mem = self._simbolo_cinta(t["read"][1], cinta, f"{donde}.read[1] (memoria)")
                mem_nueva = self._simbolo_cinta(t["write"][0], cinta, f"{donde}.write[0] (memoria nueva)")
                escribe = self._simbolo_cinta(t["write"][1], cinta, f"{donde}.write[1] (símbolo escrito)")
            if len(self.errores) > n_errores:
                continue

            # Determinismo: una segunda regla para la misma situación es un
            # error, aunque sea idéntica; nunca se sobrescribe en silencio.
            if formato == "escalar":
                situacion = (estado, lee)
                origen, destino = estado, siguiente
                texto_situacion = f"(estado={estado}, lee={lee})"
            else:
                situacion = (estado, mem, lee)
                origen, destino = _compuesto(estado, mem), _compuesto(siguiente, mem_nueva)
                texto_situacion = f"(estado={estado}, memoria={mem}, lee={lee})"
            if situacion in definida_en:
                self.errores.append(f"{donde}: no determinismo, la situación {texto_situacion} "
                                    f"ya está definida en la transición #{definida_en[situacion]}")
                continue
            definida_en[situacion] = i

            if estado in aceptacion:
                self.advertencias.append(f"{donde}: sale del estado de aceptación {estado!r}; "
                                         f"nunca se ejecuta porque la máquina se detiene al aceptar")
            transiciones[(origen, lee)] = Transicion(origen, lee, escribe, mueve, destino, i)

        if len(formatos) > 1:
            self.errores.append(
                "no se pueden mezclar formatos de transición: la #{} es escalar y la #{} usa "
                "listas [símbolo, memoria]".format(formatos["escalar"], formatos["memoria"]))
        return transiciones, next(iter(formatos), "escalar")

    def _formato(self, read: Any, write: Any, donde: str) -> Optional[str]:
        if isinstance(read, str) and isinstance(write, str):
            return "escalar"
        if isinstance(read, list) and isinstance(write, list):
            if len(read) == 2 and len(write) == 2:
                return "memoria"
            self.errores.append(f"{donde}: en el formato con memoria 'read' debe ser "
                                f"[símbolo, memoria] y 'write' [memoria_nueva, símbolo]; "
                                f"se recibieron {len(read)} y {len(write)} elementos")
            return None
        self.errores.append(f"{donde}: 'read' y 'write' deben ser ambos símbolos o ambos "
                            f"listas de dos elementos; se obtuvo read={_describir(read)}, "
                            f"write={_describir(write)}")
        return None

    def _referencia_estado(self, valor: Any, estados: list[str], donde: str) -> Optional[str]:
        estado = self._texto(valor, donde)
        if estado is not None and estado not in estados:
            self.errores.append(f"{donde}: el estado {estado!r} no está declarado en states")
        return estado

    def _simbolo_cinta(self, valor: Any, cinta: list[str], donde: str) -> Optional[str]:
        simbolo = self._texto(valor, donde)
        if simbolo is not None and simbolo not in cinta:
            self.errores.append(f"{donde}: el símbolo {simbolo!r} no pertenece a tape_alphabet")
        return simbolo

    # ---- entradas -------------------------------------------------------

    def _entradas(self, valor: Any) -> list[str]:
        # Solo se exige que cada entrada sea texto. Que sus símbolos estén en
        # Σ se comprueba por cadena al simular: una entrada inválida no
        # impide ejecutar las demás.
        if not isinstance(valor, list):
            self.errores.append(f"inputs: se esperaba una lista, se obtuvo {_describir(valor)}")
            return []
        if not valor:
            self.advertencias.append("inputs está vacío: no hay cadenas que simular")
        entradas = []
        for i, v in enumerate(valor):
            if not isinstance(v, str):
                pista = '; para la cadena vacía escriba ""' if v is None else ""
                self.errores.append(f"inputs[{i}]: se esperaba una cadena, se obtuvo {_describir(v)}{pista}")
            else:
                entradas.append(v)
        return entradas


def _compuesto(estado: str, memoria: str) -> str:
    return f"[{estado},{memoria}]"


def _describir(valor: Any) -> str:
    if isinstance(valor, dict):
        return "un mapeo"
    if isinstance(valor, list):
        return "una lista"
    if valor is None:
        return "nada (valor vacío)"
    if isinstance(valor, str):
        return f"el texto {valor!r}"
    return f"{type(valor).__name__} {valor!r}"
