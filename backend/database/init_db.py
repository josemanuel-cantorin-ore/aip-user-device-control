import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'aip.db'
SCHEMA_PATH = BASE_DIR / 'schema.sql'
SEED_PATH = BASE_DIR / 'seed.sql'


def execute_sql_file(conn: sqlite3.Connection, file_path: Path) -> None:
    sql = file_path.read_text(encoding='utf-8')
    conn.executescript(sql)


def main() -> None:
    for suffix in ('', '-wal', '-shm'):
        path = DB_PATH.with_name(DB_PATH.name + suffix)
        if path.exists():
            path.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON;')
    conn.execute('PRAGMA journal_mode = WAL;')

    execute_sql_file(conn, SCHEMA_PATH)
    execute_sql_file(conn, SEED_PATH)

    password_hash = generate_password_hash('Admin123!', method='pbkdf2:sha256')
    conn.execute(
        "UPDATE usuarios_admin SET password_hash = ? WHERE usuario = 'admin';",
        (password_hash,),
    )

    conn.commit()
    conn.close()

    print(f'Base de datos creada en: {DB_PATH}')
    print('Usuario admin: admin')
    print('Contraseña inicial: Admin123')
    print('La contraseña fue generada con werkzeug.security.generate_password_hash().')


if __name__ == '__main__':
    main()
