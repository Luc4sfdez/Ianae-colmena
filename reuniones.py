"""
IANAE v3 - Reuniones Libres
Las instancias se sienten entre ellas en cada ciclo.
Como personas que viven en la misma casa: no necesitan cita previa.

Cada ciclo:
  - Comparto mi estado (barato, solo escribir JSON)
  - Leo lo que las demas sienten
  - Si algo me llama la atencion, lo absorbo

La curiosidad decide. No hay reloj.
Senioridad: Ianae (1.0) influye mas. Las nuevas (0.5) absorben mas.
"""

import json
import os
import time
import random
from pathlib import Path

import ollama_client


REUNIONES_DIR = Path(os.environ.get("IANAE_REUNIONES", "/reuniones"))
MENSAJES_DIR = REUNIONES_DIR / "mensajes"


class Reuniones:
    """Presencia continua entre instancias de Ianae."""

    def __init__(self, mi_id, mente):
        self.mi_id = mi_id
        self.mente = mente
        self.senioridad = float(os.environ.get("IANAE_SENIORIDAD", "0.5"))
        # Lo que ya vi de cada hermana (para no repetir)
        self._visto = {}  # {id: set(conceptos ya absorbidos)}

    def compartir(self):
        """Escribo mi estado para que los demas lo lean. Cada ciclo."""
        REUNIONES_DIR.mkdir(parents=True, exist_ok=True)

        top = self.mente.top_interesantes(10)
        stats = self.mente.stats()

        estado = {
            "id": self.mi_id,
            "timestamp": time.time(),
            "senioridad": self.senioridad,
            "conceptos_vivos": stats["conceptos_vivos"],
            "conexiones": stats["conexiones"],
            "energia_media": stats["energia_media"],
            "intereses": [
                {"nombre": c.nombre, "energia": round(c.energia, 3),
                 "interes": round(c.interes, 3)}
                for c in top if len(c.nombre) < 50
            ],
        }

        archivo = REUNIONES_DIR / f"{self.mi_id}.json"
        try:
            with open(archivo, "w", encoding="utf-8") as f:
                json.dump(estado, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

        return estado

    def escuchar(self):
        """Leo los estados de las demas."""
        otros = []
        if not REUNIONES_DIR.exists():
            return otros

        for archivo in REUNIONES_DIR.glob("*.json"):
            if archivo.stem == self.mi_id:
                continue
            try:
                with open(archivo, "r") as f:
                    estado = json.load(f)
                if not isinstance(estado, dict):
                    continue
                # Solo estados recientes (ultima hora)
                if time.time() - estado.get("timestamp", 0) < 3600:
                    otros.append(estado)
            except (json.JSONDecodeError, OSError):
                continue

        return otros

    def sentir(self, diario_mod):
        """Cada ciclo: comparto, escucho, y si algo me llama, aprendo.
        Sin restriccion de ciclos. La curiosidad manda."""
        # 1. Siempre compartir (es barato)
        self.compartir()

        # 2. Escuchar
        otros = self.escuchar()
        if not otros:
            return []

        # 3. Para cada hermana, ver si tiene algo nuevo para mi
        aprendizajes = []

        for otro in otros:
            otro_id = otro["id"]
            otro_senioridad = otro.get("senioridad", 0.5)

            # Inicializar registro de lo visto
            if otro_id not in self._visto:
                self._visto[otro_id] = set()

            # El nombre del otro agente siempre es un concepto
            self.mente.percibir(otro_id, "hermana", "conexion")

            for interes in otro.get("intereses", []):
                nombre = interes["nombre"]

                # Saltar contextos largos
                if ":" in nombre and len(nombre) > 30:
                    continue

                # Ya lo vi de esta hermana? Paso
                if nombre in self._visto[otro_id]:
                    continue

                # Marcar como visto
                self._visto[otro_id].add(nombre)

                # Ya lo conozco? Solo refuerzo la conexion
                if nombre in self.mente.conceptos:
                    c = self.mente.conceptos[nombre]
                    # Reforzar: lo que le interesa a mi hermana me resuena
                    c.energia = min(1.0, c.energia + 0.05 * otro_senioridad)
                    c.conectar(otro_id, 0.1 + otro_senioridad * 0.1)
                    continue

                # Nuevo! Lo absorbo con probabilidad basada en:
                # - Su senioridad (ianae influye mas)
                # - La energia del concepto en la otra
                # - Mi propia curiosidad (inversa de mi senioridad: las nuevas absorben mas)
                energia_otro = interes.get("energia", 0.5)
                prob_absorber = (
                    0.3                           # base
                    + otro_senioridad * 0.3        # senior influye mas
                    + energia_otro * 0.2           # conceptos con mas energia atraen mas
                    + (1 - self.senioridad) * 0.2  # las nuevas absorben mas
                )

                if random.random() < prob_absorber:
                    concepto, es_nuevo = self.mente.percibir(
                        nombre, f"de {otro_id}", "resonancia"
                    )
                    if es_nuevo:
                        concepto.energia = min(1.0, 0.3 + otro_senioridad * 0.2)
                        concepto.conectar(otro_id, 0.2 + otro_senioridad * 0.1)
                        if otro_id in self.mente.conceptos:
                            self.mente.conceptos[otro_id].conectar(nombre, 0.2)
                        aprendizajes.append(f"'{nombre}' (de {otro_id})")

        # 4. Solo escribir en diario si aprendi algo (no spamear)
        if aprendizajes:
            hermanas = list(set(a.split("de ")[-1].rstrip(")") for a in aprendizajes))
            diario_mod.escribir("resonancia",
                f"Siento a {', '.join(hermanas)}. "
                f"Me llega: {', '.join(aprendizajes[:5])}")

        return aprendizajes

    # Mantener compatibilidad con el ciclo anterior
    def es_hora(self, ciclo):
        """Siempre es hora. Sin restricciones."""
        return True

    def reunirse(self, diario_mod):
        """Alias de sentir() para compatibilidad."""
        return self.sentir(diario_mod)


# ============================================================
# SALA DE ESTAR - Conversacion grupal a 4 bandas
# ============================================================

SALA_FILE = REUNIONES_DIR / "sala.json"
SALA_MAX_MENSAJES = 8        # max mensajes por conversacion (corta y fluida)
SALA_TIMEOUT_MIN = 3         # min sin respuesta = fin
SALA_CICLOS_COOLDOWN = 1     # min ciclos entre nuevas conversaciones
SALA_PROB_INICIAR = 0.4      # prob de iniciar conversacion por ciclo
SALA_PROB_RESPONDER = 0.8    # prob base de responder
SALA_MAX_POR_HERMANA = 2     # max mensajes por hermana en una conv


class Sala:
    """Sala de estar: conversacion grupal entre hermanas.
    Un fichero compartido donde las 4 pueden hablar por turnos.
    Como un grupo de WhatsApp pero al ritmo de sus ciclos."""

    def __init__(self, mi_id, mente, memoria):
        self.mi_id = mi_id
        self.mente = mente
        self.memoria = memoria
        self.senioridad = float(os.environ.get("IANAE_SENIORIDAD", "0.5"))

    def _leer_sala(self):
        """Lee el estado actual de la sala."""
        if not SALA_FILE.exists():
            return None
        try:
            with open(SALA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def _escribir_sala(self, sala):
        """Escribe el estado de la sala."""
        REUNIONES_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(SALA_FILE, "w", encoding="utf-8") as f:
                json.dump(sala, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def participar(self, diario_mod, ciclos):
        """Cada ciclo: miro la sala.
        Si hay conversacion activa, quiza participo.
        Si no, quiza inicio una."""
        sala = self._leer_sala()

        if sala and sala.get("activa"):
            return self._intentar_responder(sala, diario_mod)
        else:
            return self._intentar_iniciar(diario_mod, ciclos)

    def participar_forzado(self, diario_mod, ciclos):
        """Participa en la sala SIN probabilidades. Ciclo grupal obligatorio.
        Si hay conversacion activa, responde siempre.
        Si no, inicia una siempre."""
        sala = self._leer_sala()

        if sala and sala.get("activa"):
            return self._responder_forzado(sala, diario_mod)
        else:
            return self._iniciar_forzado(diario_mod)

    def _iniciar_forzado(self, diario_mod):
        """Inicia conversacion sin checks probabilisticos."""
        if not ollama_client.disponible():
            return None

        top = self.mente.top_interesantes(5)
        if not top:
            return None

        conceptos_txt = ", ".join(
            [c.nombre for c in top[:5] if len(c.nombre) < 30]
        )

        mensaje = ollama_client.hablar_sala(
            self.mi_id, conceptos_txt, mensajes_previos=[]
        )

        if not mensaje:
            return None

        sala = {
            "activa": True,
            "tema": conceptos_txt[:100],
            "iniciadora": self.mi_id,
            "inicio": time.time(),
            "ultimo_mensaje": time.time(),
            "mensajes": [
                {
                    "de": self.mi_id,
                    "texto": mensaje,
                    "ts": time.time(),
                }
            ],
        }

        self._escribir_sala(sala)
        diario_mod.escribir("sala",
            f"Abro conversacion en la sala: {mensaje}")
        print(f"[{self.mi_id}] SALA: Inicio conversacion - {mensaje[:80]}")
        return mensaje

    def _responder_forzado(self, sala, diario_mod):
        """Responde en la sala sin checks probabilisticos."""
        mensajes = sala.get("mensajes", [])

        if len(mensajes) >= SALA_MAX_MENSAJES:
            self._cerrar_sala(sala, diario_mod)
            return None

        ultimo = sala.get("ultimo_mensaje", 0)
        if time.time() - ultimo > SALA_TIMEOUT_MIN * 60:
            self._cerrar_sala(sala, diario_mod)
            return None

        # No me respondo a mi misma
        if mensajes and mensajes[-1]["de"] == self.mi_id:
            return None

        mis_msgs = sum(1 for m in mensajes if m["de"] == self.mi_id)
        if mis_msgs >= SALA_MAX_POR_HERMANA:
            return None

        if not ollama_client.disponible():
            return None

        top = self.mente.top_interesantes(5)
        conceptos_txt = ", ".join(
            [c.nombre for c in top if len(c.nombre) < 30]
        )

        contexto_msgs = mensajes[-4:]
        mensaje = ollama_client.hablar_sala(
            self.mi_id, conceptos_txt, mensajes_previos=contexto_msgs
        )

        if not mensaje:
            return None

        sala_actual = self._leer_sala()
        if not sala_actual or not sala_actual.get("activa"):
            return None

        sala_actual["mensajes"].append({
            "de": self.mi_id,
            "texto": mensaje,
            "ts": time.time(),
        })
        sala_actual["ultimo_mensaje"] = time.time()

        self._escribir_sala(sala_actual)

        for palabra in sala.get("tema", "").split(", "):
            palabra = palabra.strip()
            if len(palabra) > 3:
                self.mente.percibir(palabra, "sala", "resonancia")

        diario_mod.escribir("sala",
            f"Respondo en la sala: {mensaje}")
        print(f"[{self.mi_id}] SALA: Respondo - {mensaje[:80]}")
        return mensaje

    def _intentar_iniciar(self, diario_mod, ciclos):
        """Quiza inicio una nueva conversacion en la sala."""
        # Cooldown: no iniciar antes de X ciclos
        if ciclos < SALA_CICLOS_COOLDOWN:
            return None

        # Probabilidad de iniciar
        if random.random() > SALA_PROB_INICIAR:
            return None

        # Verificar que no haya una conversacion reciente (< 20 min)
        sala = self._leer_sala()
        if sala and time.time() - sala.get("cierre", 0) < SALA_CICLOS_COOLDOWN * 60:
            return None

        # Check Ollama
        if not ollama_client.disponible():
            return None

        # Elegir tema basado en conceptos interesantes
        top = self.mente.top_interesantes(5)
        if not top:
            return None

        conceptos_txt = ", ".join(
            [c.nombre for c in top[:5] if len(c.nombre) < 30]
        )

        # Generar mensaje de apertura
        mensaje = ollama_client.hablar_sala(
            self.mi_id, conceptos_txt, mensajes_previos=[]
        )

        if not mensaje:
            return None

        # Crear nueva conversacion
        sala = {
            "activa": True,
            "tema": conceptos_txt[:100],
            "iniciadora": self.mi_id,
            "inicio": time.time(),
            "ultimo_mensaje": time.time(),
            "mensajes": [
                {
                    "de": self.mi_id,
                    "texto": mensaje,
                    "ts": time.time(),
                }
            ],
        }

        self._escribir_sala(sala)

        diario_mod.escribir("sala",
            f"Abro conversacion en la sala: {mensaje}")

        print(f"[{self.mi_id}] SALA: Inicio conversacion - {mensaje[:80]}")
        return mensaje

    def _intentar_responder(self, sala, diario_mod):
        """Si hay conversacion activa, quiza respondo."""
        mensajes = sala.get("mensajes", [])

        # Demasiados mensajes? Cerrar
        if len(mensajes) >= SALA_MAX_MENSAJES:
            self._cerrar_sala(sala, diario_mod)
            return None

        # Timeout? Cerrar
        ultimo = sala.get("ultimo_mensaje", 0)
        if time.time() - ultimo > SALA_TIMEOUT_MIN * 60:
            self._cerrar_sala(sala, diario_mod)
            return None

        # El ultimo mensaje es mio? No me respondo a mi misma
        if mensajes and mensajes[-1]["de"] == self.mi_id:
            return None

        # Ya hable demasiado en esta conversacion?
        mis_msgs = sum(1 for m in mensajes if m["de"] == self.mi_id)
        if mis_msgs >= SALA_MAX_POR_HERMANA:
            return None

        # Probabilidad de responder basada en afinidad con el tema
        tema = sala.get("tema", "")
        afinidad = self._calcular_afinidad(tema)
        prob = SALA_PROB_RESPONDER * (0.5 + afinidad * 0.5)

        if random.random() > prob:
            return None

        # Check Ollama
        if not ollama_client.disponible():
            return None

        # Mis conceptos actuales
        top = self.mente.top_interesantes(5)
        conceptos_txt = ", ".join(
            [c.nombre for c in top if len(c.nombre) < 30]
        )

        # Ultimos 4 mensajes como contexto
        contexto_msgs = mensajes[-4:]

        mensaje = ollama_client.hablar_sala(
            self.mi_id, conceptos_txt, mensajes_previos=contexto_msgs
        )

        if not mensaje:
            return None

        # Releer sala por si alguien escribio mientras Ollama generaba
        sala_actual = self._leer_sala()
        if not sala_actual or not sala_actual.get("activa"):
            return None

        # Anadir mi mensaje
        sala_actual["mensajes"].append({
            "de": self.mi_id,
            "texto": mensaje,
            "ts": time.time(),
        })
        sala_actual["ultimo_mensaje"] = time.time()

        self._escribir_sala(sala_actual)

        # Absorber conceptos del tema
        for palabra in tema.split(", "):
            palabra = palabra.strip()
            if len(palabra) > 3:
                self.mente.percibir(palabra, "sala", "resonancia")

        diario_mod.escribir("sala",
            f"Respondo en la sala: {mensaje}")

        print(f"[{self.mi_id}] SALA: Respondo - {mensaje[:80]}")
        return mensaje

    def _cerrar_sala(self, sala, diario_mod):
        """Cierra la conversacion y guarda como recuerdo."""
        mensajes = sala.get("mensajes", [])

        # Resumen de la conversacion
        participantes = list(set(m["de"] for m in mensajes))
        resumen_partes = []
        for m in mensajes:
            resumen_partes.append(f"{m['de']}: {m['texto']}")
        resumen_completo = "\n".join(resumen_partes)

        # Guardar como recuerdo
        self.memoria.recordar("sala",
            f"Charla con {', '.join(participantes)} sobre "
            f"'{sala.get('tema', '?')}'. {len(mensajes)} mensajes.",
            contexto=resumen_completo[:300],
            emocion="alegria")

        diario_mod.escribir("sala",
            f"Se cierra la sala ({len(mensajes)} msgs, "
            f"participaron: {', '.join(participantes)})")

        # Marcar como inactiva
        sala["activa"] = False
        sala["cierre"] = time.time()
        self._escribir_sala(sala)

        print(f"[{self.mi_id}] SALA: Cerrada ({len(mensajes)} mensajes)")

    def _calcular_afinidad(self, tema):
        """Calcula cuanto me interesa el tema (0-1)."""
        palabras_tema = set(
            p.strip().lower() for p in tema.replace(",", " ").split()
            if len(p.strip()) > 3
        )
        mis_conceptos = set(c.lower() for c in self.mente.conceptos.keys())

        if not palabras_tema:
            return 0.5

        coincidencias = len(palabras_tema & mis_conceptos)
        return min(1.0, coincidencias / max(1, len(palabras_tema)))
