-- 1) Quién usó el PC-12 ayer
SELECT
    a.nombres,
    a.apellidos,
    e.codigo,
    s.fecha_hora_inicio,
    s.fecha_hora_fin,
    s.tipo_cierre
FROM sesiones s
JOIN alumnos a ON a.id = s.alumno_id
JOIN equipos e ON e.id = s.equipo_id
WHERE e.codigo = 'PC-12'
  AND s.fecha_hora_inicio >= datetime('now', '-1 day')
  AND s.fecha_hora_inicio < datetime('now');

-- 2) Equipos ocupados ahora
SELECT
    v.codigo,
    v.ip,
    v.nombres,
    v.apellidos,
    v.grado,
    v.seccion,
    v.fecha_hora_inicio,
    v.ultimo_latido
FROM v_sesiones_activas v;

-- 3) Sesiones abiertas sin latido reciente
SELECT
    s.id,
    e.codigo,
    a.nombres,
    a.apellidos,
    s.fecha_hora_inicio,
    s.ultimo_latido,
    (strftime('%s', 'now') - strftime('%s', s.ultimo_latido)) AS segundos_sin_latido
FROM sesiones s
JOIN equipos e ON e.id = s.equipo_id
JOIN alumnos a ON a.id = s.alumno_id
WHERE s.fecha_hora_fin IS NULL
  AND (s.ultimo_latido IS NULL OR (strftime('%s', 'now') - strftime('%s', s.ultimo_latido)) > 180)
ORDER BY segundos_sin_latido DESC;

-- 4) Cierre masivo de sesiones por el admin
UPDATE sesiones
SET fecha_hora_fin = datetime('now'),
    ultimo_latido = datetime('now'),
    tipo_cierre = 'admin',
    cerrado_por = (SELECT id FROM usuarios_admin WHERE usuario = 'admin'),
    observacion = 'Cierre masivo por administrador'
WHERE fecha_hora_fin IS NULL;

-- 5) Responsables probables de una incidencia
SELECT
    i.id AS incidencia_id,
    i.descripcion,
    e.codigo AS equipo,
    s.id AS sesion_id,
    a.nombres,
    a.apellidos,
    a.grado,
    a.seccion,
    s.fecha_hora_inicio,
    s.fecha_hora_fin
FROM incidencias i
JOIN equipos e ON e.id = i.equipo_id
LEFT JOIN v_responsables_incidencia vri ON vri.incidencia_id = i.id
LEFT JOIN sesiones s ON s.id = vri.sesion_id
LEFT JOIN alumnos a ON a.id = s.alumno_id
WHERE i.id = 1;


