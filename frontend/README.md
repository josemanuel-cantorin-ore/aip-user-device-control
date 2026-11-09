# Frontend del sistema AIP

Este directorio contiene las pantallas del alumno y de administración, conectadas con Flask y SQLite.

## Archivos

- registro.html: pantalla de uso del alumno para registrar su acceso a un equipo detectado. Se usará con datos de la tabla `equipos` (codigo, ip, nombre_host) y de `alumnos` (grado, seccion, nombres, apellidos), además de la tabla `sesiones` para registrar el inicio de uso.
- login.html: acceso de usuarios administrativos.
- bitacora.html: consulta de auditoría de solo lectura para el rol `admin`.
- css/estilos.css: estilos visuales y diseño responsivo para ambas pantallas.
- js/registro.js: lógica de registro del alumno, latido y cierre de sesión.
- admin.html: panel del administrador con resumen general de equipos y detalle del equipo seleccionado. Se pensará para consultar la vista `v_estado_aula` y la tabla `sesiones`.
- js/admin.js: estado del aula, cierres administrativos, incidencias y sesión del administrador.
- js/bitacora.js: consulta paginada y filtrable de acciones auditadas.

## Qué tablas y campos se usarán más adelante

- `equipos`: `codigo`, `ip`, `nombre_host`, `estado`, `ubicacion`
- `alumnos`: `nombres`, `apellidos`, `grado`, `seccion`, `pin_hash`
- `sesiones`: `alumno_id`, `equipo_id`, `fecha_hora_inicio`, `fecha_hora_fin`, `ultimo_latido`, `tipo_cierre`
- `incidencias`: `equipo_id`, `descripcion`, `severidad`, `estado`, `fecha_hora_reporte`

## Cómo abrir

- Inicie el servidor Flask y abra `/registro` para la pantalla del alumno.
- Abra `/login.html` para autenticarse; luego podrá acceder al panel y a las páginas administrativas.
