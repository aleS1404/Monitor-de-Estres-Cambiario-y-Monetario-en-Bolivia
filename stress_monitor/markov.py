"""Cap. 3: índice de estrés y cadena de Markov de tres estados."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

ESTADOS = ["Estable", "Tensión", "Crisis"]

# Episodios de referencia para validar los estados (definidos por el autor; ver informe)
EPISODIOS = {
    "Bonanza 2006-2013": ("2006-01-31", "2013-12-31"),
    "Caída de reservas 2014-2019": ("2014-01-31", "2019-12-31"),
    "Pandemia 2020": ("2020-01-31", "2020-12-31"),
    "Escasez de dólares 2023-2025": ("2023-01-31", "2025-11-30"),
    "Transición cambiaria dic-2025→may-2026": ("2025-12-31", "2026-05-31"),
    "Régimen flexible jun-2026→": ("2026-06-30", "2100-01-01"),
}


def _z(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std(ddof=0)


def stress_index(m: pd.DataFrame, gap_monthly: pd.Series | None = None) -> pd.DataFrame:
    """Índice = promedio de z-scores de componentes (mayor = más estrés):
       −Δ12 log RIB, −Δ6 bolivianización de depósitos a tipo de cambio constante y, si existe, +brecha (%).
       Estandarización con toda la muestra (descriptiva, no predictiva)."""
    comp = pd.DataFrame(index=m.index)
    comp["reservas"] = -_z(np.log(m["rib"]).diff(12) * 100)
    if "depositos_mn" in m:   # sin efecto de valoración (ver data.bolivianizacion_neutral_change)
        from .data import bolivianizacion_neutral_change
        comp["bolivianizacion"] = -_z(bolivianizacion_neutral_change(m, 6))
    else:
        comp["bolivianizacion"] = -_z(m["bolivianizacion_depositos"].diff(6))
    if gap_monthly is not None and len(gap_monthly.dropna()) >= 12:
        g = gap_monthly.reindex(m.index)
        if g.notna().sum() >= 12:
            comp["brecha"] = _z(g)
    comp["indice"] = comp.mean(axis=1, skipna=True)
    comp.loc[comp.drop(columns="indice").notna().sum(axis=1) < 2, "indice"] = np.nan
    return comp


def classify(idx: pd.Series, q: tuple[float, float] = (0.60, 0.85)) -> pd.Series:
    """Estados por cuantiles del índice: <q1 Estable, q1–q2 Tensión, ≥q2 Crisis."""
    x = idx.dropna()
    t1, t2 = x.quantile(q[0]), x.quantile(q[1])
    s = pd.Series(np.where(x >= t2, 2, np.where(x >= t1, 1, 0)), index=x.index, name="estado")
    s.attrs["umbrales"] = (float(t1), float(t2))
    return s


@dataclass
class MarkovFit:
    counts: np.ndarray
    P: np.ndarray
    stationary: np.ndarray
    sojourn: np.ndarray
    n_trans: int
    present: list[int]


def transition_counts(states: pd.Series, k: int = 3) -> np.ndarray:
    a = states.to_numpy(dtype=int)
    C = np.zeros((k, k), dtype=int)
    for i, j in zip(a[:-1], a[1:]):
        C[i, j] += 1
    return C


def stationary_distribution(P: np.ndarray) -> np.ndarray:
    k = P.shape[0]
    A = np.vstack([P.T - np.eye(k), np.ones(k)])
    b = np.zeros(k + 1); b[-1] = 1
    pi, *_ = np.linalg.lstsq(A, b, rcond=None)
    pi = np.clip(pi, 0, None)
    return pi / pi.sum()


def fit_markov(states: pd.Series, k: int = 3) -> MarkovFit:
    C = transition_counts(states, k)
    rows = C.sum(axis=1)
    P = np.where(rows[:, None] > 0, C / np.maximum(rows[:, None], 1), 0.0)
    for i in range(k):               # fila sin observaciones → estado absorbente (aviso en la UI)
        if rows[i] == 0:
            P[i, i] = 1.0
    with np.errstate(divide="ignore"):
        sojourn = np.where(P.diagonal() < 1, 1 / (1 - P.diagonal()), np.inf)
    return MarkovFit(C, P, stationary_distribution(P), sojourn, int(C.sum()),
                     [i for i in range(k) if rows[i] > 0])


def forecast_state_probs(P: np.ndarray, current: int, horizons=(1, 3, 6)) -> dict[int, np.ndarray]:
    e = np.zeros(P.shape[0]); e[current] = 1
    return {h: e @ np.linalg.matrix_power(P, h) for h in horizons}


def test_independence(C: np.ndarray) -> dict:
    """H0: el estado siguiente es independiente del actual (no hay dependencia de Markov)."""
    keep_r = C.sum(axis=1) > 0
    keep_c = C.sum(axis=0) > 0
    T = C[np.ix_(keep_r, keep_c)]
    if T.shape[0] < 2 or T.shape[1] < 2:
        return {"chi2": np.nan, "gl": 0, "p_valor": np.nan, "nota": "tabla degenerada"}
    chi2, p, dof, _ = stats.chi2_contingency(T, correction=False)
    return {"chi2": float(chi2), "gl": int(dof), "p_valor": float(p), "nota": ""}


def test_second_order(states: pd.Series, k: int = 3) -> dict:
    """H0: la cadena es de orden 1 frente a orden 2 (razón de verosimilitud, por estado intermedio)."""
    a = states.to_numpy(dtype=int)
    N = np.zeros((k, k, k))
    for i, j, l in zip(a[:-2], a[1:-1], a[2:]):
        N[i, j, l] += 1
    lr, dof = 0.0, 0
    for j in range(k):
        T = N[:, j, :]
        T = T[np.ix_(T.sum(axis=1) > 0, T.sum(axis=0) > 0)]
        if T.shape[0] < 2 or T.shape[1] < 2:
            continue
        g, _, d, _ = stats.chi2_contingency(T, correction=False, lambda_="log-likelihood")
        lr += g; dof += d
    p = float(stats.chi2.sf(lr, dof)) if dof > 0 else np.nan
    return {"lr": float(lr), "gl": int(dof), "p_valor": p}


def episode_table(states: pd.Series) -> pd.DataFrame:
    rows = []
    for name, (a, b) in EPISODIOS.items():
        s = states[(states.index >= a) & (states.index <= b)]
        if s.empty:
            continue
        sh = s.value_counts(normalize=True).reindex(range(3), fill_value=0)
        rows.append({"episodio": name, "meses": len(s), **{ESTADOS[i]: float(sh[i]) for i in range(3)}})
    return pd.DataFrame(rows)


def compare_periods(states: pd.Series, split: str = "2023-01-31") -> dict:
    pre, post = states[states.index < split], states[states.index >= split]
    out = {}
    for name, s in (("antes", pre), ("después", post)):
        if len(s) < 3:
            out[name] = {"n": len(s), "aviso": "muestra insuficiente"}
            continue
        f = fit_markov(s)
        out[name] = {"n": len(s), "P": f.P, "estacionaria": f.stationary, "permanencia": f.sojourn,
                     "aviso": "pocas observaciones (<30)" if len(s) < 30 else ""}
    return out


def robustness(idx: pd.Series, grids=((0.50, 0.80), (0.60, 0.85), (0.667, 0.90), (0.70, 0.95))) -> pd.DataFrame:
    rows = []
    for q in grids:
        f = fit_markov(classify(idx, q))
        rows.append({"q_tensión": q[0], "q_crisis": q[1],
                     **{f"π {ESTADOS[i]}": f.stationary[i] for i in range(3)},
                     **{f"permanencia {ESTADOS[i]}": f.sojourn[i] for i in range(3)},
                     "P(Estable→Estable)": f.P[0, 0], "P(Crisis→Crisis)": f.P[2, 2]})
    return pd.DataFrame(rows)
