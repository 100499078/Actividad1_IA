"""Catalogo compartido de festejos disponibles en el simulador.

Este modulo no contiene angulos articulares: esas secuencias dependen del
modelo del robot y viven en ``robots.py``. Si concentra la identidad publica
de cada festejo (nombre, aliases, duracion y descripcion) para que el agente,
la consola y las validaciones hablen el mismo idioma.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Festejo:
    gesto: str
    jugador: str
    aliases: tuple[str, ...]
    duracion: float
    descripcion: str


FESTEJOS: tuple[Festejo, ...] = (
    Festejo(
        gesto="siu",
        jugador="Cristiano Ronaldo",
        aliases=("cristiano ronaldo", "cristiano", "ronaldo", "cr7", "siu"),
        duracion=3.2,
        descripcion="SIU: giro sugerido y aterrizaje con brazos abajo y abiertos",
    ),
    Festejo(
        gesto="messi",
        jugador="Lionel Messi",
        aliases=("lionel messi", "leo messi", "messi", "leo"),
        duracion=3.0,
        descripcion="Brazos elevados y manos apuntando al cielo",
    ),
    Festejo(
        gesto="mbappe",
        jugador="Kylian Mbappe",
        aliases=("kylian mbappe", "mbappe", "kylian"),
        duracion=3.0,
        descripcion="Brazos cruzados sobre el pecho",
    ),
    Festejo(
        gesto="bellingham",
        jugador="Jude Bellingham",
        aliases=("jude bellingham", "bellingham", "jude", "belligol"),
        duracion=3.0,
        descripcion="Brazos extendidos, pecho abierto y piernas separadas",
    ),
    Festejo(
        gesto="griezmann",
        jugador="Antoine Griezmann",
        aliases=("antoine griezmann", "griezmann", "antoine", "take the l"),
        duracion=3.6,
        descripcion="Take the L estilizado, sin salto ni fase aerea",
    ),
    Festejo(
        gesto="quintero",
        jugador="Juan Fernando Quintero",
        aliases=("juan fernando quintero", "juanfer quintero", "juanfer", "quintero"),
        duracion=3.4,
        descripcion="Gesto de frotar la lampara de Aladino",
    ),
)

POR_GESTO = {f.gesto: f for f in FESTEJOS}
ALIAS_A_GESTO = {
    alias: festejo.gesto
    for festejo in FESTEJOS
    for alias in festejo.aliases
}
ALIASES_ORDENADOS = tuple(sorted(ALIAS_A_GESTO, key=len, reverse=True))


def jugadores_disponibles() -> str:
    return ", ".join(f.jugador for f in FESTEJOS)


def duracion_de(gesto: str, predeterminada: float = 3.0) -> float:
    festejo = POR_GESTO.get(gesto)
    return festejo.duracion if festejo is not None else predeterminada


def gestos_publicos() -> tuple[str, ...]:
    return tuple(f.gesto for f in FESTEJOS)
