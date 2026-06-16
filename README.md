# ☕ Aroma del Sur — Análisis de Datos

**Proyecto Final · LAD3012 (Algoritmos y Análisis de Datos) · UDLAP · Verano I 2026**
Consultora: **AzTech Consultores** — Cliente: Director Roberto Mendoza

---

## 👥 Equipo

> ⚠️ **Llenar antes de entregar:**

| Integrante | Rol | Responsabilidad principal |
|---|---|---|
| (Nombre 1) | (p. ej. Limpieza de datos) | |
| (Nombre 2) | (p. ej. Análisis y SQL) | |
| (Nombre 3) | (p. ej. Clustering y visualización) | |
| (Nombre 4) | (p. ej. Dashboard y reporte) | |

*Todos los integrantes pueden explicar cualquier parte del análisis (ver `Documento_de_Estudio.docx`).*

---

## 🎯 El encargo

El Director de Aroma del Sur (cadena de 8 cafeterías: 5 en Puebla, 3 en CDMX) llegó con tres preguntas:

1. ¿Qué sucursales están perdiendo dinero?
2. ¿Hay clientes que ya no regresan?
3. ¿Qué productos realmente dejan ganancia?

Este proyecto responde las tres con datos, y además verifica su percepción de "crecimiento del 18%".

---

## 📁 Estructura del repositorio

```
aroma-del-sur/
├── data/                              # Datos crudos (4 CSV con errores intencionales)
│   ├── ventas.csv
│   ├── productos.csv
│   ├── sucursales.csv
│   └── clientes_app.csv
├── output/                            # Salidas generadas por pipeline.py
│   ├── ventas_limpio.csv
│   ├── productos_limpio.csv
│   ├── sucursales_limpio.csv
│   ├── clientes_limpio.csv
│   ├── clientes_clusters.csv          # Clientes con su segmento asignado
│   └── resultados.json                # Todos los resultados numéricos del análisis
├── pipeline.py                        # Pipeline maestro: limpieza + EDA + SQL + estadística + clustering
├── Aroma_del_Sur_Analisis.ipynb       # Notebook completo (corre de inicio a fin sin errores)
├── dashboard.py                       # Dashboard interactivo (Streamlit, 3 vistas + código backend)
├── Reporte_Ejecutivo_Aroma_del_Sur.pdf  # Informe de 5 páginas para el Director
├── Documento_de_Estudio.docx          # Guía de estudio del equipo para la defensa oral
├── guion_presentacion.md              # Estructura sugerida de la presentación (15 min)
├── requirements.txt                   # Dependencias de Python
└── README.md                          # Este archivo
```

---

## ▶️ Cómo correr el proyecto

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Ejecutar el pipeline (limpieza + análisis)

Genera todos los archivos limpios y `resultados.json` en `output/`:

```bash
python pipeline.py
```

### 3. Abrir el notebook

```bash
jupyter notebook Aroma_del_Sur_Analisis.ipynb
```

El notebook está organizado en 8 secciones: carga y diagnóstico, limpieza, EDA, consultas SQL,
estadística descriptiva y correlación, clustering K-Means, recomendaciones (Escalera del Insight) y conclusión.
Se puede correr completo con *Kernel → Restart & Run All*.

### 4. Levantar el dashboard interactivo

```bash
streamlit run dashboard.py
```

Se abre en el navegador (normalmente `http://localhost:8501`). Tiene tres vistas (KPIs y Sucursales,
Productos, Clientes y Segmentos), filtros en la barra lateral, y un interruptor
**"Mostrar código de backend"** que revela el código pandas/SQL que genera cada tabla y gráfica.

> El dashboard lee `output/resultados.json`, así que corre `pipeline.py` antes (ya viene incluido en `output/`).

---

## 🔍 Resumen de hallazgos

- **Sucursales:** las 3 de CDMX pierden por renta alta; La Paz (Puebla) pierde por tráfico bajo (~7 ventas/día vs ~19 del promedio). Las otras 4 de Puebla son rentables.
- **Clientes:** el 21.4% son "dormidos" (~348 días sin comprar) que sí gastaban; los VIP (18.3%) generan el 64.7% del ingreso. Segmentación con K-Means (k=4).
- **Productos:** el café en grano 1kg es lo más rentable (alto ingreso + ~50% margen); el frappé vende mucho pero deja poco margen (~23%).
- **Verificación:** el "crecimiento del 18%" no aparece en los datos; año contra año las ventas están planas (−2.5%).

Detalle completo y justificación de cada decisión en `Documento_de_Estudio.docx`.

---

## 🛠️ Notas técnicas

- **Limpieza:** se conservó el 97.4% de las ventas (de 85,300 a 83,122 filas). Los clientes quedaron en 14,200 únicos, que coincide con los registrados en la app.
- **Decisión clave:** los totales de venta faltantes **no** se reconstruyeron con `precio × cantidad` porque el total real incluye descuentos/recargos; reconstruirlos habría falseado el ingreso. Se eliminaron (eran ~0.4%).
- **Herramientas:** Python (pandas, NumPy, scikit-learn, matplotlib, seaborn), SQL (SQLite), Streamlit.
