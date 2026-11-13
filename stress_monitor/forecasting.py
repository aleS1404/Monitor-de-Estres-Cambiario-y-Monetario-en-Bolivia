"""Cap. 4 (descomposición, suavizamiento exponencial) y cap. 6 (Box-Jenkins, SARIMA)."""
from __future__ import annotations

import itertools
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.stats.stattools import jarque_bera
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.statespace.sarimax import SARIMAX

from .stationarity import adf

warnings.filterwarnings("ignore")
SEASONAL_VARS = ["rib", "ipc", "depositos_me", "base_monetaria"]
WINDOW_START = "2005-01-01"
BURN_IN = 24   # residuos iniciales del filtro de Kalman (inicialización difusa) se descartan


# ---------- Cap. 4 ----------
def decompose(s: pd.Series, model: str = "multiplicative", period: int = 12):
    s = s.dropna()
    try:
        return seasonal_decompose(s, model=model, period=period, extrapolate_trend="period")
    except (ValueError, TypeError):   # statsmodels < 0.15
        return seasonal_decompose(s, model=model, period=period, extrapolate_trend="freq")


def seasonal_strength(s: pd.Series, period: int = 12) -> float:
    """Fs = max(0, 1 − Var(resto)/Var(estacional+resto)) sobre la serie en log-diferencias de tendencia."""
    d = decompose(np.log(s.dropna()), model="additive", period=period)
    r, sea = d.resid.dropna(), d.seasonal.loc[d.resid.dropna().index]
    return float(max(0.0, 1 - r.var() / (sea + r).var()))


def holt_winters_forecast(y: pd.Series, steps: int = 6, period: int = 12) -> pd.Series:
    m = ExponentialSmoothing(y, trend="add", damped_trend=True, seasonal="add",
                             seasonal_periods=period, initialization_method="estimated").fit()
    return m.forecast(steps)


# ---------- Cap. 6 ----------
def log_series(m: pd.DataFrame, col: str, start: str = WINDOW_START) -> pd.Series:
    s = m[col].dropna()
    s = s[s.index >= start]
    s = np.log(s)
    s.index = pd.DatetimeIndex(s.index)
    return s.asfreq("ME")


def choose_d(y: pd.Series, max_d: int = 1) -> int:
    """d≤1 por defecto: ADF tiene poca potencia con quiebres estructurales y d=2 sobrediferencia."""
    d, z = 0, y
    while d < max_d and not adf(z)["estacionaria_5%"]:
        z = z.diff().dropna(); d += 1
    return d


def choose_D(y: pd.Series, period: int = 12) -> int:
    return 1 if seasonal_strength(np.exp(y), period) > 0.64 else 0


@dataclass
class SarimaSpec:
    order: tuple[int, int, int]
    seasonal_order: tuple[int, int, int, int]
    aic: float


def fit_sarima(y: pd.Series, order, seasonal_order):
    mod = SARIMAX(y, order=order, seasonal_order=seasonal_order,
                  enforce_stationarity=False, enforce_invertibility=False)
    return mod.fit(disp=False, maxiter=200)


def select_sarima(y: pd.Series, period: int = 12, max_p: int = 2, max_q: int = 2) -> SarimaSpec:
    """Identificación Box-Jenkins semiautomática: d y D por pruebas, (p,q,P,Q) por AIC."""
    d, D = choose_d(y), choose_D(y, period)
    best = None
    for p, q, P, Q in itertools.product(range(max_p + 1), range(max_q + 1), (0, 1), (0, 1)):
        if p + q + P + Q == 0 and d + D == 0:
            continue
        try:
            r = fit_sarima(y, (p, d, q), (P, D, Q, period))
        except Exception:  # noqa: BLE001
            continue
        if np.isfinite(r.aic) and (best is None or r.aic < best.aic):
            best = SarimaSpec((p, d, q), (P, D, Q, period), float(r.aic))
    if best is None:
        raise RuntimeError("No se pudo ajustar ningún SARIMA")
    return best


def forecast_log(res, steps: int, alpha: float = 0.05) -> pd.DataFrame:
    f = res.get_forecast(steps)
    ci = f.conf_int(alpha=alpha)
    out = pd.DataFrame({"media": f.predicted_mean, "inf": ci.iloc[:, 0], "sup": ci.iloc[:, 1]})
    return np.exp(out)


def diagnostics(res, spec: SarimaSpec, lags=(12, 24)) -> dict:
    e = pd.Series(res.resid).iloc[BURN_IN:]
    k = spec.order[0] + spec.order[2] + spec.seasonal_order[0] + spec.seasonal_order[2]
    out = {"n_resid": len(e), "media_resid": float(e.mean()), "sd_resid": float(e.std())}
    for L in lags:
        lb = acorr_ljungbox(e, lags=[L], model_df=k)
        out[f"ljung_box_p_{L}"] = float(lb["lb_pvalue"].iloc[0])
    jb, p, skew, kurt = jarque_bera(e)
    out.update({"jarque_bera_p": float(p), "asimetria": float(skew), "curtosis": float(kurt)})
    out["residuos_blancos_5%"] = bool(out["ljung_box_p_12"] > 0.05 and out["ljung_box_p_24"] > 0.05)
    return out


def anomalies(res, spec: SarimaSpec, z: float = 2.5) -> pd.DataFrame:
    """Residuos estandarizados fuera de ±z desviaciones (alerta temprana, cap. 7)."""
    e = pd.Series(res.resid).iloc[BURN_IN:]
    zz = (e - e.mean()) / e.std()
    out = pd.DataFrame({"residuo_z": zz, "anomalia": zz.abs() > z})
    return out


def rolling_validation(y: pd.Series, spec: SarimaSpec, n_origins: int = 24, horizons=(1, 3, 6),
                       period: int = 12) -> pd.DataFrame:
    """Validación con ventana móvil (origen creciente): SARIMA vs ingenuo vs Holt-Winters.
    Errores en escala original (exp del log). Devuelve MAPE, RMSE y cobertura del IC95 de SARIMA."""
    H = max(horizons)
    n = len(y)
    origins = list(range(n - H - n_origins, n - H))
    recs = []
    for t in origins:
        train = y.iloc[: t + 1]
        try:
            res = fit_sarima(train, spec.order, spec.seasonal_order)
            f = res.get_forecast(H)
            mean, ci = f.predicted_mean, f.conf_int(alpha=0.05)
            hw = holt_winters_forecast(train, H, period)
        except Exception:  # noqa: BLE001
            continue
        for h in horizons:
            actual = np.exp(y.iloc[t + h])
            naive = np.exp(train.iloc[-1])
            recs.append({"h": h, "real": actual,
                         "sarima": float(np.exp(mean.iloc[h - 1])),
                         "ingenuo": float(naive),
                         "holt_winters": float(np.exp(hw.iloc[h - 1])),
                         "cubre": bool(np.exp(ci.iloc[h - 1, 0]) <= actual <= np.exp(ci.iloc[h - 1, 1]))})
    d = pd.DataFrame(recs)
    if d.empty:
        return d
    rows = []
    for h, g in d.groupby("h"):
        for mod in ("sarima", "ingenuo", "holt_winters"):
            err = g[mod] - g["real"]
            rows.append({"h": h, "modelo": mod, "MAPE_%": float((err.abs() / g["real"]).mean() * 100),
                         "RMSE": float(np.sqrt((err ** 2).mean())), "n": len(g),
                         "cobertura_IC95": float(g["cubre"].mean()) if mod == "sarima" else np.nan})
    return pd.DataFrame(rows)


def full_analysis(m: pd.DataFrame, col: str, steps: int = 12, validate: bool = False,
                  start: str = WINDOW_START) -> dict:
    y = log_series(m, col, start)
    spec = select_sarima(y)
    res = fit_sarima(y, spec.order, spec.seasonal_order)
    out = {"col": col, "y": y, "spec": spec, "res": res,
           "forecast": forecast_log(res, steps), "diag": diagnostics(res, spec),
           "anom": anomalies(res, spec)}
    if validate:
        out["validation"] = rolling_validation(y, spec)
    return out
