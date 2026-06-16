"""
PIPELINE MAESTRO - Cafetería Aroma del Sur
Limpieza + EDA + SQL + Estadística + Clustering.
Genera datasets limpios y un JSON con todos los resultados clave.
"""
import pandas as pd
import numpy as np
import unicodedata
import json
import sqlite3
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

R = {}  # diccionario de resultados

def norm_txt(s):
    """quita acentos, espacios extra y pasa a minúsculas para comparar"""
    if pd.isna(s):
        return s
    s = str(s).strip().lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    return s

def parse_fecha(serie):
    """maneja fechas mixtas DD/MM/YYYY y YYYY-MM-DD"""
    s = serie.astype(str).str.strip()
    out = pd.to_datetime(s, format='%Y-%m-%d', errors='coerce')
    mask = out.isna()
    out[mask] = pd.to_datetime(s[mask], format='%d/%m/%Y', errors='coerce')
    return out

# =====================================================================
# 1. PRODUCTOS
# =====================================================================
p = pd.read_csv('data/productos.csv')
R['prod_filas_inicial'] = len(p)
R['prod_dup_id'] = int(p['producto_id'].duplicated().sum())
p = p.drop_duplicates('producto_id', keep='first')

# categorías: normalizar acentos+mayúsculas a forma canónica
cat_map = {
    'cafe caliente':'Café caliente', 'cafe frio':'Café frío',
    'para llevar':'Para llevar', 'pasteleria':'Pastelería',
    'panaderia':'Panadería', 'snacks salados':'Snacks salados',
    'bebidas':'Bebidas', 'temporada':'Temporada',
}
p['categoria'] = p['categoria'].apply(norm_txt).map(cat_map)
R['prod_categorias'] = sorted(p['categoria'].dropna().unique().tolist())
R['prod_n_categorias'] = p['categoria'].nunique()

# costo: 2 nulos -> imputar con mediana de margen de la categoría
p['fecha_alta'] = parse_fecha(p['fecha_alta'])
# margen típico por categoría (costo/precio) para imputar
p['ratio_costo'] = p['costo'] / p['precio']
ratio_cat = p.groupby('categoria')['ratio_costo'].median()
mask_costo = p['costo'].isna()
R['prod_costo_nulos'] = int(mask_costo.sum())
p.loc[mask_costo, 'costo'] = (
    p.loc[mask_costo, 'precio'] * p.loc[mask_costo, 'categoria'].map(ratio_cat)
).round(2)
p = p.drop(columns='ratio_costo')

# columnas derivadas de negocio
p['margen_unit'] = (p['precio'] - p['costo']).round(2)
p['margen_pct'] = ((p['precio'] - p['costo']) / p['precio'] * 100).round(1)
R['prod_filas_final'] = len(p)
R['prod_margen_pct_prom'] = round(p['margen_pct'].mean(), 1)

# =====================================================================
# 2. SUCURSALES
# =====================================================================
s = pd.read_csv('data/sucursales.csv')
R['suc_filas'] = len(s)
# ciudad: normalizar
ciudad_map = {'puebla':'Puebla', 'cdmx':'CDMX', 'ciudad de mexico':'CDMX'}
s['ciudad'] = s['ciudad'].apply(norm_txt).map(ciudad_map)
R['suc_ciudades'] = s['ciudad'].value_counts().to_dict()
# renta: quitar coma y convertir
s['renta_mensual'] = s['renta_mensual'].astype(str).str.replace(',', '', regex=False).astype(float)
# m2: 1 nulo -> mediana
R['suc_m2_nulos'] = int(s['m2'].isna().sum())
s['m2'] = s['m2'].fillna(s['m2'].median())
s['fecha_apertura'] = parse_fecha(s['fecha_apertura'])
s['renta_x_m2'] = (s['renta_mensual'] / s['m2']).round(0)

# =====================================================================
# 3. VENTAS
# =====================================================================
v = pd.read_csv('data/ventas.csv')
R['ven_filas_inicial'] = len(v)
R['ven_dup_completos'] = int(v.duplicated().sum())
R['ven_dup_id'] = int(v['venta_id'].duplicated().sum())

v = v.drop_duplicates()                          # quita 206 filas idénticas
v = v.drop_duplicates('venta_id', keep='first')  # quita ids repetidos restantes

v['total'] = pd.to_numeric(v['total'], errors='coerce')
R['ven_total_nulos'] = int(v['total'].isna().sum())
R['ven_total_negativos'] = int((v['total'] < 0).sum())

# IDs inválidos
R['ven_sucursal0'] = int((v['sucursal_id'] == 0).sum())
R['ven_prod_invalidos'] = int((~v['producto_id'].between(1, 146)).sum())
R['ven_cantidad0'] = int((v['cantidad'] == 0).sum())
R['ven_cantidad99'] = int((v['cantidad'] == 99).sum())

# método de pago: normalizar
pago_map = {'efectivo':'Efectivo', 'tarjeta':'Tarjeta', 'monedero':'Monedero', 'app':'App'}
v['metodo_pago'] = v['metodo_pago'].apply(norm_txt).map(pago_map)

# fecha
v['fecha'] = parse_fecha(v['fecha'])

# FILTRO de validez (registro de cuántas filas quita cada regla)
antes = len(v)
v = v[v['total'].notna() & (v['total'] > 0)]
v = v[v['cantidad'].between(1, 20)]              # quita 0 y 99
v = v[v['sucursal_id'].between(1, 8)]
v = v[v['producto_id'].between(1, 146)]
v = v[v['fecha'].notna()]
R['ven_filas_final'] = len(v)
R['ven_filas_eliminadas'] = antes_total = R['ven_filas_inicial'] - len(v)

# enriquecer con catálogo
v = v.merge(p[['producto_id','nombre','categoria','precio','costo','margen_unit']],
            on='producto_id', how='left')
v = v.merge(s[['sucursal_id','nombre','ciudad']].rename(
            columns={'nombre':'sucursal'}), on='sucursal_id', how='left')
v['ganancia'] = (v['total'] - v['costo']*v['cantidad']).round(2)
v['hora_num'] = v['hora'].str.split(':').str[0].astype(int)
v['mes'] = v['fecha'].dt.to_period('M').astype(str)
v['dia_semana'] = v['fecha'].dt.dayofweek  # 0=lunes
dias = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
v['dia_nombre'] = v['dia_semana'].map(lambda x: dias[x])

# =====================================================================
# 4. CLIENTES
# =====================================================================
c = pd.read_csv('data/clientes_app.csv')
R['cli_filas_inicial'] = len(c)
R['cli_dup_completos'] = int(c.duplicated().sum())
R['cli_dup_id'] = int(c['cliente_id'].duplicated().sum())
c = c.drop_duplicates()
c = c.drop_duplicates('cliente_id', keep='first')

c['total_gastado'] = pd.to_numeric(c['total_gastado'], errors='coerce')
# género
gen_map = {'m':'M','masculino':'M','f':'F','femenino':'F','otro':'Otro'}
c['genero'] = c['genero'].apply(norm_txt).map(gen_map).fillna('No especificado')
R['cli_genero'] = c['genero'].value_counts().to_dict()

# edad: valores imposibles -> NaN -> imputar mediana
R['cli_edad_invalida'] = int(((c['edad'] < 15) | (c['edad'] > 90)).sum())
c.loc[(c['edad'] < 15) | (c['edad'] > 90), 'edad'] = np.nan
edad_med = c['edad'].median()
c['edad'] = c['edad'].fillna(edad_med).astype(int)

# sucursal_favorita: 99 inválido -> NaN
R['cli_suc_fav_99'] = int((c['sucursal_favorita'] == 99).sum())
R['cli_suc_fav_nulos'] = int(c['sucursal_favorita'].isna().sum())
c.loc[c['sucursal_favorita'] == 99, 'sucursal_favorita'] = np.nan

# fechas
c['fecha_registro'] = parse_fecha(c['fecha_registro'])
c['ultima_compra'] = parse_fecha(c['ultima_compra'])
R['cli_ultima_compra_nulos'] = int(c['ultima_compra'].isna().sum())

# RECENCIA (días desde última compra) usando la fecha máx del dataset como "hoy"
fecha_corte = v['fecha'].max()
R['fecha_corte'] = str(fecha_corte.date())
c['recencia_dias'] = (fecha_corte - c['ultima_compra']).dt.days
# antigüedad como cliente
c['antiguedad_dias'] = (fecha_corte - c['fecha_registro']).dt.days
R['cli_filas_final'] = len(c)

# =====================================================================
# 5. EDA - resultados clave
# =====================================================================
R['kpi_ingreso_total'] = round(v['total'].sum(), 2)
R['kpi_ganancia_total'] = round(v['ganancia'].sum(), 2)
R['kpi_n_transacciones'] = len(v)
R['kpi_ticket_promedio'] = round(v['total'].mean(), 2)
R['kpi_margen_global_pct'] = round(v['ganancia'].sum()/v['total'].sum()*100, 1)

# por sucursal
suc_perf = v.groupby('sucursal').agg(
    ingreso=('total','sum'), ganancia=('ganancia','sum'),
    transacciones=('venta_id','count'), ticket_prom=('total','mean')
).round(2)
suc_perf = suc_perf.merge(s.set_index('nombre')[['ciudad','renta_mensual','empleados','m2']],
                          left_index=True, right_index=True)
# rentabilidad real = ganancia bruta - renta (18 meses)
suc_perf['renta_18m'] = suc_perf['renta_mensual']*18
suc_perf['util_post_renta'] = suc_perf['ganancia'] - suc_perf['renta_18m']
suc_perf['ingreso_x_empleado'] = (suc_perf['ingreso']/suc_perf['empleados']).round(0)
suc_perf = suc_perf.sort_values('util_post_renta', ascending=False)
R['suc_performance'] = suc_perf.reset_index().to_dict('records')
R['suc_peor'] = suc_perf.index[-1]
R['suc_mejor'] = suc_perf.index[0]
R['suc_perdedoras'] = suc_perf[suc_perf['util_post_renta']<0].index.tolist()

# por categoría
cat_perf = v.groupby('categoria').agg(
    ingreso=('total','sum'), ganancia=('ganancia','sum'),
    unidades=('cantidad','sum'), transacciones=('venta_id','count')
).round(2).sort_values('ingreso', ascending=False)
cat_perf['margen_pct'] = (cat_perf['ganancia']/cat_perf['ingreso']*100).round(1)
R['cat_performance'] = cat_perf.reset_index().to_dict('records')

# top y bottom productos
prod_perf = v.groupby('nombre').agg(
    ingreso=('total','sum'), ganancia=('ganancia','sum'), unidades=('cantidad','sum')
).round(2)
R['top10_productos_ingreso'] = prod_perf.sort_values('ingreso', ascending=False).head(10).reset_index().to_dict('records')
R['bottom10_productos'] = prod_perf.sort_values('ingreso').head(10).reset_index().to_dict('records')

# método de pago
R['metodo_pago_dist'] = v['metodo_pago'].value_counts().to_dict()
R['metodo_pago_ingreso'] = v.groupby('metodo_pago')['total'].sum().round(2).to_dict()

# patrón horario y por día
R['ventas_por_hora'] = v.groupby('hora_num')['total'].sum().round(2).to_dict()
R['ventas_por_dia'] = v.groupby('dia_nombre')['total'].sum().round(2).reindex(dias).to_dict()
R['hora_pico'] = int(v.groupby('hora_num')['total'].sum().idxmax())
R['dia_pico'] = v.groupby('dia_nombre')['total'].sum().idxmax()

# tendencia mensual
mes_serie = v.groupby('mes')['total'].sum().round(2)
R['ventas_por_mes'] = mes_serie.to_dict()

# =====================================================================
# 6. SQL (sqlite) - 3 consultas incluyendo JOIN
# =====================================================================
conn = sqlite3.connect(':memory:')
v.to_sql('ventas', conn, index=False)
p.to_sql('productos', conn, index=False)
s.to_sql('sucursales', conn, index=False)
c.to_sql('clientes', conn, index=False)

# Consulta 1: ingresos por ciudad (GROUP BY)
q1 = pd.read_sql("""
    SELECT ciudad, COUNT(*) AS transacciones, ROUND(SUM(total),2) AS ingreso
    FROM ventas GROUP BY ciudad ORDER BY ingreso DESC
""", conn)
R['sql_q1'] = q1.to_dict('records')

# Consulta 2: JOIN ventas+productos -> top categorías rentables
q2 = pd.read_sql("""
    SELECT pr.categoria,
           ROUND(SUM(ve.total),2) AS ingreso,
           ROUND(SUM(ve.ganancia),2) AS ganancia
    FROM ventas ve
    JOIN productos pr ON ve.producto_id = pr.producto_id
    GROUP BY pr.categoria
    ORDER BY ganancia DESC
""", conn)
R['sql_q2'] = q2.to_dict('records')

# Consulta 3: JOIN ventas+sucursales -> eficiencia por empleado
q3 = pd.read_sql("""
    SELECT su.nombre AS sucursal, su.empleados,
           ROUND(SUM(ve.total),2) AS ingreso,
           ROUND(SUM(ve.total)/su.empleados,0) AS ingreso_por_empleado
    FROM ventas ve
    JOIN sucursales su ON ve.sucursal_id = su.sucursal_id
    GROUP BY su.nombre, su.empleados
    ORDER BY ingreso_por_empleado DESC
""", conn)
R['sql_q3'] = q3.to_dict('records')
conn.close()

# =====================================================================
# 7. ESTADÍSTICA DESCRIPTIVA + CORRELACIÓN
# =====================================================================
R['stat_total'] = {
    'media': round(v['total'].mean(),2), 'mediana': round(v['total'].median(),2),
    'moda': round(v['total'].mode().iloc[0],2), 'std': round(v['total'].std(),2),
    'min': round(v['total'].min(),2), 'max': round(v['total'].max(),2),
    'q1': round(v['total'].quantile(.25),2), 'q3': round(v['total'].quantile(.75),2),
    'cv': round(v['total'].std()/v['total'].mean(),2)
}
R['stat_edad'] = {
    'media': round(c['edad'].mean(),1), 'mediana': round(c['edad'].median(),1),
    'std': round(c['edad'].std(),1)
}
R['stat_total_gastado'] = {
    'media': round(c['total_gastado'].mean(),2), 'mediana': round(c['total_gastado'].median(),2),
    'std': round(c['total_gastado'].std(),2)
}
# correlación a nivel sucursal: m2 vs ingreso, renta vs ingreso, empleados vs ingreso
corr_df = suc_perf[['ingreso','ganancia','renta_mensual','empleados','m2','ticket_prom']]
R['corr_matrix'] = corr_df.corr().round(2).to_dict()
R['corr_m2_ingreso'] = round(corr_df['m2'].corr(corr_df['ingreso']),2)
R['corr_renta_ingreso'] = round(corr_df['renta_mensual'].corr(corr_df['ingreso']),2)
R['corr_empleados_ingreso'] = round(corr_df['empleados'].corr(corr_df['ingreso']),2)
# correlación clientes: edad vs total_gastado, antiguedad vs total_gastado
cc = c.dropna(subset=['edad','total_gastado','antiguedad_dias'])
R['corr_edad_gasto'] = round(cc['edad'].corr(cc['total_gastado']),2)
R['corr_antiguedad_gasto'] = round(cc['antiguedad_dias'].corr(cc['total_gastado']),2)

# =====================================================================
# 8. CLUSTERING K-MEANS (clientes)
# =====================================================================
# features: recencia, total_gastado, antiguedad, edad. (RFM-like)
clu = c.dropna(subset=['recencia_dias','total_gastado','antiguedad_dias','edad']).copy()
feats = ['recencia_dias','total_gastado','antiguedad_dias','edad']
X = StandardScaler().fit_transform(clu[feats])

# método del codo
inertias = {}
for k in range(2,8):
    km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
    inertias[k] = round(km.inertia_,0)
R['kmeans_inercia'] = inertias

# modelo final k=4
K = 4
km = KMeans(n_clusters=K, random_state=42, n_init=10)
clu['cluster'] = km.fit_predict(X)
perfil = clu.groupby('cluster').agg(
    n=('cliente_id','count'),
    recencia_media=('recencia_dias','mean'),
    gasto_medio=('total_gastado','mean'),
    antiguedad_media=('antiguedad_dias','mean'),
    edad_media=('edad','mean')
).round(1)
perfil['pct'] = (perfil['n']/perfil['n'].sum()*100).round(1)
R['kmeans_k'] = K
R['kmeans_perfil'] = perfil.reset_index().to_dict('records')

# etiquetas de negocio deterministas (por rangos de gasto y recencia)
perfil_lbl = perfil.copy()
# el cluster de mayor gasto = VIP; el de mayor recencia (más días sin comprar) = En riesgo
vip_c = perfil_lbl['gasto_medio'].idxmax()
riesgo_c = perfil_lbl['recencia_media'].idxmax()
# de los restantes, el de menor antigüedad = Nuevos; el otro = Leales
restantes = [i for i in perfil_lbl.index if i not in (vip_c, riesgo_c)]
nuevos_c = perfil_lbl.loc[restantes, 'antiguedad_media'].idxmin()
leales_c = [i for i in restantes if i != nuevos_c][0]
nombres = {vip_c:'VIP / Campeones', riesgo_c:'En riesgo / Dormidos',
           nuevos_c:'Nuevos exploradores', leales_c:'Leales habituales'}
perfil_lbl['segmento'] = perfil_lbl.index.map(nombres)
R['kmeans_etiquetas'] = perfil_lbl.reset_index()[
    ['cluster','segmento','n','pct','gasto_medio','recencia_media','antiguedad_media','edad_media']
].to_dict('records')

# Pareto: % del gasto total que aportan los VIP
clu['gasto_total_seg'] = clu['cluster'].map(perfil['gasto_medio']*perfil['n'])
gasto_por_seg = clu.groupby('cluster').apply(lambda d: d['total_gastado'].sum())
R['gasto_por_segmento'] = {nombres[k]: round(val,2) for k,val in gasto_por_seg.items()}
R['vip_pct_clientes'] = round(perfil_lbl.loc[vip_c,'pct'],1)
R['vip_pct_gasto'] = round(gasto_por_seg[vip_c]/gasto_por_seg.sum()*100,1)

# Churn: clientes sin comprar en >180 días (entre los que tienen fecha)
con_fecha = c[c['recencia_dias'].notna()]
R['churn_180_pct'] = round((con_fecha['recencia_dias']>180).mean()*100,1)
R['churn_90_pct'] = round((con_fecha['recencia_dias']>90).mean()*100,1)
R['clientes_sin_compra_registrada'] = int(c['ultima_compra'].isna().sum())

# La Paz: detalle del caso
lp = suc_perf.loc['La Paz']
R['lapaz_transacciones'] = int(lp['transacciones'])
R['lapaz_transacciones_dia'] = round(lp['transacciones']/( (v['fecha'].max()-v['fecha'].min()).days ),1)
R['transacciones_dia_promedio'] = round(suc_perf['transacciones'].mean()/((v['fecha'].max()-v['fecha'].min()).days),1)

# =====================================================================
# GUARDAR
# =====================================================================
v.to_csv('output/ventas_limpio.csv', index=False)
p.to_csv('output/productos_limpio.csv', index=False)
s.to_csv('output/sucursales_limpio.csv', index=False)
c.to_csv('output/clientes_limpio.csv', index=False)
clu[['cliente_id']+feats+['cluster']].to_csv('output/clientes_clusters.csv', index=False)

# numpy -> tipos nativos para JSON
def clean(o):
    if isinstance(o, dict): return {str(k): clean(val) for k,val in o.items()}
    if isinstance(o, list): return [clean(x) for x in o]
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return float(o)
    if pd.isna(o) if np.isscalar(o) else False: return None
    return o

with open('output/resultados.json','w') as f:
    json.dump(clean(R), f, indent=2, ensure_ascii=False, default=str)

print("PIPELINE OK")
print(f"Ventas: {R['ven_filas_inicial']:,} -> {R['ven_filas_final']:,}")
print(f"Clientes: {R['cli_filas_inicial']:,} -> {R['cli_filas_final']:,}")
print(f"Ingreso total: ${R['kpi_ingreso_total']:,.0f}")
print(f"Ganancia total: ${R['kpi_ganancia_total']:,.0f}")
print(f"Margen global: {R['kpi_margen_global_pct']}%")
print(f"Sucursal mejor: {R['suc_mejor']} | peor: {R['suc_peor']}")
print(f"Sucursales que pierden tras renta: {R['suc_perdedoras']}")
print(f"Hora pico: {R['hora_pico']}h | Día pico: {R['dia_pico']}")
print(f"Corr m2~ingreso: {R['corr_m2_ingreso']} | renta~ingreso: {R['corr_renta_ingreso']}")
print(f"Corr edad~gasto: {R['corr_edad_gasto']}")
print(f"Segmentos k-means:")
for seg in R['kmeans_etiquetas']:
    print(f"  C{seg['cluster']}: {seg['segmento']} ({seg['pct']}%, gasto ${seg['gasto_medio']:,.0f})")
