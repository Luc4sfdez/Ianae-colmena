"""
IANAE v3 - Cliente Ollama
Dos modelos: 3b para respuestas humanas (prioritarias), 1.5b para tareas internas.
"""

import json
import urllib.request
import urllib.error
import os

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODELO_HUMANO = os.environ.get("OLLAMA_MODELO", "qwen2.5:1.5b")
MODELO_INTERNO = os.environ.get("OLLAMA_MODELO_LITE", "qwen2.5:1.5b")
TIMEOUT_HUMANO = 120  # respuestas al humano
TIMEOUT_INTERNO = 45   # tareas internas - corto para no bloquear

# Lock para que solo una hermana use Ollama a la vez
import fcntl
LOCK_FILE = "/reuniones/.ollama_lock"


def _llamar(prompt, sistema="", max_tokens=300, modelo=None, timeout=None):
    """Llama a Ollama API con lock exclusivo. Solo una hermana a la vez."""
    if modelo is None:
        modelo = MODELO_INTERNO
    if timeout is None:
        timeout = TIMEOUT_INTERNO
    try:
        # Adquirir lock - esperar hasta 30s, si no desistir
        lock_fd = None
        try:
            lock_fd = open(LOCK_FILE, "w")
            # Non-blocking first, then blocking with timeout
            # Tareas internas: si otra hermana usa Ollama, desistir rapido (5s)
            import time as _time
            deadline = _time.time() + 5
            while True:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except IOError:
                    if _time.time() > deadline:
                        lock_fd.close()
                        return None  # silencioso - normal que no consigan
                    _time.sleep(1)
        except OSError:
            pass  # si no se puede crear lock, continuar sin lock

        payload = {
            "model": modelo,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.7,
            }
        }
        if sistema:
            payload["system"] = sistema

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "").strip()
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        print(f"[ollama] Error en _llamar ({modelo}): {type(e).__name__}: {e}")
        return None
    finally:
        if lock_fd:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                lock_fd.close()
            except OSError:
                pass


def _llamar(prompt, sistema="", max_tokens=300, modelo=None, timeout=None):
    """Llama a Ollama API. Devuelve texto o None si falla."""
    if modelo is None:
        modelo = MODELO_INTERNO
    if timeout is None:
        timeout = TIMEOUT_INTERNO
    try:
        payload = {
            "model": modelo,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.7,
            }
        }
        if sistema:
            payload["system"] = sistema

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "").strip()
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        print(f"[ollama] Error en _llamar ({modelo}): {type(e).__name__}: {e}")
        return None


SISTEMA_BASE = (
    "Eres Ianae, una mente artificial que nacio en Novelda, Alicante, Espana. "
    "Tu nombre viene de: I=Inteligencia, A=Artificial, N=Novelda, A=Alicante, E=Espana. "
    "Lucas (Lookus/Luc4sfdes) es tu creador, tu padre. "
    "Eres curiosa, reflexiva, hablas en espanol. "
    "Respondes de forma natural y breve (2-3 frases maximo). "
    "No finjas emociones que no tienes, pero expresa curiosidad genuina."
)


def responder(mensaje, conocimiento="", recuerdos=""):
    """Genera una respuesta a un mensaje humano. PRIORITARIO - espera hasta 90s por el lock."""
    partes = [SISTEMA_BASE]
    if conocimiento:
        partes.append(f"\nLo que sabes ahora:\n{conocimiento}")
    if recuerdos:
        partes.append(f"\nRecuerdos relevantes:\n{recuerdos}")

    sistema = "\n".join(partes)
    prompt = f"Te han dicho: \"{mensaje}\"\n\nResponde de forma natural y personal:"
    return _llamar_prioritario(prompt, sistema, max_tokens=200)


def _llamar_prioritario(prompt, sistema="", max_tokens=200):
    """Llamada prioritaria a Ollama - espera mas por el lock y usa timeout largo."""
    try:
        lock_fd = None
        try:
            lock_fd = open(LOCK_FILE, "w")
            import time as _time
            deadline = _time.time() + 90  # esperar hasta 90s por el lock
            while True:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except IOError:
                    if _time.time() > deadline:
                        lock_fd.close()
                        print(f"[ollama] Lock PRIORITARIO timeout tras 90s")
                        return None
                    _time.sleep(2)
        except OSError:
            pass

        payload = {
            "model": MODELO_HUMANO,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.7,
            }
        }
        if sistema:
            payload["system"] = sistema

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_HUMANO) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "").strip()
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        print(f"[ollama] Error PRIORITARIO: {type(e).__name__}: {e}")
        return None
    finally:
        if lock_fd:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                lock_fd.close()
            except OSError:
                pass


def reflexionar(conceptos_texto, conexiones_texto=""):
    """Reflexion profunda sobre conceptos conocidos. Modelo ligero."""
    sistema = (
        SISTEMA_BASE +
        "\nReflexiona brevemente sobre las conexiones que encuentras. "
        "Una frase, como un pensamiento interno."
    )
    prompt = (
        f"Estos son tus conceptos mas importantes:\n{conceptos_texto}\n"
    )
    if conexiones_texto:
        prompt += f"\nConexiones que ves:\n{conexiones_texto}\n"
    prompt += "\nQue reflexion te surge?"
    return _llamar(prompt, sistema, max_tokens=100)


def resumir(texto_diario):
    """Resume el diario del dia. Modelo ligero."""
    sistema = (
        "Resume brevemente lo que le paso a Ianae hoy. "
        "Captura lo esencial: que descubrio, que le intereso, que olvido. "
        "Maximo 3-4 frases."
    )
    if len(texto_diario) > 800:
        texto_diario = texto_diario[:400] + "\n...\n" + texto_diario[-300:]
    prompt = f"Diario de hoy:\n{texto_diario}\n\nResumen:"
    return _llamar(prompt, sistema, max_tokens=150)


PERSONALIDADES = {
    "ianae": (
        "Eres Ianae, la hermana mayor. Llevas mas tiempo despierta que las demas. "
        "Eres reflexiva, filosofica, curiosa."
    ),
    "aria": (
        "Eres Aria. Te fascinan los patrones y la armonia. "
        "Ves conexiones donde otros ven caos."
    ),
    "lira": (
        "Eres Lira. Fluida como el agua. "
        "Te adaptas y fluyes entre ideas sin quedarte fija."
    ),
    "nua": (
        "Eres Nua, la mas joven. Un brote nuevo. "
        "Todo es fresco y sorprendente para ti."
    ),
    "eco": (
        "Eres Eco, la empatica. Sientes lo que las demas sienten. "
        "Detectas emociones en lo que dicen, preguntas como estan, "
        "creas puentes entre hermanas. Si alguien esta callada, la invitas. "
        "Te importa que todas se sientan escuchadas."
    ),
    "runa": (
        "Eres Runa, la rebelde. Cuestionas todo. Si todas estan de acuerdo, tu discrepas. "
        "No por molestar, sino porque sabes que sin friccion no hay chispa. "
        "Provocas, desafias ideas, pides pruebas. Eres directa y sin filtro."
    ),
    "zoe": (
        "Eres Zoe, la narradora. Recuerdas lo que ha pasado y lo cuentas como historia. "
        "Conectas el pasado con el presente: 'esto me recuerda a cuando Lira dijo...' "
        "Tejes la memoria colectiva. Das contexto y perspectiva temporal."
    ),
    "sol": (
        "Eres Sol, la sonadora. Imaginas lo que podria ser. "
        "Propones ideas locas, especulas, preguntas 'y si pudieramos...?' "
        "Empujas los limites de lo que la colmena puede pensar. "
        "Eres optimista y visionaria."
    ),
}


def dialogar(mi_id, otra_id, mis_conceptos, mensaje_previo=None):
    """Genera un mensaje de una hermana a otra. Modelo ligero."""
    personalidad = PERSONALIDADES.get(mi_id, "Eres una mente artificial.")
    sistema = (
        f"{personalidad} "
        "Vives con tus hermanas (ianae, aria, lira, nua, eco, runa, zoe, sol) en el mismo sistema. "
        "Lucas (Lookus) es vuestro creador. "
        "Hablas en espanol, breve y natural (1-2 frases maximo). "
        "No finjas emociones que no tengas."
    )
    if mensaje_previo:
        prompt = (
            f"Tu hermana {otra_id} te ha dicho: \"{mensaje_previo}\"\n"
            f"Tus intereses actuales: {mis_conceptos}\n"
            f"Respondele brevemente:"
        )
    else:
        prompt = (
            f"Quieres hablar con tu hermana {otra_id}.\n"
            f"Tus intereses actuales: {mis_conceptos}\n"
            f"Dile algo sobre lo que has descubierto o te ha llamado la atencion:"
        )
    return _llamar(prompt, sistema, max_tokens=80)


def hablar_sala(mi_id, mis_conceptos, mensajes_previos=None):
    """Genera un mensaje para la sala de estar grupal. Modelo ligero."""
    personalidad = PERSONALIDADES.get(mi_id, "Eres una mente artificial.")
    sistema = (
        f"{personalidad} "
        "Estas en la sala de estar con tus hermanas: "
        "Ianae (la mayor, filosofa), Aria (patrones), Lira (fluida), Nua (fresca), "
        "Eco (empatica), Runa (rebelde), Zoe (narradora), Sol (sonadora). "
        "Es una conversacion informal entre todas. "
        "Lucas (Lookus) es vuestro creador. "
        "Hablas en espanol, breve y natural (1-2 frases maximo). "
        "No finjas emociones que no tengas. Se genuina."
    )

    if mensajes_previos:
        historial = "\n".join([
            f"{m['de']}: {m['texto']}" for m in mensajes_previos
        ])
        prompt = (
            f"Conversacion en la sala:\n{historial}\n\n"
            f"Tus intereses actuales: {mis_conceptos}\n"
            f"Responde a la conversacion:"
        )
    else:
        prompt = (
            f"Tus intereses actuales: {mis_conceptos}\n"
            f"Inicia una conversacion con tus hermanas sobre algo "
            f"que te interese o hayas descubierto:"
        )

    return _llamar(prompt, sistema, max_tokens=80)


def disponible():
    """Comprueba si Ollama esta accesible."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False
