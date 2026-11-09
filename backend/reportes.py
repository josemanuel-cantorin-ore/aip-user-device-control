import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from analisis.analisis_uso import calcular_estadisticas, cargar_datos
except ModuleNotFoundError:  # pragma: no cover - compatibilidad con carga como paquete.
    from backend.analisis.analisis_uso import calcular_estadisticas, cargar_datos

DB_PATH = BASE_DIR / "database" / "aip.db"


def _fecha_hoy_iso() -> str:
    """Fecha actual en formato YYYY-MM-DD para nombres de archivo y exportación."""
    return datetime.utcnow().strftime("%Y-%m-%d")


def _conectar():
    """Abre una conexión SQLite con lectura y row_factory estándar."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _formatear_duracion(segundos):
    """Convierte segundos a texto legible como hh:mm:ss o '—' cuando no aplica."""
    if segundos is None:
        return "—"
    try:
        valor = int(segundos)
    except (TypeError, ValueError):
        return "—"
    if valor < 0:
        return "—"
    horas = valor // 3600
    minutos = (valor % 3600) // 60
    segundos_restantes = valor % 60
    return f"{horas:02d}:{minutos:02d}:{segundos_restantes:02d}"


def _aplicar_estilo_hoja(ws, titulo=None):
    """Aplica encabezados en negrita, fondo azul y ajuste básico de columnas."""
    if titulo:
        ws.title = titulo
    header_fill = PatternFill(fill_type="solid", fgColor="1D4ED8")
    header_font = Font(bold=True, color="FFFFFF")
    for fila in ws.iter_rows(min_row=1, max_row=1):
        for celda in fila:
            celda.fill = header_fill
            celda.font = header_font
            celda.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = "A2"
    for column_cells in ws.columns:
        max_length = 0
        column = column_cells[0].column_letter
        for cell in column_cells:
            try:
                if cell.value is None:
                    continue
                max_length = max(max_length, len(str(cell.value)))
            except Exception:
                pass
        ws.column_dimensions[column].width = min(max(12, max_length + 2), 28)


def _generar_archivo_excel(nombre_base, sheets):
    """Crear un archivo .xlsx con varias hojas desde una lista de (nombre, DataFrame)."""
    wb = Workbook()
    default_sheet = wb.active
    wb.remove(default_sheet)
    for nombre, df in sheets:
        ws = wb.create_sheet(title=str(nombre)[:31])
        if df is None or df.empty:
            ws.append(["Sin datos para este reporte."])
            ws["A1"].font = Font(bold=True, color="1F2937")
            ws.freeze_panes = "A2"
            ws.column_dimensions["A"].width = 60
            continue
        df = df.copy()
        for col in df.columns:
            if hasattr(df[col], 'dt'):
                df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
        rows = [df.columns.tolist()] + df.values.tolist()
        for row in rows:
            ws.append(row)
        _aplicar_estilo_hoja(ws)
    ruta = Path(tempfile.gettempdir()) / f"{nombre_base}_{_fecha_hoy_iso()}.xlsx"
    wb.save(ruta)
    return ruta


def _historial_sql(filtros=None):
    """Genera la consulta de historial con filtros opcionales y devuelve la base SQL y parámetros."""
    filtros = filtros or {}
    sql = """
        SELECT
            s.id,
            e.codigo AS equipo,
            a.codigo_alumno,
            a.nombres,
            a.apellidos,
            a.grado,
            a.seccion,
            s.fecha_hora_inicio AS inicio,
            s.fecha_hora_fin AS fin,
            CASE
                WHEN s.fecha_hora_inicio IS NULL OR s.fecha_hora_fin IS NULL THEN NULL
                ELSE CAST((strftime('%s', s.fecha_hora_fin) - strftime('%s', s.fecha_hora_inicio)) AS INTEGER)
            END AS duracion_segundos,
            s.tipo_cierre
        FROM sesiones s
        JOIN equipos e ON e.id = s.equipo_id
        LEFT JOIN alumnos a ON a.id = s.alumno_id
        WHERE 1 = 1
    """
    params = []
    equipo = (filtros.get("equipo") or "").strip()
    alumno = (filtros.get("alumno") or "").strip()
    grado = (filtros.get("grado") or "").strip()
    seccion = (filtros.get("seccion") or "").strip()
    tipo_cierre = (filtros.get("tipo_cierre") or "").strip()
    desde = (filtros.get("desde") or "").strip()
    hasta = (filtros.get("hasta") or "").strip()
    solo_abiertas = bool(filtros.get("solo_abiertas"))

    if equipo:
        sql += " AND lower(e.codigo) = lower(?) "
        params.append(equipo)
    if alumno:
        sql += " AND (lower(a.codigo_alumno) LIKE lower(?) OR lower(a.nombres || ' ' || a.apellidos) LIKE lower(?)) "
        valor = f"%{alumno}%"
        params.extend([valor, valor])
    if grado:
        sql += " AND a.grado = ? "
        params.append(int(grado))
    if seccion:
        sql += " AND upper(a.seccion) = upper(?) "
        params.append(seccion)
    if tipo_cierre:
        sql += " AND s.tipo_cierre = ? "
        params.append(tipo_cierre)
    if desde:
        sql += " AND date(s.fecha_hora_inicio) >= date(?) "
        params.append(desde)
    if hasta:
        sql += " AND date(s.fecha_hora_inicio) <= date(?) "
        params.append(hasta)
    if solo_abiertas:
        sql += " AND s.fecha_hora_fin IS NULL "

    sql += " ORDER BY s.fecha_hora_inicio DESC "
    return sql, params


def consultar_historial(filtros=None, pagina=None, por_pagina=None):
    """Consulta historial paginado con los filtros publicables del endpoint /api/historial."""
    filtros = filtros or {}
    pagina = int(filtros.get("pagina", pagina or 1)) if pagina is None else int(pagina)
    por_pagina = int(filtros.get("por_pagina", por_pagina or 20)) if por_pagina is None else int(por_pagina)
    por_pagina = max(1, por_pagina)
    sql, params = _historial_sql(filtros)
    con = _conectar()
    try:
        total = con.execute(f"SELECT COUNT(*) FROM ({sql})", params).fetchone()[0]
        limit_sql = sql + " LIMIT ? OFFSET ? "
        limit_params = params + [por_pagina, (pagina - 1) * por_pagina]
        filas = con.execute(limit_sql, limit_params).fetchall()
    finally:
        con.close()

    items = []
    for fila in filas:
        items.append({
            "equipo": fila["equipo"],
            "codigo_alumno": fila["codigo_alumno"],
            "alumno": " ".join(filtro for filtro in (fila["nombres"], fila["apellidos"]) if filtro).strip() if fila["nombres"] else "Sin alumno",
            "grado": fila["grado"],
            "seccion": fila["seccion"],
            "inicio": fila["inicio"],
            "fin": fila["fin"],
            "duracion_segundos": fila["duracion_segundos"],
            "duracion": _formatear_duracion(fila["duracion_segundos"]),
            "tipo_cierre": fila["tipo_cierre"] or "abierta",
        })
    return {
        "items": items,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total": total,
        "total_paginas": max(1, (total + por_pagina - 1) // por_pagina) if total else 0,
    }


def exportar_historial_excel(filtros=None):
    """Genera el archivo Excel del historial usando los mismos filtros del endpoint."""
    filtros = filtros or {}
    sql, params = _historial_sql(filtros)
    con = _conectar()
    try:
        filas = con.execute(sql, params).fetchall()
    finally:
        con.close()
    data = []
    for fila in filas:
        data.append({
            "Equipo": fila["equipo"],
            "Alumno": " ".join(filtro for filtro in (fila["nombres"], fila["apellidos"]) if filtro).strip() if fila["nombres"] else "Sin alumno",
            "Código alumno": fila["codigo_alumno"],
            "Grado": fila["grado"],
            "Sección": fila["seccion"],
            "Inicio": fila["inicio"],
            "Fin": fila["fin"],
            "Duración (HH:MM:SS)": _formatear_duracion(fila["duracion_segundos"]),
            "Tipo de cierre": fila["tipo_cierre"] or "abierta",
        })
    df = pd.DataFrame(data)
    ruta = _generar_archivo_excel("historial", [("Historial", df)])
    return ruta


def exportar_incidencias_excel(filtros=None):
    """Genera el archivo Excel de incidencias con filtros opcionales."""
    filtros = filtros or {}
    sql = """
        SELECT
            i.id,
            e.codigo AS equipo,
            i.descripcion,
            i.severidad,
            i.estado,
            i.fecha_hora_reporte,
            i.fecha_resolucion,
            i.solucion,
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
    estado = (filtros.get("estado") or "").strip()
    severidad = (filtros.get("gravedad") or "").strip()
    equipo = (filtros.get("equipo") or "").strip()
    desde = (filtros.get("desde") or "").strip()
    hasta = (filtros.get("hasta") or "").strip()

    if estado:
        sql += " AND i.estado = ? "
        params.append(estado)
    if severidad:
        sql += " AND i.severidad = ? "
        params.append(severidad)
    if equipo:
        sql += " AND lower(e.codigo) = lower(?) "
        params.append(equipo)
    if desde:
        sql += " AND date(i.fecha_hora_reporte) >= date(?) "
        params.append(desde)
    if hasta:
        sql += " AND date(i.fecha_hora_reporte) <= date(?) "
        params.append(hasta)

    sql += " ORDER BY i.fecha_hora_reporte DESC "
    con = _conectar()
    try:
        filas = con.execute(sql, params).fetchall()
    finally:
        con.close()

    datos = []
    for fila in filas:
        responsable = " ".join(filtro for filtro in (fila["nombres"], fila["apellidos"]) if filtro).strip()
        datos.append({
            "ID": fila["id"],
            "Equipo": fila["equipo"],
            "Descripción": fila["descripcion"],
            "Severidad": fila["severidad"],
            "Estado": fila["estado"],
            "Fecha reporte": fila["fecha_hora_reporte"],
            "Responsable probable": responsable or "No disponible",
            "Grado": fila["grado"],
            "Sección": fila["seccion"],
            "Fecha resolución": fila["fecha_resolucion"],
            "Solución": fila["solucion"] or "—",
        })
    df = pd.DataFrame(datos)
    ruta = _generar_archivo_excel("incidencias", [("Incidencias", df)])
    return ruta


def exportar_uso_excel():
    """Genera el Excel de uso de equipos a partir del análisis existente, reutilizando la lógica de analisis_uso.py."""
    df = cargar_datos()
    if df is None or df.empty:
        workbook = Workbook()
        ws = workbook.active
        ws.title = "Uso por equipo"
        ws.append(["No hay datos para este reporte."])
        ws["A1"].font = Font(bold=True)
        ws.freeze_panes = "A2"
        ruta = Path(tempfile.gettempdir()) / f"uso_{_fecha_hoy_iso()}.xlsx"
        workbook.save(ruta)
        return ruta

    uso_por_equipo = (
        df.groupby("codigo", as_index=False)
        .agg(horas=("horas", "sum"), cantidad_sesiones=("horas", "size"))
        .sort_values("horas", ascending=False)
        .reset_index(drop=True)
    )
    estadisticas = calcular_estadisticas(df)
    estadisticos = pd.DataFrame(
        {
            "categoria": ["media_horas", "varianza_horas", "desviacion_horas", "media_sesiones", "varianza_sesiones", "desviacion_sesiones"],
            "valor": [
                float(uso_por_equipo["horas"].mean()) if not uso_por_equipo.empty else 0.0,
                float(uso_por_equipo["horas"].var(ddof=0)) if not uso_por_equipo.empty else 0.0,
                float(uso_por_equipo["horas"].std(ddof=0)) if not uso_por_equipo.empty else 0.0,
                float(uso_por_equipo["cantidad_sesiones"].mean()) if not uso_por_equipo.empty else 0.0,
                float(uso_por_equipo["cantidad_sesiones"].var(ddof=0)) if not uso_por_equipo.empty else 0.0,
                float(uso_por_equipo["cantidad_sesiones"].std(ddof=0)) if not uso_por_equipo.empty else 0.0,
            ],
        }
    )
    stats = pd.DataFrame(
        {
            "Indicador": ["media", "varianza", "desviacion_estandar", "equipo_mas_usado", "equipo_menos_usado"],
            "Valor": [
                estadisticas.get("media", 0.0),
                estadisticas.get("varianza", 0.0),
                estadisticas.get("desviacion_estandar", 0.0),
                estadisticas.get("equipo_mas_usado", "N/A"),
                estadisticas.get("equipo_menos_usado", "N/A"),
            ],
        }
    )
    ruta = _generar_archivo_excel("uso", [("Uso por equipo", uso_por_equipo), ("Estadísticas", stats), ("Estadísticas detalladas", estadisticos)])
    return ruta


def exportar_incidencia_detalle_excel(incidencia_id):
    """Exporta el detalle completo de una incidencia con sus sesiones previas en una hoja aparte."""
    con = _conectar()
    try:
        incidencia = con.execute(
            """
            SELECT i.*, e.codigo AS equipo, s.id AS sesion_probable_id
            FROM incidencias i
            JOIN equipos e ON e.id = i.equipo_id
            LEFT JOIN sesiones s ON s.id = i.sesion_probable_id
            WHERE i.id = ?
            """,
            (incidencia_id,),
        ).fetchone()
        if incidencia is None:
            datos = pd.DataFrame([{"mensaje": "No existe la incidencia indicada."}])
            ruta = _generar_archivo_excel("incidencia_detalle", [("Incidencia", datos)])
            return ruta

        sesiones_previas = con.execute(
            """
            SELECT
                s.id,
                e.codigo AS equipo,
                a.nombres,
                a.apellidos,
                a.grado,
                a.seccion,
                s.fecha_hora_inicio,
                s.fecha_hora_fin,
                s.tipo_cierre,
                CAST((strftime('%s', s.fecha_hora_fin) - strftime('%s', s.fecha_hora_inicio)) AS INTEGER) AS duracion_segundos
            FROM sesiones s
            JOIN equipos e ON e.id = s.equipo_id
            LEFT JOIN alumnos a ON a.id = s.alumno_id
            WHERE s.equipo_id = ?
              AND s.fecha_hora_inicio < ?
            ORDER BY s.fecha_hora_inicio DESC
            LIMIT 5
            """,
            (incidencia["equipo_id"], incidencia["fecha_hora_reporte"]),
        ).fetchall()
    finally:
        con.close()

    incidencia_df = pd.DataFrame([
        {
            "ID": incidencia["id"],
            "Equipo": incidencia["equipo"],
            "Descripción": incidencia["descripcion"],
            "Severidad": incidencia["severidad"],
            "Estado": incidencia["estado"],
            "Fecha reporte": incidencia["fecha_hora_reporte"],
            "Fecha resolución": incidencia["fecha_resolucion"],
            "Solución": incidencia["solucion"] or "—",
            "Responsable probable": incidencia["sesion_probable_id"],
        }
    ])
    prev = []
    for fila in sesiones_previas:
        prev.append({
            "ID": fila["id"],
            "Equipo": fila["equipo"],
            "Alumno": " ".join(filtro for filtro in (fila["nombres"], fila["apellidos"]) if filtro).strip() if fila["nombres"] else "Sin alumno",
            "Grado": fila["grado"],
            "Sección": fila["seccion"],
            "Inicio": fila["fecha_hora_inicio"],
            "Fin": fila["fecha_hora_fin"],
            "Tipo cierre": fila["tipo_cierre"],
            "Duración": _formatear_duracion(fila["duracion_segundos"]),
        })
    prev_df = pd.DataFrame(prev)
    ruta = _generar_archivo_excel("incidencia_detalle", [("Incidencia", incidencia_df), ("Sesiones previas", prev_df)])
    return ruta
