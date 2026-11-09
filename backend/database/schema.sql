PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

BEGIN TRANSACTION;

-- =========================================================
-- 1) TABLAS BASE
-- =========================================================

CREATE TABLE IF NOT EXISTS equipos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE CHECK (codigo LIKE 'PC-%'),
    ip TEXT NOT NULL UNIQUE,
    nombre_host TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('laptop', 'PC')),
    ubicacion TEXT NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('activo', 'mantenimiento', 'baja')),
    fecha_alta TEXT NOT NULL CHECK (datetime(fecha_alta) IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS alumnos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_alumno TEXT NOT NULL UNIQUE,
    nombres TEXT NOT NULL,
    apellidos TEXT NOT NULL,
    grado INTEGER NOT NULL CHECK (grado BETWEEN 1 AND 5),
    seccion TEXT NOT NULL CHECK (seccion IN ('A', 'B', 'C', 'D')),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    pin_hash TEXT,
    CHECK (pin_hash IS NULL OR length(pin_hash) > 0)
);

CREATE TABLE IF NOT EXISTS usuarios_admin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    nombre_completo TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('admin', 'docente')),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    fecha_creacion TEXT NOT NULL CHECK (datetime(fecha_creacion) IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alumno_id INTEGER NOT NULL REFERENCES alumnos(id),
    equipo_id INTEGER NOT NULL REFERENCES equipos(id),
    fecha_hora_inicio TEXT NOT NULL CHECK (datetime(fecha_hora_inicio) IS NOT NULL),
    fecha_hora_fin TEXT CHECK (fecha_hora_fin IS NULL OR datetime(fecha_hora_fin) IS NOT NULL),
    ultimo_latido TEXT CHECK (ultimo_latido IS NULL OR datetime(ultimo_latido) IS NOT NULL),
    tipo_cierre TEXT CHECK (tipo_cierre IS NULL OR tipo_cierre IN ('admin', 'alumno', 'automatico', 'reemplazo')),
    cerrado_por INTEGER REFERENCES usuarios_admin(id),
    observacion TEXT,
    CHECK (fecha_hora_fin IS NULL OR ultimo_latido IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS incidencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipo_id INTEGER NOT NULL REFERENCES equipos(id),
    descripcion TEXT NOT NULL,
    severidad TEXT NOT NULL CHECK (severidad IN ('leve', 'moderada', 'grave')),
    estado TEXT NOT NULL CHECK (estado IN ('abierta', 'en_revision', 'resuelta')),
    fecha_hora_reporte TEXT NOT NULL CHECK (datetime(fecha_hora_reporte) IS NOT NULL),
    reportado_por INTEGER REFERENCES usuarios_admin(id),
    sesion_probable_id INTEGER REFERENCES sesiones(id),
    fecha_resolucion TEXT CHECK (fecha_resolucion IS NULL OR datetime(fecha_resolucion) IS NOT NULL),
    solucion TEXT
);

CREATE TABLE IF NOT EXISTS bitacora (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER REFERENCES usuarios_admin(id),
    accion TEXT NOT NULL,
    tabla_afectada TEXT NOT NULL,
    registro_id INTEGER,
    detalle TEXT,
    ip_origen TEXT,
    fecha_hora TEXT NOT NULL DEFAULT (datetime('now')) CHECK (datetime(fecha_hora) IS NOT NULL)
);

-- =========================================================
-- 2) ÍNDICES
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_equipos_estado ON equipos(estado);
CREATE INDEX IF NOT EXISTS idx_alumnos_grado_seccion ON alumnos(grado, seccion);
CREATE INDEX IF NOT EXISTS idx_sesiones_equipo_fecha ON sesiones(equipo_id, fecha_hora_inicio);
CREATE INDEX IF NOT EXISTS idx_sesiones_alumno_fecha ON sesiones(alumno_id, fecha_hora_inicio);
CREATE INDEX IF NOT EXISTS idx_sesiones_fecha ON sesiones(fecha_hora_inicio);
CREATE INDEX IF NOT EXISTS idx_incidencias_equipo_fecha ON incidencias(equipo_id, fecha_hora_reporte);
CREATE INDEX IF NOT EXISTS idx_incidencias_estado ON incidencias(estado);
CREATE INDEX IF NOT EXISTS idx_bitacora_admin_fecha ON bitacora(admin_id, fecha_hora);

-- Unicidad parcial: solo 1 sesión abierta por equipo y por alumno.
CREATE UNIQUE INDEX IF NOT EXISTS ux_sesion_abierta_equipo
ON sesiones(equipo_id)
WHERE fecha_hora_fin IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_sesion_abierta_alumno
ON sesiones(alumno_id)
WHERE fecha_hora_fin IS NULL;

-- =========================================================
-- 3) TRIGGERS DE SEGURIDAD
-- =========================================================

-- Las sesiones no se pueden borrar.
CREATE TRIGGER IF NOT EXISTS trg_sesiones_no_delete
BEFORE DELETE ON sesiones
BEGIN
    SELECT RAISE(ABORT, 'No se permite eliminar registros de sesiones.');
END;

-- Las sesiones solo pueden modificarse para registrar latidos o cerrarlas.
CREATE TRIGGER IF NOT EXISTS trg_sesiones_update_valid
BEFORE UPDATE ON sesiones
BEGIN
    SELECT CASE
        WHEN NEW.alumno_id <> OLD.alumno_id OR NEW.equipo_id <> OLD.equipo_id OR NEW.fecha_hora_inicio <> OLD.fecha_hora_inicio THEN
            RAISE(ABORT, 'No se permite cambiar alumno, equipo o fecha de inicio de la sesión.')
        WHEN OLD.fecha_hora_fin IS NOT NULL THEN
            RAISE(ABORT, 'No se permite modificar una sesión ya cerrada.')
        WHEN NEW.fecha_hora_fin IS NOT NULL AND NEW.tipo_cierre IS NULL THEN
            RAISE(ABORT, 'Cuando se cierra la sesión debe indicarse el tipo_cierre.')
        WHEN NEW.fecha_hora_fin IS NOT NULL AND NEW.tipo_cierre NOT IN ('admin', 'alumno', 'automatico', 'reemplazo') THEN
            RAISE(ABORT, 'tipo_cierre inválido.')
        WHEN NEW.fecha_hora_fin IS NOT NULL AND NEW.tipo_cierre <> 'automatico' AND NEW.cerrado_por IS NULL THEN
            RAISE(ABORT, 'Debe indicarse quién cerró la sesión.')
        WHEN NEW.ultimo_latido IS NULL THEN
            RAISE(ABORT, 'El último latido no puede quedar nulo durante una sesión activa.')
        ELSE NULL
    END;
END;

-- La bitácora es inmutable; solo se permiten nuevas inserciones.
CREATE TRIGGER IF NOT EXISTS trg_bitacora_no_update
BEFORE UPDATE ON bitacora
BEGIN
    SELECT RAISE(ABORT, 'La bitácora es de solo lectura.');
END;

CREATE TRIGGER IF NOT EXISTS trg_bitacora_no_delete
BEFORE DELETE ON bitacora
BEGIN
    SELECT RAISE(ABORT, 'No se permite eliminar registros de la bitácora.');
END;

-- =========================================================
-- 4) VISTAS ÚTILES
-- =========================================================

CREATE VIEW IF NOT EXISTS v_sesiones_activas AS
SELECT
    s.id AS sesion_id,
    e.codigo,
    e.ip,
    e.nombre_host,
    a.nombres,
    a.apellidos,
    a.grado,
    a.seccion,
    s.fecha_hora_inicio,
    s.ultimo_latido
FROM sesiones s
JOIN alumnos a ON a.id = s.alumno_id
JOIN equipos e ON e.id = s.equipo_id
WHERE s.fecha_hora_fin IS NULL
ORDER BY s.fecha_hora_inicio;

CREATE VIEW IF NOT EXISTS v_estado_aula AS
SELECT
    e.id,
    e.codigo,
    e.ip,
    e.nombre_host,
    e.tipo,
    e.ubicacion,
    CASE
        WHEN s.id IS NULL THEN 'libre'
        WHEN s.ultimo_latido IS NOT NULL AND (strftime('%s', 'now') - strftime('%s', s.ultimo_latido)) > 180 THEN 'sin señal'
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
ORDER BY e.codigo;

CREATE VIEW IF NOT EXISTS v_historial_equipo AS
SELECT
    e.codigo,
    e.ip,
    e.nombre_host,
    e.tipo,
    e.ubicacion,
    a.nombres,
    a.apellidos,
    a.grado,
    a.seccion,
    s.fecha_hora_inicio,
    s.fecha_hora_fin,
    s.tipo_cierre,
    s.ultimo_latido,
    s.observacion
FROM sesiones s
JOIN equipos e ON e.id = s.equipo_id
JOIN alumnos a ON a.id = s.alumno_id
ORDER BY e.codigo, s.fecha_hora_inicio;

CREATE VIEW IF NOT EXISTS v_responsables_incidencia AS
SELECT
    i.id AS incidencia_id,
    i.equipo_id,
    e.codigo,
    s.id AS sesion_id,
    a.nombres,
    a.apellidos,
    a.grado,
    a.seccion,
    s.fecha_hora_inicio,
    s.fecha_hora_fin,
    ROUND((strftime('%s', i.fecha_hora_reporte) - strftime('%s', s.fecha_hora_inicio)) / 60.0, 2) AS minutos_antes
FROM incidencias i
JOIN equipos e ON e.id = i.equipo_id
LEFT JOIN sesiones s ON s.id = (
    SELECT s2.id
    FROM sesiones s2
    WHERE s2.equipo_id = i.equipo_id
      AND s2.fecha_hora_inicio <= i.fecha_hora_reporte
      AND (s2.fecha_hora_fin IS NULL OR s2.fecha_hora_fin <= i.fecha_hora_reporte)
    ORDER BY s2.fecha_hora_fin DESC, s2.fecha_hora_inicio DESC
    LIMIT 1
)
LEFT JOIN alumnos a ON a.id = s.alumno_id;

COMMIT;
