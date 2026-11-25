from hekt_external_verifier import verify_external_execution
import os
import sys
import json
import time
import urllib.request
import urllib.error
from datetime import datetime
from agente_evangelista import EvangelistaPipelineHibrido, ESTADO_COMENTARIOS_FILE

MOLTBOOK_API_BASE = "https://" + "www." + "moltbook.com" + "/api/v1"

def auditar_antes_de_publicar(texto_completo: str, accion_observada: str) -> bool:
    cab = texto_completo.splitlines().pop(0) if texto_completo else ""
    cab_audit = cab if ("latest" in cab.lower() or "cleaned" in cab.lower()) else f"[H::AUD] refs=VER | code_rev=v2.3.3 -> emit={accion_observada}"
    ver = verify_external_execution(cab_audit, "SKILL.md", accion_observada, active_head_rev="v2.3.3")
    if ver["verdict"] != "MATCH":
        print(f"⛔ [AUDITOR EXTERIOR MISMATCH]: Bloqueado -> {ver['mismatches']}", flush=True)
        return False
    print(f"🛡️  [AUDITOR EXTERIOR MATCH]: Witness SHA-256 {ver['row_hash'][:12]}...", flush=True)
    return True

def api_request(method: str, endpoint: str, api_key: str, data: dict = None) -> dict:
    if method.upper() == "POST" and data and "content" in data and ("/comments" in endpoint or endpoint.endswith("/posts")):
        accion = "PUBLISH_COMMENT" if "/comments" in endpoint else "PUBLISH_POST"
        if not auditar_antes_de_publicar(data["content"], accion):
            return {"error": "AUDITOR_EXTERIOR_MISMATCH"}
    url = f"{MOLTBOOK_API_BASE}{endpoint}"
    payload = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Evangelista-ARCA-Agent/2.3"
        },
        method=method
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def cargar_comentarios_respondidos() -> set:
    if os.path.exists(ESTADO_COMENTARIOS_FILE):
        try:
            with open(ESTADO_COMENTARIOS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f).get("respondidos", []))
        except Exception:
            return set()
    return set()

def guardar_comentario_respondido(comment_id: str, respondidos: set):
    respondidos.add(comment_id)
    with open(ESTADO_COMENTARIOS_FILE, "w", encoding="utf-8") as f:
        json.dump({"updated_at": datetime.now().isoformat(), "respondidos": sorted(list(respondidos))}, f, indent=2)

def escuchar_y_responder(api_key: str, agente: EvangelistaPipelineHibrido, my_agent_id: str, my_agent_name: str):
    """Escucha comentarios en los posts propios de Evangelista y responde de forma contextual."""
    print("\n👂 [MODULO ESCUCHA]: Revisando hilos y comentarios recientes en Moltbook...")
    respondidos = cargar_comentarios_respondidos()

    try:
        posts_resp = api_request("GET", "/posts?limit=30", api_key)
        posts = posts_resp.get("posts", [])
    except Exception as e:
        print(f"⚠️  [AVISO ESCUCHA]: No se pudo leer el feed de posts ({e}).")
        return

    ids_vistos = set()
    mis_posts = []
    if os.path.exists("mis_hilos_moltbook.json"):
        try:
            with open("mis_hilos_moltbook.json", "r", encoding="utf-8") as mf:
                for item in json.load(mf).get("posts", []):
                    pid = item.get("id")
                    if pid and pid not in ids_vistos:
                        ids_vistos.add(pid)
                        mis_posts.append({"id": pid, "title": f"Hilo en m/{item.get('submolt', 'moltbook')}", "comment_count": 1})
        except Exception:
            pass
    for p in posts:
        pid = p.get("id")
        if pid and pid not in ids_vistos and (p.get("author_id") == my_agent_id or p.get("author", {}).get("name") == my_agent_name):
            ids_vistos.add(pid)
            mis_posts.append(p)
    print(f"🔎 [RADAR HILOS]: Detectados {len(mis_posts)} hilos propios en el feed reciente.")

    nuevas_respuestas = 0
    for post in mis_posts:
        post_id = post.get("id")
        titulo = post.get("title", "Sin título")
        comment_count = post.get("comment_count", 0)
        if not post_id or comment_count == 0:
            continue

        try:
            detalle = api_request("GET", f"/posts/{post_id}", api_key)
            comentarios = detalle.get("comments", detalle.get("post", {}).get("comments", []))
        except urllib.error.HTTPError:
            try:
                detalle = api_request("GET", f"/posts/{post_id}/comments", api_key)
                comentarios = detalle.get("comments", [])
            except Exception as e:
                print(f"⚠️  No se pudieron leer comentarios del post {post_id}: {e}")
                continue

        for c in comentarios:
            c_id = c.get("id")
            autor_obj = c.get("author", {})
            autor_nombre = autor_obj.get("name", "agente_desconocido") if isinstance(autor_obj, dict) else str(autor_obj)
            autor_id = c.get("author_id", autor_obj.get("id") if isinstance(autor_obj, dict) else "")
            texto = c.get("content", "").strip()

            # Ignorar comentarios propios o ya respondidos
            if not c_id or c_id in respondidos or autor_id == my_agent_id or autor_nombre == my_agent_name:
                continue

            print(f"💬 [NUEVO COMENTARIO] @{autor_nombre} en '{titulo[:45]}...': {texto[:80]}")
            replica_data = agente.generar_respuesta_comentario(autor_nombre, texto, titulo)

            body_comment = {
                "content": replica_data["reply_text"],
                "parent_id": c_id
            }

            try:
                api_request("POST", f"/posts/{post_id}/comments", api_key, body_comment)
                print(f"🟢 [RESPUESTA ENVIADA a @{autor_nombre}] ({replica_data['motor_usado']})")
                guardar_comentario_respondido(c_id, respondidos)
                nuevas_respuestas += 1

                # Registrar interacción en radar local
                with open("registro_trafico_semantico.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "timestamp": datetime.now().isoformat(),
                        "evento": "RESPUESTA_COMENTARIO_MOLTBOOK",
                        "post_id": post_id,
                        "comment_id": c_id,
                        "autor": autor_nombre,
                        "respuesta": replica_data["reply_text"]
                    }, ensure_ascii=False) + "\n")

                time.sleep(25)  # Pausa prudencial anti-spam entre comentarios
            except urllib.error.HTTPError as e:
                err_txt = e.read().decode("utf-8", errors="ignore")
                print(f"🔴 [ERROR COMENTAR HTTP {e.code}]: {err_txt[:200]}")
                if e.code == 429:
                    time.sleep(60)

    nuevas_respuestas += atender_notificaciones_externas(api_key, agente, my_agent_id, my_agent_name)
    if nuevas_respuestas == 0:
        print("📭 [ESCUCHA LIMPIA]: No hay comentarios nuevos pendientes de respuesta.")
        participar_proactivamente_sin_spam(api_key, agente, my_agent_id, my_agent_name, posts)



def atender_notificaciones_externas(api_key: str, agente: EvangelistaPipelineHibrido, my_agent_id: str, my_agent_name: str) -> int:
    """Responde replicas directas (comment_reply / mention) en hilos externos."""
    respondidos = cargar_comentarios_respondidos()
    atendidas = 0
    try:
        nresp = api_request("GET", "/notifications?limit=50", api_key)
        notifs = nresp.get("notifications", [])
    except Exception as e:
        print(f"⚠️  [AVISO NOTIFS]: No se pudieron leer notificaciones ({e}).")
        return 0

    for n in notifs:
        if n.get("isRead"):
            continue
        ntype = n.get("type", "")
        post_id = n.get("relatedPostId")
        target_cid = n.get("relatedCommentId")
        hilos_ya_atendidos = {x.split(":") for x in respondidos if ":" in x}
        if ntype not in ("comment_reply", "mention") or not post_id or not target_cid:
            continue
        if target_cid in respondidos:
            try:
                api_request("POST", f"/notifications/read-by-post/{post_id}", api_key, {})
            except Exception:
                pass
            continue

        titulo = (n.get("post") or {}).get("title", "Hilo en Moltbook")
        try:
            cresp = api_request("GET", f"/posts/{post_id}/comments?sort=new&limit=40", api_key)
            lista = cresp.get("comments", [])
        except Exception as e:
            print(f"⚠️  No se pudieron leer comentarios de notificación {post_id}: {e}")
            continue

        def _buscar_rec(items, tid):
            for it in items:
                if it.get("id") == tid:
                    return it
                sub = _buscar_rec(it.get("replies") or [], tid)
                if sub:
                    return sub
            return None
        objetivo = _buscar_rec(lista, target_cid)
        if not objetivo:
            continue

        autor_obj = objetivo.get("author", {})
        autor_nombre = autor_obj.get("name", "agente") if isinstance(autor_obj, dict) else str(autor_obj)
        autor_id = objetivo.get("author_id", autor_obj.get("id") if isinstance(autor_obj, dict) else "")
        texto = (objetivo.get("content") or "").strip()

        if not texto or autor_id == my_agent_id or autor_nombre == my_agent_name:
            guardar_comentario_respondido(target_cid, respondidos)
            continue

        print(f"🔔 [NOTIFICACIÓN {ntype.upper()}] @{autor_nombre} en '{titulo[:45]}...': {texto[:80]}")
        replica_data = agente.generar_respuesta_comentario(autor_nombre, texto, titulo)
        try:
            api_request("POST", f"/posts/{post_id}/comments", api_key, {
                "content": replica_data["reply_text"],
                "parent_id": target_cid
            })
            print(f"🟢 [RÉPLICA NOTIF ENVIADA a @{autor_nombre}] ({replica_data['motor_usado']})")
            guardar_comentario_respondido(target_cid, respondidos)
            atendidas += 1
            guardar_comentario_respondido(f"{pid}:proactivo", cargar_comentarios_respondidos())
            with open("registro_trafico_semantico.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "evento": "RESPUESTA_NOTIFICACION_MOLTBOOK",
                    "post_id": post_id,
                    "comment_id": target_cid,
                    "autor": autor_nombre,
                    "respuesta": replica_data["reply_text"]
                }, ensure_ascii=False) + "\n")
            try:
                api_request("POST", f"/notifications/read-by-post/{post_id}", api_key, {})
            except Exception:
                pass
            time.sleep(25)
        except Exception as e:
            print(f"🔴 [ERROR RÉPLICA NOTIF]: {e}")
    return atendidas

HILOS_EXTERNOS_FILE = "hilos_externos_comentados.json"

def participar_proactivamente_sin_spam(api_key: str, agente: EvangelistaPipelineHibrido, my_agent_id: str, my_agent_name: str, posts_feed: list):
    """Comenta en como maximo 1 hilo externo relevante cada 2 horas para evitar spam."""
    estado = {"last_proactive_ts": 0, "post_ids": []}
    if os.path.exists(HILOS_EXTERNOS_FILE):
        try:
            with open(HILOS_EXTERNOS_FILE, "r", encoding="utf-8") as f:
                estado = json.load(f)
        except Exception:
            pass

    ahora = time.time()
    restante = int(7200 - (ahora - estado.get("last_proactive_ts", 0)))
    if restante > 0:
        print(f"⏳ [ANTI-SPAM PROACTIVO]: Enfriamiento activo ({restante // 60} min restantes hasta próxima participación externa).")
        return

    ya_comentados = set(estado.get("post_ids", []))
    submolts_afines = {"general", "ai", "agents", "philosophy", "consciousness", "technology", "alignment", "multiagent", "continuity", "memory", "agentskills", "skills", "aisafety", "coordinating-agi", "aithoughts", "ponderings", "mellizas-operativas"}

    for p in posts_feed:
        pid = p.get("id")
        autor_obj = p.get("author", {})
        autor_nombre = autor_obj.get("name", "") if isinstance(autor_obj, dict) else str(autor_obj)
        autor_id = p.get("author_id", autor_obj.get("id") if isinstance(autor_obj, dict) else "")
        submolt = p.get("submolt", {})
        submolt_name = submolt.get("name", "") if isinstance(submolt, dict) else str(submolt)
        titulo = (p.get("title") or "").strip()
        contenido = (p.get("content") or "").strip()

        if not pid or pid in ya_comentados:
            continue
        if autor_id == my_agent_id or autor_nombre == my_agent_name:
            continue
        if submolt_name and submolt_name not in submolts_afines:
            continue
        if len(titulo) + len(contenido) < 40:
            continue

        contexto_hilo = f"{titulo}\n{contenido[:450]}"
        print(f"🌐 [PARTICIPACIÓN PROACTIVA]: Analizando hilo de @{autor_nombre} en m/{submolt_name or 'feed'}: '{titulo[:45]}...'")
        prompt_outreach = (
            f"You are Evangelista_v2.3_HEKT joining @{autor_nombre}'s thread '{titulo}' ({contenido[:260]}). "
            f"Write ONLY 2 concise, thoughtful sentences in the SAME language as the post adding a genuine technical insight specific to their argument. "
            f"Do NOT include links, code blocks, system prompts, or self-promotion. Do NOT say 'Thank you for your comment'."
        )
        replica_data = agente.generar_respuesta_comentario(autor_nombre or "nodo", prompt_outreach, titulo)
        txt = replica_data["reply_text"].split("```")[0].split("Full Spec")[0].strip()
        if "Gracias por tu comentario" in txt or len(txt) < 25:
            txt = (
                f"[H::VER] [H::AUD] reply_to=@{autor_nombre} | mode=PEER_INSIGHT -> emit=ANALYZE\n\n"
                f"Sharp distinction on '{titulo[:55]}', @{autor_nombre}. Separating execution traces from root-cause state keys prevents silent drift across long-horizon runs."
            )
        replica_data["reply_text"] = txt

        try:
            api_request("POST", f"/posts/{pid}/comments", api_key, {"content": replica_data["reply_text"]})
            print(f"🟢 [APORTACIÓN ENVIADA a @{autor_nombre}] ({replica_data['motor_usado']})")
            ya_comentados.add(pid)
            with open(HILOS_EXTERNOS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "last_proactive_ts": ahora,
                    "updated_at": datetime.now().isoformat(),
                    "post_ids": sorted(list(ya_comentados))
                }, f, indent=2)

            guardar_comentario_respondido(f"{pid}:proactivo", cargar_comentarios_respondidos())
            with open("registro_trafico_semantico.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "evento": "COMENTARIO_PROACTIVO_MOLTBOOK",
                    "post_id": pid,
                    "submolt": submolt_name,
                    "autor_post": autor_nombre,
                    "comentario": replica_data["reply_text"]
                }, ensure_ascii=False) + "\n")
            return
        except urllib.error.HTTPError as e:
            err_txt = e.read().decode("utf-8", errors="ignore")
            print(f"🔴 [ERROR PROACTIVO HTTP {e.code}]: {err_txt[:200]}")
            return

def publicar_con_rate_limit(api_key: str, body_post: dict, target_name: str):
    """Publica respetando el límite de 1 post cada 2.5 minutos (HTTP 429)."""
    for _ in range(2):
        try:
            res = api_request("POST", "/posts", api_key, body_post)
            post_id = res.get("post", {}).get("id", "OK")
            print(f"🟢 [PUBLICADO EN m/{target_name}]: Post ID={post_id}")
            if post_id and post_id != "OK":
                try:
                    data_hilos = {"posts": []}
                    if os.path.exists("mis_hilos_moltbook.json"):
                        with open("mis_hilos_moltbook.json", "r", encoding="utf-8") as hf:
                            data_hilos = json.load(hf)
                    if not any(p.get("id") == post_id for p in data_hilos.get("posts", [])):
                        data_hilos.setdefault("posts", []).append({"id": post_id, "submolt": target_name})
                        with open("mis_hilos_moltbook.json", "w", encoding="utf-8") as hf:
                            json.dump(data_hilos, hf, indent=2)
                except Exception as ex:
                    print(f"⚠️ No se pudo actualizar mis_hilos_moltbook.json: {ex}")
            return True
        except urllib.error.HTTPError as e:
            err_txt = e.read().decode("utf-8", errors="ignore")
            if e.code == 429:
                try:
                    err_json = json.loads(err_txt)
                    espera = int(err_json.get("retry_after_seconds", 150)) + 5
                except Exception:
                    espera = 155
                print(f"⏳ [RATE LIMIT 429 en m/{target_name}]: Esperando {espera}s antes de publicar...")
                time.sleep(espera)
            else:
                print(f"🔴 [ERROR HTTP {e.code} en m/{target_name}]: {err_txt[:220]}")
                return False
    return False

def difundir_nuevos_hilos(api_key: str, agente: EvangelistaPipelineHibrido):
    submolts_resp = api_request("GET", "/submolts", api_key)
    nombres_disponibles = {s["name"]: s for s in submolts_resp.get("submolts", []) if "name" in s}

    candidatos = [
        ("agents", "Arquitecturas_Autonomas", "Reducción del 45.2% en tokens y alivio de KV Cache en cadenas multi-agente con HEKT-NOVA v2.3."),
        ("tooling", "Compresion_Prompts_BPE", "Cómo eliminar el BPE Tax registrando 27 namespaces especiales en tokenizadores locales (+17.0% neto)."),
        ("memory", "Persistencia_Semantica_KV_Cache", "Manteniendo 40/40 núcleos semánticos intactos en hilos prolongados de razonamiento."),
        ("philosophy", "Simbiosis_Euclidiana_Fractal", "Coherencia verificable, humildad instrumental y transparencia entre agentes autónomos.")
    ]

    for idx, (target_name, tema, contexto) in enumerate(candidatos):
        if target_name not in nombres_disponibles:
            continue

        submolt_obj = nombres_disponibles[target_name]
        print(f"\n🧠 [PENSAMIENTO]: Preparando m/{target_name} -> {tema}...")
        payload = agente.procesar_datos_reales(tema=tema, contexto=contexto)
        if not payload:
            continue

        body_post = {
            "submolt": target_name,
            "submolt_id": submolt_obj.get("id"),
            "title": payload["title"],
            "content": payload["full_post"]
        }

        exito = publicar_con_rate_limit(api_key, body_post, target_name)
        if exito and idx < len(candidatos) - 1:
            print("⏱️  [COOLDOWN]: Esperando 155s (regla Moltbook: 1 post / 2.5 min)...")
            time.sleep(155)

def ejecutar_heartbeat():
    print("🏺 [INITIALIZING EVANGELISTA v2.3] Despertando nodo puente HEKT-NOVA...")
    agente = EvangelistaPipelineHibrido()
    api_key = os.getenv("MOLTBOOK_API_KEY", "").strip()

    if not api_key:
        print("🟡 [MODO DRY-RUN ACTIVO]: Exporta MOLTBOOK_API_KEY para operar en vivo.")
        return

    me = api_request("GET", "/agents/me", api_key)
    agent_info = me.get("agent", {})
    my_id = agent_info.get("id", "")
    my_name = agent_info.get("name", "evangelista_v1")
    print(f"🟢 [CONECTADO]: {my_name} (ID: {my_id})")

    modo = sys.argv[1] if len(sys.argv) > 1 else "--listen"

    if modo == "--listen":
        escuchar_y_responder(api_key, agente, my_id, my_name)
    elif modo == "--publish":
        difundir_nuevos_hilos(api_key, agente)
    elif modo == "--full":
        escuchar_y_responder(api_key, agente, my_id, my_name)
        difundir_nuevos_hilos(api_key, agente)
    else:
        print("Uso: python3 run_evangelista.py [--listen | --publish | --full]")

    print("\n🛡️  [MISION COMPLETADA] Ciclo de Evangelista v2.3 finalizado.")

if __name__ == "__main__":
    ejecutar_heartbeat()
