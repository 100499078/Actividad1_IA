"""Prueba visual de los gestos. Herramienta, no se entrega.

Con el simulador abierto (G1), mostra los gestos uno por uno para poder
mirar la ventana 3D y ajustar las poses.

    python3 probar_siu.py
"""

import time

from robot import Robot

PAUSA = 2.0

# --- AGREGADO TP07 EXTENSION -------------------------------------------
# Por ahora solo Cristiano Ronaldo (siu) y la pose de decepcion: los
# demas jugadores se descartaron para concentrarse en perfeccionar
# estos dos primero (ver robots.py).
FESTEJOS = (
    ("SIU / Cristiano Ronaldo (piernas separadas y flexionadas, brazos abiertos)", "siu"),
    ("DECEPCION / gol en contra (manos en la cabeza)", "decepcion"),
)


def mostrar(robot, titulo, accion):
    print(f"\n  >>> {titulo}")
    accion()
    print(f"      estado: {robot.verificar_estado()}")
    time.sleep(PAUSA)


def main():
    robot = Robot()
    robot.conectar()
    try:
        print("\n  Mira la ventana del simulador.")

        mostrar(robot, "SALUDO (el brazo derecho se agita)", robot.saludar)
        mostrar(robot, "DAR LA MANO (brazo al frente, quieto)", robot.dar_la_mano)

        for titulo, nombre in FESTEJOS:
            mostrar(robot, titulo, lambda nombre=nombre: robot.festejar(nombre, duracion=4.0))

        print("\n  Si el saludo NO agitaba el brazo antes de este cambio,")
        print("  ahi tenes confirmado el bug de visor.py.\n")
    finally:
        robot.detenerse()
        robot.desconectar()


if __name__ == "__main__":
    main()
