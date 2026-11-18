"""Monitor de estrés cambiario y monetario de Bolivia — tablero Streamlit.
Ejecutar:  streamlit run app/streamlit_app.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from stress_monitor import data, demo, forecasting as fc, gap as gp, markov as mk  # noqa: E402
from stress_monitor import simulation as sim, stationarity as stat  # noqa: E402
from app.editorial import VARIABLES, GOLD, MOSS, PINE, apply_theme, chart, masthead, note  # noqa: E402

st.set_page_config(page_title="Monitor de estrés — Bolivia", page_icon="🇧🇴", layout="wide")
COLORS = {0: "#2e6b4b", 1: "#b78b3e", 2: "#a34b38"}
DISCLAIMER = ("⚠️ **Aviso:** esta herramienta es académica. Informa con probabilidades y escenarios; "
              "**no es asesoría financiera ni una predicción**.")
PAGES = ["Semáforo del sistema", "Brecha cambiaria", "Reservas y depósitos", "Inflación",
         "Simulador de riesgo", "Alertas", "Variables y fuentes", "Metodología"]


# ---------------------------------------------------------------- datos (con caché)
@st.cache_data(show_spinner=False, ttl=3600)
def get_data():
    m, d = data.load_monthly(), data.load_daily_key()
    col, pdf = data.load_p2p()
    return m, d, col, pdf


@st.cache_data(show_spinner=False, ttl=3600)
def get_gap(use_demo: bool):
    m, d, col, pdf = get_data()
    g = data.build_gap(m, d, col, pdf, external=data.load_external_parallel(),
                       official_tco=data.load_bcb_tco())
    if len(g) < gp.MIN_OBS and use_demo:
        return demo.synthetic_gap(m, d), True
    return g, False


@st.cache_data(show_spinner="Ajustando SARIMA (Box-Jenkins)…")
def get_sarima(col: str, steps: int):
    m = get_data()[0]
    r = fc.full_analysis(m, col, steps=steps)
    return {"y": r["y"], "forecast": r["forecast"], "diag": r["diag"], "anom": r["anom"],
            "order": r["spec"].order, "sorder": r["spec"].seasonal_order}


@st.cache_data(show_spinner=False)
def get_results():
    p = ROOT / "reports" / "results.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def line(fig, x, y, name, **kw):
    fig.add_trace(go.Scatter(x=x, y=y, name=name, mode="lines", **kw))


def shade_states(fig, states: pd.Series):
    start, cur = states.index[0], int(states.iloc[0])
    for i in range(1, len(states)):
        if int(states.iloc[i]) != cur or i == len(states) - 1:
            fig.add_vrect(x0=start, x1=states.index[i], fillcolor=COLORS[cur], opacity=0.18, line_width=0)
            start, cur = states.index[i], int(states.iloc[i])


# ---------------------------------------------------------------- páginas
def page_semaforo(m, gap_real):
    st.header("Semáforo del sistema")
    note("¿Qué es el estrés monetario?", "Es una medida descriptiva de presión, no una calificación oficial. Combina la caída anual de reservas con el cambio de la proporción de depósitos en bolivianos calculado a un mismo tipo de cambio. Así evita confundir una conversión contable con una salida de depósitos.")
    with st.expander("Umbrales de los estados (decisión del analista)"):
        c1, c2 = st.columns(2)
        q1 = c1.slider("Percentil de inicio de **Tensión**", 0.40, 0.80, 0.60, 0.01)
        q2 = c2.slider("Percentil de inicio de **Crisis**", 0.80, 0.97, 0.85, 0.01)
    ci = mk.stress_index(m)
    states = mk.classify(ci["indice"], (q1, q2))
    fit = mk.fit_markov(states)
    cur = int(states.iloc[-1])
    t1, t2 = states.attrs["umbrales"]

    st.markdown("#### Lectura del último mes")
    st.write("El estado resume dónde cae el índice frente a su propia historia. Los componentes **z** indican cuántas desviaciones típicas está cada señal por encima o debajo de su promedio; un valor positivo aporta más presión.")
    a, b, c = st.columns([1.2, 1, 1.6])
    a.markdown(f"<div style='background:{COLORS[cur]};color:white;padding:18px;border-radius:12px;text-align:center'>"
               f"<div style='font-size:14px'>Estado a {states.index[-1]:%b %Y}</div>"
               f"<div style='font-size:34px;font-weight:700'>{mk.ESTADOS[cur]}</div></div>", unsafe_allow_html=True)
    b.metric("Índice de estrés", f"{ci['indice'].iloc[-1]:.2f}")
    b.caption(f"Umbral tensión {t1:.2f} · crisis {t2:.2f}")
    comp = ci.drop(columns="indice").iloc[-1]
    c.markdown("**Qué lo explica** (puntos z; + = más estrés)")
    c.dataframe(comp.rename("z").round(2).to_frame(), width="stretch")
    st.caption("Los estados son **relativos a la historia 1989-hoy** (percentiles del índice): «Crisis» significa que el índice "
               "está en el tramo más alto de su historia, no es un diagnóstico de crisis. "
               "La brecha se analiza por separado para conservar los mismos componentes en toda la serie.")

    fig = go.Figure(); shade_states(fig, states)
    line(fig, ci.index, ci["indice"], "Índice", line=dict(color=PINE, width=2))
    fig.update_layout(height=330, margin=dict(l=10, r=10, t=30, b=10), title="Índice de estrés y estados (verde/ámbar/rojo)")
    note("Cómo leer la serie", "Cada punto es un mes. El fondo coloreado muestra el estado que resulta de comparar el índice con los percentiles elegidos. El modelo usa dos señales en toda la historia; la brecha P2P se estudia aparte porque no existe para todos los años.")
    chart(st, fig)

    c1, c2 = st.columns(2)
    note("Modelo: cadena de Markov", "Contamos cuántas veces un estado pasó a otro entre meses consecutivos. La matriz muestra esas frecuencias como probabilidades; al multiplicarla estimamos la distribución a 1, 3 y 6 meses. Es una aproximación estadística, no una predicción de crisis.")
    probs = mk.forecast_state_probs(fit.P, cur, (1, 3, 6))
    fb = go.Figure()
    for i, name in enumerate(mk.ESTADOS):
        fb.add_bar(x=[f"{h} mes(es)" for h in probs], y=[probs[h][i] for h in probs], name=name, marker_color=COLORS[i])
    fb.update_layout(barmode="stack", height=320, title="Probabilidad de estar en cada estado", yaxis_tickformat=".0%",
                     margin=dict(l=10, r=10, t=40, b=10))
    chart(c1, fb)
    hm = go.Figure(go.Heatmap(z=fit.P, x=mk.ESTADOS, y=mk.ESTADOS, colorscale=[[0, "#e7eee3"], [1, PINE]], zmin=0, zmax=1,
                              text=np.round(fit.P, 2), texttemplate="%{text}"))
    hm.update_layout(height=320, title="Matriz de transición mensual P (fila = desde)", yaxis_autorange="reversed",
                     margin=dict(l=10, r=10, t=40, b=10))
    chart(c2, hm)

    st.markdown("#### Qué significan las probabilidades")
    st.write("**Largo plazo π** es la proporción teórica de meses en cada estado si la matriz permaneciera igual durante mucho tiempo. **Permanencia media** estima cuántos meses seguidos duraría un estado según esa misma matriz.")
    tbl = pd.DataFrame({"Estado": mk.ESTADOS, "Largo plazo π": fit.stationary,
                        "Permanencia media (meses)": fit.sojourn})
    st.dataframe(tbl.style.format({"Largo plazo π": "{:.1%}", "Permanencia media (meses)": "{:.1f}"}), width="stretch", hide_index=True)
    ind, o2 = mk.test_independence(fit.counts), mk.test_second_order(states)
    st.caption(f"Propiedad de Markov: independencia χ² p={ind['p_valor']:.2g}; orden 1 vs 2 (LR) p={o2['p_valor']:.2g}. "
               "Con p<0,05 en el segundo contraste la cadena de primer orden es una aproximación.")
    st.markdown("**Validación con episodios conocidos**")
    st.write("Comparamos los estados calculados con períodos históricos definidos antes de mirar la tabla. Cada fila indica qué porcentaje de meses de ese episodio cayó en cada estado.")
    st.dataframe(mk.episode_table(states).style.format({k: "{:.0%}" for k in mk.ESTADOS}), width="stretch", hide_index=True)
    st.markdown("**Robustez a los umbrales**")
    st.write("Esta tabla repite la clasificación con otros cortes. Si el diagnóstico cambia mucho, la lectura del semáforo depende de una elección del analista.")
    st.dataframe(mk.robustness(ci["indice"]).round(2), width="stretch", hide_index=True)
    st.info(DISCLAIMER)


def page_brecha(m, d, gap_df, is_demo):
    st.header("Brecha cambiaria")
    note("¿Qué es la brecha cambiaria?", "Es la diferencia porcentual entre el precio P2P de referencia y el tipo oficial o referencial comparable: 100 × (P2P / oficial − 1). Una brecha positiva indica que el precio anunciado en P2P está por encima de la referencia del BCB; no mide por sí sola la cantidad de dólares negociados.")
    st.markdown("#### Tres etapas del tipo de cambio")
    st.write("El gráfico separa la venta fija del Bolsín, el valor referencial publicado entre diciembre de 2025 y mayo de 2026 y el oficial flexible desde junio de 2026. Cada línea procede del Excel semanal del BCB.")
    t = m[["tc_fijo_bolsin", "tc_referencial_venta", "tc_oficial"]]["2022":]
    fig = go.Figure()
    for c, n in zip(t.columns, ["Fijo (Bolsín)", "Referencial (venta)", "Oficial flexible"]):
        fig.add_trace(go.Scatter(x=t.index, y=t[c], name=n, mode="lines+markers"))
    fig.update_layout(height=300, title="Tres regímenes del tipo de cambio (datos oficiales del BCB, Bs/USD)",
                      margin=dict(l=10, r=10, t=40, b=10))
    chart(st, fig)
    if gap_df.empty or len(gap_df) < gp.MIN_OBS:
        st.warning(f"Todavía no hay historial suficiente del dólar paralelo (se necesitan ≥{gp.MIN_OBS} días). "
                   "Para activarlo: `python -m bcb_pipeline collect --loop` (recolector propio) y/o "
                   "`python -m bcb_pipeline import-pdf HISTORICO.pdf` (tabla de activos virtuales del BCB). "
                   "También puedes activar los **datos DEMO** en la barra lateral para ver la pantalla.")
        return
    if is_demo:
        st.error("🧪 **DATOS DEMO SIMULADOS** — no son cotizaciones reales; sirven solo para ver cómo luce la pantalla.")
    else:
        st.caption(f"Fuente del paralelo: **{gap_df['fuente_p2p'].iloc[0]}**; "
                   "oficial diario: BCB (TCO) desde 29-jun-2026. La mediana P2P es un precio anunciado, no una transacción ejecutada.")
    st.markdown("#### Precio observado: P2P y oficial")
    st.write("La línea P2P es la mediana histórica de anuncios de paralelo.bo; la oficial combina la referencia mensual y el TCO diario del BCB desde el régimen flexible. Se muestran en Bs por USD de referencia. El PDF de activos virtuales y el recolector DolarApi no se empalman con esta mediana.")
    fig = go.Figure()
    line(fig, gap_df.index, gap_df["oficial"], "Oficial (referencia)"); line(fig, gap_df.index, gap_df["paralelo"], "Paralelo (USDT)")
    fig.update_layout(height=300, title="Oficial vs. paralelo (Bs/USD)", margin=dict(l=10, r=10, t=40, b=10))
    chart(st, fig)

    st.markdown("#### H1 · ¿Cuánto tarda en disiparse una brecha?")
    note("Modelo AR(1)", "Relaciona la brecha de hoy con la de ayer. El coeficiente φ mide persistencia: cerca de 1 implica ajuste lento. Si 0 < φ < 1, la vida media estima cuántos días tarda una desviación en reducirse a la mitad. ADF comprueba si la serie puede tratarse como estacionaria en la muestra elegida.")
    scope = st.radio("Muestra para el AR(1)", ["Régimen flexible (desde 29-jun-2026)", "Toda la serie"], horizontal=True)
    g = gap_df["brecha_pct"]
    if scope.startswith("Régimen"):
        g = g[g.index >= data.FECHA_FLEXIBLE]
    r = gp.ar1_gap(g)
    if not r["ok"]:
        st.info(r["motivo"])
    else:
        st.write("Estas cifras se recalculan con la muestra seleccionada. La **brecha media de largo plazo** es el nivel al que apunta el AR(1) bajo sus supuestos; no es una meta oficial.")
        c = st.columns(4)
        c[0].metric("φ (persistencia diaria)", f"{r['phi']:.3f}", f"± {1.96 * r['se_phi']:.3f}", delta_color="off")
        c[1].metric("Vida media de la brecha", f"{r['vida_media']:.1f} días" if np.isfinite(r["vida_media"]) else "∞")
        c[2].metric("Brecha media de largo plazo", f"{r['media_larga']:.2f}%")
        c[3].metric("ADF (p)", f"{r['adf']['p_valor']:.3f}", "estacionaria" if r["adf"]["estacionaria_5%"] else "no estacionaria", delta_color="off")
        note("Lectura de la banda", "La línea muestra la brecha observada. La franja es el intervalo de variación esperado bajo el AR(1) ajustado; los puntos fuera de ella son movimientos poco habituales para ese modelo, no una prueba automática de crisis.")
        fg = go.Figure(); lo, hi = r["banda95"]
        fg.add_hrect(y0=lo, y1=hi, fillcolor=MOSS, opacity=0.16, line_width=0)
        line(fg, g.index, g, "Brecha %", line=dict(color=PINE))
        fg.update_layout(height=300, title="Brecha (%) y banda esperada al 95% (AR(1))", margin=dict(l=10, r=10, t=40, b=10))
        chart(st, fg)
    st.markdown("#### H5 · ¿Qué mercado se mueve primero?")
    note("Correlación cruzada y prueba de Granger", "Comparamos variaciones diarias del precio P2P y del oficial en días hábiles. Las barras miden asociación a distintos rezagos; k positivo significa que el P2P aparece antes. La prueba de Granger pregunta si los retornos pasados de una serie mejoran la predicción de la otra, sin demostrar causalidad económica.")
    ll = gp.lead_lag(gap_df["paralelo"], gap_df["oficial"])
    if ll["ok"]:
        cc = ll["cc"]; fl = go.Figure(go.Bar(x=cc["k"], y=cc["corr"], marker_color=MOSS))
        fl.add_hline(y=cc.attrs["banda95"], line_dash="dash", line_color=GOLD); fl.add_hline(y=-cc.attrs["banda95"], line_dash="dash", line_color=GOLD)
        fl.update_layout(height=260, title="Correlación cruzada de retornos (k>0: el paralelo se adelanta al oficial)", margin=dict(l=10, r=10, t=40, b=10))
        chart(st, fl)
        fwd = ll.get("granger_par→of", {}).get(1)
        rev = ll.get("granger_of→par", {}).get(1)
        if fwd is not None and rev is not None:
            st.write("**Resultado H5.** Una correlación alta señala movimientos relacionados al rezago indicado. Un valor p pequeño en Granger indica capacidad predictiva adicional en esta muestra; puede reflejar horarios de publicación u otros factores comunes.")
            st.caption(f"H5: {ll['n']} retornos hábiles, k={ll['rezago_max']}, correlación={ll['corr_max']:.3f}; "
                       f"Granger lag 1 paralelo→oficial p={fwd:.3g}, oficial→paralelo p={rev:.3g}. "
                       "La hora de publicación puede explicar el adelanto; Granger no demuestra causalidad.")
    else:
        st.caption(ll["motivo"])
    st.markdown("#### H3 · ¿Cambió la volatilidad del P2P?")
    note("Desviación típica y prueba de Levene", "Volatilidad es cuánto varían los retornos diarios, no el nivel del dólar. Comparamos antes y después del 29 de junio de 2026 dentro de un tramo de mediana P2P con metodología comparable. Levene prueba si las dispersiones difieren; el resultado describe asociación temporal, no atribuye la causa al cambio oficial.")
    ret = gp.daily_returns(gap_df["paralelo"])
    ret = ret[(ret.index >= "2026-05-04") & (ret.index <= "2026-09-03")]
    vol = gp.volatility_by_regime(ret, str(data.FECHA_FLEXIBLE.date()))
    if vol["ok"]:
        st.write("**Resultado H3.** La razón compara la dispersión después frente a antes; mayor que 1 significa más variabilidad. El valor p de Levene evalúa si la diferencia es compatible con varianzas iguales.")
        st.caption(f"H3, mediana P2P con método comparable (4-may a 3-sep-2026): "
                   f"σ diaria antes {vol['sd_antes']:.2%} (n={vol['n_antes']}), "
                   f"después {vol['sd_despues']:.2%} (n={vol['n_despues']}), "
                   f"razón {vol['razon']:.2f}; Levene p={vol['levene_p']:.3g}.")


def page_reservas(m):
    st.header("Reservas y depósitos")
    note("Qué se observa aquí", "Las reservas internacionales brutas (RIB) son activos externos del BCB. Los depósitos son saldos que el público mantiene en el sistema financiero; los depósitos en moneda extranjera están denominados en divisas. La base monetaria mide dinero emitido y reservas bancarias, y el IPC resume precios de consumo.")
    opts = {"rib": "Reservas internacionales brutas", "depositos_me": "Depósitos en moneda extranjera",
            "base_monetaria": "Base monetaria", "ipc": "IPC"}
    c1, c2 = st.columns([2, 1])
    col = c1.selectbox("Variable", list(opts), format_func=lambda k: opts[k])
    steps = c2.slider("Horizonte (meses)", 3, 18, 12)
    selected = next(item for item in VARIABLES if item[0] == col)
    note(f"{opts[col]} · modelo SARIMA", f"{selected[4]} El gráfico toma el historial mensual del Excel del BCB y ajusta un SARIMA a logaritmos desde 2005. Este modelo usa patrones propios de meses anteriores, diferencias para estabilizar la serie y, si ayuda, una parte estacional de 12 meses. La línea futura es una estimación y la franja muestra un intervalo del 95 % bajo el modelo.")
    r = get_sarima(col, steps)
    y, f = np.exp(r["y"]), r["forecast"]
    fig = go.Figure(); h = y.iloc[-96:]
    line(fig, h.index, h, "Observado", line=dict(color=PINE))
    fig.add_trace(go.Scatter(x=list(f.index) + list(f.index[::-1]), y=list(f["sup"]) + list(f["inf"][::-1]),
                             fill="toself", fillcolor="rgba(70,108,80,.2)", line=dict(width=0), name="IC 95%"))
    line(fig, f.index, f["media"], "Pronóstico SARIMA", line=dict(color=GOLD))
    fig.update_layout(height=380, title=f"{data.NOMBRES[col]} — SARIMA{r['order']}x{r['sorder']}", margin=dict(l=10, r=10, t=40, b=10))
    chart(st, fig)
    dg = r["diag"]
    st.write("**Diagnóstico del modelo.** Ljung–Box revisa si aún quedan patrones temporales en los errores; Jarque–Bera examina su forma. Un valor p bajo advierte que los supuestos del pronóstico o de sus intervalos pueden fallar.")
    st.caption(f"Diagnóstico: Ljung-Box p(12)={dg['ljung_box_p_12']:.3f}, p(24)={dg['ljung_box_p_24']:.3f}; Jarque-Bera p={dg['jarque_bera_p']:.3g}. "
               + ("Residuos sin autocorrelación." if dg["residuos_blancos_5%"] else "⚠️ Hay autocorrelación residual: tome los intervalos con cautela."))
    res = get_results()
    if res and col in res["sarima"] and "validacion" in res["sarima"][col]:
        with st.expander("Validación con ventana móvil (últimos 24 orígenes)"):
            st.write("Se simula una decisión tomada en distintos meses del pasado: se pronostica sin mirar meses posteriores y se compara con lo que ocurrió. **MAPE** es error porcentual medio (menor es mejor); **cobertura IC95** es la parte de observaciones que cayó dentro del intervalo del 95 %. Se contrasta con un pronóstico ingenuo y Holt–Winters.")
            v = pd.DataFrame(res["sarima"][col]["validacion"])
            piv = v.pivot_table(index="h", columns="modelo", values="MAPE_%").round(2)
            piv["cobertura IC95 SARIMA"] = v[v.modelo == "sarima"].set_index("h")["cobertura_IC95"].round(2)
            st.dataframe(piv, width="stretch")
            st.caption("MAPE en %. Si el ingenuo (último valor) gana, el modelo no aporta en ese horizonte.")

    if col == "rib":
        st.subheader("Probabilidad de que las reservas crucen un umbral (Monte Carlo, GBM)")
        note("Modelo de escenarios: Monte Carlo", "El movimiento browniano geométrico (GBM) genera miles de trayectorias posibles a partir de la variación histórica reciente de RIB. Se elige un nivel de reservas y un horizonte; el resultado es la fracción de trayectorias que termina debajo o cruza ese nivel. Supone una volatilidad estable y no incorpora decisiones de política futuras.")
        s0 = float(m["rib"].iloc[-1])
        c1, c2, c3 = st.columns(3)
        th = c1.slider("Umbral (MM USD)", 1500, 5000, 3500, 100)
        hz = c2.slider("Horizonte (meses)", 1, 12, 6)
        sm = c3.slider("Multiplicador de volatilidad", 0.5, 2.0, 1.0, 0.1)
        rs = sim.reserves_simulation(m["rib"], hz, float(th), sigma_mult=sm)
        st.write("**Cómo leer las probabilidades.** La primera mira solo el último mes simulado; la segunda cuenta cualquier cruce durante el trayecto. La segunda puede ser mayor porque incluye cruces temporales.")
        k = st.columns(3)
        k[0].metric("Nivel actual", f"{s0:,.0f}"); k[1].metric("P(terminar bajo el umbral)", f"{rs['p_terminal']:.1%}")
        k[2].metric("P(cruzarlo algún mes)", f"{rs['p_cruce']:.1%}")
        fan = rs["fan"]; x = list(range(len(fan))); fm = go.Figure()
        fm.add_trace(go.Scatter(x=x + x[::-1], y=list(fan.p95) + list(fan.p5[::-1]), fill="toself", fillcolor="rgba(70,108,80,.15)", line=dict(width=0), name="5–95%"))
        fm.add_trace(go.Scatter(x=x + x[::-1], y=list(fan.p75) + list(fan.p25[::-1]), fill="toself", fillcolor="rgba(70,108,80,.3)", line=dict(width=0), name="25–75%"))
        line(fm, x, fan.p50, "Mediana", line=dict(color=PINE)); fm.add_hline(y=th, line_dash="dash", line_color=GOLD)
        fm.update_layout(height=320, xaxis_title="meses", margin=dict(l=10, r=10, t=30, b=10))
        note("Qué muestra el abanico", "La línea central es la mediana simulada. Las franjas muestran rangos centrales del 50 % y del 90 % de las trayectorias; la línea punteada es el umbral que elegiste.")
        chart(st, fm)
        st.caption(f"GBM con μ={rs['params']['mu']:.2%} y σ={rs['params']['sigma']:.2%} mensuales (últimos {rs['params']['n']} meses). "
                   "Supone retornos independientes y volatilidad constante: es un escenario, no una predicción.")
    if col == "depositos_me":
        with st.expander("⚠️ Efecto de valoración en la bolivianización"):
            st.write("**Bolivianización** es la proporción de depósitos en bolivianos. El gráfico compara el cociente calculado con un tipo de cambio que cambia y con uno fijo de Bs 6,96. Si divergen, parte del movimiento viene de cómo se convierten saldos, no de una decisión nueva de depositar en dólares.")
            t = m["2022":]; fb = go.Figure()
            line(fb, t.index, data.bolivianizacion_tc_vigente(m)["2022":], "A tipo de cambio vigente")
            line(fb, t.index, data.bolivianizacion_tc_fijo(m)["2022":], "A tipo de cambio constante (6,96)")
            fb.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10)); chart(st, fb)
            st.caption("El BCB convierte los depósitos en bolivianos a USD con el tipo de cambio vigente: al subir de 6,96 a ~12, "
                       "la bolivianización medida al tipo vigente cae por **valoración**, aunque los depósitos en dólares no aumentaron. "
                       "(La cifra oficial del BCB usa otra definición y no se mezcla aquí.)")
    st.info(DISCLAIMER)


def page_inflacion(m):
    st.header("Inflación")
    note("IPC e inflación", "El Índice de Precios al Consumidor (IPC) compara el costo de una canasta con el año base 2016=100. La inflación a 12 meses es el porcentaje que cambió ese índice frente al mismo mes del año anterior. Por eso un IPC que sigue subiendo puede coexistir con una inflación que baja: los precios aumentan, pero más despacio.")
    st.write("**Lectura de los primeros gráficos.** A la izquierda está el nivel del IPC; a la derecha su variación interanual. Ambos proceden de las series mensuales del Excel del BCB.")
    s = m["ipc"][m.index >= "2005"]
    c1, c2 = st.columns(2)
    f1 = go.Figure(); line(f1, s.index, s, "IPC", line=dict(color=PINE)); f1.update_layout(height=260, title="IPC", margin=dict(l=10, r=10, t=40, b=10))
    chart(c1, f1)
    f2 = go.Figure(); i12 = m["inflacion_12m"]["2005":]; line(f2, i12.index, i12, "Inflación 12m %")
    f2.update_layout(height=260, title="Inflación a 12 meses (%)", margin=dict(l=10, r=10, t=40, b=10)); chart(c2, f2)
    st.markdown("#### Descomposición de la serie")
    note("Modelo de descomposición multiplicativa", "Separamos el IPC en tendencia de largo plazo, patrón que se repite cada año y variación no explicada. Sirve para ver si hay estacionalidad; no identifica por sí solo la causa económica de la inflación.")
    dec = fc.decompose(s, "multiplicative")
    fd = go.Figure()
    for i, (n, v) in enumerate((("Tendencia", dec.trend), ("Estacional", dec.seasonal), ("Residuo", dec.resid))):
        fd.add_trace(go.Scatter(x=v.index, y=v, name=n, yaxis="y" if i == 0 else f"y{i + 1}"))
    fd.update_layout(height=420, title="Descomposición multiplicativa del IPC",
                     yaxis=dict(domain=[0.68, 1]), yaxis2=dict(domain=[0.35, 0.62]), yaxis3=dict(domain=[0, 0.29]),
                     margin=dict(l=10, r=10, t=40, b=10))
    chart(st, fd)
    st.write("La **fuerza de estacionalidad** resume cuánto de la variación residual se explica por el patrón anual. Un valor cercano a cero sugiere que ese patrón ayuda poco.")
    st.caption(f"Fuerza de la estacionalidad: {fc.seasonal_strength(s):.2f} (≥0,64 sería fuerte). "
               "La inflación boliviana está dominada por la tendencia y los quiebres, no por un ciclo anual.")
    r = get_sarima("ipc", 12)
    f = r["forecast"]["media"]
    full = pd.concat([m["ipc"], f])
    yoy = (full / full.shift(12) - 1).loc[f.index] * 100
    st.subheader("Pronóstico del IPC y su inflación a 12 meses implícita")
    note("SARIMA frente a Holt–Winters", "SARIMA proyecta el IPC a partir de su dependencia temporal y de patrones de 12 meses. Calculamos la inflación implícita comparando cada IPC proyectado con el de un año antes. Holt–Winters es una alternativa de suavizamiento usada como referencia en la validación; aquí tuvo mejor error reciente para IPC.")
    st.dataframe(pd.DataFrame({"IPC pronosticado": f.round(2), "IC inf": r["forecast"]["inf"].round(2),
                               "IC sup": r["forecast"]["sup"].round(2), "Inflación 12m implícita %": yoy.round(1)}).head(12), width="stretch")
    st.caption("En la validación reciente, Holt-Winters pronosticó el IPC mejor que SARIMA y los intervalos fueron cortos (quiebre de régimen).")


def page_simulador(m, d, collector):
    st.header("Simulador de riesgo cambiario")
    st.error(DISCLAIMER)
    note("¿Para qué sirve?", "Permite imaginar cuánto podrían costar en bolivianos unos dólares comprados más adelante. El costo depende del monto, del tipo inicial, del plazo y de la variación diaria supuesta. Los números son escenarios matemáticos, no cotizaciones ni recomendaciones.")
    st.write("**Modelo GBM y Monte Carlo.** El movimiento browniano geométrico genera 20.000 posibles tipos de cambio futuros usando una deriva diaria y una volatilidad. El usuario puede tomar la volatilidad del oficial BCB, de su recolector P2P si tiene suficientes días, o fijarla manualmente.")
    c1, c2 = st.columns(2)
    usd = c1.number_input("Monto en dólares (USD)", 100.0, 10_000_000.0, 10_000.0, 500.0)
    days = c2.slider("Plazo (días)", 7, 365, 90)
    fuente = st.radio("Fuente de la volatilidad", ["Oficial BCB desde ago-2026", "P2P propio (recolector)", "Manual"], horizontal=True)
    s0, mu, sig, nota = None, 0.0, None, ""
    if fuente.startswith("Oficial"):
        p = sim.fx_params(data.official_points(m, d))
        if p.get("ok"):
            s0, sig, nota = p["s0"], p["sigma_diario"], f"σ estimada con {p['n']} variaciones diarias del TCO (excluye el salto jun→jul-2026)."
    elif fuente.startswith("P2P"):
        if len(collector) >= gp.MIN_OBS:
            p = sim.fx_params(collector["p2p_venta"].dropna())
            if p.get("ok"):
                s0, sig, nota = p["s0"], p["sigma_diario"], f"σ estimada con {p['n']} días del recolector."
        else:
            st.warning("Aún no hay ≥30 días de datos P2P propios; use otra fuente.")
    if s0 is None:
        s0 = float(data.official_points(m, d).iloc[-1]) if len(data.official_points(m, d)) else 12.0
        sig = st.slider("σ diaria (%)", 0.05, 3.0, 0.5, 0.05) / 100
    c1, c2 = st.columns(2)
    s0 = c1.number_input("Tipo de cambio inicial (Bs/USD)", 5.0, 30.0, float(round(s0, 2)), 0.01)
    mu = c2.slider("Deriva diaria supuesta (%)", -0.20, 0.20, 0.0, 0.01) / 100
    if nota:
        st.caption(nota + " **Rango indicativo; sensible a cambios de régimen.**")
    out = sim.fx_cost_simulation(usd, days, s0, mu, sig)
    st.write("**Cómo leer el resultado.** 'Costo hoy' usa el tipo inicial. La mediana divide los escenarios futuros en dos mitades; el percentil 95 es un costo que solo el 5 % de trayectorias simuladas supera bajo estos supuestos. La diferencia frente a hoy es un riesgo indicativo.")
    k = st.columns(4)
    k[0].metric("Costo hoy (Bs)", f"{out['hoy']:,.0f}")
    k[1].metric("Percentil 5", f"{out['p5']:,.0f}"); k[2].metric("Mediana", f"{out['p50']:,.0f}")
    k[3].metric("Percentil 95", f"{out['p95']:,.0f}", f"{out['var95_extra']:+,.0f} vs hoy", delta_color="inverse")
    note("Distribución de costos", "Cada barra agrupa simulaciones con costos parecidos al final del plazo. Las líneas punteadas ubican el costo actual y los percentiles 5, 50 y 95. El ancho refleja el supuesto de volatilidad que elegiste.")
    fh = go.Figure(go.Histogram(x=out["sims"], nbinsx=60, marker_color=MOSS))
    for v, n in ((out["p5"], "P5"), (out["p50"], "P50"), (out["p95"], "P95"), (out["hoy"], "Hoy")):
        fh.add_vline(x=v, line_dash="dash", annotation_text=n)
    fh.update_layout(height=320, title=f"Costo en Bs de USD {usd:,.0f} dentro de {days} días (20.000 simulaciones)", margin=dict(l=10, r=10, t=40, b=10))
    chart(st, fh)


def page_alertas(m):
    st.header("Alertas")
    note("Cómo se generan", "El tablero busca tres señales: datos mensuales atrasados, cambios de estado del índice y observaciones muy distintas de las esperadas por los modelos SARIMA. Son avisos para revisar la serie y su fuente, no diagnósticos automáticos de un problema económico.")
    rows = []
    ult = m.index.max()
    lag = (pd.Timestamp.today().normalize() - ult).days
    if lag > 75:
        rows.append({"tipo": "Datos", "detalle": f"Último mes disponible: {ult:%b %Y} (hace {lag} días). Revisa la descarga del BCB."})
    ci = mk.stress_index(m); s = mk.classify(ci["indice"])
    if len(s) > 1 and s.iloc[-1] != s.iloc[-2]:
        rows.append({"tipo": "Estado", "detalle": f"Cambio de estado: {mk.ESTADOS[int(s.iloc[-2])]} → {mk.ESTADOS[int(s.iloc[-1])]} en {s.index[-1]:%b %Y}."})
    for col in ("rib", "depositos_me", "base_monetaria", "ipc"):
        a = get_sarima(col, 6)["anom"]
        rec = a[a.anomalia & (a.index >= a.index.max() - pd.DateOffset(months=24))]
        for dt_, z in rec["residuo_z"].items():
            rows.append({"tipo": "Anomalía", "detalle": f"{data.NOMBRES.get(col, col)}: residuo z={z:+.1f} en {dt_:%b %Y}"})
    if rows:
        st.write("**Qué significa cada fila.** 'Datos' pide revisar actualización; 'Estado' indica que el índice cruzó un umbral; 'Anomalía' es un error del SARIMA mayor a 2,5 desviaciones típicas en valor absoluto. Una anomalía puede deberse a un cambio real, a una revisión o a limitaciones del modelo.")
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        st.success("Sin alertas en la última actualización.")
    st.caption("Anomalía = residuo estandarizado del SARIMA con |z| > 2,5 en los últimos 24 meses (se descartan los primeros 24 meses del ajuste).")


def page_variables(m):
    st.header("Variables y fuentes")
    note("De dónde salen los números", "El Excel de Estadísticas Semanales del Banco Central de Bolivia contiene la historia mensual completa y observaciones semanales o diarias recientes. El proyecto extrae 18 variables mensuales seleccionadas; cada una conserva la fila del Excel, su fecha y su archivo de origen. Las series P2P y el TCO diario llegan por archivos externos separados.")
    a, b, c = st.columns(3)
    a.markdown('<div class="source-card"><div class="mini-label">Fuente principal</div><strong>BCB · Excel semanal</strong><br>Dinero, depósitos, reservas, precios y tipos de cambio. <a href="https://www.bcb.gob.bo/?q=estad-sticas-semanales">Ver listado oficial</a>.</div>', unsafe_allow_html=True)
    b.markdown('<div class="source-card"><div class="mini-label">Precio P2P</div><strong>paralelo.bo</strong><br>Mediana histórica de anuncios P2P, licencia CC BY 4.0. Precio anunciado, no operación ejecutada. <a href="https://paralelo.bo/metodologia">Ver metodología</a>.</div>', unsafe_allow_html=True)
    c.markdown('<div class="source-card"><div class="mini-label">Oficial diario</div><strong>BCB · TCO</strong><br>CSV diario usado desde el 29 de junio de 2026. <a href="https://www.bcb.gob.bo/grafico_evolutivo/download.php?serie=tipo_de_cambio&amp;format=csv">Ver archivo BCB</a>.</div>', unsafe_allow_html=True)
    st.caption("También se conservan el PDF de activos virtuales del BCB y capturas de DolarApi/Binance. Esas cotizaciones no se mezclan con la mediana histórica P2P en H1, H3 o H5.")

    tab1, tab2, tab3 = st.tabs(["18 variables del Excel", "Series calculadas", "Guía de modelos"])
    with tab1:
        st.write("**Cómo leer el catálogo.** 'Fila BCB' identifica la posición en el formato de Excel validado; si cambia, `check-layout` avisa. 'Meses con dato' cuenta observaciones presentes y no garantiza que la definición económica sea comparable en todo el período.")
        rows = [{"Variable": key, "Grupo": group, "Unidad": unit, "En palabras simples": meaning,
                 "Uso en este proyecto": use, "Fila BCB": row, "Meses con dato": int(m[key].notna().sum())}
                for key, row, group, unit, meaning, use in VARIABLES]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, height=570)
        key = st.selectbox("Explicación de una variable", [v[0] for v in VARIABLES],
                           format_func=lambda name: data.NOMBRES.get(name, name.replace("_", " ").capitalize()))
        selected = next(v for v in VARIABLES if v[0] == key)
        note(selected[0].replace("_", " ").capitalize(),
             f"{selected[4]} <br><strong>Unidad:</strong> {selected[3]}. <strong>Fuente:</strong> Excel semanal del BCB, fila {selected[1]}. <strong>Uso:</strong> {selected[5]}")
        st.warning("La fila 95 publica una bolivianización con definición propia del BCB. No se combina con los saldos de las filas 92 y 94 para construir el índice de estrés.")
    with tab2:
        st.write("Estas variables se construyen a partir de las fuentes originales. No son nuevas publicaciones del BCB.")
        derivadas = [
            ("Brecha cambiaria (%)", "100 × (precio P2P / referencia oficial − 1)", "Diferencia relativa entre anuncios P2P y referencia BCB.", "Brecha, AR(1), H1."),
            ("Retorno diario P2P", "Cambio del logaritmo del precio entre días consecutivos", "Movimiento relativo de un día a otro; se evitan huecos largos.", "Volatilidad H3."),
            ("Bolivianización neutral", "Cambio en 6 meses valorando ambos saldos al mismo tipo de cambio", "Quita el efecto contable de convertir bolivianos a USD con un precio distinto.", "Índice de estrés."),
            ("Índice de estrés", "Promedio de dos señales estandarizadas", "Suma presión de reservas y bolivianización neutral, en una escala común.", "Estados y Markov."),
            ("Estado", "Percentiles del índice", "Clasifica cada mes como estable, tensión o crisis relativa.", "Semáforo y matriz."),
            ("Inflación 12m implícita", "IPC previsto / IPC de hace 12 meses − 1", "Variación anual que resultaría del IPC pronosticado.", "Pantalla Inflación."),
        ]
        st.dataframe(pd.DataFrame(derivadas, columns=["Variable", "Cómo se obtiene", "En palabras simples", "Dónde aparece"]),
                     width="stretch", hide_index=True)
        st.info("Los archivos procesados se regeneran desde el Excel. `data/raw/` conserva los originales; `data/processed/` guarda tablas listas para análisis.")
    with tab3:
        st.write("Cada modelo contesta una pregunta concreta. Sus cifras están junto a los gráficos de la pantalla indicada y cambian cuando se actualizan los datos o los controles.")
        models = [
            ("Markov", "¿Con qué frecuencia cambia el estado?", "Cuenta transiciones entre meses y forma una matriz de probabilidades.", "Probabilidad a 1/3/6 meses, permanencia y contraste de orden.", "Semáforo"),
            ("AR(1)", "¿Persiste la brecha P2P?", "Compara la brecha de hoy con la de ayer.", "φ, vida media, media de largo plazo y banda.", "Brecha"),
            ("Levene", "¿Cambió la volatilidad P2P?", "Contrasta la dispersión de retornos antes y después.", "Volatilidades, razón y valor p de H3.", "Brecha"),
            ("Correlación cruzada / Granger", "¿Qué serie se adelanta?", "Compara retornos con rezagos y prueba capacidad predictiva adicional.", "Rezago, correlación y valores p de H5.", "Brecha"),
            ("Descomposición / Holt–Winters", "¿Hay patrón anual y mejora el pronóstico?", "Separa tendencia, estación y residuo; suaviza nivel y estación.", "Fuerza estacional y comparación de errores.", "Inflación"),
            ("SARIMA", "¿Qué nivel podría venir?", "Ajusta dependencia temporal y posible estacionalidad mensual.", "Pronóstico, intervalo, diagnósticos y MAPE.", "Reservas e Inflación"),
            ("Monte Carlo / GBM", "¿Qué rango de escenarios es compatible con los supuestos?", "Simula miles de trayectorias con deriva y volatilidad.", "Percentiles y probabilidades de cruzar un umbral.", "Reservas y Simulador"),
        ]
        st.dataframe(pd.DataFrame(models, columns=["Modelo", "Para qué sirve", "Cómo funciona", "Qué resultado muestra", "Pantalla"]),
                     width="stretch", hide_index=True)
        st.caption("Un valor p pequeño no demuestra causa económica. Los pronósticos y escenarios dependen de la muestra y de los supuestos del modelo.")
    st.info(DISCLAIMER)


def page_metodologia():
    st.header("Metodología")
    note("Cómo se organiza la investigación", "Primero se obtienen y verifican los Excel del BCB; luego se construyen series mensuales y diarias, se revisan sus propiedades y se ajustan modelos. Las hipótesis H1, H3 y H5 usan P2P observado; los datos DEMO no entran en los resultados académicos.")
    st.markdown("""
| Capítulo | Qué se usa aquí |
|---|---|
| 1-2 Procesos estocásticos | Series como procesos en tiempo discreto; momentos muestrales; prueba ADF |
| 3 Cadenas de Markov | Índice de estrés → 3 estados; matriz de transición; π; permanencia; pruebas de Markov |
| 4 Descomposición y suavizamiento | Descomposición del IPC; Holt-Winters como referencia |
| 5 AR/MA/ARMA, espectral | AR(1) de la brecha (vida media); periodograma de Δlog RIB |
| 6 ARIMA/SARIMA | Box-Jenkins: identificación, estimación, diagnóstico, pronóstico, validación móvil |
| 7 Aplicaciones | GBM y Monte Carlo; detección de anomalías |

**Datos:** BCB Estadísticas Semanales (Excel), [TCO diario BCB](https://www.bcb.gob.bo/grafico_evolutivo/download.php?serie=tipo_de_cambio&format=csv), [mediana P2P histórica de paralelo.bo](https://paralelo.bo/api/v1/historical.csv) (CC BY 4.0), PDF de activos virtuales del BCB y DolarApi (recolector propio). La mediana P2P no equivale a Binance ni al PDF.
**Hallazgo clave:** la caída de la bolivianización medida al tipo de cambio vigente en 2026 es un efecto de valoración, no una fuga hacia el dólar.
**Informe completo:** `reports/INFORME.md` y `reports/INFORME_ACADEMICO.docx`.
""")
    st.write("**Límites para interpretar resultados.** Los estados son relativos a la muestra; Markov de primer orden es una aproximación. SARIMA puede fallar ante cambios de régimen; sus intervalos no siempre tuvieron cobertura nominal. Granger mide utilidad predictiva de rezagos, no causa. El simulador asume una volatilidad estable.")
    st.warning("Limitaciones: pocas observaciones del régimen flexible; índice descriptivo (cuantiles); datos recientes preliminares; modelos gaussianos.")
    st.info(DISCLAIMER)


# ---------------------------------------------------------------- main
def main():
    m, d, col, pdf = get_data()
    apply_theme()
    masthead()
    st.sidebar.title("BOLIVIA · OBSERVATORIO")
    st.sidebar.caption("Monitor de estrés cambiario y monetario")
    page = st.sidebar.radio("Pantalla", PAGES, key="page")
    use_demo = st.sidebar.toggle("Datos DEMO simulados de la brecha", value=False,
                                 help="Solo para ver la pantalla mientras no haya historial P2P real.")
    gap_df, is_demo = get_gap(use_demo)
    gap_real = gap_df if not is_demo else pd.DataFrame()
    stt = data.data_status(m)
    st.sidebar.caption(f"Datos BCB hasta **{stt['ultimo_mes']:%b %Y}** · {stt['n_meses']} meses")
    st.sidebar.caption(f"Días con paralelo real: **{len(gap_real)}**")
    {"Semáforo del sistema": lambda: page_semaforo(m, gap_real),
     "Brecha cambiaria": lambda: page_brecha(m, d, gap_df, is_demo),
     "Reservas y depósitos": lambda: page_reservas(m),
     "Inflación": lambda: page_inflacion(m),
     "Simulador de riesgo": lambda: page_simulador(m, d, col),
     "Alertas": lambda: page_alertas(m),
     "Variables y fuentes": lambda: page_variables(m),
     "Metodología": page_metodologia}[page]()


main()
