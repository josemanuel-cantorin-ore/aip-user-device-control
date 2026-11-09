import argparse
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR.parent / "database"
DEFAULT_DB_PATH = DATABASE_DIR / "aip.db"
OUTPUT_DIR = BASE_DIR / "salidas"


# =========================================================
# Funciones principales
# =========================================================

def cargar_datos(db_path=None, demo=False):
    """Carga las sesiones cerradas desde SQLite o genera un DataFrame simulado."""
    if demo:
        # Modo de prueba: se genera un DataFrame con 48 equipos y cerca de 300 sesiones
        # para validar los gráficos sin tocar la base real de la AIP.
        np.random.seed(42)
        equipos = [f"PC-{numero:02d}" for numero in range(1, 49)]
        cantidad_sesiones = 300

        # Se seleccionan fechas aleatorias en un rango realista y se generan duraciones aleatorias.
        fechas_inicio = pd.to_datetime(
            np.random.choice(pd.date_range("2025-01-01", "2025-12-31", freq="D"), cantidad_sesiones)
        ) + pd.to_timedelta(np.random.randint(0, 24 * 60, cantidad_sesiones), unit="min")

        duraciones_horas = np.random.uniform(0.5, 5.5, cantidad_sesiones)
        fechas_fin = fechas_inicio + pd.to_timedelta(duraciones_horas, unit="h")

        df = pd.DataFrame(
            {
                "codigo": np.random.choice(equipos, cantidad_sesiones),
                "fecha_hora_inicio": fechas_inicio,
                "fecha_hora_fin": fechas_fin,
            }
        )
        df["horas"] = (df["fecha_hora_fin"] - df["fecha_hora_inicio"]).dt.total_seconds() / 3600.0
        return df

    if db_path is None:
        db_path = DEFAULT_DB_PATH
    db_path = Path(db_path)

    if not db_path.exists():
        raise FileNotFoundError(f"No se encontró la base de datos en: {db_path}")

    # La consulta usa pd.read_sql para cargar las sesiones cerradas unidas con el código del equipo.
    # Solo traemos columnas necesarias para analizar uso y trazabilidad.
    query = """
        SELECT
            e.codigo,
            s.fecha_hora_inicio,
            s.fecha_hora_fin
        FROM sesiones s
        JOIN equipos e ON e.id = s.equipo_id
        WHERE s.fecha_hora_fin IS NOT NULL
        ORDER BY s.fecha_hora_inicio
    """

    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql(query, conn)

    if df.empty:
        print("No se encontraron sesiones cerradas en la base de datos. Revise los datos de prueba o la información de uso.")
        return df

    # Convertimos a datetime para poder calcular duración y fechas por día de la semana.
    df["fecha_hora_inicio"] = pd.to_datetime(df["fecha_hora_inicio"], errors="coerce")
    df["fecha_hora_fin"] = pd.to_datetime(df["fecha_hora_fin"], errors="coerce")
    df = df.dropna(subset=["fecha_hora_inicio", "fecha_hora_fin"]).copy()

    # Duración en horas de cada sesión.
    df["horas"] = (df["fecha_hora_fin"] - df["fecha_hora_inicio"]).dt.total_seconds() / 3600.0
    return df


def calcular_estadisticas(df):
    """Calcula resumen estadístico de uso por equipo usando pandas y NumPy."""
    if df is None or df.empty or "horas" not in df.columns:
        return {
            "horas_por_equipo": pd.DataFrame(columns=["codigo", "horas"]),
            "media": 0.0,
            "varianza": 0.0,
            "desviacion_estandar": 0.0,
            "equipo_mas_usado": "N/A",
            "equipo_menos_usado": "N/A",
        }

    # Agrupamos por equipo y sumamos las horas totales de uso.
    horas_por_equipo = (
        df.groupby("codigo", as_index=False)["horas"]
          .sum()
          .sort_values("horas", ascending=False)
          .reset_index(drop=True)
    )

    # Convertimos a un arreglo NumPy para cálculos numéricos.
    valores = horas_por_equipo["horas"].to_numpy(dtype=float)

    media = float(np.mean(valores))
    varianza = float(np.var(valores))
    desviacion = float(np.std(valores))

    equipo_mas_usado = horas_por_equipo.iloc[0]["codigo"] if not horas_por_equipo.empty else "N/A"
    equipo_menos_usado = horas_por_equipo.iloc[-1]["codigo"] if not horas_por_equipo.empty else "N/A"

    estadisticas = {
        "horas_por_equipo": horas_por_equipo,
        "media": media,
        "varianza": varianza,
        "desviacion_estandar": desviacion,
        "equipo_mas_usado": equipo_mas_usado,
        "equipo_menos_usado": equipo_menos_usado,
    }
    return estadisticas


def graficar(df, estadisticas, carpeta_salida):
    """Genera los gráficos pedidos y los guarda como PNG en la carpeta indicada."""
    carpeta_salida = Path(carpeta_salida)
    carpeta_salida.mkdir(parents=True, exist_ok=True)

    horas_por_equipo = estadisticas["horas_por_equipo"]
    if horas_por_equipo.empty:
        print("No hay datos suficientes para graficar. Se omite la generación de imágenes.")
        return

    # Gráfico 1: barras de horas por equipo con media en línea roja punteada.
    plt.figure(figsize=(16, 8))
    sns.barplot(data=horas_por_equipo, x="codigo", y="horas", hue="codigo", dodge=False, palette="viridis", legend=False)
    plt.axhline(
        estadisticas["media"],
        color="red",
        linestyle="--",
        linewidth=1.8,
        label=f"Media: {estadisticas['media']:.2f} h",
    )
    plt.title("Horas de uso por equipo")
    plt.xlabel("Equipo")
    plt.ylabel("Horas de uso (h)")
    plt.xticks(rotation=90)
    plt.legend(title="Promedio")
    plt.tight_layout()
    plt.savefig(carpeta_salida / "horas_por_equipo.png", dpi=150)
    plt.close()

    # Gráfico 2: heatmap de uso por equipo y por día de la semana.
    # Se crea una tabla pivote con días Lunes a Domingo.
    heat_data = df.copy()
    heat_data["dia_semana"] = heat_data["fecha_hora_inicio"].dt.dayofweek
    heat_data["dia_nombre"] = heat_data["dia_semana"].map({
        0: "Lun",
        1: "Mar",
        2: "Mié",
        3: "Jue",
        4: "Vie",
        5: "Sáb",
        6: "Dom",
    })

    pivot = (
        heat_data.groupby(["codigo", "dia_nombre"], as_index=False)["horas"]
        .sum()
        .pivot(index="codigo", columns="dia_nombre", values="horas")
        .reindex(columns=["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"], fill_value=0)
    )

    plt.figure(figsize=(12, 12))
    sns.heatmap(pivot, annot=True, fmt=".1f", cmap="YlOrRd", cbar_kws={"label": "Horas"})
    plt.title("Mapa de calor: horas de uso por equipo y día de la semana")
    plt.xlabel("Día de la semana")
    plt.ylabel("Equipo")
    plt.tight_layout()
    plt.savefig(carpeta_salida / "heatmap_horas_por_equipo_y_dia.png", dpi=150)
    plt.close()

    # Gráfico 3: histograma de duración de las sesiones.
    plt.figure(figsize=(10, 6))
    sns.histplot(df["horas"], bins=20, color="steelblue", edgecolor="black")
    plt.title("Histograma de la duración de las sesiones")
    plt.xlabel("Duración de la sesión (horas)")
    plt.ylabel("Frecuencia")
    plt.tight_layout()
    plt.savefig(carpeta_salida / "histograma_duracion_sesiones.png", dpi=150)
    plt.close()

    print("Gráficos generados en la carpeta:", carpeta_salida)


def exportar_excel(estadisticas, ruta_excel):
    """Exporta un resumen Excel con dos hojas: horas por equipo y estadísticas."""
    ruta_excel = Path(ruta_excel)
    ruta_excel.parent.mkdir(parents=True, exist_ok=True)

    horas_por_equipo = estadisticas["horas_por_equipo"]
    if horas_por_equipo.empty:
        print("No hay datos para exportar a Excel.")
        return

    estadisticos_df = pd.DataFrame(
        {
            "estadistica": [
                "media",
                "varianza",
                "desviacion_estandar",
                "equipo_mas_usado",
                "equipo_menos_usado",
            ],
            "valor": [
                estadisticas["media"],
                estadisticas["varianza"],
                estadisticas["desviacion_estandar"],
                estadisticas["equipo_mas_usado"],
                estadisticas["equipo_menos_usado"],
            ],
        }
    )

    with pd.ExcelWriter(ruta_excel, engine="openpyxl") as writer:
        horas_por_equipo.to_excel(writer, sheet_name="Horas por equipo", index=False)
        estadisticos_df.to_excel(writer, sheet_name="Estadísticas", index=False)

    print(f"Resumen exportado en Excel: {ruta_excel}")


def imprimir_estadisticas(estadisticas):
    """Muestra la media, varianza, desviación estándar y equipos extremos en consola."""
    horas_por_equipo = estadisticas["horas_por_equipo"]
    if horas_por_equipo.empty:
        print("No hay datos suficientes para calcular estadísticas de uso.")
        return

    print("\n=== Estadísticas de uso por equipo ===")
    print(f"Media de horas por equipo: {estadisticas['media']:.2f} horas")
    print(f"Varianza: {estadisticas['varianza']:.2f}")
    print(f"Desviación estándar: {estadisticas['desviacion_estandar']:.2f} horas")
    print(f"Equipo más usado: {estadisticas['equipo_mas_usado']}")
    print(f"Equipo menos usado: {estadisticas['equipo_menos_usado']}")
    print("\nTop 5 equipos con mayor uso:")
    print(horas_por_equipo.head(5).to_string(index=False))


def main():
    """Bloque principal: analiza el uso de equipos y exporta resultados."""
    parser = argparse.ArgumentParser(description="Analiza el uso de equipos del Aula de Innovación Pedagógica.")
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help="Ruta de la base de datos SQLite. Por defecto usa backend/database/aip.db.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Genera un DataFrame simulado para probar el análisis sin leer la base real.",
    )
    args = parser.parse_args()

    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.demo:
        print("Modo DEMO activado. Se generarán datos simulados para probar el flujo completo.")
        df = cargar_datos(demo=True)
    else:
        db_path = Path(args.db)
        if not db_path.exists():
            print(f"No existe la base de datos: {db_path}")
            print("Ejecute este script con --demo para probar el análisis en modo demostración.")
            return
        df = cargar_datos(db_path=db_path, demo=False)

    if df.empty or "horas" not in df.columns or df["horas"].dropna().empty:
        print("No se encontraron sesiones cerradas con datos válidos para analizar.")
        print("Verifique la base de datos o use --demo para generar datos de prueba.")
        return

    estadisticas = calcular_estadisticas(df)
    imprimir_estadisticas(estadisticas)

    graficar(df, estadisticas, output_dir)
    exportar_excel(estadisticas, output_dir / "resumen_uso.xlsx")

    print("\nAnálisis finalizado con éxito.")


if __name__ == "__main__":
    main()
