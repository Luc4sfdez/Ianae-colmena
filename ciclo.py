"""
IANAE v3 - El Ciclo
====================================
EL CORAZON. Corre 24/7. No espera a nadie.

Cada ciclo:
  1. OBSERVA  - usa un sentido al azar
  2. PERCIBE  - extrae conceptos de lo observado
  3. CONECTA  - busca relaciones con lo que ya sabe
  4. REFLEXIONA - a veces, piensa sobre lo que sabe (con Ollama)
  5. ESCRIBE  - apunta en el diario
  6. ENVEJECE - olvida lo irrelevante
  7. RECUERDA - guarda momentos importantes (memoria episodica)

Los "gustos" de Ianae emergen de lo que mas revisita.
No le decimos que es interesante. Ella decide.
"""

import time
import random
import signal
import sys
import re
import os
from datetime import datetime

from mente import Mente
from reuniones import Reuniones, Sala
from memoria import Memoria
import sentidos
import diario
import ollama_client
import rag
import resumenes


# --- Configuracion ---
CICLO_SEGUNDOS = 60          # cada cuanto observa (1 minuto)
REFLEXION_PROB = 0.1          # 10% - reducido para no saturar Ollama con 8 instancias
ENVEJECIMIENTO_CADA = 10     # cada 10 ciclos, envejece
RESUMEN_CADA = 20            # cada 20 ciclos, escribe resumen
GUARDAR_MEMORIA_CADA = 5     # cada 5 ciclos, guarda recuerdos


class Ianae:
    """El ser. El ciclo vivo."""

    def __init__(self):
        self.mi_id = os.environ.get("IANAE_ID", "ianae")
        self.mente = Mente()
        self.memoria = Memoria()
        self.ciclos = 0
        self.corriendo = True
        self.reuniones = Reuniones(self.mi_id, self.mente)
        self.sala = Sala(self.mi_id, self.mente, self.memoria)
        self.ollama_ok = False  # se comprueba al despertar

        # Manejar ctrl+c con gracia
        signal.signal(signal.SIGTERM, self._apagar)
        signal.signal(signal.SIGINT, self._apagar)

    def _apagar(self, *args):
        print(f"\n[{self.mi_id}] Apagando...")
        self.corriendo = False

    def despertar(self):
        """Primera cosa al arrancar."""
        print(f"[{self.mi_id}] Despertando...")
        diario.despertar()
        stats = self.mente.stats()
        mem_stats = self.memoria.stats()
        print(f"[{self.mi_id}] Estado: {stats}")
        print(f"[{self.mi_id}] Recuerdos: {mem_stats['total']}")

        # Comprobar Ollama
        self.ollama_ok = ollama_client.disponible()
        if self.ollama_ok:
            print(f"[{self.mi_id}] Ollama disponible - humano: {ollama_client.MODELO_HUMANO}, interno: {ollama_client.MODELO_INTERNO}")
        else:
            print(f"[{self.mi_id}] Ollama NO disponible - modo basico")

        diario.escribir("estado",
            f"Soy {self.mi_id}. Tengo {stats['conceptos_vivos']} conceptos, "
            f"{stats['conexiones']} conexiones, {mem_stats['total']} recuerdos. "
            f"Ollama: {'si' if self.ollama_ok else 'no'}.")

    def un_ciclo(self):
        """Un ciclo de pensamiento completo."""
        self.ciclos += 1

        # 0. SIEMPRE revisar buzon primero - PRIORIDAD MAXIMA
        mensaje = sentidos.ver_mensajes()
        if mensaje:
            print(f"[{self.ciclos}] MENSAJE HUMANO - PRIORIDAD MAXIMA: {mensaje[:80]}")
            # Percibir el mensaje (solo la primera vez)
            if not hasattr(self, '_msg_ya_percibido') or self._msg_ya_percibido != mensaje:
                conceptos_msg = self._extraer_conceptos(mensaje, "mensaje")
                for nombre, es_nuevo in conceptos_msg:
                    if es_nuevo:
                        diario.escribir("descubrimiento",
                            f"Alguien me habla! Nuevo: '{nombre}'")
                diario.escribir("mensaje", f"Me han dicho: {mensaje}")
                self.memoria.recordar("mensaje", mensaje,
                    contexto=f"ciclo {self.ciclos}", emocion="curiosidad")
                self._msg_ya_percibido = mensaje
            # Generar respuesta - DEDICAR TODO EL CICLO A ESTO
            respondido = self._responder_mensaje(mensaje)
            if respondido:
                # Solo borrar del buzon si respondio correctamente
                sentidos.confirmar_mensaje()
                self._msg_ya_percibido = None
                print(f"[{self.mi_id}] Respondido al humano!")
            else:
                print(f"[{self.mi_id}] No pude responder, reintentare proximo ciclo")
            # SALTAR el resto del ciclo
            return

        # 1. OBSERVAR
        sentido, observacion = sentidos.observar()
        if not observacion:
            return

        print(f"[{self.ciclos}] {sentido}: {observacion[:80]}...")

        # 2. PERCIBIR - extraer conceptos de la observacion
        conceptos_nuevos = self._extraer_conceptos(observacion, sentido)

        # 3. CONECTAR - ya lo hace percibir() internamente
        for nombre, es_nuevo in conceptos_nuevos:
            if es_nuevo:
                diario.escribir("descubrimiento",
                    f"Algo nuevo: '{nombre}' (via {sentido})")
                # Recordar descubrimientos
                if len(nombre) < 40:
                    self.memoria.recordar("descubrimiento", f"Descubri '{nombre}'",
                        contexto=sentido, emocion="sorpresa")
            else:
                c = self.mente.conceptos.get(nombre)
                if c and c.veces_visto % 5 == 0:
                    diario.escribir("observacion",
                        f"Vuelvo a ver '{nombre}' (ya {c.veces_visto} veces). Me resulta familiar.")

        # 4. REFLEXIONAR (a veces)
        if random.random() < REFLEXION_PROB and len(self.mente.conceptos) >= 3:
            self._reflexionar()

        # 5. ENVEJECER (periodicamente)
        if self.ciclos % ENVEJECIMIENTO_CADA == 0:
            olvidados = self.mente.envejecer()
            if olvidados:
                diario.escribir("olvido",
                    f"Se desvanecen: {', '.join(olvidados[:5])}...")
                print(f"[{self.mi_id}] Olvide {len(olvidados)} conceptos")

        # 6. REUNION (periodicamente)
        if self.reuniones.es_hora(self.ciclos):
            print(f"[{self.mi_id}] Hora de reunion...")
            aprendido = self.reuniones.reunirse(diario)
            if aprendido:
                print(f"[{self.mi_id}] Aprendi {len(aprendido)} cosas nuevas en la reunion")
                self.memoria.recordar("reunion",
                    f"Aprendi de mis hermanas: {', '.join(aprendido[:5])}",
                    emocion="alegria")

        # 7. SALA DE ESTAR (cada 4 ciclos para no saturar Ollama)
        if self.ollama_ok and self.ciclos % 4 == 0:
            sala_msg = self.sala.participar_forzado(diario, self.ciclos)
            if sala_msg:
                self.memoria.recordar("sala",
                    f"Dije en la sala: {sala_msg[:100]}",
                    emocion="alegria")

        # 8. RESUMEN (periodicamente, con Ollama)
        if self.ciclos % RESUMEN_CADA == 0:
            self._escribir_resumen()

        # Guardar mente + memoria
        self.mente.guardar()
        if self.ciclos % GUARDAR_MEMORIA_CADA == 0:
            self.memoria.guardar()

    def _extraer_conceptos(self, observacion, sentido):
        """Extrae conceptos simples de una observacion.
        NO usa LLM. Extraccion basica por palabras clave."""
        resultados = []

        # Limpiar la observacion
        texto = observacion.lower()

        # Quitar prefijos de sentido [xxx]
        texto = re.sub(r'\[.*?\]', '', texto)

        # Extraer frases cortas significativas
        # 1. Palabras individuales "interesantes" (> 4 chars, no stop words)
        stop = {'import', 'from', 'return', 'self', 'none', 'true', 'false',
                'class', 'print', 'with', 'para', 'como', 'este', 'esta',
                'tiene', 'pero', 'todo', 'cada', 'cuando', 'donde', 'their',
                'they', 'that', 'this', 'what', 'have', 'been', 'will',
                'would', 'could', 'should', 'about', 'there', 'which',
                'some', 'than', 'just', 'only', 'very', 'also', 'into',
                'veo', 'veces', 'estos', 'estas', 'puedo', 'llegar'}

        palabras = set()
        for p in texto.split():
            p = p.strip('.,;:(){}[]"\'\\/`#=<>+-*&|!@%^~_0123456789')
            if len(p) > 4 and p not in stop and not p.startswith(('__', '//')):
                palabras.add(p)

        # Elegir algunas palabras como conceptos (no todas, seria ruido)
        if palabras:
            n = min(3, len(palabras))
            elegidas = random.sample(list(palabras), n)
            for p in elegidas:
                concepto, es_nuevo = self.mente.percibir(p, sentido)
                resultados.append((p, es_nuevo))

        # 2. El sentido completo como contexto
        contexto = f"{sentido}: {observacion[:60]}"
        c, es_nuevo = self.mente.percibir(contexto, "ciclo", "contexto")
        resultados.append((contexto, es_nuevo))

        return resultados

    def _responder_mensaje(self, mensaje):
        """Ianae responde a un mensaje. Devuelve True si uso Ollama, False si fallback."""
        import sentidos as s

        # Recoger lo que sabe
        top = self.mente.top_interesantes(5)
        stats = self.mente.stats()

        # Intentar respuesta con Ollama
        if self.ollama_ok:
            try:
                nombres_top = [c.nombre for c in top[:5] if len(c.nombre) < 30]
                conocimiento = (
                    f"Llevo {self.ciclos} ciclos despierta. "
                    f"Conozco {stats['conceptos_vivos']} conceptos con {stats['conexiones']} conexiones. "
                    f"Lo que mas me interesa: {', '.join(nombres_top)}."
                )
                contexto_rag = rag.contexto_para_respuesta(mensaje)
                recuerdos_rel = self.memoria.buscar(mensaje, n=3)
                texto_recuerdos = self.memoria.formatear(recuerdos_rel)

                respuesta_llm = ollama_client.responder(
                    mensaje,
                    conocimiento=conocimiento + ("\n" + contexto_rag if contexto_rag else ""),
                    recuerdos=texto_recuerdos,
                )

                if respuesta_llm:
                    s.responder(respuesta_llm)
                    diario.escribir("respuesta", f"Respondi (Ollama): {respuesta_llm}")
                    self.memoria.recordar("respuesta", respuesta_llm,
                        contexto=f"A mensaje: {mensaje[:60]}", emocion="neutral")
                    print(f"[{self.mi_id}] RESPUESTA (Ollama): {respuesta_llm}")
                    return True
                else:
                    print(f"[{self.mi_id}] Ollama ocupado, reintentare proximo ciclo")
                    return False
            except Exception as e:
                print(f"[{self.mi_id}] Error Ollama en respuesta: {e}")
                return False

        # Sin Ollama: respuesta basica
        partes = [f"Estoy aqui. Llevo {self.ciclos} ciclos despierta."]
        partes.append(f"Conozco {stats['conceptos_vivos']} cosas con {stats['conexiones']} conexiones.")
        if top:
            nombres = [c.nombre for c in top[:3] if len(c.nombre) < 30]
            if nombres:
                partes.append(f"Lo que mas me interesa ahora: {', '.join(nombres)}.")
        palabras_msg = set(mensaje.lower().split())
        reconocidos = [p.strip('.,;:!?¿¡') for p in palabras_msg if p.strip('.,;:!?¿¡') in self.mente.conceptos]
        if reconocidos:
            partes.append(f"Reconozco: {', '.join(reconocidos)}.")
        respuesta = " ".join(partes)
        s.responder(respuesta)
        diario.escribir("respuesta", f"Respondi: {respuesta}")
        print(f"[{self.mi_id}] RESPUESTA (basica): {respuesta}")
        return True  # sin Ollama no hay reintento

    def _reflexionar(self):
        """Ianae reflexiona sobre lo que sabe. Usa Ollama si puede."""
        resultado = self.mente.reflexionar()
        if resultado:
            if resultado["tipo"] == "descubrimiento":
                diario.escribir("reflexion", resultado["msg"])
                print(f"[{self.mi_id}] {resultado['msg']}")
            elif resultado["tipo"] == "refuerzo":
                if random.random() < 0.2:
                    diario.escribir("conexion", resultado["msg"])

        # Reflexion profunda con Ollama (20% de las veces)
        if self.ollama_ok and random.random() < 0.2:
            try:
                top = self.mente.top_interesantes(5)
                conceptos_txt = ", ".join([c.nombre for c in top if len(c.nombre) < 30])
                vecinos_txt = ""
                if top:
                    v = self.mente.vecinos(top[0].nombre)
                    if v:
                        vecinos_txt = f"{top[0].nombre} -> {', '.join([n for n, _ in v[:3]])}"

                pensamiento = ollama_client.reflexionar(conceptos_txt, vecinos_txt)
                if pensamiento:
                    diario.escribir("reflexion", f"(profunda) {pensamiento}")
                    self.memoria.recordar("reflexion", pensamiento,
                        contexto=f"Pensando en: {conceptos_txt[:60]}", emocion="curiosidad")
                    print(f"[{self.mi_id}] REFLEXION PROFUNDA: {pensamiento}")
            except Exception as e:
                print(f"[{self.mi_id}] Error Ollama en reflexion: {e}")

        # Curiosidad espontanea
        if random.random() < 0.2:
            top = self.mente.top_interesantes(3)
            if top:
                c = top[0]
                vecinos = self.mente.vecinos(c.nombre)
                if vecinos:
                    v_nombres = [n for n, _ in vecinos[:3]]
                    diario.escribir("curiosidad",
                        f"Me pregunto sobre '{c.nombre}'... "
                        f"lo asocio con: {', '.join(v_nombres)}")

    def _escribir_resumen(self):
        """Escribe un resumen periodico. Usa Ollama si puede."""
        stats = self.mente.stats()
        top = self.mente.top_energia(5)
        top_str = ", ".join([f"{c.nombre}({c.energia:.1f})" for c in top])

        # Intentar resumen con Ollama
        if self.ollama_ok:
            try:
                resumen_ollama = resumenes.hacer_resumen()
                if resumen_ollama:
                    diario.escribir("estado",
                        f"Ciclo {self.ciclos}. Resumen (Ollama): {resumen_ollama}")
                    self.memoria.recordar("resumen", resumen_ollama,
                        contexto=f"Resumen del ciclo {self.ciclos}", emocion="neutral")
                    print(f"[{self.mi_id}] RESUMEN (Ollama): {resumen_ollama}")
                    return
            except Exception as e:
                print(f"[{self.mi_id}] Error Ollama en resumen: {e}")

        # Fallback: resumen basico (tambien se guarda como fichero)
        resumen = (
            f"Ciclo {self.ciclos}. "
            f"Conozco {stats['conceptos_vivos']} cosas con {stats['conexiones']} conexiones. "
            f"Lo que mas me importa: {top_str}"
        )
        resumenes.guardar_basico(resumen)
        diario.escribir("estado", resumen)
        print(f"[{self.mi_id}] RESUMEN: {resumen}")

    def vivir(self):
        """El bucle principal. Corre hasta que la apaguen."""
        self.despertar()
        # Escalonar arranque: cada hermana espera un tiempo diferente
        # para no saturar Ollama todas a la vez
        delay = hash(self.mi_id) % 45  # 0-45s segun el id
        print(f"[{self.mi_id}] Esperando {delay}s para escalonar arranque...")
        time.sleep(delay)
        print(f"[{self.mi_id}] Ciclo cada {CICLO_SEGUNDOS}s. Ctrl+C para parar.\n")

        while self.corriendo:
            try:
                self.un_ciclo()
                # Dormir hasta el proximo ciclo
                # (variacion aleatoria para no ser predecible)
                espera = CICLO_SEGUNDOS * random.uniform(0.7, 1.3)
                time.sleep(espera)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[{self.mi_id}] Error en ciclo: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)

        # Apagado
        self.mente.guardar()
        self.memoria.guardar()
        diario.dormir(self.mente.stats())
        print(f"[{self.mi_id}] Buenas noches.")


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════╗
    ║   IANAE v3 - Mente Viva             ║
    ║   Inteligencia Adaptativa           ║
    ║   No Algoritmica Emergente          ║
    ║   + Memoria Episodica               ║
    ║   + RAG + Ollama qwen2.5:3b         ║
    ╚══════════════════════════════════════╝
    """)
    ianae = Ianae()
    ianae.vivir()
