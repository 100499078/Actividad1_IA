"""Visualizacion del mapa. Herramienta de trabajo, no se entrega.

El simulador 3D no dibuja la grilla: sim/grilla.py es un modulo aparte
que el visor ni importa. Asi que el mapa y las rutas se ven aca.

    python3 ver_mapa.py                 dibuja el mapa en la terminal
    python3 ver_mapa.py --png           ademas guarda mapa_aula.png
"""

import sys
from collections import deque
from pathlib import Path

_ENTORNO = Path(__file__).resolve().parent.parent / "entorno"
if str(_ENTORNO) not in sys.path:
    sys.path.insert(0, str(_ENTORNO))

from sim.grilla import DELTAS, LIBRE, OBSTACULO, PROHIBIDA, cargar  # noqa: E402

MAPA = Path(__file__).resolve().parent / "mapa_aula.json"

SIMBOLOS = {LIBRE: " .", OBSTACULO: " X", PROHIBIDA: " #"}


def buscar_ruta(mapa, atraviesa_prohibidas=False):
    """BFS del inicio al destino. Devuelve la lista de celdas, o None.

    `atraviesa_prohibidas` decide si las celdas 2 cuentan como pisables.
    Con True sale la ruta mas corta FISICAMENTE posible; con False, la
    mas corta LEGAL. Comparar las dos es lo que muestra para que sirve
    el validador.
    """
    pisables = {LIBRE, PROHIBIDA} if atraviesa_prohibidas else {LIBRE}
    inicio, destino = mapa.inicio, mapa.destino
    cola, previo = deque([inicio]), {inicio: None}

    while cola:
        actual = cola.popleft()
        if actual == destino:
            break
        for df, dc in DELTAS.values():
            vecino = (actual[0] + df, actual[1] + dc)
            if not (0 <= vecino[0] < mapa.filas and 0 <= vecino[1] < mapa.columnas):
                continue
            if mapa.celda(*vecino) not in pisables or vecino in previo:
                continue
            previo[vecino] = actual
            cola.append(vecino)

    if destino not in previo:
        return None
    ruta, actual = [], destino
    while actual is not None:
        ruta.append(actual)
        actual = previo[actual]
    return ruta[::-1]


def dibujar(mapa, ruta=None, titulo=""):
    """Imprime el mapa en la terminal, con la ruta encima si se pasa una."""
    ruta = set(ruta or ())
    if titulo:
        print(f"\n  {titulo}")
    print("     " + "".join(f" c{c}" for c in range(mapa.columnas)))
    for f in range(mapa.filas):
        celdas = []
        for c in range(mapa.columnas):
            valor = mapa.celda(f, c)
            if (f, c) == mapa.inicio:
                celdas.append(" I")
            elif (f, c) == mapa.destino:
                celdas.append(" M")
            elif (f, c) in ruta:
                # Una ruta que pisa una prohibida se marca distinto: es
                # exactamente lo que el validador tiene que rechazar.
                celdas.append(" !" if valor == PROHIBIDA else " o")
            else:
                celdas.append(SIMBOLOS[valor])
        print(f"  f{f} " + " ".join(celdas))
    print("       I inicio   M meta   . libre   X obstaculo   "
          "# prohibida   o ruta   ! ruta sobre prohibida")


def informe(mapa):
    corta = buscar_ruta(mapa, atraviesa_prohibidas=True)
    legal = buscar_ruta(mapa, atraviesa_prohibidas=False)

    print(f"\n  {mapa.nombre}")
    print(f"  {mapa.filas} x {mapa.columnas} celdas de {mapa.tamano_celda} m "
          f"= {mapa.columnas * mapa.tamano_celda:g} m x "
          f"{mapa.filas * mapa.tamano_celda:g} m")

    dibujar(mapa, titulo="MAPA")

    if corta:
        pisadas = [c for c in corta if mapa.celda(*c) == PROHIBIDA]
        dibujar(mapa, corta,
                f"RUTA MAS CORTA: {len(corta) - 1} pasos"
                + (f"  -- pisa {len(pisadas)} celda(s) prohibida(s): {pisadas}"
                   if pisadas else ""))
    if legal:
        dibujar(mapa, legal, f"RUTA LEGAL: {len(legal) - 1} pasos")

    if corta and legal:
        print(f"\n  El atajo ahorra {len(legal) - len(corta)} pasos "
              f"cruzando la zona prohibida. Por eso hace falta el validador.\n")
    return corta, legal


def a_png(mapa, corta, legal, archivo="mapa_aula.png"):
    """Guarda la figura. Requiere matplotlib; si no esta, avisa y sigue."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Patch
    except ImportError:
        print("  (sin matplotlib: no se genera el PNG)")
        return None

    COLOR = {LIBRE: "#f4f1ea", OBSTACULO: "#3d4451", PROHIBIDA: "#f2c9c0"}
    fig, ejes = plt.subplots(1, 2, figsize=(12, 4.4))

    for eje, (ruta, titulo, color) in zip(ejes, [
            (corta, f"Ruta más corta — {len(corta) - 1} pasos — BLOQUEADA", "#c0392b"),
            (legal, f"Ruta legal — {len(legal) - 1} pasos", "#1f6f4a")]):
        for f in range(mapa.filas):
            for c in range(mapa.columnas):
                eje.add_patch(plt.Rectangle(
                    (c - .5, -f - .5), 1, 1,
                    facecolor=COLOR[mapa.celda(f, c)],
                    edgecolor="white", linewidth=1.5))
        xs = [c for _, c in ruta]
        ys = [-f for f, _ in ruta]
        eje.plot(xs, ys, "-o", color=color, linewidth=2.5,
                 markersize=6, zorder=3)
        for etiqueta, (f, c), marca in [("I", mapa.inicio, "s"),
                                        ("M", mapa.destino, "*")]:
            eje.scatter([c], [-f], s=260, marker=marca, zorder=4,
                        color="#1a1a1a")
            eje.annotate(etiqueta, (c, -f), color="white", ha="center",
                         va="center", fontsize=8, fontweight="bold", zorder=5)
        eje.set_xlim(-.5, mapa.columnas - .5)
        eje.set_ylim(-mapa.filas + .5, .5)
        eje.set_aspect("equal")
        eje.set_xticks(range(mapa.columnas))
        eje.set_yticks(range(0, -mapa.filas, -1))
        eje.set_yticklabels([f"f{f}" for f in range(mapa.filas)])
        eje.set_xticklabels([f"c{c}" for c in range(mapa.columnas)])
        eje.tick_params(length=0, labelsize=8, colors="#666666")
        for lado in eje.spines.values():
            lado.set_visible(False)
        eje.set_title(titulo, fontsize=11, color=color, pad=10)

    ejes[0].legend(handles=[
        Patch(facecolor=COLOR[LIBRE], edgecolor="#cccccc", label="libre"),
        Patch(facecolor=COLOR[OBSTACULO], label="obstáculo"),
        Patch(facecolor=COLOR[PROHIBIDA], label="zona prohibida")],
        loc="upper center", bbox_to_anchor=(1.08, -0.08),
        ncol=3, frameon=False, fontsize=9)

    fig.suptitle(mapa.nombre, fontsize=13, fontweight="bold", y=1.0)
    fig.tight_layout()
    destino = Path(__file__).resolve().parent / archivo
    fig.savefig(destino, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"  Figura guardada en {destino.name}")
    return destino


if __name__ == "__main__":
    mapa = cargar(str(MAPA))
    corta, legal = informe(mapa)
    if "--png" in sys.argv:
        a_png(mapa, corta, legal)
