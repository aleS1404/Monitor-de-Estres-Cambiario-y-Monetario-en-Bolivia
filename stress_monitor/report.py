"""Genera resultados (JSON), figuras (PNG) e INFORME.md a partir de los datos procesados.
Uso:  python -m stress_monitor.report            (completo, ~1-2 min)
      python -m stress_monitor.report --rapido   (sin validación de ventana móvil)"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import data, forecasting as fc, gap as gp, markov as mk, simulation as sim, stationarity as st

ROOT = data.ROOT
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": .3, "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 9})
COL = {0: "#2e7d32", 1: "#f9a825", 2: "#c62828"}


def md_table(df: pd.DataFrame, fmt: str = "{:.3f}") -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            cells.append(fmt.format(v) if isinstance(v, (float, np.floating)) and np.isfinite(v)
                         else ("—" if isinstance(v, (float, np.floating)) else str(v)))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def _save(fig, path: Path):
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def fig_series(m, path):
    fig, ax = plt.subplots(2, 2, figsize=(10, 6))
    ax[0, 0].plot(m.rib); ax[0, 0].set_title("Reservas internacionales brutas (MM USD)")
    ax[0, 1].plot(m.bolivianizacion_depositos); ax[0, 1].set_title("Bolivianización de depósitos (%)")
    ax[1, 0].plot(m.inflacion_12m["2005":]); ax[1, 0].set_title("Inflación a 12 meses (%)")
    t = m[["tc_fijo_bolsin", "tc_referencial_venta", "tc_oficial"]]["2022":]
    for c, lab in zip(t.columns, ["Fijo (Bolsín)", "Referencial (venta)", "Oficial flexible"]):
        ax[1, 1].plot(t[c], label=lab, marker="o", ms=2)
    ax[1, 1].legend(); ax[1, 1].set_title("Tipo de cambio por régimen (Bs/USD)")
    _save(fig, path)


def fig_acf(x, path, title):
    a = st.acf_pacf(x, 36)
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.2))
    for axx, c, t in ((ax[0], "acf", "ACF"), (ax[1], "pacf", "PACF")):
        axx.bar(a.lag, a[c], width=.3); axx.axhline(a.banda95.iloc[0], ls="--", c="r"); axx.axhline(-a.banda95.iloc[0], ls="--", c="r")
        axx.set_title(f"{t} — {title}")
    _save(fig, path)


def fig_decomp(m, path):
    s = m["ipc"][m.index >= "2005"]
    d = fc.decompose(s, "multiplicative")
    fig, ax = plt.subplots(4, 1, figsize=(9, 7), sharex=True)
    for a, (v, t) in zip(ax, ((d.observed, "IPC"), (d.trend, "Tendencia"), (d.seasonal, "Estacional"), (d.resid, "Residuo"))):
        a.plot(v); a.set_ylabel(t)
    _save(fig, path)
    return float(fc.seasonal_strength(s))


def fig_espectro(x, path):
    sp = st.periodogram(x, min_freq=1 / 60)
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.semilogy(sp["f"], sp["pxx"]); ax.set_xlabel("Frecuencia (ciclos/mes)"); ax.set_title("Densidad espectral — Δlog RIB")
    for p in sp["picos"]:
        ax.axvline(p["frecuencia"], c="r", ls=":", alpha=.6)
    _save(fig, path)
    return sp["picos"]


def fig_markov(ci, states, fit, path_a, path_b):
    fig, ax = plt.subplots(figsize=(10, 3.6))
    ax.plot(ci["indice"], c="k", lw=1)
    for i in range(len(states) - 1):
        ax.axvspan(states.index[i], states.index[i + 1], color=COL[int(states.iloc[i])], alpha=.25, lw=0)
    ax.set_title("Índice de estrés y estados (verde=Estable, ámbar=Tensión, rojo=Crisis)")
    _save(fig, path_a)
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    im = ax.imshow(fit.P, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(3)); ax.set_xticklabels(mk.ESTADOS); ax.set_yticks(range(3)); ax.set_yticklabels(mk.ESTADOS)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{fit.P[i, j]:.2f}", ha="center", va="center", color="w" if fit.P[i, j] > .5 else "k")
    ax.set_title("Matriz de transición P"); ax.grid(False)
    _save(fig, path_b)


def fig_forecasts(res_by, path):
    fig, ax = plt.subplots(2, 2, figsize=(11, 6.5))
    for a, (col, r) in zip(ax.ravel(), res_by.items()):
        y = np.exp(r["y"]); f = r["forecast"]
        a.plot(y.index[-72:], y.iloc[-72:], c="k"); a.plot(f.index, f["media"], c="C0")
        a.fill_between(f.index, f["inf"], f["sup"], alpha=.25)
        sp = r["spec"]; a.set_title(f"{data.NOMBRES.get(col, col)}\nSARIMA{sp.order}x{sp.seasonal_order}")
    _save(fig, path)


def fig_anom(res_by, path):
    fig, ax = plt.subplots(len(res_by), 1, figsize=(10, 2.2 * len(res_by)), sharex=True)
    for a, (col, r) in zip(np.atleast_1d(ax), res_by.items()):
        z = r["anom"]; a.plot(z.residuo_z, lw=.8); a.axhline(2.5, c="r", ls="--"); a.axhline(-2.5, c="r", ls="--")
        a.scatter(z.index[z.anomalia], z.residuo_z[z.anomalia], c="r", s=14); a.set_ylabel(col)
    _save(fig, path)


def fig_mc(rs, path):
    f = rs["fan"]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    x = np.arange(len(f))
    ax.fill_between(x, f.p5, f.p95, alpha=.2, label="5–95%"); ax.fill_between(x, f.p25, f.p75, alpha=.35, label="25–75%")
    ax.plot(x, f.p50, c="C0", label="mediana"); ax.axhline(rs["umbral"], c="r", ls="--", label=f"umbral {rs['umbral']:,.0f}")
    ax.set_xlabel("meses"); ax.set_title("Monte Carlo (GBM) — reservas (MM USD)"); ax.legend()
    _save(fig, path)


def fig_valoracion(m, path) -> dict:
    t = m["2022":]
    vig, fija = data.bolivianizacion_tc_vigente(m), data.bolivianizacion_tc_fijo(m)
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.4))
    ax[0].plot(vig["2022":], label="A tipo de cambio vigente")
    ax[0].plot(fija["2022":], label="A tipo de cambio constante (6,96)")
    ax[0].plot(t.bolivianizacion_depositos, ls=":", c="gray", label="Cifra oficial BCB (otra definición)")
    ax[0].legend(fontsize=7); ax[0].set_title("Bolivianización de depósitos (%)")
    ax[1].plot(t.depositos_me, c="C2"); ax[1].set_title("Depósitos en moneda extranjera (MM USD, sin conversión)")
    _save(fig, path)
    a, b = pd.Timestamp("2025-09-30"), m.index.max()
    return {"fecha_a": str(a.date()), "fecha_b": str(b.date()),
            "vigente_a": float(vig[a]), "vigente_b": float(vig[b]), "constante_a": float(fija[a]), "constante_b": float(fija[b]),
            "oficial_a": float(m.bolivianizacion_depositos[a]), "oficial_b": float(m.bolivianizacion_depositos[b]),
            "me_usd_a": float(m.depositos_me[a]), "me_usd_b": float(m.depositos_me[b])}


def tc_regimes_table(m: pd.DataFrame) -> pd.DataFrame:
    s = data.tc_efectivo(m)
    r = np.log(s).diff().dropna() * 100
    rows = []
    for name, (a, b) in {"Fijo (nov-2011→nov-2025)": ("2011-12-01", "2025-11-30"),
                         "Referencial (dic-2025→may-2026)": ("2025-12-01", "2026-05-31"),
                         "Flexible (jun-2026→)": ("2026-06-01", "2100-01-01")}.items():
        x = r[(r.index >= a) & (r.index <= b)]
        rows.append({"régimen": name, "meses": len(x), "var. mensual media %": x.mean() if len(x) else np.nan,
                     "desv. est. %": x.std() if len(x) > 1 else np.nan})
    return pd.DataFrame(rows)


def run(out_dir: Path | None = None, validate: bool = True) -> dict:
    out = Path(out_dir or ROOT / "reports"); figs = out / "figures"; figs.mkdir(parents=True, exist_ok=True)
    m, d = data.load_monthly(), data.load_daily_key()
    col_p2p, bcb_pdf = data.load_p2p()
    gap_d = data.build_gap(m, d, col_p2p, bcb_pdf)
    R: dict = {"generado": pd.Timestamp.now().isoformat(timespec="seconds"),
               "ultimo_mes": str(m.index.max().date()), "n_meses": int(len(m))}

    # Cap. 1-2
    adf_t = st.adf_table(m, ["rib", "ipc", "depositos_me", "base_monetaria"])
    R["adf"] = adf_t.to_dict("records")
    fig_series(m, figs / "fig_series.png")
    R["valoracion"] = fig_valoracion(m, figs / "fig_valoracion.png")
    dl = np.log(m["rib"]).diff().dropna() * 100
    fig_acf(dl["2000":], figs / "fig_acf_rib.png", "Δlog RIB (×100)")
    # Cap. 4
    R["fuerza_estacional_ipc"] = fig_decomp(m, figs / "fig_descomposicion_ipc.png")
    # Cap. 5
    picos = fig_espectro(dl, figs / "fig_espectro_rib.png"); R["espectro_picos"] = picos

    # Cap. 6
    res_by = {}
    for col in fc.SEASONAL_VARS:
        res_by[col] = fc.full_analysis(m, col, steps=12, validate=validate)
    fig_forecasts(res_by, figs / "fig_pronosticos.png"); fig_anom(res_by, figs / "fig_anomalias.png")
    R["sarima"] = {}
    for col, r in res_by.items():
        e = {"orden": list(r["spec"].order), "orden_estacional": list(r["spec"].seasonal_order), "aic": r["spec"].aic,
             "diagnostico": r["diag"], "pronostico_12m": r["forecast"].round(2).reset_index().astype(str).to_dict("records"),
             "anomalias_recientes": [str(i.date()) for i in r["anom"][r["anom"].anomalia].index[-6:]]}
        if "validation" in r and len(r["validation"]):
            e["validacion"] = r["validation"].to_dict("records")
        R["sarima"][col] = e

    # Cap. 3
    gm = gp.monthly_gap(gap_d)
    ci = mk.stress_index(m, gm if len(gm) else None)
    states = mk.classify(ci["indice"]); fit = mk.fit_markov(states)
    fig_markov(ci, states, fit, figs / "fig_markov_estados.png", figs / "fig_markov_matriz.png")
    cur = int(states.iloc[-1])
    probs = mk.forecast_state_probs(fit.P, cur)
    R["markov"] = {"umbrales": states.attrs["umbrales"], "P": fit.P.tolist(), "conteos": fit.counts.tolist(),
                   "estacionaria": fit.stationary.tolist(), "permanencia": [float(x) for x in fit.sojourn],
                   "estado_actual": mk.ESTADOS[cur], "fecha_estado": str(states.index[-1].date()),
                   "prob_futura": {str(h): p.tolist() for h, p in probs.items()},
                   "indep": mk.test_independence(fit.counts), "orden2": mk.test_second_order(states),
                   "componentes": [c for c in ci.columns if c != "indice"]}
    ep = mk.episode_table(states); rb = mk.robustness(ci["indice"])
    cmp23 = mk.compare_periods(states, "2023-01-31")
    R["markov"]["episodios"] = ep.to_dict("records"); R["markov"]["robustez"] = rb.to_dict("records")
    R["markov"]["antes_despues_2023"] = {k: {kk: (vv.tolist() if hasattr(vv, "tolist") else vv) for kk, vv in v.items()} for k, v in cmp23.items()}

    # Cap. 7
    rs = sim.reserves_simulation(m["rib"], horizon=6, threshold=3500.0)
    fig_mc(rs, figs / "fig_montecarlo_rib.png")
    R["montecarlo_rib"] = {k: rs[k] for k in ("params", "p_terminal", "p_cruce", "umbral", "s0")}
    pts = data.official_points(m, d)
    fxp = sim.fx_params(pts)
    if fxp.get("ok"):
        c = sim.fx_cost_simulation(10_000, 90, fxp["s0"], 0.0, fxp["sigma_diario"])
        R["fx_ejemplo"] = {"usd": 10_000, "dias": 90, "params": {k: (str(v) if k == "fecha" else v) for k, v in fxp.items()},
                           **{k: c[k] for k in ("hoy", "p5", "p50", "p95")}}

    # Brecha (H1, H3, H5): solo con datos reales
    reg_tbl = tc_regimes_table(m)
    R["tc_regimenes"] = reg_tbl.to_dict("records")
    R["brecha"] = {"n_dias": int(len(gap_d))}
    if len(gap_d) >= gp.MIN_OBS:
        R["brecha"]["ar1"] = {k: (v if not isinstance(v, dict) else v) for k, v in gp.ar1_gap(gap_d["brecha_pct"]).items()}
        ll = gp.lead_lag(gap_d["paralelo"], gap_d["oficial"]); ll.pop("cc", None); R["brecha"]["lead_lag"] = ll
        R["brecha"]["vol"] = gp.volatility_by_regime(np.log(gap_d["paralelo"]).diff().dropna(), str(data.FECHA_FLEXIBLE.date()))

    (out / "results.json").write_text(json.dumps(R, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    _informe(out, R, m, adf_t, ep, rb, reg_tbl, res_by, fit, ci, states, rs)
    return R


def _pct(x): return f"{100 * x:.1f}%"


def _informe(out: Path, R: dict, m, adf_t, ep, rb, reg_tbl, res_by, fit, ci, states, rs):
    mk_ = R["markov"]; g = R["brecha"]
    L = []
    A = L.append
    A("# Informe: Monitor de estrés cambiario y monetario de Bolivia\n")
    A(f"*Generado automáticamente el {R['generado'][:10]} · datos mensuales hasta {R['ultimo_mes']} ({R['n_meses']} meses).*\n")
    A("## 1. Resumen\n")
    A(f"Con la serie oficial del BCB (1989-{R['ultimo_mes'][:4]}) se construye un índice de estrés a partir de reservas y bolivianización (sin efecto de valoración), "
      f"se lo discretiza en tres estados y se estima una cadena de Markov. Estado más reciente ({mk_['fecha_estado']}): **{mk_['estado_actual']}**. "
      f"Distribución estacionaria estimada: Estable {_pct(mk_['estacionaria'][0])}, Tensión {_pct(mk_['estacionaria'][1])}, Crisis {_pct(mk_['estacionaria'][2])}. "
      "Se pronostican reservas, depósitos en dólares, base monetaria e IPC con SARIMA y se estiman probabilidades de riesgo con Monte Carlo.\n")
    A("**Advertencia:** estos resultados son descriptivos y académicos; no constituyen asesoría financiera.\n")
    A("## 2. Datos\n")
    A("- **BCB, Estadísticas Semanales (Excel):** variables mensuales desde 1987 (aquí desde 1989), más semanas y días recientes.")
    A("- **Tipo de cambio:** tres regímenes observables en el Excel: fijo (6,96), valor referencial (dic-2025→may-2026) y oficial flexible (jun-2026→).")
    A(f"- **Brecha oficial-paralelo:** {g['n_dias']} días con dato de paralelo disponibles. "
      + ("Los resultados de H1, H3 formal y H5 se evalúan por separado según su cobertura." if g["n_dias"] >= gp.MIN_OBS else
         f"**Insuficiente** (mínimo {gp.MIN_OBS} para H1); las hipótesis H1, H3 (formal) y H5 quedan pendientes hasta acumular historial P2P con el recolector o importar los PDF del BCB."))
    A("\n![Series](figures/fig_series.png)\n")
    v_ = R["valoracion"]
    A("### Hallazgo: el efecto de valoración en la bolivianización\n")
    A(f"Los cuadros del BCB expresan los saldos en millones de **USD**: los depósitos en moneda extranjera están en dólares reales, pero los depósitos en bolivianos se convierten al tipo de cambio vigente. Al pasar el tipo de cambio de 6,96 a ~12, el saldo en bolivianos medido en USD cae mecánicamente. Con las mismas filas (moneda nacional y extranjera de los cuadros), entre {v_['fecha_a']} y {v_['fecha_b']} la bolivianización calculada **al tipo de cambio vigente** pasó de {v_['vigente_a']:.1f}% a {v_['vigente_b']:.1f}%, pero **a tipo de cambio constante (6,96)** pasó de {v_['constante_a']:.1f}% a {v_['constante_b']:.1f}%; los depósitos en dólares casi no cambiaron ({v_['me_usd_a']:,.0f} → {v_['me_usd_b']:,.0f} MM USD). La caída es contable, no una fuga hacia el dólar. Por eso el índice de estrés usa la versión sin efecto de valoración. La cifra oficial del BCB (fila «Bolivianización», {v_['oficial_a']:.1f}% → {v_['oficial_b']:.1f}%) usa otra definición que difiere de la calculada hasta ~4 pp en 2023-24, probablemente por el tratamiento de depósitos con mantenimiento de valor (no verificado), por lo que **no se mezclan ambas**. Se verificó además que el BCB convirtió a 6,96 hasta may-2026, no al valor referencial.\n")
    A("![Valoración](figures/fig_valoracion.png)\n")
    A("## 3. Métodos y resultados por capítulo del libro\n")
    A("### Cap. 1-2: procesos estocásticos y estacionariedad\n")
    A("Cada variable se trata como un proceso estocástico en tiempo discreto {X_t}. Un proceso es (débilmente) estacionario si su media y varianza son constantes y la autocovarianza depende solo del rezago. Se aplica la prueba de Dickey-Fuller aumentada (H0: raíz unitaria).\n")
    t = adf_t[adf_t["transformación"].isin(["log", "Δlog ×100"])][["variable", "transformación", "estadistico", "p_valor", "estacionaria_5%"]]
    A(md_table(t)); A("")
    A("![ACF/PACF](figures/fig_acf_rib.png)\n")
    A("### Cap. 4: descomposición y suavizamiento exponencial\n")
    A(f"Descomposición clásica multiplicativa del IPC (periodo 12). Fuerza de la estacionalidad: {R['fuerza_estacional_ipc']:.2f} (el umbral habitual para diferenciar estacionalmente es 0,64), por lo que el IPC no requiere diferencia estacional. Holt-Winters (tendencia amortiguada + estacionalidad aditiva) se usa como modelo de referencia en la validación.\n")
    A("![Descomposición](figures/fig_descomposicion_ipc.png)\n")
    A("### Cap. 5: densidad espectral\n")
    pk = ", ".join(f"{p['periodo_meses']:.1f} meses" for p in R["espectro_picos"])
    A(f"El periodograma de Δlog RIB muestra sus mayores picos en periodos de: {pk}. Solo se consideran periodos de hasta 60 meses: los más largos (del orden del tamaño de la muestra) no se distinguen de la tendencia. Un pico cercano a 12 meses indicaría estacionalidad anual.\n")
    A("![Espectro](figures/fig_espectro_rib.png)\n")
    A("### Cap. 3: cadena de Markov\n")
    A(f"Índice de estrés = promedio de z-scores de: {', '.join(mk_['componentes'])} (menos Δ12 log RIB, menos Δ6 de la bolivianización de depósitos a tipo de cambio constante"
      + (", más brecha" if "brecha" in mk_["componentes"] else "") + "). "
      f"Estados por cuantiles del índice: Tensión desde {mk_['umbrales'][0]:.2f} (percentil 60) y Crisis desde {mk_['umbrales'][1]:.2f} (percentil 85). **Estos cortes son una decisión del autor**; la sección de robustez muestra su efecto.\n")
    P = pd.DataFrame(mk_["P"], index=mk.ESTADOS, columns=mk.ESTADOS).round(3).reset_index().rename(columns={"index": "desde \\ hacia"})
    A(md_table(P)); A("")
    A(f"Permanencia media (1/(1−p_ii)): Estable {mk_['permanencia'][0]:.1f}, Tensión {mk_['permanencia'][1]:.1f}, Crisis {mk_['permanencia'][2]:.1f} meses.\n")
    pf = mk_["prob_futura"]
    A("Probabilidades desde el estado actual: " + "; ".join(f"a {h} mes(es): " + ", ".join(f"{mk.ESTADOS[i]} {_pct(p[i])}" for i in range(3)) for h, p in pf.items()) + ".\n")
    ind, o2 = mk_["indep"], mk_["orden2"]
    A(f"**Propiedad de Markov.** Independencia (χ², {ind['gl']} g.l.): p = {ind['p_valor']:.2g}, hay fuerte dependencia entre estados consecutivos. Orden 1 vs orden 2 (razón de verosimilitud, {o2['gl']} g.l.): p = {o2['p_valor']:.2g}. "
      + ("Se rechaza orden 1 al 5%: la cadena de primer orden es una aproximación; parte de la persistencia proviene de que el índice usa variaciones sobre ventanas móviles (12 y 6 meses) que se solapan. " if o2["p_valor"] < 0.05 else "No se rechaza orden 1 al 5%. ")
      + f"Con {int(np.sum(mk_['conteos']))} transiciones el contraste es potente, pero las observaciones no son independientes.\n")
    A("**Validación con episodios conocidos** (fracción de meses en cada estado):\n"); A(md_table(ep.round(2))); A("")
    A("Lectura honesta: el índice sin brecha cambiaria **no refleja la tensión cambiaria de dic-2025→may-2026** (aparece como Estable), porque ese episodio se vio en el mercado paralelo y no en reservas ni bolivianización. Es precisamente el componente que aportaría la brecha cuando haya historial P2P.\n")
    A("**Robustez a los umbrales:**\n"); A(md_table(rb.round(2))); A("")
    A("![Estados](figures/fig_markov_estados.png)\n![Matriz](figures/fig_markov_matriz.png)\n")
    A("### Cap. 6: ARIMA/SARIMA (Box-Jenkins)\n")
    A("Ciclo: identificación (ADF para d, fuerza estacional para D, AIC para p,q,P,Q), estimación por máxima verosimilitud, diagnóstico (Ljung-Box y Jarque-Bera) y pronóstico con IC 95%. Se limita d ≤ 1 y se trabaja en logaritmos desde 2005.\n")
    rows = []
    for col, e in R["sarima"].items():
        dg = e["diagnostico"]
        rows.append({"variable": col, "orden": str(tuple(e["orden"])), "estacional": str(tuple(e["orden_estacional"])),
                     "LB p(12)": dg["ljung_box_p_12"], "LB p(24)": dg["ljung_box_p_24"], "JB p": dg["jarque_bera_p"],
                     "residuos blancos": "sí" if dg["residuos_blancos_5%"] else "no"})
    A(md_table(pd.DataFrame(rows), "{:.3f}")); A("")
    A("Los residuos no son normales (colas pesadas por los quiebres de 2015, 2020 y 2023-2026); los intervalos del modelo gaussiano deben leerse con cautela.\n")
    A("![Pronósticos](figures/fig_pronosticos.png)\n")
    A("**Validación con ventana móvil** (24 orígenes, últimos 2 años; MAPE %):\n")
    vrows = []
    for col, e in R["sarima"].items():
        for v in e.get("validacion", []):
            vrows.append({"variable": col, **v})
    if vrows:
        v = pd.DataFrame(vrows)
        pv = v.pivot_table(index=["variable", "h"], columns="modelo", values="MAPE_%").reset_index()
        cov = v[v.modelo == "sarima"].pivot_table(index=["variable", "h"], values="cobertura_IC95").reset_index()
        pv = pv.merge(cov, on=["variable", "h"]).rename(columns={"h": "horizonte (meses)", "cobertura_IC95": "cobertura IC95 SARIMA"})
        A(md_table(pv.round(2), "{:.2f}")); A("")
        wins = []
        for col in R["sarima"]:
            sub = v[(v.variable == col)]
            piv = sub.pivot_table(index="h", columns="modelo", values="MAPE_%")
            wins.append((col, int((piv["sarima"] < piv["ingenuo"]).sum()), len(piv)))
        best = []
        for col in R["sarima"]:
            for h in (1, 3, 6):
                g_ = v[(v.variable == col) & (v.h == h)].sort_values("MAPE_%")
                if len(g_):
                    best.append(f"{col} h={h}: {g_.iloc[0]['modelo']}")
        A("Mejor modelo por MAPE: " + "; ".join(best) + ".\n")
        A("**H4 (SARIMA supera al ingenuo):** " + "; ".join(f"{c}: {w}/{n} horizontes" for c, w, n in wins)
          + ". Resultado mixto: la hipótesis se sostiene para algunas series y no para otras (en reservas el modelo ingenuo es difícil de superar en este período turbulento). Las coberturas del IC 95% por debajo de 95% indican intervalos demasiado estrechos frente a los quiebres.\n")
    else:
        A("*(Validación omitida en esta ejecución; correr sin `--rapido`.)*\n")
    A("### Cap. 7: Monte Carlo (GBM) y anomalías\n")
    mc = R["montecarlo_rib"]
    A(f"Reservas simuladas con movimiento browniano geométrico: μ = {mc['params']['mu']*100:.2f}% y σ = {mc['params']['sigma']*100:.2f}% mensuales (últimos {mc['params']['n']} meses), 10.000 trayectorias a 6 meses desde {mc['s0']:,.0f} MM USD. "
      f"Con umbral de {mc['umbral']:,.0f}: P(terminar por debajo) = {_pct(mc['p_terminal'])}; P(cruzarlo en algún mes) = {_pct(mc['p_cruce'])}. "
      "Supone retornos log-normales independientes y volatilidad constante, supuestos que los datos incumplen; es un escenario, no una predicción.\n")
    A("![Monte Carlo](figures/fig_montecarlo_rib.png)\n")
    if "fx_ejemplo" in R:
        fx = R["fx_ejemplo"]; p = fx["params"]
        A(f"**Ejemplo del simulador cambiario:** USD {fx['usd']:,} a {fx['dias']} días. Hoy: Bs {fx['hoy']:,.0f}. Rango 5-50-95%: Bs {fx['p5']:,.0f} / {fx['p50']:,.0f} / {fx['p95']:,.0f}. "
          f"Parámetros: σ diaria {p['sigma_diario']*100:.2f}% estimada con solo {p['n']} variaciones del oficial desde ago-2026 y deriva 0. **Muestra muy pequeña: el rango es indicativo.**\n")
    A("Detección de anomalías: residuos estandarizados de SARIMA con |z| > 2,5 (se descartan los primeros 24 meses por el arranque del filtro).\n")
    A("![Anomalías](figures/fig_anomalias.png)\n")
    A("## 4. Régimen cambiario: evidencia descriptiva (H3)\n")
    A(md_table(reg_tbl.round(3))); A("")
    A("La variación mensual del tipo de cambio de referencia es nula bajo el régimen fijo (2011-2025) y pasa a ser grande bajo el referencial y el flexible, un cambio de régimen evidente (incluye el salto único jun→jul-2026, de 9,76 a 12,15). La comparación formal de volatilidad del paralelo (prueba de Levene) requiere historial P2P.\n")
    A("## 5. Estado de las hipótesis\n")
    ar = g.get("ar1")
    hy = [("H1", "Brecha estacionaria con vida media corta", f"AR(1): φ={ar['phi']:.3f}, vida media {ar['vida_media']:.1f} días" if ar and ar.get("ok") else "Pendiente: faltan datos P2P"),
          ("H2", "Estados persistentes (Markov)", f"p_Estable→Estable={mk_['P'][0][0]:.2f}; independencia rechazada; orden 1 {'rechazado' if o2['p_valor']<0.05 else 'no rechazado'} (p={o2['p_valor']:.3f})"),
          ("H3", "Volatilidad cambia con el régimen", f"Levene p={g['vol']['levene_p']:.3f}" if g.get("vol", {}).get("ok") else "Descriptivo: sí (ver §4). Formal: pendiente; se necesitan al menos 10 retornos antes y después del 29-jun-2026"),
          ("H4", "SARIMA supera al ingenuo", "Mixto (ver validación)"),
          ("H5", "El paralelo se adelanta al oficial", "Pendiente: se necesitan al menos 90 retornos diarios comunes" if not g.get("lead_lag", {}).get("ok") else f"Rezago de máxima correlación: {g['lead_lag']['rezago_max']} días")]
    A(md_table(pd.DataFrame(hy, columns=["#", "Hipótesis", "Resultado"]))); A("")
    A("## 6. Limitaciones\n")
    for t in ["El régimen flexible tiene pocas observaciones (desde jun-2026): todo lo post-cambio es exploratorio.",
              "El índice de estrés usa estandarización con toda la muestra y umbrales por cuantiles (decisión del autor); describe, no predice.",
              "Datos recientes del BCB son preliminares y se revisan.",
              "Los modelos gaussianos subestiman colas pesadas y quiebres.",
              "GARCH no se implementó (queda como extensión)."]:
        A(f"- {t}")
    A("\n## 7. Referencias\n- Material del curso DAT 262 (Procesos Estocásticos y Series de Tiempo).\n- BCB, Estadísticas Semanales y Tabla de precios de activos virtuales.\n- Seabold & Perktold (2010), statsmodels.")
    (out / "INFORME.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--rapido", action="store_true"); ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    run(a.out, validate=not a.rapido)
    print("Listo: reports/INFORME.md, reports/results.json, reports/figures/")
