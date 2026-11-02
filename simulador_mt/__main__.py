"""Interfaz de terminal: python -m simulador_mt MAQUINA.yaml [opciones]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from .cargador import ErrorConfiguracion, cargar_maquina
from .motor import MAX_PASOS_POR_DEFECTO, ejecutar
from .presentacion import formatear_ejecucion, formatear_maquina, formatear_resumen


def _entero_no_negativo(texto: str) -> int:
    try:
        valor = int(texto)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{texto!r} no es un entero") from None
    if valor < 0:
        raise argparse.ArgumentTypeError("debe ser 0 o mayor")
    return valor


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m simulador_mt",
        description="Simula una Máquina de Turing de una cinta descrita en YAML "
                    "y muestra todas sus descripciones instantáneas.")
    parser.add_argument("maquina", type=Path, help="archivo YAML con la clave raíz 'mt'")
    parser.add_argument("--max-pasos", type=_entero_no_negativo, default=MAX_PASOS_POR_DEFECTO,
                        help=f"límite de pasos por entrada (por defecto {MAX_PASOS_POR_DEFECTO}); "
                             "al alcanzarlo el resultado es 'no determinado'")
    parser.add_argument("--salida", type=Path,
                        help="guarda la traza completa en este archivo (UTF-8)")
    parser.add_argument("--resumen", action="store_true",
                        help="no muestra las IDs en pantalla (el archivo de --salida "
                             "siempre las contiene todas)")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    # En Windows la salida redirigida usa cp1252 y no puede escribir δ ni ⊢.
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

    args = _parser().parse_args(argv)
    try:
        maquina = cargar_maquina(args.maquina)
    except ErrorConfiguracion as exc:
        print(exc, file=sys.stderr)
        return 1

    resultados = [ejecutar(maquina, entrada, args.max_pasos) for entrada in maquina.entradas]
    total = len(resultados)
    cabecera = formatear_maquina(maquina)
    resumen = formatear_resumen(resultados)

    pantalla = [cabecera]
    pantalla += [formatear_ejecucion(maquina, r, i, total, con_traza=not args.resumen)
                 for i, r in enumerate(resultados, start=1)]
    pantalla.append(resumen)
    print("\n".join(pantalla))

    if args.salida is not None:
        completo = [cabecera]
        completo += [formatear_ejecucion(maquina, r, i, total)
                     for i, r in enumerate(resultados, start=1)]
        completo.append(resumen)
        try:
            args.salida.parent.mkdir(parents=True, exist_ok=True)
            args.salida.write_text("\n".join(completo) + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"No se pudo escribir la traza en {args.salida}: {exc.strerror}", file=sys.stderr)
            return 1
        print(f"\nTraza completa guardada en {args.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
