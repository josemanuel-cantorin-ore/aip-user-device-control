# Diccionario de datos

| Tabla | Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|---|
| equipos | id | INTEGER | PK, AUTOINCREMENT | Identificador interno del equipo. |
| equipos | codigo | TEXT | UNIQUE, CHECK (`codigo LIKE 'PC-%'`) | Código del equipo, p. ej. `PC-12`. |
| equipos | ip | TEXT | UNIQUE, NOT NULL | Dirección IP fija del equipo. |
| equipos | nombre_host | TEXT | NOT NULL | Nombre del host en la red. |
| equipos | tipo | TEXT | CHECK (`tipo IN ('laptop', 'PC')`) | Tipo de equipo. |
| equipos | ubicacion | TEXT | NOT NULL | Ubicación física en el aula (fila y puesto). |
| equipos | estado | TEXT | CHECK (`estado IN ('activo', 'mantenimiento', 'baja')`) | Estado operativo del equipo. |
| equipos | fecha_alta | TEXT | ISO 8601, CHECK (`datetime(...)`) | Fecha de alta del equipo. |
| alumnos | id | INTEGER | PK, AUTOINCREMENT | Identificador interno del alumno. |
| alumnos | codigo_alumno | TEXT | UNIQUE, NOT NULL | Código único del alumno. |
| alumnos | nombres | TEXT | NOT NULL | Nombres del alumno. |
| alumnos | apellidos | TEXT | NOT NULL | Apellidos del alumno. |
| alumnos | grado | INTEGER | CHECK (`grado BETWEEN 1 AND 5`) | Grado del alumno (1 a 5). |
| alumnos | seccion | TEXT | CHECK (`seccion IN ('A','B','C','D')`) | Sección del alumno. |
| alumnos | activo | INTEGER | CHECK (`activo IN (0,1)`) | Estado activo/inactivo del alumno. |
| alumnos | pin_hash | TEXT | NULLABLE | Hash del PIN del alumno, nunca en texto plano. |
| usuarios_admin | id | INTEGER | PK, AUTOINCREMENT | Identificador del usuario administrador. |
| usuarios_admin | usuario | TEXT | UNIQUE, NOT NULL | Nombre de usuario de acceso. |
| usuarios_admin | password_hash | TEXT | NOT NULL | Hash de la contraseña, nunca en texto plano. |
| usuarios_admin | nombre_completo | TEXT | NOT NULL | Nombre completo del administrador/docente. |
| usuarios_admin | rol | TEXT | CHECK (`rol IN ('admin', 'docente')`) | Rol de usuario. |
| usuarios_admin | activo | INTEGER | CHECK (`activo IN (0,1)`) | Estado activo/inactivo. |
| usuarios_admin | fecha_creacion | TEXT | ISO 8601, NOT NULL | Fecha de creación del usuario. |
| sesiones | id | INTEGER | PK, AUTOINCREMENT | Identificador de la sesión. |
| sesiones | alumno_id | INTEGER | FK -> alumnos.id, NOT NULL | Alumno asociado a la sesión. |
| sesiones | equipo_id | INTEGER | FK -> equipos.id, NOT NULL | Equipo usado por el alumno. |
| sesiones | fecha_hora_inicio | TEXT | ISO 8601, NOT NULL | Fecha y hora de inicio. |
| sesiones | fecha_hora_fin | TEXT | ISO 8601, NULLABLE | Fecha y hora de cierre. |
| sesiones | ultimo_latido | TEXT | ISO 8601, NULLABLE | Fecha y hora del último latido de señal. |
| sesiones | tipo_cierre | TEXT | CHECK (`tipo_cierre IN ('admin','alumno','automatico','reemplazo')`) | Motivo del cierre. |
| sesiones | cerrado_por | INTEGER | FK -> usuarios_admin.id, NULLABLE | Admin que cerró la sesión. |
| sesiones | observacion | TEXT | NULLABLE | Observaciones del cierre o del uso. |
| incidencias | id | INTEGER | PK, AUTOINCREMENT | Identificador de la incidencia. |
| incidencias | equipo_id | INTEGER | FK -> equipos.id, NOT NULL | Equipo afectado. |
| incidencias | descripcion | TEXT | NOT NULL | Descripción de la incidencia. |
| incidencias | severidad | TEXT | CHECK (`severidad IN ('leve','moderada','grave')`) | Severidad de la incidencia. |
| incidencias | estado | TEXT | CHECK (`estado IN ('abierta','en_revision','resuelta')`) | Estado actual de la incidencia. |
| incidencias | fecha_hora_reporte | TEXT | ISO 8601, NOT NULL | Fecha del reporte. |
| incidencias | reportado_por | INTEGER | FK -> usuarios_admin.id, NULLABLE | Admin que reportó la incidencia. |
| incidencias | sesion_probable_id | INTEGER | FK -> sesiones.id, NULLABLE | Sesión sospechosa asociada. |
| incidencias | fecha_resolucion | TEXT | ISO 8601, NULLABLE | Fecha de resolución. |
| incidencias | solucion | TEXT | NULLABLE | Solución aplicada. |
| bitacora | id | INTEGER | PK, AUTOINCREMENT | Identificador del evento de auditoría. |
| bitacora | admin_id | INTEGER | FK -> usuarios_admin.id, NULLABLE | Admin que ejecutó la acción. |
| bitacora | accion | TEXT | NOT NULL | Acción registrada. |
| bitacora | tabla_afectada | TEXT | NOT NULL | Tabla afectada por la acción. |
| bitacora | registro_id | INTEGER | NULLABLE | Identificador del registro involucrado. |
| bitacora | detalle | TEXT | NULLABLE | Detalle del cambio. |
| bitacora | ip_origen | TEXT | NULLABLE | IP origen de la acción. |
| bitacora | fecha_hora | TEXT | ISO 8601, NOT NULL | Fecha y hora del evento. |
