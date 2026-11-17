import os
import re
import unicodedata
from functools import wraps
import httpx
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.environ.get("ADMIN_PASSWORD", "ghm-osorno-secret-2026"))

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()

ADMIN_EMAIL = "adminpagina.eghm26@daemosorno.cl"
ADMIN_MASTER_PASSWORD = "ADMINEGHM"

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print("Error inicializando Supabase:", e)


def login_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("usuario_email"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Sesión expirada. Inicia sesión nuevamente."}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("es_admin"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Acceso restringido al Administrador."}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def _admin_headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }


def limpiar_rut(rut: str) -> str:
    return re.sub(r"[^0-9kK]", "", (rut or "")).upper()


def formatear_rut(rut: str) -> str:
    limpio = limpiar_rut(rut)
    if len(limpio) < 2:
        return limpio
    cuerpo, dv = limpio[:-1], limpio[-1]
    cuerpo_formateado = f"{int(cuerpo):,}".replace(",", ".") if cuerpo.isdigit() else cuerpo
    return f"{cuerpo_formateado}-{dv}"


def validar_rut_chileno(rut: str) -> bool:
    limpio = limpiar_rut(rut)
    if len(limpio) < 7 or len(limpio) > 9:
        return False
    cuerpo, dv = limpio[:-1], limpio[-1]
    if not cuerpo.isdigit():
        return False

    suma = 0
    multiplo = 2
    for c in reversed(cuerpo):
        suma += int(c) * multiplo
        multiplo = 2 if multiplo == 7 else multiplo + 1

    resto = suma % 11
    if 11 - resto == 11:
        dv_esperado = "0"
    elif 11 - resto == 10:
        dv_esperado = "K"
    else:
        dv_esperado = str(11 - resto)

    return dv == dv_esperado


def normalizar_texto(texto: str) -> str:
    texto = (texto or "").strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"\s+", " ", texto)
    return texto.upper()


# ==============================================================================
# AUTENTICACIÓN: INSPECTORES Y ADMINISTRADOR
# ==============================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("usuario_email"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not supabase:
            error = "El servidor no tiene configuradas las credenciales de Supabase."
        elif not email or not password:
            error = "Ingresa tu correo electrónico y contraseña."
        else:
            try:
                auth_client = create_client(SUPABASE_URL, SUPABASE_KEY)
                res = auth_client.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })
                if res.user:
                    session["usuario_email"] = res.user.email
                    return redirect(url_for("index"))
                error = "Correo o contraseña incorrectos."
            except Exception as e:
                if "Email not confirmed" in str(e):
                    error = "Cuenta pendiente de confirmación. El administrador debe activarla."
                else:
                    error = "Correo o contraseña incorrectos."

    return render_template("login.html", error=error, modo="login")


@app.route("/admin-login", methods=["POST"])
def admin_login():
    email = (request.form.get("admin_email") or "").strip().lower()
    clave = (request.form.get("admin_password") or "").strip()

    if email == ADMIN_EMAIL and clave == ADMIN_MASTER_PASSWORD:
        session["es_admin"] = True
        return redirect(url_for("panel_admin"))

    return render_template(
        "login.html",
        error="Correo o contraseña de Administrador incorrectos.",
        modo="admin"
    )


@app.route("/admin")
@admin_requerido
def panel_admin():
    return render_template("admin.html", service_conectado=bool(SUPABASE_URL and SUPABASE_SERVICE_KEY))


@app.route("/api/admin/usuarios", methods=["GET"])
@admin_requerido
def api_listar_usuarios():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return jsonify({"error": "Falta configurar SUPABASE_SERVICE_KEY en las variables de entorno de Render."}), 500

    try:
        url = f"{SUPABASE_URL}/auth/v1/admin/users"
        r = httpx.get(url, headers=_admin_headers(), timeout=15)
        data = r.json()
        if r.status_code >= 400:
            return jsonify({"error": data.get("msg") or data.get("message") or str(data)}), r.status_code

        lista_raw = data.get("users", []) if isinstance(data, dict) else data
        usuarios = []
        for u in lista_raw:
            usuarios.append({
                "id": u.get("id", ""),
                "email": u.get("email", ""),
                "created_at": str(u.get("created_at") or "")[:10],
                "last_sign_in_at": str(u.get("last_sign_in_at") or "Nunca")[:10]
            })
        return jsonify({"usuarios": usuarios})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/usuarios", methods=["POST"])
@admin_requerido
def api_crear_usuario():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return jsonify({"error": "Falta configurar SUPABASE_SERVICE_KEY en las variables de entorno de Render."}), 500

    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or "@" not in email:
        return jsonify({"error": "Ingresa un correo electrónico válido."}), 400
    if len(password) < 6:
        return jsonify({"error": "La contraseña debe tener al menos 6 caracteres."}), 400

    try:
        url = f"{SUPABASE_URL}/auth/v1/admin/users"
        payload = {
            "email": email,
            "password": password,
            "email_confirm": True
        }
        r = httpx.post(url, headers=_admin_headers(), json=payload, timeout=15)
        res_data = r.json()
        if r.status_code >= 400:
            msg = res_data.get("msg") or res_data.get("message") or str(res_data)
            if "already" in msg.lower():
                return jsonify({"error": "Ese correo electrónico ya tiene una cuenta registrada."}), 400
            return jsonify({"error": msg}), r.status_code

        return jsonify({
            "ok": True,
            "usuario": {
                "id": res_data.get("id", ""),
                "email": res_data.get("email", email)
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/usuarios/<user_id>", methods=["DELETE"])
@admin_requerido
def api_eliminar_usuario(user_id):
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return jsonify({"error": "Falta configurar SUPABASE_SERVICE_KEY en las variables de entorno de Render."}), 500

    try:
        url = f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}"
        r = httpx.delete(url, headers=_admin_headers(), timeout=15)
        if r.status_code >= 400:
            res_data = r.json()
            return jsonify({"error": res_data.get("msg") or res_data.get("message") or str(res_data)}), r.status_code
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==============================================================================
# SISTEMA PRINCIPAL DE INSPECTORÍA
# ==============================================================================

@app.route("/")
@login_requerido
def index():
    return render_template("index.html", conectado=bool(supabase), usuario_email=session.get("usuario_email"))


@app.route("/api/datos", methods=["GET"])
@login_requerido
def api_datos():
    if not supabase:
        return jsonify({"error": "Faltan variables de entorno SUPABASE_URL y SUPABASE_KEY en el servidor."}), 500

    try:
        res_est = supabase.table("estudiantes").select("*").order("nombre").execute()
        res_atr = supabase.table("atrasos").select("*").order("fecha", desc=True).order("hora", desc=True).execute()
        res_ret = supabase.table("retiros").select("*").order("fecha", desc=True).order("hora", desc=True).execute()

        return jsonify({
            "estudiantes": res_est.data or [],
            "atrasos": res_atr.data or [],
            "retiros": res_ret.data or []
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/estudiantes", methods=["POST"])
@login_requerido
def crear_estudiante():
    if not supabase:
        return jsonify({"error": "Base de datos no conectada."}), 500

    data = request.get_json() or {}
    rut_raw = data.get("rut", "")
    nombre = re.sub(r"\s+", " ", data.get("nombre", "")).strip().upper()
    curso = (data.get("curso") or "").strip()

    if not validar_rut_chileno(rut_raw):
        return jsonify({"error": "El RUT ingresado no es válido (revisa el dígito verificador)."}), 400
    if not nombre or not curso:
        return jsonify({"error": "Nombre y curso son obligatorios."}), 400

    rut_fmt = formatear_rut(rut_raw)

    try:
        res = supabase.table("estudiantes").upsert({
            "rut": rut_fmt,
            "nombre": nombre,
            "curso": curso
        }).execute()
        return jsonify({"estudiante": res.data[0] if res.data else {"rut": rut_fmt, "nombre": nombre, "curso": curso}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/estudiantes/masivo", methods=["POST"])
@login_requerido
def carga_masiva_estudiantes():
    if not supabase:
        return jsonify({"error": "Base de datos no conectada."}), 500

    data = request.get_json() or {}
    lista = data.get("estudiantes", [])
    validos = []
    errores = []

    for idx, item in enumerate(lista, start=1):
        rut_raw = item.get("rut", "")
        nombre = re.sub(r"\s+", " ", item.get("nombre", "")).strip().upper()
        curso = (item.get("curso") or "").strip()

        if not validar_rut_chileno(rut_raw):
            errores.append(f"Fila {idx}: RUT inválido ({rut_raw})")
            continue
        if not nombre or not curso:
            errores.append(f"Fila {idx}: Falta nombre o curso")
            continue

        validos.append({
            "rut": formatear_rut(rut_raw),
            "nombre": nombre,
            "curso": curso
        })

    if not validos:
        return jsonify({"error": "No se encontraron registros válidos para importar.", "detalles": errores}), 400

    try:
        unicos = {e["rut"]: e for e in validos}.values()
        supabase.table("estudiantes").upsert(list(unicos)).execute()
        return jsonify({
            "importados": len(unicos),
            "errores": errores
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/estudiantes/<path:rut>", methods=["DELETE"])
@login_requerido
def eliminar_estudiante(rut):
    if not supabase:
        return jsonify({"error": "Base de datos no conectada."}), 500

    clave = request.headers.get("X-Admin-Key", "")
    if clave != os.environ.get("ADMIN_PASSWORD", "1234"):
        return jsonify({"error": "Clave de Inspectoría incorrecta."}), 403

    try:
        rut_fmt = formatear_rut(rut)
        supabase.table("estudiantes").delete().eq("rut", rut_fmt).execute()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/atrasos", methods=["POST"])
@login_requerido
def registrar_atraso():
    if not supabase:
        return jsonify({"error": "Base de datos no conectada."}), 500

    data = request.get_json() or {}
    rut_raw = (data.get("rut") or "").strip()
    nombre = re.sub(r"\s+", " ", data.get("nombre", "")).strip().upper()
    curso = (data.get("curso") or "").strip()
    fecha = data.get("fecha")
    hora = data.get("hora")
    motivo = (data.get("motivo") or "").strip()
    guardar_en_catalogo = bool(data.get("guardar_estudiante", False))

    if not nombre or not curso or not fecha or not hora:
        return jsonify({"error": "Nombre, curso, fecha y hora son obligatorios."}), 400

    rut_fmt = ""
    if rut_raw:
        if not validar_rut_chileno(rut_raw):
            return jsonify({"error": "El RUT ingresado no es válido."}), 400
        rut_fmt = formatear_rut(rut_raw)

    try:
        if rut_fmt and guardar_en_catalogo:
            supabase.table("estudiantes").upsert({
                "rut": rut_fmt,
                "nombre": nombre,
                "curso": curso
            }).execute()

        nuevo = {
            "rut": rut_fmt or None,
            "fecha": fecha,
            "hora": hora,
            "nombre": nombre,
            "nombre_normalizado": normalizar_texto(nombre),
            "curso": curso,
            "motivo": motivo
        }
        res = supabase.table("atrasos").insert(nuevo).execute()
        return jsonify({"registro": res.data[0]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/retiros", methods=["POST"])
@login_requerido
def registrar_retiro():
    if not supabase:
        return jsonify({"error": "Base de datos no conectada."}), 500

    data = request.get_json() or {}
    rut_raw = (data.get("rut") or "").strip()
    nombre = re.sub(r"\s+", " ", data.get("nombre", "")).strip().upper()
    curso = (data.get("curso") or "").strip()
    quien_retira = re.sub(r"\s+", " ", data.get("quien_retira", "")).strip().upper()
    parentesco = re.sub(r"\s+", " ", data.get("parentesco", "")).strip().upper()
    fecha = data.get("fecha")
    hora = data.get("hora")
    motivo = (data.get("motivo") or "").strip()
    guardar_en_catalogo = bool(data.get("guardar_estudiante", False))

    if not nombre or not curso or not quien_retira or not parentesco or not fecha or not hora:
        return jsonify({"error": "Todos los campos obligatorios deben completarse."}), 400

    rut_fmt = ""
    if rut_raw:
        if not validar_rut_chileno(rut_raw):
            return jsonify({"error": "El RUT ingresado no es válido."}), 400
        rut_fmt = formatear_rut(rut_raw)

    try:
        if rut_fmt and guardar_en_catalogo:
            supabase.table("estudiantes").upsert({
                "rut": rut_fmt,
                "nombre": nombre,
                "curso": curso
            }).execute()

        nuevo = {
            "rut": rut_fmt or None,
            "fecha": fecha,
            "hora": hora,
            "nombre": nombre,
            "nombre_normalizado": normalizar_texto(nombre),
            "curso": curso,
            "quien_retira": quien_retira,
            "parentesco": parentesco,
            "motivo": motivo
        }
        res = supabase.table("retiros").insert(nuevo).execute()
        return jsonify({"registro": res.data[0]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/<tabla>/<int:reg_id>", methods=["DELETE"])
@login_requerido
def eliminar_registro(tabla, reg_id):
    if tabla not in ("atrasos", "retiros"):
        return jsonify({"error": "Tabla no válida."}), 400
    if not supabase:
        return jsonify({"error": "Base de datos no conectada."}), 500

    clave = request.headers.get("X-Admin-Key", "")
    if clave != os.environ.get("ADMIN_PASSWORD", "1234"):
        return jsonify({"error": "Clave de Inspectoría incorrecta."}), 403

    try:
        supabase.table(tabla).delete().eq("id", reg_id).execute()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
