import os
import socket
import sqlite3
import sys
import threading
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, redirect, request, send_file, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from reportes import (
        consultar_historial,
        exportar_historial_excel,
        exportar_incidencia_detalle_excel,
        exportar_incidencias_excel,
        exportar_uso_excel,
    )
except ModuleNotFoundError:  # pragma: no cover - compatibilidad con carga como paquete.
    from backend.reportes import (
        consultar_historial,
        exportar_historial_excel,
        exportar_incidencia_detalle_excel,
        exportar_incidencias_excel,
        exportar_uso_excel,
    )

SIN_SENAL_SEGUNDOS = 120
CIERRE_AUTOMATICO_SEGUNDOS = 600

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "aip.db"
FRONTEND_DIR = BASE_DIR.parent / "frontend"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
app.config["IP_SIMULADA"] = os.getenv("IP_SIMULADA")
app.config["SECRET_KEY"] = os.getenv("AIP_SECRET_KEY")
if not app.config["SECRET_KEY"]:
    app.config["SECRET_KEY"] = "dev-insegura-cambiar-antes-de-publicar"
    print("AVISO: se usa una SECRET_KEY de desarrollo. Configure AIP_SECRET_KEY antes de publicar.")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.permanent_session_lifetime = timedelta(minutes=60)

INTENTOS_LOGIN_MAXIMOS = 5
BLOQUEO_LOGIN_SEGUNDOS = 300
intentos_login = {}
bloqueo_intentos = threading.Lock()


def es_solicitud_api() -> bool:
    """Indica si la solicitud requiere una respuesta JSON de autenticación."""
    return request.path.startswith("/api/")


def obtener_admin_sesion():
    """Valida que la cuenta de la sesión siga activa y devuelve sus datos públicos."""
    admin_id = session.get("admin_id")
    if not admin_id:
        return None

    with get_db_connection() as conn:
        fila = conn.execute(
            "SELECT id, usuario, nombre_completo, rol FROM usuarios_admin WHERE id = ? AND activo = 1",
            (admin_id,),
        ).fetchone()
    if fila is None:
        session.clear()
        return None
    return dict(fila)


def login_requerido(funcion):
    """Protege una página o API administrativa y vuelve a comprobar que el usuario siga activo."""
    @wraps(funcion)
    def protegida(*args, **kwargs):
        admin = obtener_admin_sesion()
        if admin is None:
            if es_solicitud_api():
                return jsonify({"ok": False, "mensaje": "Debe iniciar sesión."}), 401
            return redirect("/login.html")
        g.admin = admin
        return funcion(*args, **kwargs)
    return protegida


def rol_requerido(rol):
    """Restringe una ruta protegida a un rol específico."""
    def decorador(funcion):
        @wraps(funcion)
        def protegida(*args, **kwargs):
            if getattr(g, "admin", {}).get("rol") != rol:
                if es_solicitud_api():
                    return jsonify({"ok": False, "mensaje": "No tiene permiso para esta acción."}), 403
                return redirect("/admin.html")
            return funcion(*args, **kwargs)
        return login_requerido(protegida)
    return decorador


def claves_bloqueo_login(usuario: str, ip: str) -> tuple[str, str]:
    """Normaliza las claves del bloqueo para contar por usuario y por dirección IP."""
    return f"usuario:{usuario.casefold()}", f"ip:{ip}"


def login_bloqueado(claves: tuple[str, str], ahora: float) -> bool:
    """Comprueba si el usuario o la IP alcanzaron el tiempo de bloqueo."""
    with bloqueo_intentos:
        return any(intentos_login.get(clave, (0, 0))[1] > ahora for clave in claves)


def registrar_fallo_login(claves: tuple[str, str], ahora: float) -> None:
    """Cuenta el fallo y bloquea durante cinco minutos al alcanzar el límite."""
    with bloqueo_intentos:
        for clave in claves:
            cantidad, bloqueado_hasta = intentos_login.get(clave, (0, 0))
            if bloqueado_hasta <= ahora:
                cantidad += 1
                bloqueado_hasta = ahora + BLOQUEO_LOGIN_SEGUNDOS if cantidad >= INTENTOS_LOGIN_MAXIMOS else 0
            intentos_login[clave] = (cantidad, bloqueado_hasta)


def limpiar_intentos_login(claves: tuple[str, str]) -> None:
    """Reinicia los contadores de usuario e IP después de una autenticación correcta."""
    with bloqueo_intentos:
        for clave in claves:
            intentos_login.pop(clave, None)


def obtener_timestamp() -> str:
    """Devuelve una fecha única para SQLite, usando siempre UTC para evitar desfases por zona horaria."""
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def registrar_bitacora(
    admin_id: int | None,
    accion: str,
    tabla_afectada: str,
    registro_id: int | None,
    detalle: str,
    ip_origen: str | None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Registra una acción administrativa; admite la conexión de la transacción llamadora."""
    valores = (admin_id, accion, tabla_afectada, registro_id, detalle, ip_origen, obtener_timestamp())
    consulta = """
        INSERT INTO bitacora
            (admin_id, accion, tabla_afectada, registro_id, detalle, ip_origen, fecha_hora)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    if conn is not None:
        conn.execute(consulta, valores)
        return

    with get_db_connection() as conexion:
        conexion.execute(consulta, valores)
        conexion.commit()


def obtener_ip_origen() -> str:
    """Obtiene la IP del cliente directo para registrar auditoría."""
    return request.remote_addr or "desconocida"


def es_hash_demo(valor: str | None) -> bool:
    """Identifica si el valor guardado no es un hash real de PIN."""
    if not valor:
        return False
    return valor.startswith("hash_demo_") or valor.startswith("HASH_PENDIENTE_")


def get_db_connection() -> sqlite3.Connection:
    """Abre una conexión a SQLite con la configuración requerida."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def obtener_ip_local_del_host() -> str:
    """Devuelve la IP real de la máquina local, si existe, para evitar falsos 127.0.0.1."""
    try:
        hostnames = socket.gethostbyname_ex(socket.gethostname())
    except OSError:
        return "127.0.0.1"

    for ip in hostnames[2]:
        if ip and not ip.startswith("127."):
            return ip

    return hostnames[2][0] if hostnames[2] else "127.0.0.1"


def obtener_ip_cliente() -> str:
    """Obtiene la IP del cliente y permite forzar una IP de prueba."""
    ip_simulada = app.config.get("IP_SIMULADA")
    if ip_simulada:
        return ip_simulada

    ip_param = request.args.get("ip")
    if ip_param:
        return ip_param.strip()

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    ip = request.remote_addr or "127.0.0.1"
    if ip in ("127.0.0.1", "::1", "0.0.0.0"):
        return obtener_ip_local_del_host()
    return ip


def obtener_equipo_por_ip(ip: str):
    """Busca el equipo activo según la IP del cliente."""
    with get_db_connection() as conn:
        return conn.execute(
            "SELECT id, codigo, ip, estado FROM equipos WHERE ip = ? LIMIT 1",
            (ip,),
        ).fetchone()


def cerrar_sesiones_abiertas(conn: sqlite3.Connection, equipo_id: int, alumno_id: int, fecha_fin: str) -> None:
    """Cierra las sesiones abiertas del equipo y/o del alumno con tipo 'reemplazo'."""
    conn.execute(
        """
        UPDATE sesiones
        SET fecha_hora_fin = ?,
            ultimo_latido = ?,
            tipo_cierre = 'reemplazo',
            cerrado_por = 1
        WHERE fecha_hora_fin IS NULL
          AND (equipo_id = ? OR alumno_id = ?)
        """,
        (fecha_fin, fecha_fin, equipo_id, alumno_id),
    )


def obtener_sesion_abierta_equipo(conn: sqlite3.Connection, equipo_id: int):
    """Devuelve la sesión abierta del equipo, si existe."""
    return conn.execute(
        """
        SELECT id, alumno_id, equipo_id, fecha_hora_inicio, ultimo_latido
        FROM sesiones
        WHERE equipo_id = ? AND fecha_hora_fin IS NULL
        ORDER BY fecha_hora_inicio DESC
        LIMIT 1
        """,
        (equipo_id,),
    ).fetchone()


def obtener_estado_equipo_actual(conn: sqlite3.Connection, equipo: sqlite3.Row):
    """Devuelve el estado de la sesión abierta del equipo, si existe."""
    sesion = obtener_sesion_abierta_equipo(conn, equipo["id"])
    if sesion is None:
        return {
            "ok": True,
            "ocupado": False,
            "registrado": False,
            "codigo": equipo["codigo"],
            "mensaje": "",
        }

    alumno = conn.execute(
        "SELECT nombres, apellidos, grado, seccion FROM alumnos WHERE id = ? LIMIT 1",
        (sesion["alumno_id"],),
    ).fetchone()

    nombre_alumno = " ".join(filtro for filtro in (alumno["nombres"], alumno["apellidos"]) if filtro).strip() if alumno else "Alumno"
    curso = f"{alumno['grado']}.º {alumno['seccion']}" if alumno else "Curso no disponible"

    return {
        "ok": True,
        "ocupado": True,
        "registrado": True,
        "codigo": equipo["codigo"],
        "alumno": nombre_alumno,
        "grado": alumno["grado"] if alumno else None,
        "seccion": alumno["seccion"] if alumno else None,
        "curso": curso,
        "hora_inicio": sesion["fecha_hora_inicio"],
        "ultimo_latido": sesion["ultimo_latido"],
        "mensaje": "Este equipo ya está registrado.",
    }


def cerrar_sesion_por_tipo(conn: sqlite3.Connection, equipo_id: int, tipo_cierre: str, fecha_fin: str, cerrado_por: int | None = None) -> int:
    """Cierra la sesión abierta del equipo con el tipo indicado y devuelve la cantidad de filas afectadas."""
    if tipo_cierre == 'automatico':
        return conn.execute(
            """
            UPDATE sesiones
            SET fecha_hora_fin = ultimo_latido,
                tipo_cierre = 'automatico',
                cerrado_por = NULL
            WHERE equipo_id = ?
              AND fecha_hora_fin IS NULL
              AND ultimo_latido IS NOT NULL
            """,
            (equipo_id,),
        ).rowcount

    return conn.execute(
        """
        UPDATE sesiones
        SET fecha_hora_fin = ?,
            tipo_cierre = ?,
            cerrado_por = ?
        WHERE equipo_id = ?
          AND fecha_hora_fin IS NULL
        """,
        (fecha_fin, tipo_cierre, cerrado_por, equipo_id),
    ).rowcount


def cerrar_sesiones_obsoletas() -> int:
    """Cierra sesiones abiertas con latido vencido y las marca como automáticas."""
    with get_db_connection() as conn:
        filas = conn.execute(
            """
            UPDATE sesiones
            SET fecha_hora_fin = ultimo_latido,
                tipo_cierre = 'automatico',
                cerrado_por = NULL
            WHERE fecha_hora_fin IS NULL
              AND ultimo_latido IS NOT NULL
              AND (strftime('%s', 'now') - strftime('%s', ultimo_latido)) > ?
            """,
            (CIERRE_AUTOMATICO_SEGUNDOS,),
        )
        conn.commit()
        return filas.rowcount


def iniciar_hilo_cierre_automatico() -> None:
    """Inicia el hilo de limpieza automática solo una vez por arranque y sin duplicarse en debug."""
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    if getattr(app, "_hilo_cierre_automatico", None) and app._hilo_cierre_automatico.is_alive():
        return

    cerrar_sesiones_obsoletas()

    def hilo():
        while True:
            cerrar_sesiones_obsoletas()
            time.sleep(60)

    hilo_automatico = threading.Thread(target=hilo, daemon=True, name="aip-cierre-automatico")
    app._hilo_cierre_automatico = hilo_automatico
    hilo_automatico.start()


def validar_pin(alumno: sqlite3.Row, pin_ingresado: str | None) -> bool:
    """Valida el PIN del alumno solo cuando el hash guardado es real."""
    if not alumno["pin_hash"]:
        return True

    if es_hash_demo(alumno["pin_hash"]):
        return True

    if pin_ingresado is None or pin_ingresado == "":
        return False

    return check_password_hash(alumno["pin_hash"], pin_ingresado)


@app.route("/")
def index():
    """Sirve la pantalla de registro principal."""
    return send_from_directory(str(FRONTEND_DIR), "registro.html")


@app.route("/registro")
def registro():
    """Alias para acceder a la pantalla de registro."""
    return send_from_directory(str(FRONTEND_DIR), "registro.html")


@app.route("/login")
@app.route("/login.html")
def login_page():
    """Sirve la pantalla de acceso administrativo."""
    return send_from_directory(str(FRONTEND_DIR), "login.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    """Valida las credenciales y crea una sesión administrativa firmada."""
    datos = request.get_json(silent=True) or request.form.to_dict() or {}
    usuario = str(datos.get("usuario") or "").strip()
    contrasena = datos.get("contrasena")
    if not isinstance(contrasena, str):
        contrasena = ""

    ip = request.remote_addr or "desconocida"
    claves = claves_bloqueo_login(usuario, ip)
    ahora = time.monotonic()
    mensaje_error = "Usuario o contraseña incorrectos"
    if login_bloqueado(claves, ahora):
        registrar_bitacora(
            None, "login_fallido", "usuarios_admin", None,
            f"Usuario: {usuario[:100]} (intento bloqueado)", obtener_ip_origen(),
        )
        return jsonify({"ok": False, "mensaje": mensaje_error}), 401

    with get_db_connection() as conn:
        admin = conn.execute(
            "SELECT id, usuario, password_hash, nombre_completo, rol FROM usuarios_admin WHERE usuario = ? AND activo = 1",
            (usuario,),
        ).fetchone()

    if admin is None or not check_password_hash(admin["password_hash"], contrasena):
        registrar_fallo_login(claves, ahora)
        registrar_bitacora(
            None, "login_fallido", "usuarios_admin", None,
            f"Usuario: {usuario[:100]}", obtener_ip_origen(),
        )
        return jsonify({"ok": False, "mensaje": mensaje_error}), 401

    limpiar_intentos_login(claves)
    registrar_bitacora(
        admin["id"], "login_correcto", "usuarios_admin", admin["id"],
        "Inicio de sesión", obtener_ip_origen(),
    )
    session.clear()
    session.permanent = True
    session["admin_id"] = admin["id"]
    return jsonify({
        "ok": True,
        "usuario": {
            "usuario": admin["usuario"],
            "nombre_completo": admin["nombre_completo"],
            "rol": admin["rol"],
        },
    })


@app.route("/api/logout", methods=["POST"])
def api_logout():
    """Finaliza la sesión administrativa actual."""
    admin_id = session.get("admin_id")
    if admin_id is not None:
        registrar_bitacora(
            admin_id, "logout", "usuarios_admin", admin_id,
            "Cierre de sesión", obtener_ip_origen(),
        )
    session.clear()
    return jsonify({"ok": True, "mensaje": "Sesión cerrada."})


@app.route("/api/sesion_admin")
def api_sesion_admin():
    """Devuelve el usuario activo de la sesión, si existe."""
    admin = obtener_admin_sesion()
    if admin is None:
        return jsonify({"autenticado": False})
    return jsonify({"autenticado": True, "usuario": admin})


@app.route("/api/cambiar_password", methods=["POST"])
@login_requerido
def api_cambiar_password():
    """Actualiza la contraseña tras validar la contraseña actual y la longitud mínima."""
    datos = request.get_json(silent=True) or request.form.to_dict() or {}
    actual = datos.get("contrasena_actual")
    nueva = datos.get("contrasena_nueva")
    if not isinstance(actual, str) or not isinstance(nueva, str):
        return jsonify({"ok": False, "mensaje": "Complete ambas contraseñas."}), 400
    if len(nueva) < 8:
        return jsonify({"ok": False, "mensaje": "La nueva contraseña debe tener al menos 8 caracteres."}), 400

    with get_db_connection() as conn:
        admin = conn.execute(
            "SELECT password_hash FROM usuarios_admin WHERE id = ? AND activo = 1",
            (g.admin["id"],),
        ).fetchone()
        if admin is None or not check_password_hash(admin["password_hash"], actual):
            return jsonify({"ok": False, "mensaje": "La contraseña actual no es correcta."}), 401
        conn.execute(
            "UPDATE usuarios_admin SET password_hash = ? WHERE id = ?",
            (generate_password_hash(nueva), g.admin["id"]),
        )
        registrar_bitacora(
            g.admin["id"], "cambio_password", "usuarios_admin", g.admin["id"],
            "Cambio de contraseña", obtener_ip_origen(), conn,
        )
        conn.commit()
    return jsonify({"ok": True, "mensaje": "Contraseña actualizada correctamente."})


@app.route("/api/equipo")
def api_equipo():
    """Devuelve el equipo detectado para la IP del cliente."""
    ip_cliente = obtener_ip_cliente()
    equipo = obtener_equipo_por_ip(ip_cliente)

    if equipo is None or equipo["estado"] != "activo":
        return jsonify({
            "codigo": None,
            "estado": "no_registrado",
            "mensaje": "Este equipo no está registrado. Avisa al docente.",
            "ip": ip_cliente,
        })

    return jsonify({
        "codigo": equipo["codigo"],
        "estado": equipo["estado"],
        "mensaje": "",
        "ip": ip_cliente,
    })


@app.route("/api/estado_equipo")
def api_estado_equipo():
    """Devuelve el estado real del equipo para la IP del cliente, sin depender de cookies ni almacenamiento local."""
    ip_cliente = obtener_ip_cliente()
    with get_db_connection() as conn:
        equipo = obtener_equipo_por_ip(ip_cliente)
        if equipo is None or equipo["estado"] != "activo":
            return jsonify({
                "ok": True,
                "ocupado": False,
                "registrado": False,
                "codigo": None,
                "mensaje": "Este equipo no está registrado. Avisa al docente.",
            })

        estado = obtener_estado_equipo_actual(conn, equipo)
        return jsonify(estado)


@app.route("/api/equipo/sesion_actual")
def api_equipos_sesion_actual():
    """Mantiene compatibilidad con la vista actual para detectar si ya hay sesión abierta."""
    ip_cliente = obtener_ip_cliente()
    with get_db_connection() as conn:
        equipo = obtener_equipo_por_ip(ip_cliente)
        if equipo is None or equipo["estado"] != "activo":
            return jsonify({
                "ok": True,
                "registrado": False,
                "codigo": None,
                "mensaje": "Este equipo no está registrado. Avisa al docente.",
            })

        estado = obtener_estado_equipo_actual(conn, equipo)
        return jsonify({
            "ok": True,
            "registrado": estado.get("registrado", False),
            "codigo": estado.get("codigo"),
            "alumno": estado.get("alumno"),
            "curso": estado.get("curso"),
            "grado": estado.get("grado"),
            "seccion": estado.get("seccion"),
            "hora_inicio": estado.get("hora_inicio"),
            "ultimo_latido": estado.get("ultimo_latido"),
            "mensaje": estado.get("mensaje", ""),
        })


@app.route("/api/grados")
def api_grados():
    """Lista los grados con alumnos activos."""
    with get_db_connection() as conn:
        filas = conn.execute(
            "SELECT DISTINCT grado FROM alumnos WHERE activo = 1 ORDER BY grado"
        ).fetchall()
    return jsonify([fila["grado"] for fila in filas])


@app.route("/api/secciones/<int:grado>")
def api_secciones(grado):
    """Lista las secciones activas para un grado dado."""
    with get_db_connection() as conn:
        filas = conn.execute(
            "SELECT DISTINCT seccion FROM alumnos WHERE activo = 1 AND grado = ? ORDER BY seccion",
            (grado,),
        ).fetchall()
    return jsonify([fila["seccion"] for fila in filas])


@app.route("/api/alumnos/<int:grado>/<seccion>")
def api_alumnos(grado, seccion):
    """Devuelve los alumnos activos, ordenados por apellidos."""
    with get_db_connection() as conn:
        filas = conn.execute(
            """
            SELECT id, codigo_alumno, nombres, apellidos, pin_hash, grado, seccion
            FROM alumnos
            WHERE activo = 1 AND grado = ? AND seccion = ?
            ORDER BY apellidos COLLATE NOCASE, nombres COLLATE NOCASE
            """,
            (grado, seccion),
        ).fetchall()

    alumnos = []
    for fila in filas:
        alumnos.append({
            "id": fila["id"],
            "codigo_alumno": fila["codigo_alumno"],
            "nombres": fila["nombres"],
            "apellidos": fila["apellidos"],
            "nombre_completo": f"{fila['nombres']} {fila['apellidos']}",
            "grado": fila["grado"],
            "seccion": fila["seccion"],
            "tiene_pin": bool(fila["pin_hash"]) and not es_hash_demo(fila["pin_hash"]),
        })

    return jsonify(alumnos)


@app.route("/api/alumnos/buscar")
def api_alumnos_buscar():
    """Busca alumnos por nombre completo sin depender del curso."""
    termino = (request.args.get("q") or "").strip()

    with get_db_connection() as conn:
        if not termino:
            filas = conn.execute(
                """
                SELECT id, codigo_alumno, nombres, apellidos, pin_hash, grado, seccion
                FROM alumnos
                WHERE activo = 1
                ORDER BY apellidos COLLATE NOCASE, nombres COLLATE NOCASE
                LIMIT 200
                """
            ).fetchall()
        else:
            valor = f"%{termino.lower()}%"
            filas = conn.execute(
                """
                SELECT id, codigo_alumno, nombres, apellidos, pin_hash, grado, seccion
                FROM alumnos
                WHERE activo = 1
                  AND (
                        lower(codigo_alumno) LIKE ?
                     OR lower(nombres) LIKE ?
                     OR lower(apellidos) LIKE ?
                     OR lower(nombres || ' ' || apellidos) LIKE ?
                  )
                ORDER BY apellidos COLLATE NOCASE, nombres COLLATE NOCASE
                LIMIT 50
                """,
                (valor, valor, valor, valor),
            ).fetchall()

    alumnos = []
    for fila in filas:
        alumnos.append({
            "id": fila["id"],
            "codigo_alumno": fila["codigo_alumno"],
            "nombres": fila["nombres"],
            "apellidos": fila["apellidos"],
            "nombre_completo": f"{fila['nombres']} {fila['apellidos']}",
            "grado": fila["grado"],
            "seccion": fila["seccion"],
            "tiene_pin": bool(fila["pin_hash"]) and not es_hash_demo(fila["pin_hash"]),
        })

    return jsonify(alumnos)


@app.route("/api/registrar", methods=["POST"])
def api_registrar():
    """Registra la sesión del alumno en el equipo detectado."""
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    alumno_id = data.get("alumno_id")
    alumno_nombre = (data.get("alumno_nombre") or "").strip()
    pin = data.get("pin")

    if alumno_id in (None, "") and not alumno_nombre:
        return jsonify({"ok": False, "mensaje": "Seleccioná o buscá un alumno antes de registrar."}), 400

    if alumno_id not in (None, ""):
        try:
            alumno_id = int(alumno_id)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "mensaje": "El alumno seleccionado no es válido."}), 400

    ip_cliente = obtener_ip_cliente()
    equipo = obtener_equipo_por_ip(ip_cliente)
    if equipo is None or equipo["estado"] != "activo":
        return jsonify({
            "ok": False,
            "mensaje": "Este equipo no está registrado. Avisa al docente.",
        }), 404

    with get_db_connection() as conn:
        if alumno_id is not None:
            alumno = conn.execute(
                "SELECT id, nombres, apellidos, pin_hash FROM alumnos WHERE id = ? AND activo = 1",
                (alumno_id,),
            ).fetchone()
        else:
            valor = f"%{alumno_nombre.lower()}%"
            filas = conn.execute(
                """
                SELECT id, nombres, apellidos, pin_hash
                FROM alumnos
                WHERE activo = 1
                  AND (
                        lower(nombres) LIKE ?
                     OR lower(apellidos) LIKE ?
                     OR lower(nombres || ' ' || apellidos) LIKE ?
                  )
                ORDER BY apellidos COLLATE NOCASE, nombres COLLATE NOCASE
                LIMIT 10
                """,
                (valor, valor, valor),
            ).fetchall()

            if not filas:
                return jsonify({"ok": False, "mensaje": "No encontré al alumno buscado."}), 404

            if len(filas) > 1:
                alumnos = [f"{fila['nombres']} {fila['apellidos']}" for fila in filas]
                return jsonify({
                    "ok": False,
                    "mensaje": "Hay varios alumnos con ese nombre. Buscá más exacto.",
                    "alumnos": alumnos,
                }), 409

            alumno = filas[0]
            alumno_id = alumno["id"]

        if alumno is None:
            return jsonify({"ok": False, "mensaje": "El alumno no existe o no está activo."}), 404

        if not validar_pin(alumno, pin):
            return jsonify({"ok": False, "mensaje": "PIN incorrecto."}), 401

        sesion_existente = obtener_sesion_abierta_equipo(conn, equipo["id"])
        if sesion_existente is not None:
            return jsonify({
                "ok": False,
                "mensaje": "Este equipo ya está ocupado. Cerrá la sesión actual o esperá a que termine.",
            }), 409

        fecha_actual = obtener_timestamp()

        try:
            cerrar_sesiones_abiertas(conn, equipo["id"], alumno_id, fecha_actual)
            conn.execute(
                """
                INSERT INTO sesiones (alumno_id, equipo_id, fecha_hora_inicio, ultimo_latido)
                VALUES (?, ?, ?, ?)
                """,
                (alumno_id, equipo["id"], fecha_actual, fecha_actual),
            )
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            return jsonify({"ok": False, "mensaje": "No se pudo registrar la sesión. Intentá nuevamente."}), 500

    return jsonify({
        "ok": True,
        "mensaje": f"Registrado en {equipo['codigo']}. ¡Buen trabajo!",
        "equipo": equipo["codigo"],
    })


@app.route("/api/cerrar_alumno", methods=["POST"])
def api_cerrar_alumno():
    """Cierra la sesión activa del equipo cuando termina la sesión del alumno."""
    ip_cliente = obtener_ip_cliente()
    with get_db_connection() as conn:
        equipo = obtener_equipo_por_ip(ip_cliente)
        if equipo is None or equipo["estado"] != "activo":
            return jsonify({"ok": False, "mensaje": "Este equipo no está registrado. Avisa al docente."}), 404

        sesion = obtener_sesion_abierta_equipo(conn, equipo["id"])
        if sesion is None:
            return jsonify({"ok": True, "mensaje": "No había una sesión activa en este equipo."})

        fecha_fin = obtener_timestamp()
        conn.execute(
            """
            UPDATE sesiones
            SET fecha_hora_fin = ?,
                tipo_cierre = 'alumno',
                cerrado_por = 1
            WHERE id = ? AND fecha_hora_fin IS NULL
            """,
            (fecha_fin, sesion["id"]),
        )
        conn.commit()

    return jsonify({"ok": True, "mensaje": "Sesión cerrada correctamente."})


@app.route("/api/latido", methods=["POST"])
def api_latido():
    """Actualiza el último latido de la sesión abierta del equipo."""
    ip_cliente = obtener_ip_cliente()
    with get_db_connection() as conn:
        equipo = obtener_equipo_por_ip(ip_cliente)
        if equipo is None or equipo["estado"] != "activo":
            return jsonify({"ok": False, "mensaje": "Este equipo no está registrado. Avisa al docente."}), 404

        sesion = obtener_sesion_abierta_equipo(conn, equipo["id"])
        if sesion is None:
            return jsonify({"ok": False, "mensaje": "No hay una sesión activa para este equipo."}), 404

        ahora = obtener_timestamp()
        conn.execute(
            """
            UPDATE sesiones
            SET ultimo_latido = ?
            WHERE id = ? AND fecha_hora_fin IS NULL
            """,
            (ahora, sesion["id"]),
        )
        conn.commit()

    return jsonify({"ok": True, "mensaje": "Latido registrado."})


@app.route("/api/admin/cerrar/<codigo_equipo>", methods=["POST"])
@login_requerido
def api_admin_cerrar_equipo(codigo_equipo):
    """Cierra la sesión abierta de un equipo por el usuario autenticado."""
    with get_db_connection() as conn:
        equipo = conn.execute(
            "SELECT id, codigo FROM equipos WHERE codigo = ? LIMIT 1",
            (codigo_equipo,),
        ).fetchone()
        if equipo is None:
            return jsonify({"ok": False, "mensaje": "No existe ese equipo."}), 404

        fecha_fin = obtener_timestamp()
        sesion = conn.execute(
            "SELECT id FROM sesiones WHERE equipo_id = ? AND fecha_hora_fin IS NULL LIMIT 1",
            (equipo["id"],),
        ).fetchone()
        fila = conn.execute(
            """
            UPDATE sesiones
            SET fecha_hora_fin = ?,
                tipo_cierre = 'admin',
                cerrado_por = ?
            WHERE equipo_id = ? AND fecha_hora_fin IS NULL
            """,
            (fecha_fin, g.admin["id"], equipo["id"]),
        )
        cantidad_cerrada = fila.rowcount
        if cantidad_cerrada:
            registrar_bitacora(
                g.admin["id"], "cierre_sesion_individual", "sesiones",
                sesion["id"] if sesion else None,
                f"Equipo {equipo['codigo']}; sesiones cerradas: {cantidad_cerrada}",
                obtener_ip_origen(), conn,
            )
        conn.commit()

    if cantidad_cerrada == 0:
        return jsonify({"ok": True, "mensaje": "No había ninguna sesión abierta en ese equipo."})

    return jsonify({"ok": True, "mensaje": f"Sesión cerrada en {equipo['codigo']} por administración."})


@app.route("/api/admin/cerrar_todas", methods=["POST"])
@rol_requerido("admin")
def api_admin_cerrar_todas():
    """Cierra todas las sesiones abiertas con tipo de cierre 'admin'."""
    fecha_fin = obtener_timestamp()
    with get_db_connection() as conn:
        filas = conn.execute(
            """
            UPDATE sesiones
            SET fecha_hora_fin = ?,
                tipo_cierre = 'admin',
                cerrado_por = ?
            WHERE fecha_hora_fin IS NULL
            """,
            (fecha_fin, g.admin["id"]),
        )
        cantidad_cerrada = filas.rowcount
        registrar_bitacora(
            g.admin["id"], "cierre_sesiones_masivo", "sesiones", None,
            f"Sesiones cerradas: {cantidad_cerrada}", obtener_ip_origen(), conn,
        )
        conn.commit()

    return jsonify({
        "ok": True,
        "mensaje": "Se cerraron todas las sesiones abiertas.",
        "cantidad": cantidad_cerrada,
    })


@app.route("/api/admin/estado")
@login_requerido
def api_admin_estado():
    """Devuelve el estado real de todos los equipos, sumando el estado del equipo sin romper datos existentes."""
    with get_db_connection() as conn:
        filas = conn.execute(
            """
            SELECT
                e.id,
                e.codigo,
                e.ip,
                e.nombre_host,
                e.tipo,
                e.ubicacion,
                e.estado AS equipo_estado,
                CASE
                    WHEN s.id IS NULL THEN 'libre'
                    WHEN s.ultimo_latido IS NOT NULL AND (strftime('%s', 'now') - strftime('%s', s.ultimo_latido)) > ? THEN 'sin señal'
                    ELSE 'ocupado'
                END AS estado_actual,
                a.nombres AS alumno_nombres,
                a.apellidos AS alumno_apellidos,
                a.grado,
                a.seccion,
                s.fecha_hora_inicio,
                s.ultimo_latido
            FROM equipos e
            LEFT JOIN sesiones s ON s.equipo_id = e.id AND s.fecha_hora_fin IS NULL
            LEFT JOIN alumnos a ON a.id = s.alumno_id
            ORDER BY e.codigo
            """,
            (SIN_SENAL_SEGUNDOS,),
        ).fetchall()

    equipos = []
    for fila in filas:
        estado_actual = fila["estado_actual"]
        estado = "sin_señal" if estado_actual == "sin señal" else estado_actual
        nombre_alumno = " ".join(filtro for filtro in (fila["alumno_nombres"], fila["alumno_apellidos"]) if filtro).strip()
        equipos.append({
            "id": fila["id"],
            "codigo": fila["codigo"],
            "ip": fila["ip"],
            "nombre_host": fila["nombre_host"],
            "tipo": fila["tipo"],
            "ubicacion": fila["ubicacion"],
            "equipo_estado": fila["equipo_estado"],
            "estado": estado,
            "alumno": nombre_alumno or "Sin alumno",
            "grado": fila["grado"] if fila["grado"] is not None else "—",
            "seccion": fila["seccion"] if fila["seccion"] is not None else "—",
            "horaInicio": fila["fecha_hora_inicio"],
            "ultimoLatido": fila["ultimo_latido"],
        })

    return jsonify(equipos)


@app.route("/admin")
@app.route("/admin.html")
@login_requerido
def admin_page():
    """Sirve la pantalla del panel de administración."""
    return send_from_directory(str(FRONTEND_DIR), "admin.html")


@app.route("/incidencias")
@app.route("/incidencias.html")
@login_requerido
def incidencias_page():
    """Sirve la pantalla de gestión de incidencias."""
    return send_from_directory(str(FRONTEND_DIR), "incidencias.html")


@app.route("/historial")
@app.route("/historial.html")
@login_requerido
def historial_page():
    """Sirve la pantalla de historial de sesiones."""
    return send_from_directory(str(FRONTEND_DIR), "historial.html")


@app.route("/bitacora")
@app.route("/bitacora.html")
@rol_requerido("admin")
def bitacora_page():
    """Sirve la bitácora administrativa solo para el rol admin."""
    return send_from_directory(str(FRONTEND_DIR), "bitacora.html")


@app.route("/api/bitacora/usuarios")
@rol_requerido("admin")
def api_usuarios_bitacora():
    """Devuelve usuarios disponibles para el filtro de la bitácora."""
    with get_db_connection() as conn:
        filas = conn.execute(
            "SELECT id, usuario, nombre_completo FROM usuarios_admin ORDER BY usuario COLLATE NOCASE"
        ).fetchall()
    return jsonify([dict(fila) for fila in filas])


@app.route("/api/bitacora")
@rol_requerido("admin")
def api_listar_bitacora():
    """Lista la bitácora en orden descendente con filtros y paginación."""
    usuario = (request.args.get("usuario") or "").strip().lower()
    accion = (request.args.get("accion") or "").strip()
    desde = (request.args.get("desde") or "").strip()
    hasta = (request.args.get("hasta") or "").strip()
    try:
        pagina = max(1, int(request.args.get("pagina", 1)))
        por_pagina = min(100, max(1, int(request.args.get("por_pagina", 20))))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "mensaje": "Los filtros de paginación no son válidos."}), 400

    condiciones = ["1 = 1"]
    parametros = []
    if usuario:
        condiciones.append(
            "(lower(coalesce(ua.usuario, '')) LIKE ? "
            "OR lower(coalesce(ua.nombre_completo, '')) LIKE ? "
            "OR lower(coalesce(b.detalle, '')) LIKE ?)"
        )
        valor_usuario = f"%{usuario}%"
        parametros.extend([valor_usuario, valor_usuario, valor_usuario])
    if accion:
        condiciones.append("b.accion = ?")
        parametros.append(accion)
    if desde:
        condiciones.append("date(b.fecha_hora) >= date(?)")
        parametros.append(desde)
    if hasta:
        condiciones.append("date(b.fecha_hora) <= date(?)")
        parametros.append(hasta)
    where_sql = " AND ".join(condiciones)

    with get_db_connection() as conn:
        total = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM bitacora b
            LEFT JOIN usuarios_admin ua ON ua.id = b.admin_id
            WHERE {where_sql}
            """,
            parametros,
        ).fetchone()[0]
        filas = conn.execute(
            f"""
            SELECT b.id, b.admin_id, ua.usuario, ua.nombre_completo, b.accion,
                   b.tabla_afectada, b.registro_id, b.detalle, b.ip_origen, b.fecha_hora
            FROM bitacora b
            LEFT JOIN usuarios_admin ua ON ua.id = b.admin_id
            WHERE {where_sql}
            ORDER BY b.fecha_hora DESC, b.id DESC
            LIMIT ? OFFSET ?
            """,
            parametros + [por_pagina, (pagina - 1) * por_pagina],
        ).fetchall()

    total_paginas = 0 if total == 0 else (total + por_pagina - 1) // por_pagina
    return jsonify({
        "items": [dict(fila) for fila in filas],
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total_paginas": total_paginas,
    })


def obtener_sesion_probable(conn: sqlite3.Connection, equipo_id: int, fecha_reporte: str):
    """Determina el responsable probable de la incidencia según la regla de negocio exigida."""
    sesion_abierta = conn.execute(
        """
        SELECT s.id, s.alumno_id, s.equipo_id, s.fecha_hora_inicio, s.fecha_hora_fin, s.tipo_cierre,
               a.nombres, a.apellidos, a.grado, a.seccion, a.codigo_alumno
        FROM sesiones s
        JOIN alumnos a ON a.id = s.alumno_id
        WHERE s.equipo_id = ?
          AND s.fecha_hora_fin IS NULL
        ORDER BY s.fecha_hora_inicio DESC
        LIMIT 1
        """,
        (equipo_id,),
    ).fetchone()
    if sesion_abierta is not None:
        return sesion_abierta

    return conn.execute(
        """
        SELECT s.id, s.alumno_id, s.equipo_id, s.fecha_hora_inicio, s.fecha_hora_fin, s.tipo_cierre,
               a.nombres, a.apellidos, a.grado, a.seccion, a.codigo_alumno
        FROM sesiones s
        JOIN alumnos a ON a.id = s.alumno_id
        WHERE s.equipo_id = ?
          AND s.fecha_hora_inicio <= ?
          AND s.fecha_hora_fin IS NOT NULL
          AND s.fecha_hora_fin <= ?
        ORDER BY s.fecha_hora_fin DESC, s.fecha_hora_inicio DESC
        LIMIT 1
        """,
        (equipo_id, fecha_reporte, fecha_reporte),
    ).fetchone()


def serializar_responsable(sesion):
    """Normaliza la sesión responsable para devolver JSON limpio."""
    if sesion is None:
        return None
    nombre_alumno = " ".join(filtro for filtro in (sesion["nombres"], sesion["apellidos"]) if filtro).strip()
    return {
        "id": sesion["id"],
        "alumno_id": sesion["alumno_id"],
        "codigo_alumno": sesion["codigo_alumno"],
        "alumno": nombre_alumno or "Sin alumno",
        "grado": sesion["grado"],
        "seccion": sesion["seccion"],
        "inicio": sesion["fecha_hora_inicio"],
        "fin": sesion["fecha_hora_fin"],
        "tipo_cierre": sesion["tipo_cierre"],
    }


@app.route("/api/incidencias", methods=["POST"])
@login_requerido
def api_crear_incidencia():
    """Crea una nueva incidencia con responsable probable y datos mínimos requeridos."""
    data = request.get_json(silent=True) or {}
    equipo_codigo = (data.get("equipo") or data.get("equipo_codigo") or "").strip()
    descripcion = (data.get("descripcion") or "").strip()
    severidad = (data.get("gravedad") or "leve").strip().lower()

    if not equipo_codigo:
        return jsonify({"ok": False, "mensaje": "Debe indicar el equipo."}), 400
    if not descripcion:
        return jsonify({"ok": False, "mensaje": "La descripción de la incidencia es obligatoria."}), 400
    if severidad not in {"leve", "moderada", "grave"}:
        return jsonify({"ok": False, "mensaje": "La severidad debe ser leve, moderada o grave."}), 400

    with get_db_connection() as conn:
        equipo = conn.execute(
            "SELECT id, codigo FROM equipos WHERE codigo = ? LIMIT 1",
            (equipo_codigo,),
        ).fetchone()
        if equipo is None:
            return jsonify({"ok": False, "mensaje": "No existe ese equipo."}), 404

        fecha_reporte = obtener_timestamp()
        sesion_probable = obtener_sesion_probable(conn, equipo["id"], fecha_reporte)
        cursor = conn.execute(
            """
            INSERT INTO incidencias (equipo_id, descripcion, severidad, estado, fecha_hora_reporte, reportado_por, sesion_probable_id)
            VALUES (?, ?, ?, 'abierta', ?, ?, ?)
            """,
            (equipo["id"], descripcion, severidad, fecha_reporte, g.admin["id"], sesion_probable["id"] if sesion_probable else None),
        )
        incidencia_id = cursor.lastrowid
        registrar_bitacora(
            g.admin["id"], "creacion_incidencia", "incidencias", incidencia_id,
            f"Equipo {equipo['codigo']}; severidad {severidad}",
            obtener_ip_origen(), conn,
        )
        conn.commit()

    return jsonify({
        "ok": True,
        "mensaje": "Incidencia registrada correctamente.",
        "incidencia_id": incidencia_id,
        "responsable_probable": serializar_responsable(sesion_probable),
    })


@app.route("/api/incidencias")
@login_requerido
def api_listar_incidencias():
    """Lista incidencias con filtros opcionales y paginación simple."""
    estado = (request.args.get("estado") or "").strip()
    gravedad = (request.args.get("gravedad") or "").strip()
    equipo = (request.args.get("equipo") or "").strip()
    desde = (request.args.get("desde") or "").strip()
    hasta = (request.args.get("hasta") or "").strip()
    pagina = max(1, int(request.args.get("pagina", 1) or 1))
    por_pagina = max(1, int(request.args.get("por_pagina", 20) or 20))

    sql = """
        SELECT
            i.id,
            i.descripcion,
            i.severidad,
            i.estado,
            i.fecha_hora_reporte,
            i.fecha_resolucion,
            i.solucion,
            e.codigo AS equipo,
            a.nombres,
            a.apellidos,
            a.grado,
            a.seccion
        FROM incidencias i
        JOIN equipos e ON e.id = i.equipo_id
        LEFT JOIN sesiones s ON s.id = i.sesion_probable_id
        LEFT JOIN alumnos a ON a.id = s.alumno_id
        WHERE 1 = 1
    """
    params = []
    if estado:
        sql += " AND i.estado = ? "
        params.append(estado)
    if gravedad:
        sql += " AND i.severidad = ? "
        params.append(gravedad)
    if equipo:
        sql += " AND lower(e.codigo) = lower(?) "
        params.append(equipo)
    if desde:
        sql += " AND date(i.fecha_hora_reporte) >= date(?) "
        params.append(desde)
    if hasta:
        sql += " AND date(i.fecha_hora_reporte) <= date(?) "
        params.append(hasta)

    sql_total = "SELECT COUNT(*) FROM (" + sql + ")"
    with get_db_connection() as conn:
        total = conn.execute(sql_total, params).fetchone()[0]
        orden_sql = sql + " ORDER BY i.fecha_hora_reporte DESC LIMIT ? OFFSET ? "
        filas = conn.execute(orden_sql, params + [por_pagina, (pagina - 1) * por_pagina]).fetchall()

    items = []
    for fila in filas:
        responsable = " ".join(filtro for filtro in (fila["nombres"], fila["apellidos"]) if filtro).strip()
        items.append({
            "id": fila["id"],
            "equipo": fila["equipo"],
            "descripcion": fila["descripcion"],
            "severidad": fila["severidad"],
            "estado": fila["estado"],
            "fecha_hora_reporte": fila["fecha_hora_reporte"],
            "fecha_resolucion": fila["fecha_resolucion"],
            "solucion": fila["solucion"],
            "responsable_probable": {
                "alumno": responsable or "Sin alumno",
                "grado": fila["grado"],
                "seccion": fila["seccion"],
            } if fila["nombres"] or fila["apellidos"] else None,
        })

    total_paginas = 0 if total == 0 else max(1, (total + por_pagina - 1) // por_pagina)
    return jsonify({
        "items": items,
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total_paginas": total_paginas,
    })


@app.route("/api/incidencias/<int:incidencia_id>")
@login_requerido
def api_detalle_incidencia(incidencia_id):
    """Devuelve el detalle completo de una incidencia con responsable y 5 sesiones previas."""
    with get_db_connection() as conn:
        incidencia = conn.execute(
            """
            SELECT i.id, i.descripcion, i.severidad, i.estado, i.solucion,
                   i.fecha_hora_reporte, i.fecha_resolucion, i.sesion_probable_id,
                   e.codigo AS equipo_codigo, e.id AS equipo_id
            FROM incidencias i
            JOIN equipos e ON e.id = i.equipo_id
            WHERE i.id = ?
            """,
            (incidencia_id,),
        ).fetchone()
        if incidencia is None:
            return jsonify({"ok": False, "mensaje": "No existe esa incidencia."}), 404

        responsable = None
        if incidencia["sesion_probable_id"] is not None:
            responsable_sesion = conn.execute(
                """
                SELECT s.id, s.alumno_id, s.fecha_hora_inicio, s.fecha_hora_fin, s.tipo_cierre,
                       a.nombres, a.apellidos, a.grado, a.seccion, a.codigo_alumno
                FROM sesiones s
                JOIN alumnos a ON a.id = s.alumno_id
                WHERE s.id = ?
                """,
                (incidencia["sesion_probable_id"],),
            ).fetchone()
            responsable = serializar_responsable(responsable_sesion)

        sesiones_previas = conn.execute(
            """
            SELECT s.id, s.alumno_id, s.fecha_hora_inicio, s.fecha_hora_fin, s.tipo_cierre,
                   a.nombres, a.apellidos, a.grado, a.seccion, a.codigo_alumno
            FROM sesiones s
            JOIN alumnos a ON a.id = s.alumno_id
            WHERE s.equipo_id = ?
              AND s.fecha_hora_inicio < ?
            ORDER BY s.fecha_hora_inicio DESC
            LIMIT 5
            """,
            (incidencia["equipo_id"], incidencia["fecha_hora_reporte"]),
        ).fetchall()

    return jsonify({
        "id": incidencia["id"],
        "equipo": incidencia["equipo_codigo"],
        "descripcion": incidencia["descripcion"],
        "severidad": incidencia["severidad"],
        "estado": incidencia["estado"],
        "solucion": incidencia["solucion"],
        "fecha_hora_reporte": incidencia["fecha_hora_reporte"],
        "fecha_resolucion": incidencia["fecha_resolucion"],
        "responsable_probable": responsable,
        "sesiones_previas": [serializar_responsable(sesion) for sesion in sesiones_previas],
    })


@app.route("/api/incidencias/<int:incidencia_id>/estado", methods=["PUT", "PATCH"])
@login_requerido
def api_actualizar_estado_incidencia(incidencia_id):
    """Cambia el estado de una incidencia y registra la solución si corresponde."""
    data = request.get_json(silent=True) or {}
    estado = (data.get("estado") or "").strip().lower()
    if estado not in {"abierta", "en_revision", "resuelta"}:
        return jsonify({"ok": False, "mensaje": "El estado no es válido."}), 400

    solucion = (data.get("solucion") or "").strip()
    if estado == "resuelta" and not solucion:
        return jsonify({"ok": False, "mensaje": "Al resolver la incidencia debe dejar una solución."}), 400

    with get_db_connection() as conn:
        incidencia = conn.execute(
            "SELECT id, estado, solucion FROM incidencias WHERE id = ?",
            (incidencia_id,),
        ).fetchone()
        if incidencia is None:
            return jsonify({"ok": False, "mensaje": "No existe esa incidencia."}), 404

        fecha_resolucion = obtener_timestamp() if estado == "resuelta" else None
        solucion_guardada = solucion if estado == "resuelta" else (incidencia["solucion"] if incidencia["solucion"] is not None else None)
        conn.execute(
            """
            UPDATE incidencias
            SET estado = ?, solucion = ?, fecha_resolucion = ?
            WHERE id = ?
            """,
            (estado, solucion_guardada, fecha_resolucion, incidencia_id),
        )
        if incidencia["estado"] != estado:
            registrar_bitacora(
                g.admin["id"], "cambio_estado_incidencia", "incidencias", incidencia_id,
                f"Estado: {incidencia['estado']} -> {estado}",
                obtener_ip_origen(), conn,
            )
        conn.commit()

    return jsonify({
        "ok": True,
        "mensaje": "Estado actualizado correctamente.",
        "estado": estado,
    })


@app.route("/api/historial")
@login_requerido
def api_historial():
    """Devuelve el historial de sesiones con filtros y paginación."""
    filtros = {
        "equipo": (request.args.get("equipo") or "").strip(),
        "alumno": (request.args.get("alumno") or "").strip(),
        "grado": (request.args.get("grado") or "").strip(),
        "seccion": (request.args.get("seccion") or "").strip(),
        "desde": (request.args.get("desde") or "").strip(),
        "hasta": (request.args.get("hasta") or "").strip(),
        "tipo_cierre": (request.args.get("tipo_cierre") or "").strip(),
        "solo_abiertas": str(request.args.get("solo_abiertas", "0")).lower() in {"1", "true", "yes", "on"},
        "pagina": request.args.get("pagina", 1),
        "por_pagina": request.args.get("por_pagina", 20),
    }
    return jsonify(consultar_historial(filtros=filtros))


@app.route("/api/reportes/historial.xlsx")
@login_requerido
def api_exportar_historial_excel():
    """Descarga el Excel del historial con los mismos filtros aplicados en la API."""
    filtros = {
        "equipo": (request.args.get("equipo") or "").strip(),
        "alumno": (request.args.get("alumno") or "").strip(),
        "grado": (request.args.get("grado") or "").strip(),
        "seccion": (request.args.get("seccion") or "").strip(),
        "desde": (request.args.get("desde") or "").strip(),
        "hasta": (request.args.get("hasta") or "").strip(),
        "tipo_cierre": (request.args.get("tipo_cierre") or "").strip(),
        "solo_abiertas": str(request.args.get("solo_abiertas", "0")).lower() in {"1", "true", "yes", "on"},
    }
    try:
        ruta = exportar_historial_excel(filtros)
        registrar_bitacora(
            g.admin["id"], "descarga_reporte_excel", "sesiones", None,
            "Reporte de historial", obtener_ip_origen(),
        )
        return send_file(ruta, as_attachment=True, download_name=f"historial_{datetime.utcnow().strftime('%Y-%m-%d')}.xlsx")
    except Exception as exc:
        return jsonify({"ok": False, "mensaje": f"No se pudo generar el Excel: {exc}"}), 500


@app.route("/api/reportes/incidencias.xlsx")
@login_requerido
def api_exportar_incidencias_excel():
    """Descarga el Excel de incidencias con filtros del listado."""
    filtros = {
        "estado": (request.args.get("estado") or "").strip(),
        "gravedad": (request.args.get("gravedad") or "").strip(),
        "equipo": (request.args.get("equipo") or "").strip(),
        "desde": (request.args.get("desde") or "").strip(),
        "hasta": (request.args.get("hasta") or "").strip(),
    }
    try:
        ruta = exportar_incidencias_excel(filtros)
        registrar_bitacora(
            g.admin["id"], "descarga_reporte_excel", "incidencias", None,
            "Reporte de incidencias", obtener_ip_origen(),
        )
        return send_file(ruta, as_attachment=True, download_name=f"incidencias_{datetime.utcnow().strftime('%Y-%m-%d')}.xlsx")
    except Exception as exc:
        return jsonify({"ok": False, "mensaje": f"No se pudo generar el Excel: {exc}"}), 500


@app.route("/api/reportes/uso.xlsx")
@login_requerido
def api_exportar_uso_excel():
    """Descarga el Excel con horas de uso por equipo y estadísticas de uso."""
    try:
        ruta = exportar_uso_excel()
        registrar_bitacora(
            g.admin["id"], "descarga_reporte_excel", "sesiones", None,
            "Reporte de uso", obtener_ip_origen(),
        )
        return send_file(ruta, as_attachment=True, download_name=f"uso_{datetime.utcnow().strftime('%Y-%m-%d')}.xlsx")
    except Exception as exc:
        return jsonify({"ok": False, "mensaje": f"No se pudo generar el Excel: {exc}"}), 500


@app.route("/api/reportes/incidencia/<int:incidencia_id>.xlsx")
@login_requerido
def api_exportar_incidencia_detalle_excel(incidencia_id):
    """Descarga el detalle de una incidencia y sus sesiones previas."""
    try:
        ruta = exportar_incidencia_detalle_excel(incidencia_id)
        registrar_bitacora(
            g.admin["id"], "descarga_reporte_excel", "incidencias", incidencia_id,
            "Reporte de detalle de incidencia", obtener_ip_origen(),
        )
        return send_file(ruta, as_attachment=True, download_name=f"incidencia_{incidencia_id}_{datetime.utcnow().strftime('%Y-%m-%d')}.xlsx")
    except Exception as exc:
        return jsonify({"ok": False, "mensaje": f"No se pudo generar el Excel: {exc}"}), 500


if __name__ == "__main__":
    iniciar_hilo_cierre_automatico()
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_DEBUG") == "1")
