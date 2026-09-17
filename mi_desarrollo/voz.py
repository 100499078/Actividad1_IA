"""Entrada de voz para el agente del TP07.

La captura se hace localmente y el WAV temporal se envia a OpenAI Whisper.
El modulo es opcional: si falta una dependencia o la clave de API, la consola
escrita sigue funcionando normalmente.
"""

from __future__ import annotations

import os
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path


MODELO_TRANSCRIPCION = "whisper-1"
MODELO_TRADUCCION_PREDETERMINADO = "gpt-4o-mini"
SEGUNDOS_PREDETERMINADOS = 5.0
FRECUENCIA_MUESTREO = 16_000

_CONTEXTO_FESTEJOS = (
    "Esta es una orden breve para un robot. Puede mencionar a Cristiano "
    "Ronaldo, CR7, Lionel Messi, Kylian Mbappe, Jude Bellingham, Antoine "
    "Griezmann o Juan Fernando Quintero."
)


class ErrorVoz(RuntimeError):
    """Error recuperable de configuracion, grabacion o API."""


@dataclass(frozen=True)
class ResultadoVoz:
    texto: str
    transcripcion: str
    idioma: str | None
    traducido: bool


class ReconocedorVoz:
    """Graba una orden, la transcribe y, si hace falta, la pasa a espanol."""

    def __init__(self, cliente=None, grabador=None):
        self._cliente = cliente
        self._grabador = grabador

    def escuchar(self, segundos: float = SEGUNDOS_PREDETERMINADOS) -> ResultadoVoz:
        if segundos <= 0:
            raise ErrorVoz("la duracion de grabacion debe ser mayor que cero")

        # Se valida antes de encender el microfono. Si no hay clave, falla
        # inmediatamente y la consola escrita puede seguir usandose.
        self._obtener_cliente()
        ruta = self._grabar_wav(segundos)
        try:
            return self.transcribir(ruta)
        finally:
            ruta.unlink(missing_ok=True)

    def transcribir(self, ruta_audio: str | Path) -> ResultadoVoz:
        """Transcribe un archivo y devuelve un comando listo para el agente."""
        ruta = Path(ruta_audio)
        if not ruta.is_file():
            raise ErrorVoz(f"no existe el audio: {ruta}")

        cliente = self._obtener_cliente()
        try:
            with ruta.open("rb") as audio:
                respuesta = cliente.audio.transcriptions.create(
                    model=MODELO_TRANSCRIPCION,
                    file=audio,
                    response_format="verbose_json",
                    prompt=_CONTEXTO_FESTEJOS,
                    temperature=0,
                )
        except Exception as exc:  # La SDK usa varias clases segun el fallo.
            raise ErrorVoz(f"OpenAI no pudo transcribir el audio: {exc}") from exc

        texto = _campo(respuesta, "text").strip()
        idioma = _campo(respuesta, "language", predeterminado=None)
        if not texto:
            raise ErrorVoz("no se detecto ninguna frase en la grabacion")

        if idioma is None or _es_espanol(str(idioma)):
            return ResultadoVoz(texto, texto, idioma, False)

        traducido = self._traducir_al_espanol(cliente, texto)
        return ResultadoVoz(traducido, texto, str(idioma), True)

    def _grabar_wav(self, segundos: float) -> Path:
        grabador = self._grabador
        if grabador is None:
            try:
                import sounddevice as grabador
            except ImportError as exc:
                raise ErrorVoz(
                    "falta el microfono de Python; instala 'sounddevice' con "
                    "py -3 -m pip install sounddevice"
                ) from exc

        try:
            muestras = grabador.rec(
                int(segundos * FRECUENCIA_MUESTREO),
                samplerate=FRECUENCIA_MUESTREO,
                channels=1,
                dtype="int16",
            )
            grabador.wait()
        except Exception as exc:
            raise ErrorVoz(f"no se pudo grabar desde el microfono: {exc}") from exc

        temporal = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temporal.close()
        ruta = Path(temporal.name)
        try:
            with wave.open(str(ruta), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)  # int16
                wav.setframerate(FRECUENCIA_MUESTREO)
                wav.writeframes(muestras.tobytes())
        except Exception:
            ruta.unlink(missing_ok=True)
            raise
        return ruta

    def _obtener_cliente(self):
        if self._cliente is not None:
            return self._cliente

        try:
            from dotenv import load_dotenv

            raiz = Path(__file__).resolve().parent.parent
            load_dotenv(raiz / ".env")
        except ImportError:
            pass

        if not os.getenv("OPENAI_API_KEY"):
            raise ErrorVoz(
                "falta OPENAI_API_KEY; copia .env.example como .env y agrega tu clave"
            )

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ErrorVoz(
                "falta la SDK de OpenAI; instala 'openai' con "
                "py -3 -m pip install openai"
            ) from exc

        self._cliente = OpenAI()
        return self._cliente

    @staticmethod
    def _traducir_al_espanol(cliente, texto: str) -> str:
        try:
            respuesta = cliente.responses.create(
                model=os.getenv(
                    "OPENAI_TRANSLATION_MODEL",
                    MODELO_TRADUCCION_PREDETERMINADO,
                ),
                instructions=(
                    "Traduce la orden del usuario al espanol. Devuelve solamente "
                    "la orden traducida, sin explicaciones. Conserva nombres propios, "
                    "cantidades, negaciones y unidades exactamente."
                ),
                input=texto,
            )
            traduccion = respuesta.output_text.strip()
        except Exception as exc:
            raise ErrorVoz(f"OpenAI no pudo traducir la orden: {exc}") from exc

        if not traduccion:
            raise ErrorVoz("OpenAI devolvio una traduccion vacia")
        return traduccion


def _campo(objeto, nombre: str, predeterminado=""):
    if isinstance(objeto, dict):
        return objeto.get(nombre, predeterminado)
    return getattr(objeto, nombre, predeterminado)


def _es_espanol(idioma: str) -> bool:
    valor = idioma.lower().strip().replace("_", "-")
    return valor == "es" or valor.startswith("es-") or valor in {
        "spanish",
        "espanol",
        "español",
    }
