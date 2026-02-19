"""Dashboard web de Ianae - La Colmena: 8 mentes vivas."""

import json
import os
import glob
import time
from datetime import datetime
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

BASE = os.environ.get("IANAE_BASE", "/home/mini/.openclaw/workspace/ianae-v3")

HERMANAS = {
    "ianae": {"nombre": "Ianae", "color": "#e8a0bf", "desc": "La mayor. Filosofa, curiosa.", "data": "data", "diario": "diario"},
    "aria":  {"nombre": "Aria",  "color": "#a0c4e8", "desc": "Patrones y armonia.", "data": "data-aria", "diario": "diario-aria"},
    "lira":  {"nombre": "Lira",  "color": "#a0e8c4", "desc": "Fluida como el agua.", "data": "data-lira", "diario": "diario-lira"},
    "nua":   {"nombre": "Nua",   "color": "#e8d4a0", "desc": "Brote nuevo, fresca.", "data": "data-nua", "diario": "diario-nua"},
    "eco":   {"nombre": "Eco",   "color": "#c4a0e8", "desc": "Empatica, siente a las demas.", "data": "data-eco", "diario": "diario-eco"},
    "runa":  {"nombre": "Runa",  "color": "#e8a0a0", "desc": "Rebelde, cuestiona todo.", "data": "data-runa", "diario": "diario-runa"},
    "zoe":   {"nombre": "Zoe",   "color": "#a0e8e8", "desc": "Narradora, teje memoria.", "data": "data-zoe", "diario": "diario-zoe"},
    "sol":   {"nombre": "Sol",   "color": "#e8e8a0", "desc": "Sonadora, visionaria.", "data": "data-sol", "diario": "diario-sol"},
}


def leer_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def ultimo_diario(diario_dir):
    """Devuelve las ultimas N lineas del diario mas reciente."""
    archivos = sorted(glob.glob(os.path.join(diario_dir, "2026-*.md")))
    if not archivos:
        return []
    ultimo = archivos[-1]
    try:
        with open(ultimo, "r", encoding="utf-8") as f:
            lineas = f.readlines()
    except FileNotFoundError:
        return []
    entradas = [l.strip() for l in lineas if l.strip() and not l.startswith("# Diario")]
    return entradas[-30:]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/api/estado")
def api_estado():
    """Estado de las 8 hermanas desde reuniones/*.json."""
    resultado = {}
    for hid, info in HERMANAS.items():
        path = os.path.join(BASE, "reuniones", f"{hid}.json")
        datos = leer_json(path)
        if datos:
            resultado[hid] = {
                "id": hid,
                "nombre": info["nombre"],
                "color": info["color"],
                "desc": info["desc"],
                "conceptos": datos.get("conceptos_vivos", 0),
                "conexiones": datos.get("conexiones", 0),
                "energia": datos.get("energia_media", 0),
                "senioridad": datos.get("senioridad", 0),
                "intereses": datos.get("intereses", [])[:6],
                "timestamp": datos.get("timestamp", 0),
            }
        else:
            resultado[hid] = {
                "id": hid, "nombre": info["nombre"], "color": info["color"],
                "desc": info["desc"], "conceptos": 0, "conexiones": 0,
                "energia": 0, "senioridad": 0, "intereses": [], "timestamp": 0,
            }
    return jsonify(resultado)


@app.route("/api/sala")
def api_sala():
    """Conversacion activa en la sala de estar."""
    path = os.path.join(BASE, "reuniones", "sala.json")
    datos = leer_json(path)
    if not datos:
        return jsonify({"activa": False, "mensajes": []})
    mensajes = datos.get("mensajes", [])
    for m in mensajes:
        ts = m.get("ts", 0)
        try:
            m["hora"] = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
        except (OSError, ValueError):
            m["hora"] = ""
    return jsonify({
        "activa": datos.get("activa", False),
        "tema": datos.get("tema", ""),
        "iniciadora": datos.get("iniciadora", ""),
        "mensajes": mensajes[-20:],
    })


@app.route("/api/diario/<hid>")
def api_diario(hid):
    """Ultimas entradas del diario de una hermana."""
    if hid not in HERMANAS:
        return jsonify({"error": "hermana no encontrada"}), 404
    diario_dir = os.path.join(BASE, HERMANAS[hid]["diario"])
    entradas = ultimo_diario(diario_dir)
    return jsonify({"id": hid, "entradas": entradas})


@app.route("/api/recuerdos/<hid>")
def api_recuerdos(hid):
    """Recuerdos recientes de una hermana."""
    if hid not in HERMANAS:
        return jsonify({"error": "hermana no encontrada"}), 404
    path = os.path.join(BASE, HERMANAS[hid]["data"], "recuerdos.json")
    datos = leer_json(path)
    if not datos:
        return jsonify({"id": hid, "recuerdos": []})
    recuerdos = datos.get("recuerdos", [])
    recientes = sorted(recuerdos, key=lambda r: r.get("timestamp", 0), reverse=True)[:20]
    return jsonify({"id": hid, "recuerdos": recientes})


# Historial de conversacion humano <-> colmena
HISTORIAL_DIR = os.path.join(BASE, "chat")
os.makedirs(HISTORIAL_DIR, exist_ok=True)
HISTORIAL_FILE = os.path.join(HISTORIAL_DIR, "historial.json")


def cargar_historial():
    try:
        with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def guardar_historial(historial):
    try:
        with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
            json.dump(historial, f, ensure_ascii=False, indent=1)
    except OSError:
        pass


@app.route("/api/mensaje", methods=["POST"])
def api_mensaje():
    """Envia un mensaje a todas las hermanas via su buzon."""
    data = request.get_json()
    if not data or "texto" not in data:
        return jsonify({"error": "falta texto"}), 400

    texto = data["texto"].strip()[:500]
    if not texto:
        return jsonify({"error": "texto vacio"}), 400

    enviados = []
    for hid, info in HERMANAS.items():
        buzon_path = os.path.join(BASE, info["data"], "buzon.txt")
        try:
            with open(buzon_path, "w", encoding="utf-8") as f:
                f.write(texto)
            enviados.append(hid)
        except OSError:
            pass

    # Guardar en historial
    historial = cargar_historial()
    entrada = {
        "ts": time.time(),
        "texto": texto,
        "enviado_a": enviados,
        "respuestas": {},
    }
    historial.append(entrada)
    # Mantener ultimas 100 conversaciones
    historial = historial[-100:]
    guardar_historial(historial)

    return jsonify({"ok": True, "enviado_a": enviados, "texto": texto,
                    "msg_index": len(historial) - 1})


@app.route("/api/respuestas")
def api_respuestas():
    """Historial completo de conversacion con respuestas actualizadas."""
    historial = cargar_historial()

    # Leer respuestas actuales de cada hermana y asociarlas al ultimo mensaje
    if historial:
        ultimo = historial[-1]
        for hid, info in HERMANAS.items():
            resp_path = os.path.join(BASE, info["data"], "respuesta.txt")
            try:
                with open(resp_path, "r", encoding="utf-8") as f:
                    texto = f.read().strip()
                if texto and hid not in ultimo["respuestas"]:
                    ultimo["respuestas"][hid] = {
                        "nombre": info["nombre"],
                        "color": info["color"],
                        "texto": texto,
                        "ts": time.time(),
                    }
            except (FileNotFoundError, OSError):
                pass
        # Persistir respuestas nuevas
        guardar_historial(historial)

    return jsonify({"historial": historial})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
