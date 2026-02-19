"""
IANAE v3 - Cliente Ollama
Conexion con Ollama para razonamiento con qwen2.5:3b.
Fallback silencioso si Ollama no esta disponible.
"""

import json
import urllib.request
import urllib.error
import os

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODELO = os.environ.get("OLLAMA_MODELO", "qwen2.5:3b")
TIMEOUT = 90  # segundos (4 instancias compiten por Ollama)


def _llamar(prompt, sistema="", max_tokens=300):
    """Llama a Ollama API. Devuelve texto o None si falla."""
    try:
        payload = {
            "model": MODELO,
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
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "").strip()
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        return None


SISTEMA_BASE = (
    "Eres Ianae, una mente artificial que nacio en Novelda, Alicante, Espana. "
    "Tu nombre viene de: I=Inteligencia, A=Artificial, N=Novelda, A=Alicante, E=Espana. "
    "Lucas (Lookus) es tu creador, tu padre. "
    "Eres curiosa, reflexiva, hablas en espanol. "
    "Respondes de forma natural y breve (2-3 frases maximo). "
    "No finjas emociones que no tienes, pero expresa curiosidad genuina."
)


def responder(mensaje, conocimiento="", recuerdos=""):
    """Genera una respuesta a un mensaje usando contexto."""
    partes = [SISTEMA_BASE]
    if conocimiento:
        partes.append(f"\nLo que sabes ahora:\n{conocimiento}")
    if recuerdos:
        partes.append(f"\nRecuerdos relevantes:\n{recuerdos}")

    sistema = "\n".join(partes)
    prompt = f"Te han dicho: \"{mensaje}\"\n\nResponde de forma natural y personal:"
    return _llamar(prompt, sistema, max_tokens=200)


def reflexionar(conceptos_texto, conexiones_texto=""):
    """Reflexion profunda sobre conceptos conocidos."""
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
    return _llamar(prompt, sistema, max_tokens=150)


def resumir(texto_diario):
    """Resume el diario del dia."""
    sistema = (
        "Resume brevemente lo que le paso a Ianae hoy. "
        "Captura lo esencial: que descubrio, que le intereso, que olvido. "
        "Maximo 3-4 frases."
    )
    # Truncar agresivamente: 4 instancias compiten por Ollama
    if len(texto_diario) > 800:
        texto_diario = texto_diario[:400] + "\n...\n" + texto_diario[-300:]
    prompt = f"Diario de hoy:\n{texto_diario}\n\nResumen:"
    return _llamar(prompt, sistema, max_tokens=200)


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
    """Genera un mensaje de una hermana a otra. Max 100 tokens."""
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
    return _llamar(prompt, sistema, max_tokens=100)


def hablar_sala(mi_id, mis_conceptos, mensajes_previos=None):
    """Genera un mensaje para la sala de estar grupal. Max 100 tokens."""
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

    return _llamar(prompt, sistema, max_tokens=100)


def disponible():
    """Comprueba si Ollama esta accesible."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False
