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

st.set_page_config(page_title="Monitor de estrés — Bolivia", page_icon="📈", layout="wide")
COLORS = {0: "#2e7d32", 1: "#f9a825", 2: "#c62828"}
DISCLAIMER = ("⚠️ **Aviso:** esta herramienta es académica. Informa con probabilidades y escenarios; "
              "**no es asesoría financiera ni una predicción**.")
PAGES = ["Semáforo del sistema", "Brecha cambiaria", "Reservas y depósitos", "Inflación",
         "Simulador de riesgo", "Alertas", "Metodología"]


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
    with st.expander("Umbrales de los estados (decisión del analista)"):
        c1, c2 = st.columns(2)
        q1 = c1.slider("Percentil de inicio de **Tensión**", 0.40, 0.80, 0.60, 0.01)
        q2 = c2.slider("Percentil de inicio de **Crisis**", 0.80, 0.97, 0.85, 0.01)
    ci = mk.stress_index(m)
    states = mk.classify(ci["indice"], (q1, q2))
    fit = mk.fit_markov(states)
    cur = int(states.iloc[-1])
    t1, t2 = states.attrs["umbrales"]

    a, b, c = st.columns([1.2, 1, 1.6])
    a.markdown(f"<div style='background:{COLORS[cur]};color:white;padding:18px;border-radius:12px;text-align:center'>"
               f"<div style='font-size:14px'>Estado a {states.index[-1]:%b %Y}</div>"
               f"<div style='font-size:34px;font-weight:700'>{mk.ESTADOS[cur]}</div></div>", unsafe_allow_html=True)
    b.metric("Índice de estrés", f"{ci['indice'].iloc[-1]:.2f}", f"umbral tensión {t1:.2f} · crisis {t2:.2f}", delta_color="off")
    comp = ci.drop(columns="indice").iloc[-1]
    c.markdown("**Qué lo explica** (puntos z; + = más estrés)")
    c.dataframe(comp.rename("z").round(2).to_frame(), width="stretch")
    st.caption("Los estados son **relativos a la historia 1989-hoy** (percentiles del índice): «Crisis» significa que el índice "
               "está en el tramo más alto de su historia, no es un diagnóstico de crisis. "
               "La brecha se analiza por separado para conservar los mismos componentes en toda la serie.")

    fig = go.Figure(); shade_states(fig, states)
    line(fig, ci.index, ci["indice"], "Índice", line=dict(color="black", width=1.2))
    fig.update_layout(height=330, margin=dict(l=10, r=10, t=30, b=10), title="Índice de estrés y estados (verde/ámbar/rojo)")
    st.plotly_chart(fig, width="stretch")

    c1, c2 = st.columns(2)
    probs = mk.forecast_state_probs(fit.P, cur, (1, 3, 6))
    fb = go.Figure()
    for i, name in enumerate(mk.ESTADOS):
        fb.add_bar(x=[f"{h} mes(es)" for h in probs], y=[probs[h][i] for h in probs], name=name, marker_color=COLORS[i])
    fb.update_layout(barmode="stack", height=320, title="Probabilidad de estar en cada estado", yaxis_tickformat=".0%",
                     margin=dict(l=10, r=10, t=40, b=10))
    c1.plotly_chart(fb, width="stretch")
    hm = go.Figure(go.Heatmap(z=fit.P, x=mk.ESTADOS, y=mk.ESTADOS, colorscale="Blues", zmin=0, zmax=1,
                              text=np.round(fit.P, 2), texttemplate="%{text}"))
    hm.update_layout(height=320, title="Matriz de transición mensual P (fila = desde)", yaxis_autorange="reversed",
                     margin=dict(l=10, r=10, t=40, b=10))
    c2.plotly_chart(hm, width="stretch")

    tbl = pd.DataFrame({"Estado": mk.ESTADOS, "Largo plazo π": fit.stationary,
                        "Permanencia media (meses)": fit.sojourn})
    st.dataframe(tbl.style.format({"Largo plazo π": "{:.1%}", "Permanencia media (meses)": "{:.1f}"}), width="stretch", hide_index=True)
    ind, o2 = mk.test_independence(fit.counts), mk.test_second_order(states)
    st.caption(f"Propiedad de Markov: independencia χ² p={ind['p_valor']:.2g}; orden 1 vs 2 (LR) p={o2['p_valor']:.2g}. "
               "Con p<0,05 en el segundo contraste la cadena de primer orden es una aproximación.")
    st.markdown("**Validación con episodios conocidos**")
    st.dataframe(mk.episode_table(states).style.format({k: "{:.0%}" for k in mk.ESTADOS}), width="stretch", hide_index=True)
    st.markdown("**Robustez a los umbrales**")
    st.dataframe(mk.robustness(ci["indice"]).round(2), width="stretch", hide_index=True)
    st.info(DISCLAIMER)


def page_brecha(m, d, gap_df, is_demo):
    st.header("Brecha cambiaria")
    t = m[["tc_fijo_bolsin", "tc_referencial_venta", "tc_oficial"]]["2022":]
    fig = go.Figure()
    for c, n in zip(t.columns, ["Fijo (Bolsín)", "Referencial (venta)", "Oficial flexible"]):
        fig.add_trace(go.Scatter(x=t.index, y=t[c], name=n, mode="lines+markers"))
    fig.update_layout(height=300, title="Tres regímenes del tipo de cambio (datos oficiales del BCB, Bs/USD)",
                      margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, width="stretch")
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
    fig = go.Figure()
    line(fig, gap_df.index, gap_df["oficial"], "Oficial (referencia)"); line(fig, gap_df.index, gap_df["paralelo"], "Paralelo (USDT)")
    fig.update_layout(height=300, title="Oficial vs. paralelo (Bs/USD)", margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, width="stretch")

    scope = st.radio("Muestra para el AR(1)", ["Régimen flexible (desde 29-jun-2026)", "Toda la serie"], horizontal=True)
    g = gap_df["brecha_pct"]
    if scope.startswith("Régimen"):
        g = g[g.index >= data.FECHA_FLEXIBLE]
    r = gp.ar1_gap(g)
    if not r["ok"]:
        st.info(r["motivo"])
    else:
        c = st.columns(4)
        c[0].metric("φ (persistencia diaria)", f"{r['phi']:.3f}", f"± {1.96 * r['se_phi']:.3f}", delta_color="off")
        c[1].metric("Vida media de la brecha", f"{r['vida_media']:.1f} días" if np.isfinite(r["vida_media"]) else "∞")
        c[2].metric("Brecha media de largo plazo", f"{r['media_larga']:.2f}%")
        c[3].metric("ADF (p)", f"{r['adf']['p_valor']:.3f}", "estacionaria" if r["adf"]["estacionaria_5%"] else "no estacionaria", delta_color="off")
        fg = go.Figure(); lo, hi = r["banda95"]
        fg.add_hrect(y0=lo, y1=hi, fillcolor="#1976d2", opacity=0.12, line_width=0)
        line(fg, g.index, g, "Brecha %", line=dict(color="#1976d2"))
        fg.update_layout(height=300, title="Brecha (%) y banda esperada al 95% (AR(1))", margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fg, width="stretch")
    ll = gp.lead_lag(gap_df["paralelo"], gap_df["oficial"])
    if ll["ok"]:
        cc = ll["cc"]; fl = go.Figure(go.Bar(x=cc["k"], y=cc["corr"]))
        fl.add_hline(y=cc.attrs["banda95"], line_dash="dash", line_color="red"); fl.add_hline(y=-cc.attrs["banda95"], line_dash="dash", line_color="red")
        fl.update_layout(height=260, title="Correlación cruzada de retornos (k>0: el paralelo se adelanta al oficial)", margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fl, width="stretch")
        fwd = ll.get("granger_par→of", {}).get(1)
        rev = ll.get("granger_of→par", {}).get(1)
        if fwd is not None and rev is not None:
            st.caption(f"H5: {ll['n']} retornos hábiles, k={ll['rezago_max']}, correlación={ll['corr_max']:.3f}; "
                       f"Granger lag 1 paralelo→oficial p={fwd:.3g}, oficial→paralelo p={rev:.3g}. "
                       "La hora de publicación puede explicar el adelanto; Granger no demuestra causalidad.")
    else:
        st.caption(ll["motivo"])
    ret = gp.daily_returns(gap_df["paralelo"])
    ret = ret[(ret.index >= "2026-05-04") & (ret.index <= "2026-09-03")]
    vol = gp.volatility_by_regime(ret, str(data.FECHA_FLEXIBLE.date()))
    if vol["ok"]:
        st.caption(f"H3, mediana P2P con método comparable (4-may a 3-sep-2026): "
                   f"σ diaria antes {vol['sd_antes']:.2%} (n={vol['n_antes']}), "
                   f"después {vol['sd_despues']:.2%} (n={vol['n_despues']}), "
                   f"razón {vol['razon']:.2f}; Levene p={vol['levene_p']:.3g}.")


def page_reservas(m):
    st.header("Reservas y depósitos")
    opts = {"rib": "Reservas internacionales brutas", "depositos_me": "Depósitos en moneda extranjera",
            "base_monetaria": "Base monetaria", "ipc": "IPC"}
    c1, c2 = st.columns([2, 1])
    col = c1.selectbox("Variable", list(opts), format_func=lambda k: opts[k])
    steps = c2.slider("Horizonte (meses)", 3, 18, 12)
    r = get_sarima(col, steps)
    y, f = np.exp(r["y"]), r["forecast"]
    fig = go.Figure(); h = y.iloc[-96:]
    line(fig, h.index, h, "Observado", line=dict(color="black"))
    fig.add_trace(go.Scatter(x=list(f.index) + list(f.index[::-1]), y=list(f["sup"]) + list(f["inf"][::-1]),
                             fill="toself", fillcolor="rgba(25,118,210,.2)", line=dict(width=0), name="IC 95%"))
    line(fig, f.index, f["media"], "Pronóstico SARIMA", line=dict(color="#1976d2"))
    fig.update_layout(height=380, title=f"{data.NOMBRES[col]} — SARIMA{r['order']}x{r['sorder']}", margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, width="stretch")
    dg = r["diag"]
    st.caption(f"Diagnóstico: Ljung-Box p(12)={dg['ljung_box_p_12']:.3f}, p(24)={dg['ljung_box_p_24']:.3f}; Jarque-Bera p={dg['jarque_bera_p']:.3g}. "
               + ("Residuos sin autocorrelación." if dg["residuos_blancos_5%"] else "⚠️ Hay autocorrelación residual: tome los intervalos con cautela."))
    res = get_results()
    if res and col in res["sarima"] and "validacion" in res["sarima"][col]:
        with st.expander("Validación con ventana móvil (últimos 24 orígenes)"):
            v = pd.DataFrame(res["sarima"][col]["validacion"])
            piv = v.pivot_table(index="h", columns="modelo", values="MAPE_%").round(2)
            piv["cobertura IC95 SARIMA"] = v[v.modelo == "sarima"].set_index("h")["cobertura_IC95"].round(2)
            st.dataframe(piv, width="stretch")
            st.caption("MAPE en %. Si el ingenuo (último valor) gana, el modelo no aporta en ese horizonte.")

    if col == "rib":
        st.subheader("Probabilidad de que las reservas crucen un umbral (Monte Carlo, GBM)")
        s0 = float(m["rib"].iloc[-1])
        c1, c2, c3 = st.columns(3)
        th = c1.slider("Umbral (MM USD)", 1500, 5000, 3500, 100)
        hz = c2.slider("Horizonte (meses)", 1, 12, 6)
        sm = c3.slider("Multiplicador de volatilidad", 0.5, 2.0, 1.0, 0.1)
        rs = sim.reserves_simulation(m["rib"], hz, float(th), sigma_mult=sm)
        k = st.columns(3)
        k[0].metric("Nivel actual", f"{s0:,.0f}"); k[1].metric("P(terminar bajo el umbral)", f"{rs['p_terminal']:.1%}")
        k[2].metric("P(cruzarlo algún mes)", f"{rs['p_cruce']:.1%}")
        fan = rs["fan"]; x = list(range(len(fan))); fm = go.Figure()
        fm.add_trace(go.Scatter(x=x + x[::-1], y=list(fan.p95) + list(fan.p5[::-1]), fill="toself", fillcolor="rgba(25,118,210,.15)", line=dict(width=0), name="5–95%"))
        fm.add_trace(go.Scatter(x=x + x[::-1], y=list(fan.p75) + list(fan.p25[::-1]), fill="toself", fillcolor="rgba(25,118,210,.3)", line=dict(width=0), name="25–75%"))
        line(fm, x, fan.p50, "Mediana"); fm.add_hline(y=th, line_dash="dash", line_color="red")
        fm.update_layout(height=320, xaxis_title="meses", margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fm, width="stretch")
        st.caption(f"GBM con μ={rs['params']['mu']:.2%} y σ={rs['params']['sigma']:.2%} mensuales (últimos {rs['params']['n']} meses). "
                   "Supone retornos independientes y volatilidad constante: es un escenario, no una predicción.")
    if col == "depositos_me":
        with st.expander("⚠️ Efecto de valoración en la bolivianización"):
            t = m["2022":]; fb = go.Figure()
            line(fb, t.index, data.bolivianizacion_tc_vigente(m)["2022":], "A tipo de cambio vigente")
            line(fb, t.index, data.bolivianizacion_tc_fijo(m)["2022":], "A tipo de cambio constante (6,96)")
            fb.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10)); st.plotly_chart(fb, width="stretch")
            st.caption("El BCB convierte los depósitos en bolivianos a USD con el tipo de cambio vigente: al subir de 6,96 a ~12, "
                       "la bolivianización medida al tipo vigente cae por **valoración**, aunque los depósitos en dólares no aumentaron. "
                       "(La cifra oficial del BCB usa otra definición y no se mezcla aquí.)")
    st.info(DISCLAIMER)


def page_inflacion(m):
    st.header("Inflación")
    s = m["ipc"][m.index >= "2005"]
    c1, c2 = st.columns(2)
    f1 = go.Figure(); line(f1, s.index, s, "IPC"); f1.update_layout(height=260, title="IPC", margin=dict(l=10, r=10, t=40, b=10))
    c1.plotly_chart(f1, width="stretch")
    f2 = go.Figure(); i12 = m["inflacion_12m"]["2005":]; line(f2, i12.index, i12, "Inflación 12m %")
    f2.update_layout(height=260, title="Inflación a 12 meses (%)", margin=dict(l=10, r=10, t=40, b=10)); c2.plotly_chart(f2, width="stretch")
    dec = fc.decompose(s, "multiplicative")
    fd = go.Figure()
    for i, (n, v) in enumerate((("Tendencia", dec.trend), ("Estacional", dec.seasonal), ("Residuo", dec.resid))):
        fd.add_trace(go.Scatter(x=v.index, y=v, name=n, yaxis="y" if i == 0 else f"y{i + 1}"))
    fd.update_layout(height=420, title="Descomposición multiplicativa del IPC",
                     yaxis=dict(domain=[0.68, 1]), yaxis2=dict(domain=[0.35, 0.62]), yaxis3=dict(domain=[0, 0.29]),
                     margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fd, width="stretch")
    st.caption(f"Fuerza de la estacionalidad: {fc.seasonal_strength(s):.2f} (≥0,64 sería fuerte). "
               "La inflación boliviana está dominada por la tendencia y los quiebres, no por un ciclo anual.")
    r = get_sarima("ipc", 12)
    f = r["forecast"]["media"]
    full = pd.concat([m["ipc"], f])
    yoy = (full / full.shift(12) - 1).loc[f.index] * 100
    st.subheader("Pronóstico del IPC y su inflación a 12 meses implícita")
    st.dataframe(pd.DataFrame({"IPC pronosticado": f.round(2), "IC inf": r["forecast"]["inf"].round(2),
                               "IC sup": r["forecast"]["sup"].round(2), "Inflación 12m implícita %": yoy.round(1)}).head(12), width="stretch")
    st.caption("En la validación reciente, Holt-Winters pronosticó el IPC mejor que SARIMA y los intervalos fueron cortos (quiebre de régimen).")


def page_simulador(m, d, collector):
    st.header("Simulador de riesgo cambiario")
    st.error(DISCLAIMER)
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
    k = st.columns(4)
    k[0].metric("Costo hoy (Bs)", f"{out['hoy']:,.0f}")
    k[1].metric("Percentil 5", f"{out['p5']:,.0f}"); k[2].metric("Mediana", f"{out['p50']:,.0f}")
    k[3].metric("Percentil 95", f"{out['p95']:,.0f}", f"{out['var95_extra']:+,.0f} vs hoy", delta_color="inverse")
    fh = go.Figure(go.Histogram(x=out["sims"], nbinsx=60, marker_color="#1976d2"))
    for v, n in ((out["p5"], "P5"), (out["p50"], "P50"), (out["p95"], "P95"), (out["hoy"], "Hoy")):
        fh.add_vline(x=v, line_dash="dash", annotation_text=n)
    fh.update_layout(height=320, title=f"Costo en Bs de USD {usd:,.0f} dentro de {days} días (20.000 simulaciones)", margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fh, width="stretch")


def page_alertas(m):
    st.header("Alertas")
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
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        st.success("Sin alertas en la última actualización.")
    st.caption("Anomalía = residuo estandarizado del SARIMA con |z| > 2,5 en los últimos 24 meses (se descartan los primeros 24 meses del ajuste).")


def page_metodologia():
    st.header("Metodología")
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
**Informe completo:** `reports/INFORME.md`.
""")
    st.warning("Limitaciones: pocas observaciones del régimen flexible; índice descriptivo (cuantiles); datos recientes preliminares; modelos gaussianos.")
    st.info(DISCLAIMER)


# ---------------------------------------------------------------- main
def main():
    m, d, col, pdf = get_data()
    st.sidebar.title("📈 Monitor de estrés")
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
     "Metodología": page_metodologia}[page]()


main()
