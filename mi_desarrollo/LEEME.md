# Tu carpeta de trabajo — TP07

| Archivo | Para qué |
|---|---|
| `mi_tp07.py` | Acá escribís tu agente. **Es lo que entregás.** |
| `casos_prueba.json` | Los 25 casos de la cátedra. Dados hechos. |
| `evaluar.py` | Dado hecho. Calcula tu accuracy y la tabla de fallos. |
| `ejecutor.py` | Dado hecho. Convierte a velocidad y tiempo, y manda al robot. |
| `robot.py` | No lo toques. |
| `dataset.csv` | **Extensión**: 5 ejemplos para que veas el formato. Completalo vos. |
| `entrenar.py` | Dado hecho. Entrena con tu dataset y te da las métricas. |

## Cómo lo ejecutás

**Con robot** (para ver al G1 hacerte caso):

1. Abrí `INICIAR_SIMULADOR` y elegí el robot.
2. Doble clic en `EJECUTAR_MI_CODIGO`, o `python3 mi_desarrollo/mi_tp07.py`.

El programa abre directamente la consola interactiva. Si además querés correr
los 25 casos originales, usá `python3 mi_desarrollo/mi_tp07.py --evaluar`.

### Activar comandos por voz (OpenAI Whisper)

La consola acepta texto y audio. Para habilitar el micrófono una sola vez:

```bat
py -3 -m pip install -r requirements-voz.txt
copy .env.example .env
```

Abrí `.env`, reemplazá `tu_clave_aqui` por tu `OPENAI_API_KEY` y no compartas
ese archivo. Al ejecutar el programa, escribí normalmente o presioná **Enter**
para grabar una orden de 5 segundos. Whisper transcribe el audio; si detecta
otro idioma, la orden se traduce al español antes de pasar por el mismo
clasificador y validador que usa el texto.

Si falta la clave, internet, el micrófono o una dependencia, sólo se desactiva
la voz: siempre podés seguir escribiendo.

**Sin robot** (para trabajar el clasificador tranquilo):

```
python3 mi_desarrollo/mi_tp07.py --sin-robot
```

Corre los 25 casos y te da la accuracy, sin abrir nada.

## Modo interactivo

Con el robot conectado podés escribirle órdenes y nombres de jugadores:

```
  > CR7
  > festejá como Messi
  > gol de Mbappé
  > imitá a Bellingham
  > jugadores
  > [Enter para hablar]
  > salir
```

Jugadores disponibles: Cristiano Ronaldo, Lionel Messi, Kylian Mbappé, Jude
Bellingham, Antoine Griezmann y Juan Fernando Quintero. Los festejos solo están
habilitados para el G1 simulado; no se envían al robot físico.

## Extensión: entrenar un modelo (nivel 2)

Con reglas alcanza para aprobar. Si querés ir más lejos:

**1. Armá tu dataset.** `dataset.csv` trae 5 ejemplos para que veas el formato:

```
texto,intencion
dale para adelante,MOVER
frená ahí,DETENERSE
```

Completalo hasta unos 80. Las intenciones válidas son `MOVER`, `GIRAR`,
`DETENERSE`, `SALUDO`, `CONSULTAR_ESTADO` y `DESCONOCIDO`.

**2. Entrená y mirá tus métricas:**

```
python3 mi_desarrollo/entrenar.py
```

Te avisa si al dataset le falta algo: pocas filas, una intención sin ejemplos,
textos repetidos.

**3. Usalo en tu agente.** En `ClasificadorIntencion.__init__` hay dos líneas
comentadas:

```python
from entrenar import entrenar_desde_csv
self.modelo = entrenar_desde_csv()
```

Y en `clasificar()`:

```python
if self.modelo is not None:
    return self.modelo.predict([texto])[0]
```

Dejá las reglas de respaldo: si el dataset no está, el agente sigue andando.

**El extractor, el validador y el ejecutor no se enteran.** Cambiás una sola
clase.

**4. Compará.** ¿El modelo le gana a tus reglas? ¿En qué casos pierde? Esa
comparación es parte del informe.

> Necesitás `scikit-learn`: `pip install --user scikit-learn`.
> Sin él, el TP se hace igual con reglas.

## Qué entregás si hiciste la extensión

Una **carpeta** con los dos archivos:

```
tp07_apellido/
├── mi_tp07.py
└── dataset.csv
```

No hace falta que entregues el modelo entrenado: se entrena solo al arrancar,
en milisegundos. Y así el profesor puede **leer** tu dataset.
