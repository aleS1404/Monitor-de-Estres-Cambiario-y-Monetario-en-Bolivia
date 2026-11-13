"""Genera y ejecuta los notebooks por capítulo.  Uso: python notebooks/build_notebooks.py"""
from pathlib import Path

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

HERE = Path(__file__).resolve().parent
SETUP = '''import sys, warnings
from pathlib import Path
sys.path.insert(0, str(Path.cwd().parent))
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from stress_monitor import data, stationarity as stat, markov as mk, forecasting as fc, gap as gp, simulation as sim, demo
plt.rcParams.update({"figure.dpi": 100, "axes.grid": True, "grid.alpha": .3})
m = data.load_monthly(); d = data.load_daily_key()
print("Datos mensuales:", m.index.min().date(), "→", m.index.max().date(), f"({len(m)} meses)")'''

NB = {}
NB["cap1_2_estacionariedad"] = ("Cap. 1-2 · Procesos estocásticos y estacionariedad", [
 ("md", "Cada variable se modela como un proceso estocástico en tiempo discreto $\\{X_t\\}$. Es **débilmente estacionario** si $E[X_t]=\\mu$, $Var(X_t)=\\sigma^2$ y $Cov(X_t,X_{t+k})=\\gamma(k)$ solo dependen del rezago $k$. La prueba ADF contrasta $H_0$: raíz unitaria."),
 ("code", "fig, ax = plt.subplots(2, 2, figsize=(11, 6))\nfor a, c in zip(ax.ravel(), ['rib', 'ipc', 'depositos_me', 'base_monetaria']):\n    a.plot(m[c].dropna()); a.set_title(data.NOMBRES[c])\nplt.tight_layout()"),
 ("md", "### Momentos muestrales de Δlog(RIB)"),
 ("code", "dl = np.log(m['rib']).diff().dropna() * 100\nmo = stat.sample_moments(dl, 6)\nprint('media %.3f | varianza %.3f' % (mo['media'], mo['varianza']))\nprint('autocovarianzas γ(0..6):', np.round(mo['autocovarianzas'], 2))"),
 ("md", "### Prueba ADF: niveles no estacionarios, diferencias estacionarias"),
 ("code", "t = stat.adf_table(m, ['rib', 'ipc', 'depositos_me', 'base_monetaria'])\nt[t['transformación'].isin(['log', 'Δlog ×100'])].round(3)"),
 ("code", "a = stat.acf_pacf(dl['2000':], 36)\nfig, ax = plt.subplots(1, 2, figsize=(11, 3))\nax[0].bar(a.lag, a.acf, width=.3); ax[1].bar(a.lag, a.pacf, width=.3)\nfor x in ax: x.axhline(a.banda95[0], c='r', ls='--'); x.axhline(-a.banda95[0], c='r', ls='--')\nax[0].set_title('ACF Δlog RIB'); ax[1].set_title('PACF Δlog RIB'); plt.tight_layout()"),
])
NB["cap3_markov"] = ("Cap. 3 · Cadena de Markov del estrés", [
 ("md", "**Índice de estrés** = promedio de z-scores de −Δ12 log(RIB) y −Δ6 bolivianización **a tipo de cambio constante** (sin efecto de valoración). Estados por percentiles: Tensión ≥ p60, Crisis ≥ p85 (decisión del analista)."),
 ("code", "ci = mk.stress_index(m); states = mk.classify(ci['indice'])\nprint('umbrales:', np.round(states.attrs['umbrales'], 2))\nci.tail(6).round(2)"),
 ("code", "fit = mk.fit_markov(states)\nprint(pd.DataFrame(fit.P, index=mk.ESTADOS, columns=mk.ESTADOS).round(3))\nprint('π =', dict(zip(mk.ESTADOS, fit.stationary.round(3))))\nprint('permanencia (meses) =', dict(zip(mk.ESTADOS, fit.sojourn.round(1))))"),
 ("md", "Tiempo medio de permanencia en $i$: $1/(1-p_{ii})$. Distribución estacionaria: $\\pi P=\\pi$."),
 ("code", "cur = int(states.iloc[-1]); pr = mk.forecast_state_probs(fit.P, cur)\nprint('Estado actual:', mk.ESTADOS[cur], states.index[-1].date())\nfor h, p in pr.items(): print(f'a {h} mes(es):', dict(zip(mk.ESTADOS, p.round(3))))"),
 ("md", "### ¿Se cumple la propiedad de Markov?"),
 ("code", "print('Independencia χ²:', mk.test_independence(fit.counts))\nprint('Orden 1 vs 2 (LR):', mk.test_second_order(states))"),
 ("md", "### Validación con episodios y robustez"),
 ("code", "display(mk.episode_table(states).round(2)); display(mk.robustness(ci['indice']).round(2))"),
 ("md", "### Antes y después de 2023 (escasez de dólares)"),
 ("code", "cmp = mk.compare_periods(states, '2023-01-31')\nfor k, v in cmp.items():\n    print(k, '| n =', v['n'], '|', v.get('aviso', ''))\n    if 'P' in v: print(np.round(v['P'], 2))"),
 ("code", "fig, ax = plt.subplots(figsize=(11, 3.2)); ax.plot(ci['indice'], c='k', lw=1)\ncol = {0: 'green', 1: 'orange', 2: 'red'}\nfor i in range(len(states) - 1): ax.axvspan(states.index[i], states.index[i + 1], color=col[int(states.iloc[i])], alpha=.25, lw=0)\nax.set_title('Índice de estrés y estados')"),
])
NB["cap4_descomposicion"] = ("Cap. 4 · Descomposición y suavizamiento exponencial", [
 ("md", "Modelo clásico multiplicativo: $X_t = T_t \\cdot S_t \\cdot e_t$. La *fuerza estacional* $F_s=\\max(0,1-Var(e)/Var(S+e))$ guía si hace falta diferenciar estacionalmente."),
 ("code", "s = m['ipc'][m.index >= '2005']\ndec = fc.decompose(s, 'multiplicative')\nfig, ax = plt.subplots(4, 1, figsize=(10, 7), sharex=True)\nfor a, (v, t) in zip(ax, ((dec.observed, 'IPC'), (dec.trend, 'Tendencia'), (dec.seasonal, 'Estacional'), (dec.resid, 'Residuo'))): a.plot(v); a.set_ylabel(t)\nplt.tight_layout()\nprint('Fuerza estacional IPC: %.2f' % fc.seasonal_strength(s))"),
 ("code", "for c in ['depositos_me', 'base_monetaria', 'rib']: print(c, 'Fs = %.2f' % fc.seasonal_strength(m[c][m.index >= '2005']))"),
 ("md", "### Holt-Winters (tendencia amortiguada + estacionalidad) frente al modelo ingenuo, pronóstico a 6 meses"),
 ("code", "y = fc.log_series(m, 'depositos_me')\ntrain, real = y.iloc[:-6], np.exp(y.iloc[-6:])\nhw = np.exp(fc.holt_winters_forecast(train, 6)); naive = pd.Series(np.exp(train.iloc[-1]), index=real.index)\nprint('MAPE HW      : %.2f%%' % ((hw.values - real.values).__abs__() / real.values).mean().__mul__(100))\nprint('MAPE ingenuo : %.2f%%' % ((naive.values - real.values).__abs__() / real.values).mean().__mul__(100))\npd.DataFrame({'real': real, 'HW': hw.values, 'ingenuo': naive.values}).round(0)"),
])
NB["cap5_ar_espectral"] = ("Cap. 5 · AR(1), vida media y densidad espectral", [
 ("md", "**AR(1):** $G_t=c+\\phi G_{t-1}+\\varepsilon_t$. Media de largo plazo $c/(1-\\phi)$ y **vida media** $\\ln(0{,}5)/\\ln\\phi$ (tiempo para que se cierre la mitad de una desviación). Densidad espectral: $f(\\omega)$ estimada con el periodograma."),
 ("code", "dl = np.log(m['rib']).diff().dropna()\nsp = stat.periodogram(dl, min_freq=1/60)\nfig, ax = plt.subplots(figsize=(9, 3)); ax.semilogy(sp['f'], sp['pxx']); ax.set_xlabel('ciclos/mes'); ax.set_title('Periodograma de Δlog RIB (periodos ≤ 60 meses)')\nprint('Picos:', [round(p['periodo_meses'], 1) for p in sp['picos']], 'meses')"),
 ("md", "### Brecha oficial–paralelo con datos observados\nParalelo: mediana P2P de [paralelo.bo](https://paralelo.bo/api/v1/historical.csv), CC BY 4.0. Oficial diario: [BCB TCO](https://www.bcb.gob.bo/grafico_evolutivo/download.php?serie=tipo_de_cambio&format=csv) desde 29-jun-2026. La mediana P2P es un anuncio y no se mezcla con Binance ni el PDF."),
 ("code", "col, pdf = data.load_p2p(); ext = data.load_external_parallel(); tco = data.load_bcb_tco(); g = data.build_gap(m, d, col, pdf, external=ext, official_tco=tco)\nassert len(ext) >= 30, 'Descargue el historial real: python -m bcb_pipeline fetch-history'\nr = gp.ar1_gap(g['brecha_pct'][g.index >= data.FECHA_FLEXIBLE])\nprint({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k in ('n', 'phi', 'vida_media', 'media_larga', 'adf')})"),
 ("code", "x = g['brecha_pct']\nfig, ax = plt.subplots(figsize=(10, 3)); ax.plot(x); ax.axvline(data.FECHA_FLEXIBLE, c='r', ls='--', label='29-jun-2026'); ax.legend(); ax.set_title('Brecha observada (%)')"),
 ("md", "### H3 y H5 con datos reales\nH3 compara volatilidad de la misma mediana P2P entre 4-may y 3-sep-2026; H5 usa retornos hábiles desde julio. Los valores de Granger son predictivos, no causales."),
 ("code", "ret = gp.daily_returns(g['paralelo']); ret = ret[(ret.index >= '2026-05-04') & (ret.index <= '2026-09-03')]\nprint('H3:', gp.volatility_by_regime(ret, str(data.FECHA_FLEXIBLE.date())))\nll = gp.lead_lag(g['paralelo'], g['oficial']); ll.pop('cc', None); print('H5:', ll)"),
])
NB["cap6_sarima"] = ("Cap. 6 · Box-Jenkins con SARIMA (reservas)", [
 ("md", "Ciclo de Box-Jenkins: **identificación** (estacionariedad, ACF/PACF), **estimación**, **diagnóstico** y **pronóstico**."),
 ("code", "y = fc.log_series(m, 'rib')\nprint('d sugerido:', fc.choose_d(y), '| D sugerido:', fc.choose_D(y))\nprint(stat.adf(y)['p_valor'], stat.adf(y.diff().dropna())['p_valor'])"),
 ("code", "spec = fc.select_sarima(y); print(spec)\nres = fc.fit_sarima(y, spec.order, spec.seasonal_order)\nprint(fc.diagnostics(res, spec))"),
 ("code", "e = pd.Series(res.resid).iloc[fc.BURN_IN:]\nfig, ax = plt.subplots(1, 3, figsize=(12, 3))\nax[0].plot(e); ax[0].set_title('Residuos'); a = stat.acf_pacf(e, 24); ax[1].bar(a.lag, a.acf, width=.3); ax[1].set_title('ACF residuos'); ax[2].hist(e, 30); ax[2].set_title('Histograma')\nplt.tight_layout()"),
 ("code", "f = fc.forecast_log(res, 12); h = np.exp(y.iloc[-72:])\nfig, ax = plt.subplots(figsize=(10, 3.5)); ax.plot(h.index, h, c='k'); ax.plot(f.index, f.media); ax.fill_between(f.index, f['inf'], f['sup'], alpha=.25); ax.set_title('Pronóstico RIB (MM USD)')\nf.round(0)"),
 ("md", "### Validación con ventana móvil (12 orígenes para que el notebook sea rápido)"),
 ("code", "v = fc.rolling_validation(y, spec, n_origins=12)\nv.pivot_table(index='h', columns='modelo', values='MAPE_%').round(2)"),
])
NB["cap7_montecarlo_anomalias"] = ("Cap. 7 · Monte Carlo (GBM) y anomalías", [
 ("md", "**GBM:** $S_t=S_0\\exp\\{(\\mu-\\sigma^2/2)t+\\sigma W_t\\}$. Los parámetros se estiman con los log-retornos recientes."),
 ("code", "rs = sim.reserves_simulation(m['rib'], horizon=6, threshold=3500.0)\nprint(rs['params']); print('P(terminal < umbral) = %.1f%% | P(cruce) = %.1f%%' % (100*rs['p_terminal'], 100*rs['p_cruce']))\nf = rs['fan']; fig, ax = plt.subplots(figsize=(8, 3.4)); ax.fill_between(f.index, f.p5, f.p95, alpha=.2); ax.fill_between(f.index, f.p25, f.p75, alpha=.35); ax.plot(f.p50); ax.axhline(3500, c='r', ls='--')"),
 ("md", "### Costo en bolivianos de una deuda en dólares\nσ estimada con el TCO diario del BCB desde ago-2026 (excluye el salto jun→jul). El rango depende del régimen y de los supuestos."),
 ("code", "p = sim.fx_params(data.official_points(m, d)); print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in p.items()})\nc = sim.fx_cost_simulation(10_000, 90, p['s0'], 0.0, p['sigma_diario'])\nprint({k: round(v) for k, v in c.items() if k != 'sims'})\nplt.hist(c['sims'], 60); plt.title('Costo en Bs de USD 10.000 a 90 días')"),
 ("md", "### Detección de anomalías: residuos de SARIMA con |z| > 2,5"),
 ("code", "a = fc.full_analysis(m, 'depositos_me', steps=6)['anom']\nprint(a[a.anomalia].tail(8).round(2))\nfig, ax = plt.subplots(figsize=(10, 3)); ax.plot(a.residuo_z, lw=.8); ax.axhline(2.5, c='r', ls='--'); ax.axhline(-2.5, c='r', ls='--'); ax.scatter(a.index[a.anomalia], a.residuo_z[a.anomalia], c='r')"),
])


def build(execute=True):
    ep = ExecutePreprocessor(timeout=900, kernel_name="python3")
    for name, (title, cells) in NB.items():
        nb = nbf.v4.new_notebook()
        nb.cells = [nbf.v4.new_markdown_cell(f"# {title}\n*Proyecto DAT 262 · Monitor de estrés cambiario y monetario de Bolivia*"),
                    nbf.v4.new_code_cell(SETUP)]
        for kind, src in cells:
            nb.cells.append(nbf.v4.new_markdown_cell(src) if kind == "md" else nbf.v4.new_code_cell(src))
        if execute:
            ep.preprocess(nb, {"metadata": {"path": str(HERE)}})
        nbf.write(nb, HERE / f"{name}.ipynb")
        print("OK", name)


if __name__ == "__main__":
    build()
