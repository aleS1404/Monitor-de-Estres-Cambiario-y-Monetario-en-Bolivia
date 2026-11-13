"""Cap. 7: movimiento browniano geométrico y simulación Monte Carlo."""
from __future__ import annotations

import numpy as np
import pandas as pd


def gbm_paths(s0: float, mu: float, sigma: float, steps: int, n_paths: int = 10_000,
              seed: int | None = 42) -> np.ndarray:
    """Trayectorias S_t = S_0 exp((μ − σ²/2)t + σ W_t) con μ, σ por paso. Devuelve (n_paths, steps+1)."""
    rng = np.random.default_rng(seed)
    z = rng.standard_normal((n_paths, steps))
    inc = (mu - 0.5 * sigma ** 2) + sigma * z
    logs = np.concatenate([np.zeros((n_paths, 1)), np.cumsum(inc, axis=1)], axis=1)
    return s0 * np.exp(logs)


def estimate_gbm(s: pd.Series, window: int | None = 36) -> dict:
    """μ y σ por período a partir de log-retornos (ventana final opcional)."""
    r = np.log(s.dropna()).diff().dropna()
    if window:
        r = r.iloc[-window:]
    return {"mu": float(r.mean()), "sigma": float(r.std(ddof=1)), "n": int(len(r))}


def fan(paths: np.ndarray, qs=(5, 25, 50, 75, 95)) -> pd.DataFrame:
    return pd.DataFrame({f"p{q}": np.percentile(paths, q, axis=0) for q in qs})


def reserves_simulation(rib: pd.Series, horizon: int = 6, threshold: float = 3000.0,
                        window: int = 36, n_paths: int = 10_000, seed: int = 42,
                        sigma_mult: float = 1.0) -> dict:
    """Monte Carlo de reservas (MM USD): P(terminal < umbral) y P(cruzar el umbral en algún mes)."""
    p = estimate_gbm(rib, window)
    paths = gbm_paths(float(rib.dropna().iloc[-1]), p["mu"], p["sigma"] * sigma_mult, horizon, n_paths, seed)
    return {"params": p, "paths": paths, "fan": fan(paths),
            "p_terminal": float((paths[:, -1] < threshold).mean()),
            "p_cruce": float((paths.min(axis=1) < threshold).mean()),
            "umbral": threshold, "s0": float(rib.dropna().iloc[-1])}


def fx_params(series: pd.Series) -> dict:
    """Deriva (μ, σ) DIARIOS desde observaciones posiblemente irregulares (diarias/semanales/mensuales):
       σ² = Σ r² / Σ Δt ; μ = Σ r / Σ Δt."""
    s = series.dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    if len(s) < 3:
        return {"ok": False, "n": len(s)}
    r = np.log(s).diff().dropna()
    dt = pd.Series(s.index, index=s.index).diff().dt.days.loc[r.index].astype(float)
    dt = dt.replace(0, np.nan).dropna()
    r = r.loc[dt.index]
    sigma = float(np.sqrt((r ** 2).sum() / dt.sum()))
    mu = float(r.sum() / dt.sum())
    return {"ok": True, "n": int(len(r)), "mu_diario": mu, "sigma_diario": sigma,
            "sigma_anual": sigma * np.sqrt(365), "s0": float(s.iloc[-1]), "fecha": s.index[-1]}


def fx_cost_simulation(usd: float, horizon_days: int, s0: float, mu_daily: float, sigma_daily: float,
                       n_paths: int = 20_000, seed: int = 7) -> dict:
    """Distribución del costo en Bs de `usd` dólares dentro de `horizon_days` días."""
    paths = gbm_paths(s0, mu_daily, sigma_daily, horizon_days, n_paths, seed)
    term = paths[:, -1] * usd
    return {"hoy": s0 * usd, "p5": float(np.percentile(term, 5)), "p50": float(np.percentile(term, 50)),
            "p95": float(np.percentile(term, 95)), "media": float(term.mean()),
            "sims": term, "var95_extra": float(np.percentile(term, 95) - s0 * usd)}
