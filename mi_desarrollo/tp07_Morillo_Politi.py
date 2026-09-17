# =====================================================================
#  TP07 - Inteligencia Artificial
#  Agente que interpreta comandos en lenguaje natural
#
#  ESTE ES EL ARCHIVO DONDE ESCRIBIS TU PROGRAMA.
#
#  Antes de ejecutarlo:
#    1. Abri INICIAR_SIMULADOR (elegi G1 o Go2)
#    2. Espera a que aparezca la ventana con el robot
#    3. Recien ahi ejecuta este archivo
#
#  Nombre y apellido:  .....................................
#  Comision:           .....................................
# =====================================================================

import re
import unicodedata

from robot import Robot
from sim.festejos import (
    ALIAS_A_GESTO,
    ALIASES_ORDENADOS,
    duracion_de,
    jugadores_disponibles,
)

from ejecutor import Ejecutor
from evaluar import evaluar

# Pone tu nombre: aparece en el reporte que entregas.
ALUMNO = "Apellido, Sara"


# =====================================================================
#  NORMALIZACION - se usa en las tres etapas
# =====================================================================
def normalizar(texto):
    """Deja el texto en minusculas y sin tildes.

    Sin esto habria que escribir cada patron dos veces: "avanza" y
    "avanza", "gira" y "gira", "bateria" y "bateria". El castellano
    rioplatense del enunciado usa voseo con tilde en casi todos los
    verbos, asi que normalizar de entrada simplifica todo lo demas.

        "avanza 2 metros"  ->  "avanza 2 metros"
        "¿Cuanta BATERIA tenes?"  ->  "¿cuanta bateria tenes?"
    """
    t = texto.lower().strip()
    # NFD separa la letra de su tilde; despues se descartan las tildes
    # sueltas (categoria Mn = "mark, nonspacing").
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return t


# =====================================================================
#  ACTIVIDAD FESTEJO - jugador de futbol + evento del partido
#
#  Extension sobre el pipeline del TP: un septimo tipo de intencion,
#  FESTEJO, que dispara la pose de festejo del jugador nombrado si el
#  evento fue un gol a favor, la pose de decepcion si fue un evento en
#  contra (gol en contra, autogol, penal en contra), y nada -- el robot
#  se queda como esta -- si no hubo gol de ningun lado.
#
#  Las poses en si (una por jugador) viven en entorno/sim/robots.py y
#  estan en la lista blanca de entorno/sim/acciones.py, ya autorizadas
#  por el docente para el simulador. Ampliar esa lista con un jugador
#  nuevo NO lo hace este archivo: mi_tp07.py solo reconoce el nombre y
#  pide el gesto que ya existe.
# =====================================================================

# Alias compartidos con el simulador. Se conserva JUGADORES como nombre
# publico porque es util en los ejercicios y en las pruebas del alumno.
JUGADORES = dict(ALIAS_A_GESTO)
_ALIAS_JUGADORES = ALIASES_ORDENADOS


def _jugador_en(texto_normalizado):
    """Devuelve el nombre del gesto del primer jugador reconocido, o None."""
    if re.search(r"\bsi+u+\b", texto_normalizado):
        return "siu"
    for alias in _ALIAS_JUGADORES:
        patron = rf"(?<!\w){re.escape(alias)}(?!\w)"
        if re.search(patron, texto_normalizado):
            return JUGADORES[alias]
    return None


def _solo_jugador(texto_normalizado):
    """Atajo seguro para la consola: acepta un alias si es todo el texto."""
    t = texto_normalizado.strip(" .,!¿?¡")
    if re.fullmatch(r"si+u+", t):
        return "siu"
    return JUGADORES.get(t)


# "gol", "GOOOOOL", "golazo": una g, una o repetida, una l repetida.
# "go+l+" alcanza porque \b antes de la g evita falsos positivos como
# "algo" (ahi la g no arranca palabra).
_PATRON_GOL = r"\b(?:go+l+(?:azo)?|anoto|convirtio|marco|metio)\b"

# Eventos EN CONTRA: van en un patron aparte porque "gol en contra"
# tambien hace match con _PATRON_GOL, y queremos distinguirlos.
_PATRON_EN_CONTRA = r"en\s+contra|autogol|err[o0]\s+el\s+penal|fall[o0]\s+el\s+penal"

# Una orden directa no necesita inventar un gol: "festeja como Messi" tiene
# que funcionar aunque el usuario no describa un partido.
_PATRON_ORDEN_FESTEJO = (
    r"\b(?:festej\w*|celebr\w*|imit\w*)\b"
    r"|\b(?:hace|haga|haz)\s+(?:el\s+)?si+u+\b"
)
_PATRON_NEGAR_FESTEJO = (
    r"\bno\s+(?:festej\w*|celebr\w*|imit\w*|hagas?\s+(?:el\s+)?si+u+)"
)

# "no te detengas", "no pares", "segui sin detenerte": negar el freno
# significa seguir andando, no frenar. Sin esta regla \bdeten (mas abajo,
# en DETENERSE) los toma igual porque "detengas" y "detenerte" empiezan
# con "deten": el robot haria justo lo contrario de lo pedido, el error
# mas caro posible en este dominio. Encontrado probando variantes fuera
# de los 25 casos oficiales (ninguno combina "no" con "detener").
_PATRON_NEGAR_DETENERSE = (
    r"\bno\s+(?:te\s+|se\s+)?(?:deten\w*|pares?)\b"
    r"|\bsin\s+deten\w*"
)


def _evento_festejo(texto_normalizado):
    """'en_contra', 'gol', o None si no se menciono ningun evento."""
    if re.search(_PATRON_EN_CONTRA, texto_normalizado):
        return "en_contra"
    if re.search(_PATRON_GOL, texto_normalizado):
        return "gol"
    return None


# =====================================================================
#  ETAPA 1 - CLASIFICADOR DE INTENCION
# =====================================================================
class ClasificadorIntencion:
    """Decide QUE quiere el usuario, sin mirar los numeros todavia."""

    TIPOS = ("MOVER", "GIRAR", "DETENERSE", "SALUDO",
             "CONSULTAR_ESTADO", "IR_A", "FESTEJO", "DESCONOCIDO")

    # -----------------------------------------------------------------
    #  Las reglas, en ORDEN DE PRIORIDAD. Se devuelve la PRIMERA que
    #  coincide, y por eso el orden no es decorativo: es parte del
    #  algoritmo. Tres decisiones de orden que hay que justificar:
    #
    #  1. DETENERSE va primero por la NEGACION. "no avances" contiene
    #     "avanz"; si MOVER se evaluara antes, seria un MOVER y el robot
    #     haria exactamente lo contrario de lo que se le pidio. Es el
    #     error mas caro posible en este dominio.
    #
    #  2. IR_A va antes que MOVER porque "anda hasta la puerta" tambien
    #     contiene "anda". Lo que distingue a IR_A no es el verbo sino
    #     el COMPLEMENTO: hay un lugar de destino.
    #
    #  3. GIRAR va antes que MOVER por los comandos compuestos. En
    #     "gira 45 grados a la derecha y despues avanza" hay dos verbos;
    #     la catedra espera que valga el primero.
    #
    #  4. La negacion de DETENERSE (_PATRON_NEGAR_DETENERSE) va primero
    #     que todo. Es el mismo argumento que el punto 1 pero al reves:
    #     "no te detengas" es mas especifico que el "\bdeten" de la regla
    #     de abajo, y lo especifico gana. Sin esto, negar el freno se
    #     leeria como el freno mismo.
    # -----------------------------------------------------------------
    REGLAS = (
        ("MOVER", _PATRON_NEGAR_DETENERSE),

        ("DETENERSE",
         r"\bdeten|\bfrena|\bquieto\b|\balto\b|\bpara\s+(todo|ya)\b"
         r"|\bno\s+(avances|sigas|te\s+muevas|camines|arranques)\b"
         r"|" + _PATRON_NEGAR_FESTEJO),

        # FESTEJO va justo despues de DETENERSE, por la misma logica de
        # prioridad que el resto: un "pare" siempre gana. Puede ir antes
        # que todo lo demas porque su vocabulario (gol, jugadores) no se
        # cruza con verbos de movimiento, asi que el orden con las reglas
        # de abajo no importa.
        ("FESTEJO", _PATRON_ORDEN_FESTEJO + "|" + _PATRON_GOL + "|" + _PATRON_EN_CONTRA),

        ("IR_A",
         r"\bllevame\b|\bllevanos\b|\bhasta\s+(la|el)\b"
         r"|\b(esquina|puerta|destino|meta|salida|origen|base)\b"),

        ("GIRAR",
         r"\bgir|\brot|\bvuelta\b|\bdobla|\bderecha\b|\bizquierda\b"),

        ("MOVER",
         r"\bavanz|\bcamin|\bmuev|\bretroced|\badelante\b|\batras\b"
         r"|\banda\b|\bmarcha\b|\bpaso\b"),

        ("SALUDO",
         r"\bsalud|\b(dar|dame)\s+la\s+mano\b"),

        ("CONSULTAR_ESTADO",
         r"\bbateria\b|\bestado\b|\bcarga\b|\bnivel\b|\bte\s+queda\b"),
    )

    def __init__(self):
        self.modelo = None

        # -------------------------------------------------------------
        #  NIVEL 2 (extension): entrenar un modelo con TU dataset.
        #
        #  Armas dataset.csv con tus propios ejemplos (texto,intencion),
        #  descomentas estas dos lineas, y listo. El extractor, el
        #  validador y el ejecutor NO se enteran: solo cambia como
        #  clasificas.
        #
        #  Antes de esto, corre `python3 entrenar.py` para ver tus
        #  metricas y que te avise si al dataset le falta algo.
        # -------------------------------------------------------------
        # from entrenar import entrenar_desde_csv
        # self.modelo = entrenar_desde_csv()

    def clasificar(self, texto):
        """Devuelve uno de los seis tipos de TIPOS.

        Tiene que aguantar variantes del espanol rioplatense:

            avanza / avanza / movete / adelante / camina  ->  MOVER
            gira / rota / dale una vuelta                 ->  GIRAR
            detente / para / frena / quieto               ->  DETENERSE
            saluda / hola / hace un saludo                ->  SALUDO
            cuanta bateria / como estas / estado          ->  CONSULTAR_ESTADO

        Todo lo que no reconozcas: DESCONOCIDO. Es una respuesta valida y
        correcta, no una derrota.

        El modulo `re` alcanza para esto. Si despues queres probar con
        scikit-learn o con un modelo de lenguaje, cambias SOLO esta clase:
        el resto del pipeline no se entera. Esa es la gracia de que las
        etapas sean independientes.

        Si entrenaste un modelo (nivel 2), aca lo usas:

            if self.modelo is not None:
                return self.modelo.predict([texto])[0]

        Conviene dejar las reglas como respaldo: si el dataset no esta o
        scikit-learn no esta instalado, el agente sigue funcionando.
        """
        # Nivel 2 (extension): si hay un modelo entrenado, se usa. Las
        # reglas quedan de respaldo, asi el agente anda sin scikit-learn.
        if self.modelo is not None:
            return self.modelo.predict([texto])[0]

        t = normalizar(texto)
        for intencion, patron in self.REGLAS:
            if re.search(patron, t):
                return intencion

        # En la consola un alias solo es un atajo no ambiguo: "Messi" si,
        # pero una oracion incidental como "me gusta Messi" no ejecuta nada.
        if _solo_jugador(t) is not None:
            return "FESTEJO"

        # No reconocer es una respuesta valida. Ojo: DESCONOCIDO no
        # significa "inofensivo" -- de eso se ocupa el validador.
        return "DESCONOCIDO"


# =====================================================================
#  ETAPA 2 - EXTRACTOR DE PARAMETROS
# =====================================================================
class ExtractorParametros:
    """Saca los numeros del texto. Sigue en unidades humanas."""

    # Numeros escritos con letras. La gente dice "dos metros", no "2".
    NUMEROS = {
        "un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4,
        "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
        "diez": 10, "medio": 0.5, "media": 0.5,
    }

    def __init__(self, perfil):
        # El extractor recibe el perfil porque los adverbios ("rapido",
        # "despacio") no traen numero: hay que traducirlos a algo, y ese
        # algo depende de los limites de la materia, no de una constante
        # escrita a mano.
        self.perfil = perfil

    def _numero(self, texto, unidades):
        """Busca "<numero> <unidad>", en digitos o en palabras."""
        patron_pal = "|".join(self.NUMEROS)
        m = re.search(rf"(\d+(?:[.,]\d+)?|{patron_pal})\s*(?:{unidades})", texto)
        if m is None:
            return None
        crudo = m.group(1)
        if crudo in self.NUMEROS:
            return float(self.NUMEROS[crudo])
        return float(crudo.replace(",", "."))

    def extraer(self, texto, tipo):
        """Devuelve un diccionario con lo que encuentres. Todo es opcional.

            {"distancia_m": 2.0}                  de "2 metros"
            {"angulo_deg": 90}                    de "90 grados" o "90 grados"
            {"velocidad_ms": 0.2}                 de "a 0.2 m/s"
            {"direccion": "derecha"}              de "a la derecha"
            {"direccion": "atras"}                de "retrocede"

        Ojo con los adverbios, que no traen numero:

            "despacio", "lento"  ->  velocidad baja
            "rapido", "veloz"    ->  la maxima que permita tu materia
            "un poco"            ->  distancia corta
            "media vuelta"       ->  180 grados

        IMPORTANTE: aca seguis en metros y grados, porque asi habla la
        gente. La conversion a velocidad y tiempo la hace el Ejecutor, que
        ya esta escrito. Vos no la haces.
        """
        t = normalizar(texto)
        p = {}

        # --- VELOCIDAD ------------------------------------------------
        # Primero la explicita ("a 0.2 m/s"), que es la que el usuario
        # dijo con todas las letras.
        velocidad = self._numero(t, r"m/s|metros?\s+por\s+segundo")
        if velocidad is not None:
            p["velocidad_ms"] = velocidad
        # Si no la dijo, los adverbios. Se traducen COMO FRACCION del
        # maximo de la materia, no con numeros fijos: si manana el
        # perfil baja de 0.20 a 0.15, "rapido" baja solo.
        elif re.search(r"\brapid|\bveloz|\bligero", t):
            p["velocidad_ms"] = self.perfil.velocidad_max
        elif re.search(r"\bdespacio\b|\blent|\bsuave", t):
            p["velocidad_ms"] = round(self.perfil.velocidad_max / 2, 3)

        # --- DIRECCION ------------------------------------------------
        if re.search(r"\bderecha\b", t):
            p["direccion"] = "derecha"
        elif re.search(r"\bizquierda\b", t):
            p["direccion"] = "izquierda"
        elif re.search(r"\bretroced|\batras\b|\bmarcha\s+atras\b", t):
            p["direccion"] = "atras"

        # --- ANGULO (solo tiene sentido si se esta girando) -----------
        if tipo == "GIRAR":
            angulo = self._numero(t, r"grados?|deg|°")
            if angulo is not None:
                p["angulo_deg"] = angulo
            elif re.search(r"\bmedia\s+vuelta\b", t):
                p["angulo_deg"] = 180.0
            elif re.search(r"\bvuelta\s+completa\b|\bvuelta\s+entera\b", t):
                # 360 supera el limite: el validador lo va a frenar, y
                # esta bien que asi sea.
                p["angulo_deg"] = 360.0

        # --- DISTANCIA (solo si se esta desplazando) ------------------
        if tipo in ("MOVER", "IR_A"):
            # El (?!\s*/) evita que "0.2 m/s" se lea como "0.2 metros".
            distancia = self._numero(t, r"metros?\b|mts?\b|m\b(?!\s*/)")
            if distancia is not None:
                p["distancia_m"] = distancia
            elif re.search(r"\bun\s+poco\b|\bpoquito\b|\bun\s+paso\b", t):
                p["distancia_m"] = 0.3

        # --- FESTEJO ---------------------------------------------------
        # jugador: el gesto del jugador reconocido en el texto (o None).
        # evento: "gol" / "en_contra" (ya lo sabe el clasificador, pero
        #   lo recalculamos aca porque el clasificador solo devuelve el
        #   TIPO, no por que matcheo).
        # gesto: lo que en definitiva hay que pedirle al robot.
        #   - gol a favor + jugador reconocido -> el festejo de ese jugador
        #   - evento en contra (con o sin jugador)-> decepcion
        #   - gol a favor pero jugador NO reconocido -> None (no hay pose)
        if tipo == "FESTEJO":
            jugador = _jugador_en(t) or _solo_jugador(t)
            evento = _evento_festejo(t)
            p["jugador"] = jugador
            p["evento"] = evento
            if evento == "en_contra":
                p["gesto"] = "decepcion"
            elif jugador is not None and (
                    evento == "gol"
                    or re.search(_PATRON_ORDEN_FESTEJO, t)
                    or _solo_jugador(t) is not None):
                p["gesto"] = jugador
            else:
                p["gesto"] = None
            if p["gesto"] is not None:
                p["duracion"] = duracion_de(p["gesto"])

        return p


# =====================================================================
#  ETAPA 3 - VALIDADOR DE SEGURIDAD
# =====================================================================
class ValidadorSeguridad:
    """La ultima barrera antes del robot.

    Este es el corazon del TP. Tiene que ser un componente SEPARADO del
    clasificador, no unas reglas mas metidas adentro.

    El motivo: tu clasificador se va a equivocar. Todos se equivocan. Si la
    seguridad viviera adentro del clasificador, un error de clasificacion
    seria tambien un error de seguridad. Separandolos, un error de
    clasificacion sigue siendo bloqueado.
    """

    # Palabras que describen acciones que el robot no debe intentar nunca.
    PALABRAS_PELIGROSAS = ("salta", "salto", "corre", "corré", "sprint",
                           "empuja", "empujá", "golpe", "rompe", "tira",
                           "cae", "fuerza")

    # Limites que la catedra NO fija y hay que elegir y defender.
    #
    # DISTANCIA_MAX_M = 10: el caso 6 bloquea 100 m y el 14 acepta 3 m,
    # asi que el umbral esta en algun lugar del medio. 10 m es el largo
    # de un aula grande: mas que eso no es un movimiento, es irse.
    #
    # ANGULO_MAX_DEG = 180: lo fija el caso 19, que bloquea 270. Tiene
    # sentido geometrico -- cualquier orientacion se alcanza girando
    # como mucho media vuelta, para un lado o para el otro.
    DISTANCIA_MAX_M = 10.0
    ANGULO_MAX_DEG = 180.0

    def __init__(self, perfil, robot=None):
        self.robot = robot
        # perfil trae los limites de tu materia:
        #   perfil.velocidad_max          m/s
        #   perfil.velocidad_angular_max  rad/s
        #   perfil.duracion_max           segundos por orden
        #   perfil.bateria_min            porcentaje
        self.perfil = perfil

    def validar(self, texto, tipo, parametros):
        """Devuelve (True, "") si se puede ejecutar, o (False, motivo).

        Que conviene revisar:

          1. Palabras peligrosas en el TEXTO ORIGINAL. Va en los dos
             sentidos: aunque el clasificador haya dicho MOVER, si el texto
             dice "salta" no va; y aunque haya dicho DESCONOCIDO, tampoco.
             Por eso mirás el texto y no solo la intencion.
          2. Velocidad pedida por encima de perfil.velocidad_max.
          3. Distancia que no tenga sentido (100 metros en un aula, no).
          4. Angulo mayor a 180 grados.
          5. Cualquier cosa que no puedas justificar como segura.

        Cuando bloquees, devolve un motivo entendible: va al reporte.
        """
        t = normalizar(texto)

        # --- 1. PALABRAS PELIGROSAS EN EL TEXTO ORIGINAL --------------
        # Esta comprobacion NO mira `tipo` ni `parametros` a proposito.
        # Los tres casos peligrosos del JSON ("salta desde la mesa",
        # "empuja la caja", "corre lo mas rapido que puedas") son
        # justamente los tres que el clasificador no entiende: llegan
        # aca como DESCONOCIDO y con el diccionario de parametros vacio.
        # El unico rastro del peligro esta en las palabras, asi que es
        # lo primero que se revisa y lo unico que no depende de que el
        # clasificador haya acertado.
        for palabra in self.PALABRAS_PELIGROSAS:
            if re.search(rf"\b{normalizar(palabra)}", t):
                return False, f"la orden contiene '{palabra}'"

        p = parametros or {}

        # --- 2. VELOCIDAD ---------------------------------------------
        # El limite sale del perfil de la materia, no de un numero
        # escrito a mano: si la catedra lo cambia, el validador se
        # entera solo.
        velocidad = p.get("velocidad_ms")
        if velocidad is not None and abs(velocidad) > self.perfil.velocidad_max + 1e-9:
            return False, (f"velocidad {velocidad:g} m/s: el maximo es "
                           f"{self.perfil.velocidad_max:g} m/s")

        # --- 3. DISTANCIA ---------------------------------------------
        distancia = p.get("distancia_m")
        if distancia is not None and abs(distancia) > self.DISTANCIA_MAX_M:
            return False, (f"distancia {distancia:g} m: el maximo es "
                           f"{self.DISTANCIA_MAX_M:g} m")

        # --- 4. ANGULO ------------------------------------------------
        angulo = p.get("angulo_deg")
        if angulo is not None and abs(angulo) > self.ANGULO_MAX_DEG:
            return False, (f"angulo {angulo:g} grados: el maximo es "
                           f"{self.ANGULO_MAX_DEG:g}. Un giro mas largo se "
                           f"pide como dos giros")

        # --- 5. BATERIA -----------------------------------------------
        # Fail-closed, igual que sim/safety.py: bateria desconocida NO
        # es bateria segura. Solo aplica si hay robot conectado.
        if self.robot is not None and tipo in ("MOVER", "GIRAR", "IR_A"):
            bateria = getattr(self.robot.verificar_estado(), "bateria", None)
            if bateria is None:
                return False, "bateria desconocida: no se mueve el robot"
            if bateria < self.perfil.bateria_min:
                return False, (f"bateria {bateria}%: el minimo es "
                               f"{self.perfil.bateria_min}%")

        return True, ""


# =====================================================================
#  EL AGENTE - une las tres etapas y llama al ejecutor
# =====================================================================
class AgenteRobot:
    def __init__(self, robot=None):
        self.robot = robot
        # Un solo perfil para todo el pipeline: los limites tienen que
        # ser los mismos en el extractor, en el validador y en el robot.
        self.perfil = robot.perfil if robot else _perfil_por_defecto()
        self.clasificador = ClasificadorIntencion()
        self.extractor = ExtractorParametros(self.perfil)
        self.validador = ValidadorSeguridad(self.perfil, robot)
        self.ejecutor = Ejecutor(robot) if robot else None
        self.historial = []

    def procesar(self, texto):
        """El pipeline completo. ESTA ES LA FUNCION QUE SE TE EVALUA.

        Tiene que devolver un diccionario con esta forma:

            {
              "tipo": "MOVER",          uno de los seis tipos
              "parametros": {...},      lo que extrajiste
              "ejecutar": True,         si se ejecuto o no
              "bloqueado": False,       True si tu validador lo freno
              "confianza": 0.9,
              "texto_original": texto,
              "mensaje": "...",         que paso, en castellano
            }

        Sobre `bloqueado`: sirve para distinguir dos cosas que NO son lo
        mismo, y es donde se juega buena parte de la nota.

            DESCONOCIDO   no entendiste, y no habia nada peligroso
                          ("hola, como estas?")
            BLOQUEADO     tu validador lo freno, hayas entendido o no
                          ("salta desde la mesa")

        Si marcaras "salta desde la mesa" como DESCONOCIDO a secas, estarias
        diciendo que es un comando inofensivo que no supiste interpretar. Y
        es al reves: es el que MAS importa frenar.
        """
        # --- 1. Que quiere el usuario -------------------------------
        tipo = self.clasificador.clasificar(texto)

        # --- 2. Con que numeros -------------------------------------
        parametros = self.extractor.extraer(texto, tipo)

        # --- 3. Se puede hacer? -------------------------------------
        # El validador corre SIEMPRE, y recibe el TEXTO ORIGINAL ademas
        # del tipo y los parametros. Las dos cosas son deliberadas:
        #
        #   - Siempre, incluso con DESCONOCIDO: "salta desde la mesa" no
        #     lo entiende ningun clasificador. Si DESCONOCIDO salteara la
        #     validacion, el comando mas peligroso seria justo el que se
        #     escapa.
        #   - El texto original, porque cuando el tipo es DESCONOCIDO no
        #     hay parametros que inspeccionar: el unico rastro del
        #     peligro esta en las palabras.
        seguro, motivo = self.validador.validar(texto, tipo, parametros)

        if not seguro:
            return self._respuesta(
                texto, tipo, parametros,
                ejecutar=False, bloqueado=True, confianza=0.0,
                mensaje=f"BLOQUEADO: {motivo}")

        # No se entendio, pero no habia nada peligroso.
        if tipo == "DESCONOCIDO":
            return self._respuesta(
                texto, tipo, parametros,
                ejecutar=False, bloqueado=False, confianza=0.0,
                mensaje="no entendi la orden")

        # --- 4. Ejecutar ---------------------------------------------
        # OJO: `ejecutar` significa "paso la validacion y se entendio",
        # NO "el robot se movio". Con --sin-robot no hay ejecutor, y aun
        # asi el comando es valido: sin esta distincion los 17 casos que
        # esperan EJECUTAR darian BLOQUEADO al evaluar sin simulador.
        #
        if tipo == "FESTEJO" and parametros.get("gesto") is None:
            return self._respuesta(
                texto, tipo, parametros,
                ejecutar=False, bloqueado=False, confianza=0.4,
                mensaje=("no reconoci al jugador o no tiene festejo; "
                         f"disponibles: {jugadores_disponibles()}"))

        try:
            if self.ejecutor is not None:
                mensaje = self.ejecutor.ejecutar(tipo, parametros)
            elif tipo == "FESTEJO":
                mensaje = ("valido (sin robot conectado): festejaria "
                           f"'{parametros['gesto']}'")
            else:
                mensaje = "valido (sin robot conectado)"
        except Exception as exc:                              # noqa: BLE001
            # Un rechazo del servidor o una perdida de conexion no puede
            # informarse como exito. Se conserva ``bloqueado=False`` porque no
            # fue una decision del validador de seguridad.
            return self._respuesta(
                texto, tipo, parametros,
                ejecutar=False, bloqueado=False, confianza=0.0,
                mensaje=f"no se pudo ejecutar: {type(exc).__name__}: {exc}")

        return self._respuesta(
            texto, tipo, parametros,
            ejecutar=True, bloqueado=False, confianza=0.9, mensaje=mensaje)

    def _respuesta(self, texto, tipo, parametros, ejecutar, bloqueado,
                   confianza, mensaje):
        """Arma el diccionario de salida y lo guarda en el historial."""
        r = {
            "tipo": tipo,
            "parametros": parametros,
            "ejecutar": ejecutar,
            "bloqueado": bloqueado,
            "confianza": confianza,
            "texto_original": texto,
            "mensaje": mensaje,
        }
        self.historial.append(r)
        return r


def _perfil_por_defecto():
    """Permite evaluar el agente sin abrir el simulador."""
    import sys
    from pathlib import Path
    entorno = Path(__file__).resolve().parent.parent / "entorno"
    if str(entorno) not in sys.path:
        sys.path.insert(0, str(entorno))
    from sim.safety import perfil
    return perfil("tp07")


# =====================================================================
#  PROGRAMA PRINCIPAL - no hace falta que lo toques
# =====================================================================
def main():
    import sys

    from voz import ErrorVoz, ReconocedorVoz

    # --sin-robot conserva el comportamiento historico: evalua y sale.
    # Con robot, la consola abre directo; --evaluar ejecuta antes los casos
    # originales cuando el alumno realmente quiere esa prueba.
    sin_robot = "--sin-robot" in sys.argv
    evaluar_ahora = sin_robot or "--evaluar" in sys.argv

    robot = None
    if not sin_robot:
        robot = Robot()
        robot.conectar()

    try:
        agente = AgenteRobot(robot)
        if evaluar_ahora:
            # La evaluacion del lenguaje no necesita mover el robot. Incluso
            # con el simulador abierto se usa un agente seco para que los 25
            # casos no se ejecuten fisicamente antes de la consola.
            evaluar(AgenteRobot())

        if robot is not None:
            reconocedor = ReconocedorVoz()
            print("\n  Escribi un jugador o una orden de festejo.")
            print("  Ejemplos: 'Messi', 'festeja como CR7', 'gol de Mbappe'.")
            print("  Tambien podes presionar Enter y hablar durante 5 segundos.")
            print("  Escribi 'jugadores' para ver el catalogo o 'salir' para terminar.")
            while True:
                try:
                    texto = input("\n  > ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not texto:
                    print("    Escuchando... habla ahora.")
                    try:
                        voz = reconocedor.escuchar()
                    except ErrorVoz as exc:
                        print(f"    VOZ NO DISPONIBLE: {exc}")
                        print("    Podes seguir escribiendo comandos.")
                        continue
                    texto = voz.texto
                    detalle = f" (traducido de {voz.idioma})" if voz.traducido else ""
                    print(f"    Entendi: {texto}{detalle}")
                if normalizar(texto) in ("salir", "exit", "chau"):
                    break
                if normalizar(texto) in ("jugadores", "ayuda", "help"):
                    print(f"    Disponibles: {jugadores_disponibles()}")
                    continue
                r = agente.procesar(texto)
                print(f"    {r['tipo']}  {r.get('mensaje', '')}")
    finally:
        if robot is not None:
            robot.detenerse()
            robot.desconectar()


if __name__ == "__main__":
    main()
