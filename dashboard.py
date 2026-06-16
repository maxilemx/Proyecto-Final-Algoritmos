"""
Dashboard interactivo — Cafetería "Aroma del Sur"
Proyecto Final LAD3012 · UDLAP · Verano I 2026
AzTech Consultores

Cómo correr:
    pip install streamlit pandas
    streamlit run dashboard.py

El dashboard lee output/resultados.json (generado por pipeline.py).
Incluye un interruptor "Mostrar código de backend" que revela, junto a cada
tabla y gráfica, el código pandas/SQL que la genera.
"""

import json
import os
import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------------
# Configuración de página y paleta café
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Aroma del Sur — Dashboard",
    page_icon="☕",
    layout="wide",
)

CAFE_OSCURO = "#3E2C23"
CAFE = "#6F4E37"
CAFE_MEDIO = "#B07D52"
CAFE_CLARO = "#C9A66B"
CREMA = "#F3EBE3"

st.markdown(f"""
<style>
    .stApp {{ background-color: {CREMA}; }}
    h1, h2, h3 {{ color: {CAFE_OSCURO}; }}
    [data-testid="stMetricValue"] {{ color: {CAFE}; font-weight: 700; }}
    [data-testid="stMetricLabel"] {{ color: {CAFE_OSCURO}; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {CAFE_CLARO}33; border-radius: 8px 8px 0 0;
        padding: 8px 18px; color: {CAFE_OSCURO};
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {CAFE}; color: white;
    }}
    section[data-testid="stSidebar"] {{ background-color: {CAFE_OSCURO}; }}
    section[data-testid="stSidebar"] * {{ color: {CREMA}; }}
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Gráficas con estilo café (matplotlib, mismo look que el notebook)
# ----------------------------------------------------------------------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.colors import LinearSegmentedColormap

VERDE = "#2E7D52"   # ganancia / positivo
ROJO = "#B0392A"    # pérdida / negativo
# Degradado verde "de la casa": de crema a verde café (para tablas y barras)
VERDE_GRAD = LinearSegmentedColormap.from_list("verde_aroma", ["#FBF7F2", "#A7D3A7", "#2E7D52"])

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 12, "text.color": CAFE_OSCURO,
    "axes.labelcolor": CAFE_OSCURO, "xtick.color": CAFE_OSCURO, "ytick.color": CAFE_OSCURO,
})


def _fig(figsize=(7, 3.6)):
    """Crea una figura/eje ya con el fondo crema y los bordes café."""
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(CREMA)
    ax.set_facecolor(CREMA)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(CAFE_MEDIO)
    return fig, ax


def _miles(x, _=None):
    """Formato corto de pesos para ejes y etiquetas: 1,234,567 -> $1.2M / $234k."""
    a = abs(x)
    if a >= 1_000_000:
        return f"${x/1_000_000:.1f}M"
    if a >= 1_000:
        return f"${x/1_000:.0f}k"
    return f"${x:.0f}"


def _colores_grad(valores):
    """Asigna un color del degradado verde según el valor (más alto = más verde)."""
    v = pd.Series(valores).astype(float)
    norm = plt.Normalize(v.min(), v.max())
    return VERDE_GRAD(norm(v.values))


def mostrar(fig):
    """Renderiza la figura en Streamlit y la cierra para liberar memoria."""
    st.pyplot(fig)
    plt.close(fig)


def grafica_sucursales(df):
    """Barras horizontales de utilidad por sucursal: verde gana, rojo pierde."""
    d = df.sort_values("util_post_renta")
    fig, ax = _fig((8, 0.52 * len(d) + 1))
    colores = [VERDE if v >= 0 else ROJO for v in d["util_post_renta"]]
    ax.barh(d["sucursal"], d["util_post_renta"], color=colores, edgecolor=CAFE_OSCURO, lw=0.4)
    ax.axvline(0, color=CAFE_OSCURO, lw=1)
    ax.set_xlabel("Utilidad final tras renta (18 meses)")
    ax.xaxis.set_major_formatter(FuncFormatter(_miles))
    for y, v in enumerate(d["util_post_renta"]):
        ax.text(v, y, ("  " + _miles(v)) if v >= 0 else (_miles(v) + "  "),
                va="center", ha="left" if v >= 0 else "right",
                fontsize=9, color=CAFE_OSCURO, fontweight="bold")
    ax.margins(x=0.18)
    fig.tight_layout()
    return fig


def grafica_categorias_ingreso(cat):
    """Barras horizontales de ingreso por categoría, coloreadas por el degradado verde."""
    d = cat.sort_values("ingreso")
    fig, ax = _fig((6.2, 4))
    ax.barh(d["categoria"], d["ingreso"], color=_colores_grad(d["ingreso"]),
            edgecolor=CAFE_OSCURO, lw=0.4)
    ax.set_xlabel("Ingreso")
    ax.xaxis.set_major_formatter(FuncFormatter(_miles))
    for y, v in enumerate(d["ingreso"]):
        ax.text(v, y, " " + _miles(v), va="center", ha="left", fontsize=8, color=CAFE_OSCURO)
    ax.margins(x=0.16)
    fig.tight_layout()
    return fig


def grafica_cuadrante(cat):
    """Dispersión ingreso vs margen; tamaño de burbuja = unidades. Medianas = cuadrantes."""
    fig, ax = _fig((9, 4.6))
    x = cat["ingreso"].astype(float)
    y = cat["margen_pct"].astype(float)
    s = cat["unidades"].astype(float)
    sizes = (s / s.max()) * 1100 + 120
    ax.scatter(x, y, s=sizes, color=CAFE_MEDIO, alpha=0.65,
               edgecolor=CAFE_OSCURO, linewidth=1.2, zorder=3)
    ax.axvline(x.median(), color=CAFE_CLARO, ls="--", lw=1, zorder=1)
    ax.axhline(y.median(), color=CAFE_CLARO, ls="--", lw=1, zorder=1)
    for i, (_, r) in enumerate(cat.iterrows()):
        dy = 9 if i % 2 == 0 else -15
        ax.annotate(r["categoria"], (r["ingreso"], r["margen_pct"]),
                    xytext=(8, dy), textcoords="offset points",
                    fontsize=8, color=CAFE_OSCURO, fontweight="bold", zorder=4,
                    bbox=dict(boxstyle="round,pad=0.12", fc=CREMA, ec="none", alpha=0.55))
    ax.set_xlabel("Ingreso  →  (vende más)")
    ax.set_ylabel("Margen %  →  (deja más)")
    ax.xaxis.set_major_formatter(FuncFormatter(_miles))
    fig.tight_layout()
    return fig


def grafica_horas(vph):
    """Barras de ingreso por hora con los dos picos resaltados."""
    fig, ax = _fig((7, 3.2))
    horas = list(vph.index)
    colores = [CAFE if 7 <= h <= 10 else CAFE_MEDIO if 16 <= h <= 19 else CAFE_CLARO
               for h in horas]
    ax.bar(horas, vph["ingreso"], color=colores, edgecolor=CAFE_OSCURO, lw=0.3)
    ax.set_xlabel("Hora del día")
    ax.set_ylabel("Ingreso")
    ax.set_xticks(horas)
    ax.yaxis.set_major_formatter(FuncFormatter(_miles))
    fig.tight_layout()
    return fig


def grafica_meses(vpm):
    """Línea de tendencia mensual del ingreso."""
    fig, ax = _fig((7, 3.2))
    xs = range(len(vpm))
    ax.plot(xs, vpm["ingreso"], color=CAFE, marker="o", ms=4, lw=2)
    ax.fill_between(xs, vpm["ingreso"], color=CAFE, alpha=0.08)
    ax.set_ylabel("Ingreso")
    ax.set_xticks(list(xs))
    ax.set_xticklabels(vpm.index, rotation=90, fontsize=7)
    ax.yaxis.set_major_formatter(FuncFormatter(_miles))
    fig.tight_layout()
    return fig


def grafica_ciudad(q1):
    """Barras de ingreso por ciudad."""
    fig, ax = _fig((4.6, 3))
    ax.bar(q1["ciudad"], q1["ingreso"], color=_colores_grad(q1["ingreso"]),
           edgecolor=CAFE_OSCURO, lw=0.4, width=0.55)
    ax.set_ylabel("Ingreso")
    ax.yaxis.set_major_formatter(FuncFormatter(_miles))
    for i, v in enumerate(q1["ingreso"]):
        ax.text(i, v, _miles(v), ha="center", va="bottom", fontsize=8, color=CAFE_OSCURO)
    ax.margins(y=0.15)
    fig.tight_layout()
    return fig


def grafica_pareto(gasto_dict):
    """Diagrama de Pareto: % de gasto por segmento (barras) + % acumulado (línea)."""
    s = pd.Series(gasto_dict).sort_values(ascending=False)
    pct = s / s.sum() * 100
    cum = pct.cumsum()
    fig, ax = _fig((7, 4))
    ax.bar(range(len(s)), pct.values, color=CAFE, width=0.6, edgecolor=CAFE_OSCURO, lw=0.3)
    ax.set_ylabel("% del gasto (barras)")
    ax.set_xticks(range(len(s)))
    ax.set_xticklabels(s.index, rotation=20, ha="right", fontsize=8)
    ax.set_ylim(0, max(pct.values) * 1.18)
    for i, v in enumerate(pct.values):
        ax.text(i, v, f"{v:.0f}%", ha="center", va="bottom", fontsize=8,
                color=CAFE_OSCURO, fontweight="bold")
    ax2 = ax.twinx()
    ax2.plot(range(len(s)), cum.values, color=ROJO, marker="o", lw=2, zorder=5)
    ax2.set_ylabel("% acumulado (línea)", color=ROJO)
    ax2.tick_params(axis="y", colors=ROJO)
    ax2.set_ylim(0, 108)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_color(ROJO)
    for i, v in enumerate(cum.values):
        ax2.text(i, v + 2, f"{v:.0f}%", ha="center", fontsize=8, color=ROJO)
    fig.tight_layout()
    return fig


# ----------------------------------------------------------------------------
# Carga de datos
# ----------------------------------------------------------------------------
@st.cache_data
def cargar_resultados():
    ruta = os.path.join(os.path.dirname(__file__), "output", "resultados.json")
    if not os.path.exists(ruta):
        ruta = "output/resultados.json"
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def cargar_clusters():
    for ruta in ["output/clientes_clusters.csv",
                 os.path.join(os.path.dirname(__file__), "output", "clientes_clusters.csv")]:
        if os.path.exists(ruta):
            return pd.read_csv(ruta)
    return None


try:
    R = cargar_resultados()
except Exception as e:
    st.error(f"No se pudo cargar output/resultados.json. Corre primero `python pipeline.py`. Detalle: {e}")
    st.stop()

clusters_df = cargar_clusters()


def peso(x):
    """Formatea un número como pesos mexicanos."""
    try:
        return f"${x:,.0f}"
    except (ValueError, TypeError):
        return str(x)


def bloque_codigo(titulo, codigo):
    """Muestra un expander con el código de backend si el interruptor está activo."""
    if st.session_state.get("mostrar_codigo", False):
        with st.expander(f"🧑‍💻 Código de backend — {titulo}"):
            st.code(codigo, language="python")


# ----------------------------------------------------------------------------
# Barra lateral: filtros e interruptor de código
# ----------------------------------------------------------------------------
st.sidebar.title("☕ Aroma del Sur")
st.sidebar.caption("AzTech Consultores · LAD3012 UDLAP")
st.sidebar.markdown("---")

st.sidebar.subheader("⚙️ Opciones")
st.session_state["mostrar_codigo"] = st.sidebar.toggle(
    "Mostrar código de backend",
    value=False,
    help="Revela, junto a cada tabla y gráfica, el código pandas/SQL que la genera.",
)

st.sidebar.markdown("---")
st.sidebar.subheader("🔎 Filtros")
suc_df_full = pd.DataFrame(R["suc_performance"])
ciudades = ["Todas"] + sorted(suc_df_full["ciudad"].unique().tolist())
filtro_ciudad = st.sidebar.selectbox("Ciudad", ciudades)

solo_perdedoras = st.sidebar.checkbox("Solo sucursales que pierden dinero", value=False)

st.sidebar.markdown("---")
st.sidebar.caption(
    f"Periodo de datos hasta: **{R.get('fecha_corte', 'N/D')}**\n\n"
    f"Transacciones válidas: **{R['kpi_n_transacciones']:,}**"
)


# Aplicar filtros a la tabla de sucursales
suc_df = suc_df_full.copy()
if filtro_ciudad != "Todas":
    suc_df = suc_df[suc_df["ciudad"] == filtro_ciudad]
if solo_perdedoras:
    suc_df = suc_df[suc_df["util_post_renta"] < 0]


# ----------------------------------------------------------------------------
# Encabezado
# ----------------------------------------------------------------------------
st.title("☕ Aroma del Sur — Tablero de Análisis")
st.markdown(
    f"**Análisis de 8 sucursales · {R['kpi_n_transacciones']:,} transacciones · "
    f"14,200 clientes** · Cliente: Director Roberto Mendoza"
)
if st.session_state["mostrar_codigo"]:
    st.info("🧑‍💻 **Modo código activado:** debajo de cada tabla y gráfica verás el código "
            "pandas/SQL que la genera. Desactívalo en la barra lateral para una vista limpia.")

tab1, tab2, tab3 = st.tabs(["📊 KPIs y Sucursales", "🥐 Productos", "👥 Clientes y Segmentos"])


# ============================================================================
# VISTA 1 — KPIs y Sucursales
# ============================================================================
with tab1:
    st.header("Indicadores clave del negocio")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Ingreso total", peso(R["kpi_ingreso_total"]))
    c2.metric("Ganancia bruta", peso(R["kpi_ganancia_total"]))
    c3.metric("Margen global", f"{R['kpi_margen_global_pct']}%")
    c4.metric("Transacciones", f"{R['kpi_n_transacciones']:,}")
    c5.metric("Ticket promedio", peso(R["kpi_ticket_promedio"]))

    bloque_codigo("KPIs globales", """# KPIs sobre el DataFrame de ventas limpio (ventas)
ingreso_total   = ventas['total'].sum()
ganancia_total  = ventas['ganancia'].sum()          # ganancia = (precio - costo) * cantidad
margen_global   = ganancia_total / ingreso_total * 100
n_transacciones = len(ventas)
ticket_promedio = ingreso_total / n_transacciones""")

    st.markdown("---")
    st.subheader("💰 Pregunta 1 del Director: ¿qué sucursales pierden dinero?")
    st.caption("Utilidad final = ganancia bruta − (renta mensual × 18 meses del periodo). "
               "Vender mucho no basta: la renta puede comerse la ganancia.")

    tabla_suc = suc_df[["sucursal", "ciudad", "ingreso", "ganancia",
                        "transacciones", "ticket_prom", "renta_18m", "util_post_renta"]].copy()
    tabla_suc.columns = ["Sucursal", "Ciudad", "Ingreso", "Ganancia bruta",
                         "Transacciones", "Ticket prom.", "Renta 18m", "Utilidad final"]
    tabla_suc = tabla_suc.sort_values("Utilidad final", ascending=False)

    def color_util(v):
        return f"color: {'#1a7a3c' if v >= 0 else '#b00020'}; font-weight:700"

    st.dataframe(
        tabla_suc.style
        .format({"Ingreso": "${:,.0f}", "Ganancia bruta": "${:,.0f}",
                 "Transacciones": "{:,.0f}", "Ticket prom.": "${:,.2f}",
                 "Renta 18m": "${:,.0f}", "Utilidad final": "${:,.0f}"})
        .background_gradient(subset=["Ingreso"], cmap=VERDE_GRAD)
        .map(color_util, subset=["Utilidad final"]),
        width='stretch', hide_index=True,
    )
    st.caption("La columna *Ingreso* se sombrea en verde: más oscuro = más ingreso. "
               "La *Utilidad final* se colorea aparte (verde gana, rojo pierde).")

    if not suc_df.empty:
        mostrar(grafica_sucursales(suc_df))
        st.caption("Barras hacia la izquierda (rojas) = sucursales que pierden dinero tras la renta.")

    bloque_codigo("Utilidad por sucursal", """# Rentabilidad real por sucursal (pandas)
MESES = 18  # el periodo de datos cubre ~18 meses

suc = (ventas.groupby('sucursal')
             .agg(ingreso=('total', 'sum'),
                  ganancia=('ganancia', 'sum'),
                  transacciones=('venta_id', 'count'))
             .reset_index())

# Unir con el catálogo de sucursales para traer la renta
suc = suc.merge(sucursales[['nombre', 'ciudad', 'renta_mensual', 'empleados', 'm2']],
                left_on='sucursal', right_on='nombre')

suc['ticket_prom']     = suc['ingreso'] / suc['transacciones']
suc['renta_18m']       = suc['renta_mensual'] * MESES
suc['util_post_renta'] = suc['ganancia'] - suc['renta_18m']
suc = suc.sort_values('util_post_renta', ascending=False)""")

    st.markdown("---")
    cizq, cder = st.columns(2)

    with cizq:
        st.subheader("🏙️ Ingreso por ciudad")
        q1 = pd.DataFrame(R["sql_q1"])
        st.dataframe(
            q1.rename(columns={"ciudad": "Ciudad", "transacciones": "Transacciones",
                               "ingreso": "Ingreso"})
            .style.format({"Transacciones": "{:,.0f}", "Ingreso": "${:,.0f}"})
            .background_gradient(subset=["Ingreso"], cmap=VERDE_GRAD),
            width='stretch', hide_index=True,
        )
        mostrar(grafica_ciudad(q1))
        bloque_codigo("Ingreso por ciudad (SQL Q1)", """-- Consulta SQL 1: ingreso por ciudad (GROUP BY)
SELECT s.ciudad,
       COUNT(*)        AS transacciones,
       SUM(v.total)    AS ingreso
FROM   ventas v
JOIN   sucursales s ON v.sucursal_id = s.sucursal_id
GROUP  BY s.ciudad
ORDER  BY ingreso DESC;""")

    with cder:
        st.subheader("👷 Ingreso por empleado")
        st.caption("¿CDMX pierde por personal ineficiente? No: su ingreso/empleado es normal. "
                   "El problema es la renta. La Paz sí tiene exceso de personal para su tráfico.")
        q3 = pd.DataFrame(R["sql_q3"])
        st.dataframe(
            q3.rename(columns={"sucursal": "Sucursal", "empleados": "Empleados",
                               "ingreso_por_empleado": "Ingreso/empleado"})
            [["Sucursal", "Empleados", "Ingreso/empleado"]]
            .style.format({"Ingreso/empleado": "${:,.0f}"}),
            width='stretch', hide_index=True,
        )
        bloque_codigo("Ingreso por empleado (SQL Q3)", """-- Consulta SQL 3: ingreso por empleado (JOIN ventas + sucursales)
SELECT s.nombre AS sucursal,
       s.empleados,
       SUM(v.total)                  AS ingreso,
       SUM(v.total) / s.empleados    AS ingreso_por_empleado
FROM   ventas v
JOIN   sucursales s ON v.sucursal_id = s.sucursal_id
GROUP  BY s.nombre, s.empleados
ORDER  BY ingreso_por_empleado DESC;""")

    st.markdown("---")
    st.subheader("⏰ ¿Cuándo vende la cafetería?")
    cizq2, cder2 = st.columns(2)

    with cizq2:
        st.markdown("**Ingreso por hora del día**")
        vph = pd.DataFrame({
            "hora": [int(h) for h in R["ventas_por_hora"].keys()],
            "ingreso": list(R["ventas_por_hora"].values()),
        }).set_index("hora")
        mostrar(grafica_horas(vph))
        st.caption("Dos picos: mañana (7–10h, café al trabajo, café oscuro) y tarde "
                   "(16–19h, café medio). Valle al mediodía (11–15h, tono claro).")

    with cder2:
        st.markdown("**Tendencia mensual**")
        vpm = pd.DataFrame({
            "mes": list(R["ventas_por_mes"].keys()),
            "ingreso": list(R["ventas_por_mes"].values()),
        }).set_index("mes")
        mostrar(grafica_meses(vpm))
        st.caption("Estacional: picos en diciembre, valle en verano. Año contra año (dic–may): ventas planas (−2.5%).")

    bloque_codigo("Patrones de tiempo", """# Ingreso por hora y por mes (pandas, sobre la columna de fecha ya convertida a datetime)
ventas['hora'] = ventas['fecha_hora'].dt.hour
por_hora = ventas.groupby('hora')['total'].sum()

ventas['mes'] = ventas['fecha_hora'].dt.to_period('M').astype(str)
por_mes = ventas.groupby('mes')['total'].sum()

# Verificación del 'crecimiento del 18%': comparar mismos meses (dic-may) año vs año
periodo_a = por_mes.loc['2024-12':'2025-05'].sum()
periodo_b = por_mes.loc['2025-12':'2026-05'].sum()
crecimiento = (periodo_b / periodo_a - 1) * 100   # ≈ -2.5%  -> NO hay crecimiento de fondo""")


# ============================================================================
# VISTA 2 — Productos
# ============================================================================
with tab2:
    st.header("Pregunta 3 del Director: ¿qué productos dejan ganancia?")
    st.caption("Vender mucho ≠ ganar mucho. Cruzamos ingreso con margen para encontrar lo realmente rentable.")

    cat = pd.DataFrame(R["cat_performance"])

    cizq, cder = st.columns([3, 2])
    with cizq:
        st.subheader("Desempeño por categoría")
        tab_cat = cat.rename(columns={
            "categoria": "Categoría", "ingreso": "Ingreso", "ganancia": "Ganancia",
            "unidades": "Unidades", "transacciones": "Transacciones", "margen_pct": "Margen %"})
        st.dataframe(
            tab_cat.style.format({
                "Ingreso": "${:,.0f}", "Ganancia": "${:,.0f}",
                "Unidades": "{:,.0f}", "Transacciones": "{:,.0f}", "Margen %": "{:.1f}%"})
            .background_gradient(subset=["Ingreso"], cmap=VERDE_GRAD)
            .background_gradient(subset=["Margen %"], cmap="YlOrBr"),
            width='stretch', hide_index=True,
        )
        st.caption("Verde = ingreso (más oscuro, más vende). Ámbar = margen %.")
    with cder:
        st.subheader("Ingreso por categoría")
        mostrar(grafica_categorias_ingreso(cat))

    bloque_codigo("Desempeño por categoría (SQL Q2 / pandas)", """-- Consulta SQL 2: categorías rentables (JOIN ventas + productos)
SELECT p.categoria,
       SUM(v.total)                        AS ingreso,
       SUM((p.precio - p.costo)*v.cantidad) AS ganancia
FROM   ventas v
JOIN   productos p ON v.producto_id = p.producto_id
GROUP  BY p.categoria
ORDER  BY ingreso DESC;

# Equivalente en pandas, con margen %:
cat = (ventas.merge(productos, on='producto_id')
             .groupby('categoria')
             .agg(ingreso=('total','sum'),
                  ganancia=('ganancia','sum'),
                  unidades=('cantidad','sum'))
             .reset_index())
cat['margen_pct'] = cat['ganancia'] / cat['ingreso'] * 100""")

    st.markdown("---")
    st.subheader("🎯 Vender mucho ≠ ganar mucho: ingreso vs margen por categoría")
    st.caption("Cada burbuja es una categoría; su tamaño = unidades vendidas. Las líneas "
               "punteadas son las medianas. **Abajo-derecha** = mucho ingreso pero margen bajo "
               "(revisar precio/costo, p. ej. el café frío del frappé). **Arriba-derecha** = "
               "las joyas: mucho ingreso y buen margen.")
    mostrar(grafica_cuadrante(cat))
    bloque_codigo("Cuadrante ingreso vs margen", """# Mapa ingreso vs margen por categoría (cat ya se calculó arriba)
# Eje X = ingreso, Eje Y = margen %, tamaño de burbuja = unidades vendidas.
# Las líneas punteadas son las medianas: parten el plano en 4 cuadrantes.
import matplotlib.pyplot as plt
plt.scatter(cat['ingreso'], cat['margen_pct'], s=cat['unidades'])
plt.axvline(cat['ingreso'].median()); plt.axhline(cat['margen_pct'].median())""")

    st.markdown("---")
    cizq2, cder2 = st.columns(2)

    with cizq2:
        st.subheader("🏆 Top productos por ingreso")
        top = pd.DataFrame(R["top10_productos_ingreso"])
        top["margen_%"] = (top["ganancia"] / top["ingreso"] * 100).round(1)
        st.dataframe(
            top.rename(columns={"nombre": "Producto", "ingreso": "Ingreso",
                                "ganancia": "Ganancia", "unidades": "Unidades",
                                "margen_%": "Margen %"})
            .style.format({"Ingreso": "${:,.0f}", "Ganancia": "${:,.0f}",
                           "Unidades": "{:,.0f}", "Margen %": "{:.1f}%"})
            .background_gradient(subset=["Ingreso"], cmap=VERDE_GRAD),
            width='stretch', hide_index=True,
        )
        st.caption("El café en grano 1kg es la joya: alto ingreso Y alto margen. "
                   "El Frappe Grande es #1 en ingreso pero margen bajo (~23%).")

    with cder2:
        st.subheader("📉 Productos de bajo desempeño")
        bot = pd.DataFrame(R["bottom10_productos"])
        st.dataframe(
            bot.rename(columns={"nombre": "Producto", "ingreso": "Ingreso",
                                "ganancia": "Ganancia", "unidades": "Unidades"})
            .style.format({"Ingreso": "${:,.0f}", "Ganancia": "${:,.0f}", "Unidades": "{:,.0f}"}),
            width='stretch', hide_index=True,
        )
        st.caption("Bajo ingreso. Revisar (no necesariamente eliminar): algunos son complementos o de temporada.")

    bloque_codigo("Top / bottom productos", """# Ranking de productos por ingreso (pandas)
prod = (ventas.merge(productos, on='producto_id')
              .groupby('nombre')
              .agg(ingreso=('total','sum'),
                   ganancia=('ganancia','sum'),
                   unidades=('cantidad','sum'))
              .reset_index())
top10    = prod.sort_values('ingreso', ascending=False).head(10)
bottom10 = prod.sort_values('ingreso').head(10)""")


# ============================================================================
# VISTA 3 — Clientes y Segmentos
# ============================================================================
with tab3:
    st.header("Pregunta 2 del Director: ¿hay clientes que ya no regresan?")
    st.caption("Segmentamos 14,200 clientes con K-Means (modelo RFM). Respuesta corta: sí, el 21.4% está dormido.")

    perfiles = pd.DataFrame(R["kmeans_perfil"])
    nombres = {3: "VIP / Campeones", 2: "Leales habituales",
               1: "En riesgo / Dormidos", 0: "Nuevos exploradores"}
    iconos = {3: "👑", 2: "💛", 1: "⚠️", 0: "🌱"}
    perfiles["nombre"] = perfiles["cluster"].map(nombres)
    perfiles["icono"] = perfiles["cluster"].map(iconos)
    perfiles = perfiles.sort_values("gasto_medio", ascending=False)

    # 4 tarjetas con líneas divisorias verticales simples entre columnas
    cols = st.columns([1, 0.05, 1, 0.05, 1, 0.05, 1])
    seg_cols = [cols[0], cols[2], cols[4], cols[6]]
    for rc in (cols[1], cols[3], cols[5]):
        rc.markdown(
            f'<div style="border-left:1px solid {CAFE_CLARO}; height:300px; '
            f'margin:8px auto 0;"></div>', unsafe_allow_html=True)
    for col, (_, fila) in zip(seg_cols, perfiles.iterrows()):
        with col:
            st.markdown(f"### {fila['icono']} {fila['nombre']}")
            st.metric("% de clientes", f"{fila['pct']}%")
            st.metric("Gasto promedio", peso(fila["gasto_medio"]))
            st.metric("Días desde última compra", f"{fila['recencia_media']:.0f}")
            st.caption(f"Edad media: {fila['edad_media']:.0f} años · {fila['n']:,} clientes")

    bloque_codigo("Segmentación K-Means", """# Clustering RFM con K-Means (scikit-learn)
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

features = ['recencia_dias', 'total_gastado', 'antiguedad_dias', 'edad']
X = clientes[features].values

# Estandarizar es indispensable: las variables están en escalas muy distintas
X_esc = StandardScaler().fit_transform(X)

# k=4 elegido con el método del codo (la inercia deja de bajar mucho en k=4)
km = KMeans(n_clusters=4, random_state=42, n_init=10)
clientes['cluster'] = km.fit_predict(X_esc)

perfil = clientes.groupby('cluster').agg(
    n=('cliente_id','count'),
    recencia_media=('recencia_dias','mean'),
    gasto_medio=('total_gastado','mean'),
    antiguedad_media=('antiguedad_dias','mean'),
    edad_media=('edad','mean'))""")

    st.markdown("---")
    cizq, cder = st.columns(2)

    with cizq:
        st.subheader("📊 Principio de Pareto")
        st.metric("Los VIP son el", f"{R['vip_pct_clientes']}% de los clientes")
        st.metric("…pero generan el", f"{R['vip_pct_gasto']}% del gasto")
        st.caption("2 de cada 3 pesos vienen de menos de 1 de cada 5 clientes. "
                   "Perder un VIP duele mucho más que perder un cliente promedio.")
        mostrar(grafica_pareto(R["gasto_por_segmento"]))
        st.caption("Barras = % del gasto que aporta cada segmento. Línea roja = % acumulado: "
                   "los VIP solos ya explican casi dos tercios del total.")

    with cder:
        st.subheader("⚠️ Indicadores de abandono (churn)")
        st.metric("Sin comprar +180 días", f"{R['churn_180_pct']}% de clientes")
        st.metric("Sin comprar +90 días", f"{R['churn_90_pct']}% de clientes")
        st.metric("Registrados que NUNCA compraron", f"{R['clientes_sin_compra_registrada']:,}")
        st.caption("Más de un tercio de la base se está enfriando. El segmento 'Dormidos' "
                   "(21.4%) llevaba ~348 días sin volver y aun así gastaba $2,197 en promedio: "
                   "clientes valiosos que se enfriaron y se pueden reactivar.")

    bloque_codigo("Pareto y churn", """# Pareto: ¿qué % del gasto generan los VIP?
gasto_por_seg = clientes.groupby('segmento')['total_gastado'].sum()
vip_pct_gasto = gasto_por_seg['VIP / Campeones'] / gasto_por_seg.sum() * 100

# Churn por recencia
churn_180 = (clientes['recencia_dias'] > 180).mean() * 100
churn_90  = (clientes['recencia_dias'] > 90).mean() * 100
nunca_compraron = clientes['ultima_compra'].isna().sum()""")

    if clusters_df is not None and "cluster" in clusters_df.columns:
        st.markdown("---")
        with st.expander("🔬 Explorar el dataset de clientes segmentados (datos reales)"):
            st.dataframe(clusters_df.head(200), width='stretch', height=300)
            st.caption(f"Mostrando 200 de {len(clusters_df):,} clientes. Generado por pipeline.py → clientes_clusters.csv")


# ----------------------------------------------------------------------------
# Pie de página
# ----------------------------------------------------------------------------
st.markdown("---")
st.caption(
    "Dashboard generado para el Proyecto Final de LAD3012 (Algoritmos y Análisis de Datos), "
    "UDLAP, Verano I 2026. Datos procesados con pipeline.py. "
    "Activa **'Mostrar código de backend'** en la barra lateral para ver el código detrás de cada tabla."
)
