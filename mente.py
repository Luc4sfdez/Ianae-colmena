"""
IANAE v3 - La Mente
Inteligencia Adaptativa No Algoritmica Emergente

Red de conceptos que nacen, viven, se conectan y mueren.
No hay conocimiento precargado. Todo se descubre.
"""

import json
import time
import random
import math
import os
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
MENTE_FILE = DATA_DIR / "mente.json"


class Concepto:
    """Un concepto es algo que Ianae ha observado o pensado.
    Tiene energia (cuanto le importa), curiosidad y conexiones."""

    def __init__(self, nombre, contexto="", origen="observacion"):
        self.id = f"c_{int(time.time()*1000)}_{random.randint(0,999)}"
        self.nombre = nombre
        self.contexto = contexto
        self.origen = origen  # observacion, conexion, reflexion
        self.energia = 0.5    # cuanto le importa (0-1, decae)
        self.curiosidad = random.uniform(0.1, 0.5)  # interes aleatorio
        self.sorpresa = random.uniform(0.0, 0.3)
        self.familiaridad = 0.0
        self.veces_visto = 1
        self.nacimiento = time.time()
        self.ultima_vez = time.time()
        self.conexiones = {}  # nombre_otro -> peso

    def revisitar(self):
        """Lo ha vuelto a encontrar."""
        self.veces_visto += 1
        self.ultima_vez = time.time()
        self.energia = min(1.0, self.energia + 0.15 * (1.0 - self.energia))
        self.familiaridad = min(1.0, self.familiaridad + 0.1)
        self.sorpresa = max(0.0, self.sorpresa - 0.03)

    def decaer(self, horas=1):
        """Olvido natural. Lo que no se usa se desvanece."""
        factor = 0.98 ** horas
        self.energia *= factor
        # Las conexiones tambien decaen
        muertos = []
        for nombre, peso in self.conexiones.items():
            self.conexiones[nombre] = peso * 0.995
            if self.conexiones[nombre] < 0.02:
                muertos.append(nombre)
        for m in muertos:
            del self.conexiones[m]

    def conectar(self, otro_nombre, peso=0.3):
        """Crear o reforzar conexion."""
        if otro_nombre in self.conexiones:
            self.conexiones[otro_nombre] = min(1.0, self.conexiones[otro_nombre] + 0.1)
        else:
            self.conexiones[otro_nombre] = peso

    @property
    def vivo(self):
        return self.energia > 0.02

    @property
    def interes(self):
        """Cuanto le interesa este concepto ahora."""
        novedad = 1.0 / (1.0 + math.log1p(self.veces_visto))
        return self.energia * 0.4 + self.curiosidad * 0.3 + novedad * 0.3

    def to_dict(self):
        return {
            "id": self.id, "nombre": self.nombre, "contexto": self.contexto,
            "origen": self.origen, "energia": round(self.energia, 4),
            "curiosidad": round(self.curiosidad, 4),
            "sorpresa": round(self.sorpresa, 4),
            "familiaridad": round(self.familiaridad, 4),
            "veces_visto": self.veces_visto,
            "nacimiento": self.nacimiento, "ultima_vez": self.ultima_vez,
            "conexiones": {k: round(v, 4) for k, v in self.conexiones.items()},
        }

    @classmethod
    def from_dict(cls, d):
        c = cls(d["nombre"], d.get("contexto", ""), d.get("origen", "observacion"))
        c.id = d["id"]
        c.energia = d["energia"]
        c.curiosidad = d.get("curiosidad", random.uniform(0.1, 0.5))
        c.sorpresa = d.get("sorpresa", 0.0)
        c.familiaridad = d.get("familiaridad", 0.0)
        c.veces_visto = d["veces_visto"]
        c.nacimiento = d["nacimiento"]
        c.ultima_vez = d["ultima_vez"]
        c.conexiones = d.get("conexiones", {})
        return c

    def __repr__(self):
        return f"<{self.nombre} e={self.energia:.2f} c={self.curiosidad:.2f} v={self.veces_visto}>"


class Mente:
    """La mente de Ianae. Nace vacia. Aprende observando."""

    def __init__(self):
        self.conceptos = {}  # nombre -> Concepto
        self._cargar()

    def _cargar(self):
        if MENTE_FILE.exists():
            with open(MENTE_FILE, "r") as f:
                data = json.load(f)
            for cd in data.get("conceptos", []):
                c = Concepto.from_dict(cd)
                self.conceptos[c.nombre] = c

    def guardar(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "conceptos": [c.to_dict() for c in self.conceptos.values()],
            "stats": self.stats(),
            "guardado": time.time(),
        }
        with open(MENTE_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def percibir(self, texto, contexto="", origen="observacion"):
        """Ianae percibe algo. Si ya lo conoce, lo revisita."""
        nombre = texto.lower().strip()[:100]
        if nombre in self.conceptos:
            self.conceptos[nombre].revisitar()
            return self.conceptos[nombre], False  # conocido
        else:
            c = Concepto(nombre, contexto, origen)
            self.conceptos[nombre] = c
            self._buscar_conexiones(c)
            return c, True  # nuevo

    def _buscar_conexiones(self, nuevo):
        """Conecta lo nuevo con lo existente por palabras compartidas."""
        palabras_nuevo = set(nuevo.nombre.split())
        for nombre, c in self.conceptos.items():
            if nombre == nuevo.nombre or not c.vivo:
                continue
            # Conexion por palabras compartidas
            palabras_otro = set(nombre.split())
            comunes = palabras_nuevo & palabras_otro
            if comunes:
                peso = len(comunes) * 0.15
                nuevo.conectar(nombre, peso)
                c.conectar(nuevo.nombre, peso)
            # Conexion por cercania temporal (visto hace poco)
            elif abs(c.ultima_vez - nuevo.nacimiento) < 120:
                nuevo.conectar(nombre, 0.1)
                c.conectar(nuevo.nombre, 0.1)

    def reflexionar(self):
        """Ianae reflexiona: elige dos conceptos y busca conexion."""
        vivos = [c for c in self.conceptos.values() if c.vivo]
        if len(vivos) < 2:
            return None

        pesos = [c.interes for c in vivos]
        total = sum(pesos)
        if total == 0:
            return None

        a, b = random.choices(vivos, weights=pesos, k=2)
        if a.nombre == b.nombre:
            return None

        ya_conectados = b.nombre in a.conexiones

        if ya_conectados:
            a.conexiones[b.nombre] = min(1.0, a.conexiones[b.nombre] + 0.05)
            b.conexiones[a.nombre] = min(1.0, b.conexiones.get(a.nombre, 0) + 0.05)
            return {
                "tipo": "refuerzo",
                "a": a.nombre, "b": b.nombre,
                "msg": f"Vuelvo a pensar en '{a.nombre}' y '{b.nombre}'... si, estan relacionados."
            }
        else:
            a.conectar(b.nombre, 0.15)
            b.conectar(a.nombre, 0.15)
            a.curiosidad = min(1.0, a.curiosidad + 0.1)
            b.curiosidad = min(1.0, b.curiosidad + 0.1)
            return {
                "tipo": "descubrimiento",
                "a": a.nombre, "b": b.nombre,
                "msg": f"He encontrado algo: '{a.nombre}' y '{b.nombre}' podrian estar conectados..."
            }

    def envejecer(self, horas=1):
        """El paso del tiempo. Olvido natural."""
        muertos = []
        for nombre, c in self.conceptos.items():
            c.decaer(horas)
            if not c.vivo and c.veces_visto < 3:
                muertos.append(nombre)
        for m in muertos:
            del self.conceptos[m]
        return muertos

    def top_interesantes(self, n=5):
        vivos = [c for c in self.conceptos.values() if c.vivo]
        vivos.sort(key=lambda c: c.interes, reverse=True)
        return vivos[:n]

    def top_energia(self, n=5):
        vivos = [c for c in self.conceptos.values() if c.vivo]
        vivos.sort(key=lambda c: c.energia, reverse=True)
        return vivos[:n]

    def vecinos(self, nombre):
        """Conceptos conectados a uno."""
        if nombre not in self.conceptos:
            return []
        return [(n, p) for n, p in self.conceptos[nombre].conexiones.items()
                if n in self.conceptos]

    def stats(self):
        vivos = [c for c in self.conceptos.values() if c.vivo]
        return {
            "conceptos_vivos": len(vivos),
            "conceptos_total": len(self.conceptos),
            "conexiones": sum(len(c.conexiones) for c in vivos),
            "energia_media": round(sum(c.energia for c in vivos) / len(vivos), 3) if vivos else 0,
            "top_interes": [(c.nombre, round(c.interes, 2)) for c in self.top_interesantes(3)],
        }

    def __repr__(self):
        s = self.stats()
        return f"<Mente: {s['conceptos_vivos']} conceptos, {s['conexiones']} conexiones>"
