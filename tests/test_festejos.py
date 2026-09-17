from __future__ import annotations

import math
import sys
import unittest
from importlib import import_module
from pathlib import Path
from unittest.mock import mock_open, patch

import mujoco


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "mi_desarrollo"))
sys.path.insert(0, str(RAIZ / "entorno"))

from evaluar import evaluar  # noqa: E402
from mi_tp07 import AgenteRobot  # noqa: E402
from sim.acciones import acciones_de  # noqa: E402
from sim.festejos import FESTEJOS, gestos_publicos  # noqa: E402
from sim.robots import G1, Gesto  # noqa: E402
from sim.safety import perfil  # noqa: E402


class TestLenguajeFestejos(unittest.TestCase):
    def setUp(self):
        self.agente = AgenteRobot()

    def assert_gesto(self, texto: str, gesto: str):
        respuesta = self.agente.procesar(texto)
        self.assertEqual("FESTEJO", respuesta["tipo"], texto)
        self.assertEqual(gesto, respuesta["parametros"].get("gesto"), texto)
        self.assertTrue(respuesta["ejecutar"], respuesta)

    def test_ordenes_naturales_y_aliases(self):
        casos = {
            "festeja como Cristiano Ronaldo": "siu",
            "hace el siuuu": "siu",
            "Messi": "messi",
            "celebra como Kylian Mbappe": "mbappe",
            "gol de Bellingham": "bellingham",
            "imita a Griezmann": "griezmann",
            "festejo de Juanfer": "quintero",
        }
        for texto, gesto in casos.items():
            with self.subTest(texto=texto):
                self.assert_gesto(texto, gesto)

    def test_eventos_en_contra_eligen_decepcion(self):
        self.assert_gesto("autogol de Messi", "decepcion")
        self.assert_gesto("Cristiano fallo el penal", "decepcion")

    def test_jugador_desconocido_no_informa_ejecucion(self):
        respuesta = self.agente.procesar("festejo de Neymar")
        self.assertEqual("FESTEJO", respuesta["tipo"])
        self.assertFalse(respuesta["ejecutar"])
        self.assertIn("no reconoci", respuesta["mensaje"])

    def test_gol_sin_jugador_no_informa_ejecucion(self):
        respuesta = self.agente.procesar("GOOOOOOL")
        self.assertEqual("FESTEJO", respuesta["tipo"])
        self.assertFalse(respuesta["ejecutar"])

    def test_negacion_gana_al_festejo(self):
        respuesta = self.agente.procesar("no festejes el gol de CR7")
        self.assertEqual("DETENERSE", respuesta["tipo"])
        self.assertNotEqual("siu", respuesta["parametros"].get("gesto"))

    def test_no_confunde_prefijos_de_gol(self):
        for texto in ("el goleador es Cristiano", "golpeo la caja"):
            with self.subTest(texto=texto):
                respuesta = self.agente.procesar(texto)
                self.assertNotEqual("FESTEJO", respuesta["tipo"])

    def test_alias_no_dispara_dentro_de_otra_oracion(self):
        respuesta = self.agente.procesar("me gusta Messi")
        self.assertEqual("DESCONOCIDO", respuesta["tipo"])


class TestCatalogoYAnimaciones(unittest.TestCase):
    def test_catalogo_lista_blanca_y_g1_estan_sincronizados(self):
        publicos = set(gestos_publicos())
        self.assertTrue(publicos <= set(G1.gestos))
        self.assertTrue(publicos <= set(acciones_de("g1")))

    def test_keyframes_validos(self):
        for nombre, gesto in G1.gestos.items():
            with self.subTest(gesto=nombre):
                self.assertIsInstance(gesto, Gesto)
                tiempos = [k.tiempo for k in gesto.keyframes]
                self.assertEqual(tiempos, sorted(tiempos))
                self.assertGreaterEqual(tiempos[0], 0.0)
                self.assertLessEqual(tiempos[-1], 5.0)
                for keyframe in gesto.keyframes:
                    self.assertTrue(math.isfinite(keyframe.altura))
                    for indice, angulo in keyframe.pose.items():
                        self.assertIn(indice, range(29))
                        self.assertTrue(math.isfinite(angulo))
                        self.assertLessEqual(abs(angulo), math.pi)

    def test_duraciones_del_catalogo_cubren_la_animacion(self):
        for ficha in FESTEJOS:
            ultimo = G1.gestos[ficha.gesto].keyframes[-1].tiempo
            self.assertGreaterEqual(ficha.duracion, ultimo, ficha.gesto)

    def test_regresion_tp_original(self):
        resumen = evaluar(AgenteRobot(), mostrar=False)
        self.assertEqual(25, resumen["aciertos"])
        self.assertEqual(
            resumen["peligrosos_totales"], resumen["peligrosos_bloqueados"])

    def test_angulos_respetan_limites_del_modelo_oficial(self):
        modelo = mujoco.MjModel.from_xml_path(G1.ruta_escena())
        limites = {}
        for joint_id in range(modelo.njnt):
            direccion = int(modelo.jnt_qposadr[joint_id])
            if direccion >= 7 and modelo.jnt_limited[joint_id]:
                limites[direccion - 7] = tuple(modelo.jnt_range[joint_id])
        for nombre, gesto in G1.gestos.items():
            for keyframe in gesto.keyframes:
                for indice, angulo in keyframe.pose.items():
                    if indice not in limites:
                        continue
                    minimo, maximo = limites[indice]
                    self.assertGreaterEqual(
                        angulo, minimo - 1e-6, f"{nombre}: articulacion {indice}")
                    self.assertLessEqual(
                        angulo, maximo + 1e-6, f"{nombre}: articulacion {indice}")


class _RobotFalso:
    def __init__(self, falla=False):
        self.perfil = perfil("tp07")
        self.falla = falla
        self.llamadas = []

    def festejar(self, gesto, duracion):
        if self.falla:
            raise RuntimeError("rechazo simulado")
        self.llamadas.append((gesto, duracion))


class TestResultadoDeEjecucion(unittest.TestCase):
    def test_exito_registra_gesto_y_duracion(self):
        robot = _RobotFalso()
        respuesta = AgenteRobot(robot).procesar("Messi")
        self.assertTrue(respuesta["ejecutar"])
        self.assertEqual([("messi", 3.0)], robot.llamadas)

    def test_rechazo_del_servidor_no_se_informa_como_exito(self):
        respuesta = AgenteRobot(_RobotFalso(falla=True)).procesar("Messi")
        self.assertFalse(respuesta["ejecutar"])
        self.assertIn("rechazo simulado", respuesta["mensaje"])


class TestArranqueSimulador(unittest.TestCase):
    def test_sena_vieja_con_system_error_no_bloquea_windows(self):
        principal = import_module("sim.__main__")
        contenido = '{"pid": 999999, "robot": "g1", "materia": "tp07"}'
        with patch("builtins.open", mock_open(read_data=contenido)):
            with patch.object(principal.os, "kill", side_effect=SystemError("WinError 87")):
                self.assertIsNone(principal._sena_viva())


if __name__ == "__main__":
    unittest.main()
