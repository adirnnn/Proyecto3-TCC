"""Formato de texto de la máquina, las IDs y los resultados.

Notación de ID (Hopcroft): α[q]β. El estado va entre corchetes justo antes
del símbolo que lee el cabezal. Se muestra la ventana relevante de la cinta
(ver Configuracion.ventana), así que los blancos dentro de ella aparecen
explícitamente y el cabezal puede estar en una posición negativa.
"""

from __future__ import annotations

from .modelo import MaquinaTuring
from .motor import Configuracion, Resultado, Terminacion

SEPARADOR = "=" * 72
SUBSEPARADOR = "-" * 72


def formatear_estado(estado: str) -> str:
    # Los estados compuestos del formato con memoria ya llevan corchetes.
    return estado if estado.startswith("[") else f"[{estado}]"


def formatear_id(config: Configuracion) -> str:
    partes = []
    for posicion in config.ventana():
        if posicion == config.cabezal:
            partes.append(formatear_estado(config.estado))
        partes.append(config.leer(posicion))
    return "".join(partes)


def formatear_cinta(config: Configuracion, sangria: str = "  ") -> list[str]:
    """Vista en tres filas: posiciones, símbolos y cabezal."""
    posiciones = list(config.ventana())
    ancho = max(len(str(p)) for p in posiciones)
    fila_pos = " ".join(str(p).rjust(ancho) for p in posiciones)
    fila_cinta = " ".join(config.leer(p).rjust(ancho) for p in posiciones)
    columna = posiciones.index(config.cabezal) * (ancho + 1) + ancho - 1
    return [
        f"{sangria}posición: {fila_pos}",
        f"{sangria}cinta:    {fila_cinta}",
        f"{sangria}cabezal:  {' ' * columna}^ estado {config.estado}",
    ]


def formatear_maquina(maquina: MaquinaTuring) -> str:
    lineas = [
        SEPARADOR,
        f"Máquina: {maquina.nombre}  (formato de transiciones: {maquina.formato})",
        SEPARADOR,
        f"Q  = {{{', '.join(maquina.estados)}}}",
        f"Σ  = {{{', '.join(maquina.alfabeto_entrada)}}}",
        f"Γ  = {{{', '.join(maquina.alfabeto_cinta)}}}",
        f"blanco = {maquina.blanco}",
        f"q0 = {maquina.estado_inicial}",
        f"F  = {{{', '.join(sorted(maquina.estados_aceptacion))}}}",
        f"δ  ({len(maquina.transiciones)} transiciones):",
    ]
    for t in sorted(maquina.transiciones.values(), key=lambda t: t.indice):
        lineas.append(f"  #{t.indice:<3} {t}")
    for advertencia in maquina.advertencias:
        lineas.append(f"ADVERTENCIA: {advertencia}")
    return "\n".join(lineas)


def formatear_ejecucion(maquina: MaquinaTuring, resultado: Resultado, numero: int,
                        total: int, con_traza: bool = True) -> str:
    descripcion = "cadena vacía" if resultado.entrada == "" else f"longitud {len(resultado.entrada)}"
    lineas = [SEPARADOR, f"Entrada {numero}/{total}: \"{resultado.entrada}\" ({descripcion})", SUBSEPARADOR]

    if resultado.terminacion is Terminacion.INVALIDA:
        lineas += [f"Resultado: {resultado.terminacion.value}",
                   f"Motivo: {resultado.motivo}",
                   "La máquina no se ejecutó."]
        return "\n".join(lineas)

    inicial, final = resultado.configuraciones[0], resultado.final
    lineas += ["Configuración inicial:", *formatear_cinta(inicial)]
    if con_traza:
        lineas += _traza(resultado)
    else:
        lineas.append(f"(traza omitida en pantalla; pasos: {resultado.pasos})")
    lineas += ["Configuración final:", *formatear_cinta(final)]
    lineas.append(f"  ID final: {formatear_id(final)}")
    lineas += _contenido_final(maquina, final)
    lineas += [f"Resultado: {resultado.terminacion.value}",
               f"Motivo: {resultado.motivo}",
               f"Pasos: {resultado.pasos}"]
    return "\n".join(lineas)


def _traza(resultado: Resultado) -> list[str]:
    ids = [formatear_id(c) for c in resultado.configuraciones]
    ancho_id = max(len(i) for i in ids)
    ancho_paso = len(str(resultado.pasos))
    lineas = ["Descripciones instantáneas (cabezal = posición de la celda leída):"]
    for config, texto in zip(resultado.configuraciones, ids):
        flecha = "⊢" if config.transicion else " "
        regla = f"   por #{config.transicion.indice}: {config.transicion}" if config.transicion else ""
        lineas.append(f"  {config.paso:>{ancho_paso}} {flecha} {texto:<{ancho_id}}"
                      f"   cabezal={config.cabezal}{regla}")
    return lineas


def _contenido_final(maquina: MaquinaTuring, final: Configuracion) -> list[str]:
    # Se muestra lo que realmente quedó en la cinta, sin limpiar marcadores;
    # si contiene símbolos que no son de Σ (marcas o blancos interiores) se
    # dice explícitamente en vez de ocultarlos.
    contenido = "".join(final.simbolos)
    if not contenido:
        return ['  Contenido no blanco de la cinta: "" (cinta en blanco)']
    fin = final.inicio + len(final.simbolos) - 1
    lineas = [f'  Contenido no blanco de la cinta: "{contenido}" (celdas {final.inicio}..{fin})']
    ajenos = sorted({s for s in final.simbolos if s not in maquina.alfabeto_entrada})
    if ajenos:
        lineas.append(f"  Aviso: el contenido incluye símbolos que no son de Σ: {', '.join(ajenos)}")
    return lineas


def formatear_resumen(resultados: list[Resultado]) -> str:
    lineas = [SEPARADOR, "Resumen", SUBSEPARADOR]
    citadas = [f'"{r.entrada}"' for r in resultados]
    ancho = max(len(c) for c in citadas) if citadas else 0
    for i, (r, citada) in enumerate(zip(resultados, citadas), start=1):
        if r.final is None:
            detalle = "(no se ejecutó)"
        else:
            detalle = f'pasos={r.pasos}  cinta: "{"".join(r.final.simbolos)}"'
        lineas.append(f"  {i:>2}. {citada:<{ancho}}  {r.terminacion.value:<9}  {detalle}")
    return "\n".join(lineas)
