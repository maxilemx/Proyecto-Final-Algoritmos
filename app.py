"""
Dashboard Superstore — Edición Analítica · LAD3012 D09
======================================================
Autor: Máximo Galván Galindo · ID 182484

Tablero ejecutivo de rentabilidad sobre el dataset Superstore (2014–2017).
El análisis y el diseño visual viven en este archivo:
  - .streamlit/config.toml -> tema base de colores (subir al repo en esa carpeta)
  - bloque CSS             -> tarjetas de KPI, tipografía, captions
  - estilizar()            -> plantilla unificada para todas las gráficas
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import re

# ============================================================
# CONFIGURACION DE PAGINA
# ============================================================
st.set_page_config(
    page_title="Superstore Dashboard",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# IDENTIDAD DEL AUTOR
# ============================================================
TU_NOMBRE = "Máximo Galván Galindo"
TU_ID     = "182484"

# ============================================================
# INSIGHT DE NEGOCIO (hallazgo + recomendación)
# ============================================================
TU_INSIGHT = """
**Hallazgo.** El descuento es el principal destructor de utilidad de la tienda.
Las líneas con descuento mayor a 20% —apenas el 14% del total— acumulan cerca de
**−$135,000**, casi un tercio de lo que gana el resto del negocio, y arriba de ese
umbral más de 9 de cada 10 órdenes pierden dinero. La evidencia geográfica lo
confirma: los 10 estados donde más se descuenta (Texas, Illinois, Ohio…) operan
**todos** en números rojos, mientras que los estados con descuento bajo promedian
+27% de margen. A nivel de producto, **Muebles** vende casi tanto como las demás
categorías pero deja un margen de apenas ~3%.

**Recomendación.** Fijar un tope de descuento de 20% (con autorización gerencial
para excepciones) y revisar el precio de la categoría Muebles. Recuperar la mitad
de esa pérdida elevaría la utilidad total **cerca de 24%** sin vender una sola
unidad más.
"""

# ============================================================
# SISTEMA DE COLOR (semántico: verde = gana, rojo = pierde)
# ============================================================
C_PRIMARY = "#1E2761"   # azul marino — neutro / marca / volumen
C_NEG     = "#E15554"   # rojo — pérdida / alerta
C_POS     = "#1F9D71"   # verde — ganancia / positivo
C_AMBER   = "#E8A33D"   # acento terciario
C_GRID    = "#E8ECF3"
C_TEXT    = "#1A1D29"
CAT_SEQ   = [C_PRIMARY, C_POS, C_AMBER]
REG_SEQ   = [C_PRIMARY, C_POS, C_AMBER, C_NEG]
DIVERGING = "RdYlGn"
PLOTLY_FONT = "Inter, -apple-system, Segoe UI, Roboto, sans-serif"

# ============================================================
# CSS — tipografía, tarjetas de KPI, captions
# (Si Streamlit cambia sus 'testids' internos en el futuro, la app
# sigue funcionando; solo perdería parte del estilo.)
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, .stApp, [class*="css"] { font-family: 'Inter', sans-serif; }

[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E8ECF3;
    border-left: 4px solid #1E2761;
    border-radius: 12px;
    padding: 16px 18px;
    box-shadow: 0 1px 3px rgba(16,24,40,0.06);
}
[data-testid="stMetricValue"] { font-weight: 800; color: #1E2761; }
[data-testid="stMetricLabel"] p { color: #5B6472; font-weight: 600; font-size: 0.85rem; }

h1 { color: #1E2761; font-weight: 800; letter-spacing: -0.5px; }
h2, h3 { color: #1E2761; font-weight: 700; }

[data-testid="stCaptionContainer"] { color: #5B6472; }
[data-testid="stAlert"] { border-radius: 12px; }
hr { margin: 0.9rem 0; border-color: #E8ECF3; }
[data-testid="stSidebar"] { background: #F4F6FA; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# PLANTILLA UNIFICADA DE GRÁFICAS
# ============================================================
def estilizar(fig, height=420):
    fig.update_layout(
        font=dict(family=PLOTLY_FONT, size=13, color=C_TEXT),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(t=30, l=10, r=10, b=10),
        hoverlabel=dict(font_size=12, font_family=PLOTLY_FONT, bgcolor="white"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    bgcolor="rgba(0,0,0,0)"),
    )
    return fig


def ejes_cartesianos(fig):
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=C_GRID)
    fig.update_yaxes(gridcolor=C_GRID, zeroline=False, linecolor=C_GRID)
    return fig


# ============================================================
# CARGAR DATOS (cache + robusto al nombre del archivo)
# ============================================================
def _normalizar_columnas(df):
    """Renombra las columnas a los nombres canónicos que usa el tablero,
    sin importar si el CSV las trae con guion, espacio, guion bajo, pegadas,
    o con palabras extra (p. ej. 'Sub Category', 'Subcategory', 'Product
    Sub-Category' -> 'Sub-Category'). Hace dos pasadas: coincidencia exacta y,
    para lo que falte, coincidencia por subcadena (subcategory antes que
    category para que no se confundan)."""
    # orden importa: subcategory ANTES que category
    canon = {
        "subcategory": "Sub-Category", "category": "Category",
        "orderid": "Order ID", "orderdate": "Order Date",
        "shipdate": "Ship Date", "shipmode": "Ship Mode",
        "customerid": "Customer ID", "customername": "Customer Name",
        "productid": "Product ID", "productname": "Product Name",
        "segment": "Segment", "country": "Country", "city": "City",
        "state": "State", "postalcode": "Postal Code", "region": "Region",
        "sales": "Sales", "quantity": "Quantity",
        "discount": "Discount", "profit": "Profit",
    }
    clave = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
    claves = {c: clave(c) for c in df.columns}
    asignado, usados = {}, set()
    # 1) coincidencia exacta
    for c in df.columns:
        dest = canon.get(claves[c])
        if dest and dest not in usados:
            asignado[c] = dest
            usados.add(dest)
    # 2) por subcadena para los canónicos que falten (en el orden de 'canon')
    for key, dest in canon.items():
        if dest in usados:
            continue
        for c in df.columns:
            if c in asignado:
                continue
            if key in claves[c]:            # p. ej. 'subcategory' en 'productsubcategory'
                asignado[c] = dest
                usados.add(dest)
                break
    return df.rename(columns=asignado)


def _parse_fechas(serie):
    """Convierte la columna de fecha sin importar el formato del CSV.
    Distintas versiones del dataset Superstore usan mes/día, día/mes o ISO;
    probamos los formatos comunes y, si ninguno calza, dejamos que pandas
    infiera (como hacía la plantilla original). Así nunca truena la carga."""
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return pd.to_datetime(serie, format=fmt)
        except (ValueError, TypeError):
            continue
    return pd.to_datetime(serie)  # inferencia flexible como último recurso


@st.cache_data
def cargar_datos():
    for nombre in ("superstore.csv", "Superstore.csv"):
        if Path(nombre).exists():
            ruta = nombre
            break
    else:
        ruta = "superstore.csv"
    df = pd.read_csv(ruta, encoding="latin-1")
    df = _normalizar_columnas(df)
    if "Order Date" in df.columns:
        df["Order Date"] = _parse_fechas(df["Order Date"])
        df["Year"]     = df["Order Date"].dt.year
        df["MonthNum"] = df["Order Date"].dt.month
        df["Month"]    = df["Order Date"].dt.to_period("M").astype(str)
    return df

df = cargar_datos()

# ------------------------------------------------------------
# Verificación de columnas: si el CSV no trae alguna columna esperada,
# mostramos un mensaje claro con los nombres reales en vez de tronar.
# ------------------------------------------------------------
_REQUERIDAS = ["Order Date", "Order ID", "Segment", "State", "Region",
               "Category", "Sales", "Quantity", "Discount", "Profit"]
_faltan = [c for c in _REQUERIDAS if c not in df.columns]
if _faltan:
    st.error(
        "**No pude reconocer algunas columnas de tu archivo de datos.**\n\n"
        f"Faltan (con el nombre que el tablero espera): `{', '.join(_faltan)}`\n\n"
        f"Tu archivo trae estas columnas: `{', '.join(map(str, df.columns))}`\n\n"
        "Manda una captura de este mensaje para terminar de ajustar el tablero, "
        "o renombra esas columnas en el CSV."
    )
    st.stop()

# Líneas base históricas (sin filtros) para los deltas de KPI
BASE_MARGEN  = 100 * df["Profit"].sum() / df["Sales"].sum()
BASE_PERDIDA = 100 * (df["Profit"] < 0).mean()
BASE_DESC    = 100 * df["Discount"].mean()
BASE_TICKET  = df["Sales"].sum() / df["Order ID"].nunique()

# ============================================================
# ENCABEZADO
# ============================================================
st.markdown("<h1>🏪 Superstore — Tablero Ejecutivo de Rentabilidad</h1>",
            unsafe_allow_html=True)
st.caption(f"Por **{TU_NOMBRE}** · ID {TU_ID} · LAD3012 · UDLAP Verano I 2026")
st.markdown(
    "Diagnóstico de **dónde se gana y dónde se pierde dinero**, con foco en las "
    "palancas que un gerente puede mover esta semana. Usa los filtros del panel "
    "izquierdo; todas las métricas y gráficas se recalculan al instante."
)
st.markdown("---")

# ============================================================
# === SECCIÓN 1 === FILTROS (sidebar)
# ============================================================
st.sidebar.header("🔎 Filtros")
regiones = st.sidebar.multiselect(
    "Región", options=sorted(df["Region"].unique()),
    default=sorted(df["Region"].unique()))
categorias = st.sidebar.multiselect(
    "Categoría", options=sorted(df["Category"].unique()),
    default=sorted(df["Category"].unique()))
segmentos = st.sidebar.multiselect(
    "Segmento", options=sorted(df["Segment"].unique()),
    default=sorted(df["Segment"].unique()))
anios = st.sidebar.multiselect(
    "Año", options=sorted(df["Year"].unique()),
    default=sorted(df["Year"].unique()))

df_f = df[
    df["Region"].isin(regiones) &
    df["Category"].isin(categorias) &
    df["Segment"].isin(segmentos) &
    df["Year"].isin(anios)
].copy()

if len(df_f) == 0:
    st.warning("No hay datos con esos filtros. Selecciona al menos una opción en cada filtro.")
    st.stop()

# ============================================================
# === SECCIÓN 2 === KPIs (6 métricas, con delta vs histórico)
# El delta compara la selección actual contra el total 2014–2017,
# para detectar si el segmento filtrado está mejor o peor que el promedio.
# ============================================================
ventas      = df_f["Sales"].sum()
ganancia    = df_f["Profit"].sum()
margen      = 100 * ganancia / ventas if ventas else 0
ordenes     = df_f["Order ID"].nunique()
ticket      = ventas / ordenes if ordenes else 0
pct_perdida = 100 * (df_f["Profit"] < 0).mean()
desc_prom   = 100 * df_f["Discount"].mean()

k1, k2, k3 = st.columns(3)
k1.metric("Ventas totales", f"${ventas:,.0f}",
          help="Suma de Sales con los filtros aplicados")
k2.metric("Ganancia total", f"${ganancia:,.0f}",
          help="Suma de Profit con los filtros aplicados")
k3.metric("Margen %", f"{margen:.1f}%",
          delta=f"{margen - BASE_MARGEN:+.1f} pp vs histórico ({BASE_MARGEN:.1f}%)",
          help="Ganancia / Ventas. El histórico es el margen 2014–2017 sin filtros")

k4, k5, k6 = st.columns(3)
k4.metric("Ticket promedio", f"${ticket:,.0f}",
          delta=f"{ticket - BASE_TICKET:+,.0f} vs histórico",
          help="Venta promedio por orden (Sales / órdenes únicas)")
k5.metric("Líneas con pérdida", f"{pct_perdida:.1f}%",
          delta=f"{pct_perdida - BASE_PERDIDA:+.1f} pp vs histórico ({BASE_PERDIDA:.1f}%)",
          delta_color="inverse",
          help="Porcentaje de líneas de venta con ganancia negativa. Más bajo = mejor")
k6.metric("Descuento promedio", f"{desc_prom:.1f}%",
          delta=f"{desc_prom - BASE_DESC:+.1f} pp vs histórico ({BASE_DESC:.1f}%)",
          delta_color="inverse",
          help="Descuento medio de las líneas filtradas. Más alto suele significar menos margen")

st.markdown("---")

# ============================================================
# === SECCIÓN 3 === DIAGNÓSTICO AUTOMÁTICO
# Dos alertas dinámicas que resumen la historia con los filtros activos.
# ============================================================
st.subheader("🚨 Diagnóstico automático")

mask_alto = df_f["Discount"] > 0.20
perdida_desc = df_f.loc[mask_alto, "Profit"].sum()
lineas_alto = int(mask_alto.sum())
pct_lineas_alto = 100 * mask_alto.mean()

# categoría de menor margen
cat_m = df_f.groupby("Category").agg(S=("Sales", "sum"), P=("Profit", "sum"))
cat_m["Margin"] = 100 * cat_m["P"] / cat_m["S"]
cat_m = cat_m.sort_values("Margin")
peor_cat = cat_m.index[0]
peor_cat_margen = cat_m["Margin"].iloc[0]

d1, d2 = st.columns(2)
with d1:
    if perdida_desc < 0:
        st.error(
            f"**Descuentos agresivos:** las {lineas_alto:,} líneas con descuento "
            f"mayor a 20% ({pct_lineas_alto:.0f}% del total) acumulan "
            f"**${perdida_desc:,.0f}** de utilidad. Es dinero que se regala."
        )
    else:
        st.success(
            f"Con estos filtros, las líneas con descuento mayor a 20% "
            f"({lineas_alto:,} líneas) aún son rentables (${perdida_desc:,.0f})."
        )
with d2:
    if peor_cat_margen < 8:
        st.error(
            f"**Categoría de bajo margen:** *{peor_cat}* deja apenas "
            f"**{peor_cat_margen:.1f}%** de margen en el periodo filtrado — muy por "
            f"debajo del resto. Candidata a revisión de precio y descuentos."
        )
    else:
        st.info(
            f"La categoría de menor margen es *{peor_cat}* "
            f"({peor_cat_margen:.1f}%), aún en terreno saludable con estos filtros."
        )

st.markdown("---")

# ============================================================
# === SECCIÓN 4 === ¿DÓNDE ESTÁ EL DINERO? (composición)
# Ventas vs ganancia por categoría y por segmento de cliente.
# ============================================================
st.subheader("🗺️ ¿Dónde está el dinero?")
c_cat, c_seg = st.columns(2)

with c_cat:
    st.markdown("**Por categoría de producto**")
    cat = (df_f.groupby("Category")
               .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
               .reset_index())
    cat["Margin"] = 100 * cat["Profit"] / cat["Sales"]
    fig_cat = go.Figure()
    fig_cat.add_bar(x=cat["Category"], y=cat["Sales"], name="Ventas",
                    marker_color=C_PRIMARY)
    fig_cat.add_bar(x=cat["Category"], y=cat["Profit"], name="Ganancia",
                    marker_color=C_POS,
                    text=[f"{m:.0f}% margen" for m in cat["Margin"]],
                    textposition="outside")
    fig_cat.update_layout(barmode="group")
    estilizar(fig_cat, height=420)
    ejes_cartesianos(fig_cat)
    st.plotly_chart(fig_cat, use_container_width=True)
    st.caption("💡 Lectura ejecutiva: una barra de ventas alta con ganancia chica "
               "(Muebles) es un problema de rentabilidad, no de demanda.")

with c_seg:
    st.markdown("**Por segmento de cliente**")
    seg = (df_f.groupby("Segment")
               .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
               .reset_index())
    seg["Margin"] = 100 * seg["Profit"] / seg["Sales"]
    fig_seg = go.Figure()
    fig_seg.add_bar(x=seg["Segment"], y=seg["Sales"], name="Ventas",
                    marker_color=C_PRIMARY)
    fig_seg.add_bar(x=seg["Segment"], y=seg["Profit"], name="Ganancia",
                    marker_color=C_POS,
                    text=[f"{m:.0f}% margen" for m in seg["Margin"]],
                    textposition="outside")
    fig_seg.update_layout(barmode="group")
    estilizar(fig_seg, height=420)
    ejes_cartesianos(fig_seg)
    st.plotly_chart(fig_seg, use_container_width=True)
    st.caption("💡 Lectura ejecutiva: *Consumer* es el segmento más grande pero el de "
               "menor margen; *Home Office* vende menos pero es el más rentable.")

st.markdown("---")

# ============================================================
# === SECCIÓN 5 === EL FACTOR DESCUENTO (la palanca clave)
# (a) Análisis de umbral: margen por tramo de descuento.
# (b) Evidencia geográfica: descuento promedio vs margen por estado
#     (correlación ≈ −0.97 con todos los datos: relación casi perfecta).
# ============================================================
st.subheader("💸 El factor descuento: dónde se rompe la rentabilidad")
c_cliff, c_evid = st.columns([3, 2])

with c_cliff:
    st.markdown("**Margen por tramo de descuento**")
    bins   = [-0.001, 0.0, 0.10, 0.20, 0.30, 0.50, 1.0]
    labels = ["Sin desc.", "1-10%", "11-20%", "21-30%", "31-50%", "51-80%"]
    df_f["DiscBucket"] = pd.cut(df_f["Discount"], bins=bins, labels=labels)
    db = (df_f.groupby("DiscBucket", observed=True)
              .agg(Lineas=("Sales", "size"), Sales=("Sales", "sum"),
                   Profit=("Profit", "sum"))
              .reset_index())
    db["Margin"] = 100 * db["Profit"] / db["Sales"]
    db["PctPerdida"] = (df_f.groupby("DiscBucket", observed=True)
                            .apply(lambda x: 100 * (x["Profit"] < 0).mean(),
                                   include_groups=False)
                            .reindex(db["DiscBucket"]).values)

    fig_cliff = go.Figure()
    fig_cliff.add_bar(
        x=db["DiscBucket"], y=db["Margin"], name="Margen %",
        marker_color=[C_POS if m >= 0 else C_NEG for m in db["Margin"]],
        text=[f"{m:.0f}%" for m in db["Margin"]], textposition="outside")
    fig_cliff.add_trace(go.Scatter(
        x=db["DiscBucket"], y=db["PctPerdida"], name="% de líneas con pérdida",
        yaxis="y2", mode="lines+markers", line=dict(color=C_PRIMARY, width=3)))
    fig_cliff.update_layout(
        yaxis=dict(title="Margen %"),
        yaxis2=dict(title="% líneas con pérdida", overlaying="y",
                    side="right", range=[0, 105]))
    estilizar(fig_cliff, height=440)
    fig_cliff.update_xaxes(showgrid=False, zeroline=False, linecolor=C_GRID)
    st.plotly_chart(fig_cliff, use_container_width=True)
    st.caption(
        "💡 Lectura ejecutiva: el margen aguanta hasta el 20% de descuento; "
        "**a partir de ahí se desploma** y casi todas las órdenes pierden dinero "
        "(línea azul). Conclusión operativa: **tope de 20%**.")

with c_evid:
    st.markdown("**La prueba por estado** *(cada punto = un estado)*")
    ev = (df_f.groupby(["State", "Region"])
              .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"),
                   Disc=("Discount", "mean"), N=("Sales", "size"))
              .reset_index())
    ev = ev[ev["N"] >= 20]  # estados con muestra suficiente
    ev["Margin"] = 100 * ev["Profit"] / ev["Sales"]
    ev["DiscPct"] = 100 * ev["Disc"]
    fig_ev = px.scatter(
        ev, x="DiscPct", y="Margin", size="Sales", color="Region",
        hover_name="State", size_max=40, color_discrete_sequence=REG_SEQ,
        labels={"DiscPct": "Descuento promedio (%)", "Margin": "Margen (%)",
                "Sales": "Ventas ($)"})
    fig_ev.add_hline(y=0, line_dash="dash", line_color=C_NEG)
    if len(ev) >= 3:
        r = ev[["DiscPct", "Margin"]].corr().iloc[0, 1]
        fig_ev.add_annotation(
            x=0.98, y=0.95, xref="paper", yref="paper", showarrow=False,
            text=f"correlación r = {r:.2f}",
            font=dict(size=12, color=C_PRIMARY), align="right")
    estilizar(fig_ev, height=440)
    ejes_cartesianos(fig_ev)
    st.plotly_chart(fig_ev, use_container_width=True)
    st.caption(
        "💡 Lectura ejecutiva: a más descuento promedio, menos margen — la relación "
        "es casi una línea recta. **No es mala suerte de algunos estados: es la "
        "política de descuentos.**")

st.markdown("---")

# ============================================================
# === SECCIÓN 6 === CONCENTRACIÓN POR ESTADO (Pareto / ABC)
# La versión reducida del dataset no trae clientes; hacemos el Pareto por
# estado, que responde la misma pregunta de concentración del negocio.
# ============================================================
st.subheader("👥 Concentración de ventas por estado (análisis de Pareto)")
par = (df_f.groupby("State")
           .agg(Sales=("Sales", "sum"))
           .reset_index()
           .sort_values("Sales", ascending=False)
           .reset_index(drop=True))
par["CumPct"] = 100 * par["Sales"].cumsum() / par["Sales"].sum()
n20 = max(int(len(par) * 0.2), 1)
pct_top20 = 100 * par.head(n20)["Sales"].sum() / par["Sales"].sum()

topn = par.head(15)
fig_par = go.Figure()
fig_par.add_bar(x=topn["State"], y=topn["Sales"], name="Ventas",
                marker_color=C_PRIMARY)
fig_par.add_trace(go.Scatter(
    x=topn["State"], y=topn["CumPct"],
    name="% acumulado de ventas (todos los estados)",
    yaxis="y2", mode="lines+markers", line=dict(color=C_POS, width=3)))
fig_par.update_layout(
    yaxis=dict(title="Ventas ($)"),
    yaxis2=dict(title="% acumulado", overlaying="y", side="right",
                range=[0, 100]),
    xaxis_tickangle=-40)
estilizar(fig_par, height=440)
fig_par.update_xaxes(showgrid=False, zeroline=False, linecolor=C_GRID)
st.plotly_chart(fig_par, use_container_width=True)
st.caption(
    f"💡 Lectura ejecutiva: el **20% de los estados concentra el {pct_top20:.0f}% "
    "de las ventas**. El esfuerzo comercial y de inventario debería priorizar ese "
    "puñado de mercados. *(Se grafican los 15 mayores; la línea verde acumula sobre "
    "el total.)*")

st.markdown("---")

# ============================================================
# === SECCIÓN 8 === TENDENCIA Y ESTACIONALIDAD
# Línea mensual (ventas + ganancia) + reloj estacional radial por año.
# ============================================================
st.subheader("📈 Tendencia y estacionalidad")
c_line, c_rad = st.columns([3, 2])

with c_line:
    st.markdown("**Ventas y ganancia mensuales**")
    ml = (df_f.groupby("Month")
              .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
              .reset_index())
    fig_ml = go.Figure()
    fig_ml.add_trace(go.Scatter(x=ml["Month"], y=ml["Sales"], name="Ventas",
                                mode="lines+markers", line=dict(color=C_PRIMARY)))
    fig_ml.add_trace(go.Scatter(x=ml["Month"], y=ml["Profit"], name="Ganancia",
                                mode="lines+markers", line=dict(color=C_POS)))
    estilizar(fig_ml, height=420)
    ejes_cartesianos(fig_ml)
    st.plotly_chart(fig_ml, use_container_width=True)
    st.caption("💡 Lectura ejecutiva: la tienda crece año con año (~20-30% en ventas) "
               "y los picos de fin de año concentran el grueso del resultado.")

with c_rad:
    st.markdown("**Reloj estacional** *(ventas por mes, un anillo por año)*")
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    fig_rad = go.Figure()
    for i, yr in enumerate(sorted(df_f["Year"].unique())):
        sub = (df_f[df_f["Year"] == yr].groupby("MonthNum")["Sales"]
               .sum().reindex(range(1, 13), fill_value=0))
        fig_rad.add_trace(go.Scatterpolar(
            r=sub.values, theta=meses, name=str(yr), fill="toself", opacity=0.4,
            line=dict(color=REG_SEQ[i % len(REG_SEQ)])))
    estilizar(fig_rad, height=420)
    fig_rad.update_layout(legend=dict(orientation="h", y=-0.08, x=0))
    st.plotly_chart(fig_rad, use_container_width=True)
    st.caption("💡 Lectura ejecutiva: el patrón se repite cada año (fuerte en "
               "sep–dic, débil en feb). Útil para planear **inventario y personal**.")

st.markdown("---")

# ============================================================
# === SECCIÓN 9 === MAPA GEOGRÁFICO (EE. UU.)
# ============================================================
st.subheader("📍 Rentabilidad por estado")
ABBR = {'Alabama':'AL','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO',
'Connecticut':'CT','Delaware':'DE','District of Columbia':'DC','Florida':'FL','Georgia':'GA',
'Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY',
'Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI',
'Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE',
'Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY',
'North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR',
'Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD',
'Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virginia':'VA','Washington':'WA',
'West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY'}
geo = (df_f.groupby("State")
           .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
           .reset_index())
geo["Code"] = geo["State"].map(ABBR)
geo["Margin"] = 100 * geo["Profit"] / geo["Sales"]
fig_geo = px.choropleth(
    geo.dropna(subset=["Code"]), locations="Code", locationmode="USA-states",
    color="Profit", scope="usa", hover_name="State",
    color_continuous_scale=DIVERGING, color_continuous_midpoint=0,
    custom_data=["Sales", "Margin"],
    labels={"Profit": "Ganancia ($)"})
fig_geo.update_traces(
    hovertemplate="<b>%{hovertext}</b><br>Ganancia: $%{z:,.0f}"
                  "<br>Ventas: $%{customdata[0]:,.0f}"
                  "<br>Margen: %{customdata[1]:.1f}%<extra></extra>")
estilizar(fig_geo, height=460)
fig_geo.update_geos(bgcolor="rgba(0,0,0,0)", lakecolor="rgba(0,0,0,0)")
st.plotly_chart(fig_geo, use_container_width=True)
n_rojos = int((geo["Profit"] < 0).sum())
st.caption(
    f"💡 Lectura ejecutiva: **{n_rojos} estados** operan con pérdida (en rojo). "
    "La gráfica de la sección de descuentos explica por qué: los estados en rojo "
    "son los más descontados.")

st.markdown("---")

# ============================================================
# === SECCIÓN 10 === TABLA: top 10 órdenes por venta
# ============================================================
st.subheader("📋 Top 10 órdenes por venta")
top10 = (
    df_f.sort_values("Sales", ascending=False)
        .head(10)
        [["Order ID", "Order Date", "Category", "Region", "Sales", "Profit"]]
)
st.dataframe(
    top10, use_container_width=True, hide_index=True,
    column_config={
        "Order Date": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
        "Sales":  st.column_config.NumberColumn("Ventas", format="$%.0f"),
        "Profit": st.column_config.NumberColumn("Ganancia", format="$%.0f"),
    })
st.caption("💡 Dato curioso: varias de las órdenes más grandes pierden dinero — "
           "vender mucho no es lo mismo que ganar mucho.")

st.markdown("---")

# ============================================================
# === SECCIÓN 11 === PREGUNTAS GUÍA (panel desplegable)
# ============================================================
with st.expander("🔍 Preguntas guía para profundizar en el análisis"):
    st.markdown("""
**Juega con los filtros del panel izquierdo mientras te haces estas preguntas:**

1. **Región menos rentable.** Deja solo una región a la vez. ¿Cuál tiene el margen
más bajo? Compara su KPI de descuento promedio contra el histórico.

2. **Categoría problema.** En "¿Dónde está el dinero?", ¿qué categoría vende mucho
pero deja poco margen? ¿Qué decisión tomarías como gerente con esa categoría?

3. **El umbral del descuento.** En "El factor descuento", confirma a partir de qué
nivel el margen se vuelve negativo. ¿Vale la pena una venta con 30%+ de descuento?

4. **Causa, no casualidad.** En "La prueba por estado", ¿hay algún estado con mucho
descuento y buen margen? ¿Qué te dice eso sobre quién controla la rentabilidad?

5. **Patrón temporal.** En el reloj estacional, ¿qué meses se repiten como fuertes
o débiles cada año? ¿Qué implica para inventario, contratación y promociones?

6. **Reto extra (modo CEO).** Si tuvieras 10 segundos para tomar UNA decisión con
este tablero, ¿cuál sería y por qué? (Pista: revisa el diagnóstico automático.)

---
**Tu insight ideal:** una frase con TU hallazgo (con un dato concreto) + una frase
con TU recomendación.
    """)

# ============================================================
# === SECCIÓN 12 === INSIGHT DE NEGOCIO
# ============================================================
st.subheader("💡 Insight de negocio")
st.info(TU_INSIGHT)

# ============================================================
# === SECCIÓN 13 === FOOTER
# ============================================================
st.markdown("---")
st.caption("Tablero preparado con pandas + plotly + Streamlit · LAD3012 D09 · "
           f"{TU_NOMBRE} ({TU_ID})")
