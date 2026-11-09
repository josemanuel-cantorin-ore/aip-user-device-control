import sqlite3
from datetime import datetime
from getpass import getpass
from pathlib import Path

from werkzeug.security import generate_password_hash


DB_PATH = Path(__file__).resolve().parent / "database" / "aip.db"


def solicitar_rol() -> str:
    """Solicita un rol permitido por el esquema actual."""
    while True:
        rol = input("Rol (admin/docente): ").strip().lower()
        if rol in {"admin", "docente"}:
            return rol
        print("El rol debe ser admin o docente.")


def solicitar_contrasena() -> str:
    """Solicita y confirma una contraseña sin mostrarla en pantalla."""
    while True:
        contrasena = getpass("Contraseña (mínimo 8 caracteres): ")
        if len(contrasena) < 8:
            print("La contraseña debe tener al menos 8 caracteres.")
            continue
        confirmacion = getpass("Repita la contraseña: ")
        if contrasena == confirmacion:
            return contrasena
        print("Las contraseñas no coinciden.")


def main() -> None:
    """Crea un usuario administrativo guardando únicamente el hash de su contraseña."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No se encontró la base de datos: {DB_PATH}")

    usuario = input("Usuario: ").strip()
    nombre = input("Nombre completo: ").strip()
    if not usuario or not nombre:
        raise ValueError("El usuario y el nombre completo son obligatorios.")
    rol = solicitar_rol()
    contrasena = solicitar_contrasena()
    password_hash = generate_password_hash(contrasena)
    fecha_creacion = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO usuarios_admin
                    (usuario, password_hash, nombre_completo, rol, activo, fecha_creacion)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (usuario, password_hash, nombre, rol, fecha_creacion),
            )
    except sqlite3.IntegrityError as error:
        raise ValueError("No se pudo crear el usuario; verifique que el nombre de usuario no exista.") from error

    print(f"Usuario {usuario!r} creado con rol {rol}.")


if __name__ == "__main__":
    main()
