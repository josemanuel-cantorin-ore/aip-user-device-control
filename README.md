# Prototipo de registro de asignación de equipos

Proyecto para gestionar asignación de equipos, sesiones de uso, incidencias y análisis de uso en un aula de innovación pedagógica.

## Estructura

- backend/
  - database/: scripts SQL, base de datos SQLite y utilidad de inicialización.
  - analisis/: análisis de uso y salidas generadas (gráficos y Excel).
  - requirements.txt: dependencias de Python.
- frontend/: preparado para futuros archivos CSS y JavaScript.
- docs/: documentación del modelo de datos, proceso y diagrama entidad-relación.

## Uso rápido

1. Crear la base de datos:
   python backend/database/init_db.py
2. Ejecutar el análisis de uso con datos de demostración:
   python backend/analisis/analisis_uso.py --demo

La base de datos real se usa desde backend/database/aip.db y los resultados del análisis se almacenan en backend/analisis/salidas/.

## Acceso administrativo

Ejecute el servidor con `python backend/app.py`. El registro del alumno sigue disponible en `/registro`; las páginas de administración requieren una cuenta activa.

Antes de publicar el servidor, configure `AIP_SECRET_KEY` con un valor secreto y único. Si no está configurada, el servidor muestra un aviso y usa una clave solo para desarrollo. Para crear cuentas admin o docente, ejecute `python backend/crear_admin.py`.
