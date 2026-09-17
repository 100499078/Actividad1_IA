from __future__ import annotations

import sys
import unittest
from os import environ
from pathlib import Path
from tempfile import NamedTemporaryFile
from types import SimpleNamespace
from unittest.mock import patch


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "mi_desarrollo"))

from voz import FRECUENCIA_MUESTREO, ErrorVoz, ReconocedorVoz  # noqa: E402


class _TranscripcionesFalsas:
    def __init__(self, texto, idioma):
        self.texto = texto
        self.idioma = idioma
        self.llamadas = []

    def create(self, **argumentos):
        self.llamadas.append(argumentos)
        return SimpleNamespace(text=self.texto, language=self.idioma)


class _RespuestasFalsas:
    def __init__(self, traduccion=""):
        self.traduccion = traduccion
        self.llamadas = []

    def create(self, **argumentos):
        self.llamadas.append(argumentos)
        return SimpleNamespace(output_text=self.traduccion)


def _cliente_falso(texto, idioma, traduccion=""):
    transcripciones = _TranscripcionesFalsas(texto, idioma)
    respuestas = _RespuestasFalsas(traduccion)
    cliente = SimpleNamespace(
        audio=SimpleNamespace(transcriptions=transcripciones),
        responses=respuestas,
    )
    return cliente, transcripciones, respuestas


class TestTranscripcion(unittest.TestCase):
    def setUp(self):
        temporal = NamedTemporaryFile(suffix=".wav", delete=False)
        temporal.write(b"audio de prueba")
        temporal.close()
        self.ruta = Path(temporal.name)

    def tearDown(self):
        self.ruta.unlink(missing_ok=True)

    def test_espanol_no_hace_una_segunda_llamada(self):
        cliente, transcripciones, respuestas = _cliente_falso(
            "festeja como Messi", "spanish"
        )

        resultado = ReconocedorVoz(cliente=cliente).transcribir(self.ruta)

        self.assertEqual("festeja como Messi", resultado.texto)
        self.assertFalse(resultado.traducido)
        self.assertEqual(1, len(transcripciones.llamadas))
        self.assertEqual([], respuestas.llamadas)
        self.assertEqual("whisper-1", transcripciones.llamadas[0]["model"])

    def test_otro_idioma_se_traduce_al_espanol(self):
        cliente, _, respuestas = _cliente_falso(
            "Celebrate like Messi", "english", "Festeja como Messi"
        )

        resultado = ReconocedorVoz(cliente=cliente).transcribir(self.ruta)

        self.assertEqual("Festeja como Messi", resultado.texto)
        self.assertEqual("Celebrate like Messi", resultado.transcripcion)
        self.assertTrue(resultado.traducido)
        self.assertEqual(1, len(respuestas.llamadas))

    def test_rechaza_una_transcripcion_vacia(self):
        cliente, _, _ = _cliente_falso("  ", "spanish")
        with self.assertRaisesRegex(ErrorVoz, "ninguna frase"):
            ReconocedorVoz(cliente=cliente).transcribir(self.ruta)


class _MuestrasFalsas:
    def tobytes(self):
        return b"\x00\x00" * 8


class _GrabadorFalso:
    def __init__(self):
        self.argumentos = None
        self.espero = False

    def rec(self, cantidad, **argumentos):
        self.argumentos = (cantidad, argumentos)
        return _MuestrasFalsas()

    def wait(self):
        self.espero = True


class TestGrabacion(unittest.TestCase):
    def test_genera_wav_mono_de_16_khz(self):
        import wave

        grabador = _GrabadorFalso()
        reconocedor = ReconocedorVoz(grabador=grabador)
        ruta = reconocedor._grabar_wav(1.0)
        try:
            with wave.open(str(ruta), "rb") as audio:
                self.assertEqual(1, audio.getnchannels())
                self.assertEqual(2, audio.getsampwidth())
                self.assertEqual(FRECUENCIA_MUESTREO, audio.getframerate())
            self.assertEqual(FRECUENCIA_MUESTREO, grabador.argumentos[0])
            self.assertTrue(grabador.espero)
        finally:
            ruta.unlink(missing_ok=True)

    def test_sin_api_key_no_intenta_grabar(self):
        grabador = _GrabadorFalso()
        reconocedor = ReconocedorVoz(grabador=grabador)

        with patch.dict(environ, {}, clear=True):
            with self.assertRaisesRegex(ErrorVoz, "OPENAI_API_KEY"):
                reconocedor.escuchar(1.0)

        self.assertIsNone(grabador.argumentos)


if __name__ == "__main__":
    unittest.main()
