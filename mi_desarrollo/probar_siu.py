"""Prueba visual de los gestos. Herramienta, no se entrega.

Con el simulador abierto (G1), mostra los gestos uno por uno para poder
mirar la ventana 3D y ajustar las poses.

    python3 probar_siu.py
"""

import time

from robot import Robot
from sim.festejos import FESTEJOS

PAUSA = 2.0

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

        for festejo in FESTEJOS:
            titulo = f"{festejo.jugador.upper()} / {festejo.descripcion}"
            mostrar(
                robot,
                titulo,
                lambda f=festejo: robot.festejar(f.gesto, duracion=f.duracion),
            )

        print("\n  Si el saludo NO agitaba el brazo antes de este cambio,")
        print("  ahi tenes confirmado el bug de visor.py.\n")
    finally:
        robot.detenerse()
        robot.desconectar()


if __name__ == "__main__":
    main()
