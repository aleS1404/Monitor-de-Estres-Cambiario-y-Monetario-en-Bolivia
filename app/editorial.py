"""Estilo editorial verde y catálogo de conceptos para el tablero."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

PINE = "#173d32"
MOSS = "#466c50"
SAGE = "#8da38a"
GOLD = "#ac8150"
PAPER = "#f8f5ec"
INK = "#202b25"


def apply_theme() -> None:
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Libre+Baskerville:wght@400;700&display=swap');
:root { color-scheme: light; }
.stApp, [data-testid="stAppViewContainer"] { background: #f8f5ec; color: #202b25; }
[data-testid="stHeader"] { background: rgba(248,245,236,.9); }
[data-testid="stSidebar"] { background: #173d32; border-right: 5px solid #ac8150; }
[data-testid="stSidebar"] * { color: #f4f0e4 !important; }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
    background: #2c5945; border-left: 3px solid #c6a26f; border-radius: 2px;
}
[data-testid="stSidebar"] hr { border-color: #7b9a82; }
html, body, [class*="css"], [data-testid="stMarkdownContainer"] p, label, button {
    font-family: 'DM Sans', Arial, sans-serif;
}
h1, h2, h3, h4, [data-testid="stMetricLabel"] {
    font-family: 'Libre Baskerville', Georgia, serif !important; color: #173d32 !important;
}
h1, h2 { letter-spacing: -.025em; }
h1 { border-bottom: 2px solid #173d32; padding-bottom: .35rem; }
h2 { border-bottom: 1px solid #b7b29f; padding-bottom: .25rem; }
[data-testid="stMetric"] { background: #fffdf8; border: 1px solid #d9d8c9;
    border-top: 3px solid #466c50; padding: 12px 16px; box-shadow: 2px 3px 0 #ece8dc; }
[data-testid="stMetricValue"] { font-family: 'Libre Baskerville', Georgia, serif; color: #173d32; }
[data-testid="stExpander"], [data-testid="stDataFrame"] { border-color: #d1d4c7 !important; }
[data-testid="stAlert"] { border-radius: 2px; }
[data-testid="stTabs"] button[aria-selected="true"] { color: #173d32 !important; border-bottom-color: #173d32 !important; }
a { color: #285c48 !important; }
.edition-masthead { border-top: 5px double #173d32; border-bottom: 3px double #173d32;
    padding: 14px 0 12px; margin: 0 0 25px; text-align: center; }
[data-testid="stMarkdownContainer"] p.edition-kicker { color: #8a6c41; text-transform: uppercase; letter-spacing: .18em;
    font: 700 11px 'DM Sans',sans-serif; margin: 0 0 8px; }
[data-testid="stMarkdownContainer"] p.edition-title { color: #173d32; font: 700 clamp(27px, 3.1vw, 45px) 'Libre Baskerville',Georgia,serif;
    font-size: 36px !important; font-weight: 700 !important; font-family: 'Libre Baskerville',Georgia,serif !important;
    letter-spacing: -.04em; line-height: 1.25; margin: 0; }
[data-testid="stMarkdownContainer"] p.edition-subtitle { color: #425b4d; font: 12px 'DM Sans',sans-serif; letter-spacing: .07em;
    text-transform: uppercase; margin: 10px 0 0; }
.section-note { border-left: 3px solid #ac8150; background: #f1eee3; padding: 12px 16px;
    margin: 12px 0 20px; color: #34473a; font-size: .94rem; line-height: 1.65; }
.section-note strong { color: #173d32; }
.mini-label { color: #8a6c41; font: 700 11px 'DM Sans',sans-serif; letter-spacing: .12em;
    text-transform: uppercase; margin-bottom: 6px; }
.source-card { background: #fffdf8; border: 1px solid #d9d8c9; border-top: 3px solid #466c50;
    padding: 15px 17px; min-height: 145px; font-size: .9rem; line-height: 1.55; }
.source-card strong { font-family: 'Libre Baskerville',Georgia,serif; color: #173d32; }
</style>
""", unsafe_allow_html=True)


def masthead() -> None:
    st.markdown("""
<div class="edition-masthead">
  <p class="edition-kicker">Observatorio académico · DAT 262 · Bolivia</p>
  <div class="edition-title" style="font-family:Georgia,serif;font-size:34px;font-weight:700;line-height:1.2;color:#173d32;letter-spacing:-.04em;margin:8px auto 10px;max-width:850px">Monitor de estrés cambiario y monetario</div>
  <p class="edition-subtitle">Edición de datos · Banco Central de Bolivia · Procesos estocásticos</p>
</div>
""", unsafe_allow_html=True)


def note(title: str, body: str) -> None:
    st.markdown(f'<div class="section-note"><strong>{title}</strong><br>{body}</div>', unsafe_allow_html=True)


def chart(container, fig: go.Figure) -> None:
    fig.update_layout(
        paper_bgcolor="#f8f5ec", plot_bgcolor="#f8f5ec",
        font=dict(family="DM Sans, Arial, sans-serif", color=INK, size=12),
        title_font=dict(family="Libre Baskerville, Georgia, serif", color=PINE, size=16),
        colorway=[PINE, GOLD, MOSS, "#a8a377", "#7a927e", "#a66d5c"],
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#fffdf8", font_color=INK),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#e6e3d8", zerolinecolor="#d0d0c3")
    fig.update_yaxes(showgrid=True, gridcolor="#e6e3d8", zerolinecolor="#d0d0c3")
    container.plotly_chart(fig, width="stretch")


# Las filas corresponden al layout Excel BCB validado en bcb_pipeline/parse.py.
# Descripciones breves para exposición oral; la metodología completa está en el informe académico.
VARIABLES = [
    ("base_monetaria", 8, "Dinero", "Millones de Bs", "Dinero emitido y reservas bancarias en el BCB.", "Pronóstico SARIMA y alertas."),
    ("ipc", 70, "Precios", "Índice (2016=100)", "Precio promedio de una canasta de consumo; el nivel por sí solo no es inflación.", "Descomposición, SARIMA e inflación implícita."),
    ("inflacion_12m", 73, "Precios", "% interanual", "Cuánto subió el IPC frente al mismo mes del año anterior.", "Contexto del poder adquisitivo."),
    ("ahorro_mn", 87, "Depósitos", "Millones de USD del cuadro", "Ahorro en moneda nacional, convertido a USD para el cuadro del BCB.", "Contexto; no entra al índice."),
    ("ahorro_me", 89, "Depósitos", "Millones de USD", "Ahorro mantenido en moneda extranjera.", "Contexto; no entra al índice."),
    ("bolivianizacion_ahorro", 90, "Depósitos", "%", "Parte del ahorro que está en bolivianos según la definición del BCB.", "Contexto; distinto de bolivianización de depósitos."),
    ("depositos_mn", 92, "Depósitos", "Millones de USD del cuadro", "Saldos de depósitos en bolivianos convertidos a USD en el Excel.", "Reconstruir el saldo en Bs y neutralizar valoración."),
    ("depositos_me", 94, "Depósitos", "Millones de USD", "Saldos de depósitos denominados en moneda extranjera.", "SARIMA y bolivianización neutral."),
    ("bolivianizacion_depositos", 95, "Depósitos", "%", "Porcentaje oficial de depósitos en bolivianos, con definición propia del BCB.", "Referencia separada; no se mezcla con filas 92/94."),
    ("rib", 141, "Reservas", "Millones de USD", "Activos externos brutos que mantiene el banco central.", "Índice, SARIMA y escenarios Monte Carlo."),
    ("rin", 158, "Reservas", "Millones de USD", "Reservas netas después de los ajustes de la definición oficial.", "Contexto; no se duplica con RIB en el índice."),
    ("bolsin_sf", 167, "Divisas", "Millones de USD", "Dólares adjudicados al sistema financiero mediante Bolsín.", "Contexto de oferta oficial de divisas."),
    ("ventas_directas_sf", 169, "Divisas", "Millones de USD", "Dólares vendidos directamente al sistema financiero.", "Contexto de oferta oficial de divisas."),
    ("compras_bcb_sf", 171, "Divisas", "Millones de USD", "Dólares comprados por el BCB al sistema financiero.", "Contexto de flujos de divisas."),
    ("tc_fijo_bolsin", 177, "Tipo de cambio", "Bs/USD", "Precio oficial de venta usado en el período de tipo fijo.", "Comparar regímenes y construir referencia histórica."),
    ("tc_oficial", 179, "Tipo de cambio", "Bs/USD", "Cotización oficial flexible publicada en el Excel desde junio de 2026.", "Referencia mensual; el análisis diario usa CSV BCB."),
    ("tc_referencial_venta", 180, "Tipo de cambio", "Bs/USD", "Valor referencial de venta publicado entre diciembre de 2025 y mayo de 2026.", "Describir transición; no se usa para convertir depósitos."),
    ("tcr", 182, "Tipo de cambio", "Índice (dic-2022=100)", "Precio relativo de la moneda frente a socios comerciales, ajustado por inflación.", "Contexto de competitividad; no tiene modelo propio."),
]
