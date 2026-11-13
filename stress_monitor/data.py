"""Carga de datos procesados, series derivadas y brecha oficial-paralelo."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
P2P_DB = ROOT / "data" / "p2p" / "p2p.sqlite"

# Fechas de régimen cambiario (verificadas en el Excel del BCB y la prensa)
FECHA_REFERENCIAL = pd.Timestamp("2025-12-01")   # aparece el "valor referencial" de venta
FECHA_FLEXIBLE = pd.Timestamp("2026-06-29")      # el BCB publica cotización oficial diaria
TC_FIJO = 6.96                                    # Bs/USD, fijo desde 2011

NOMBRES = {
    "rib": "Reservas internacionales brutas (MM USD)",
    "rin": "Reservas internacionales netas (MM USD)",
    "depositos_me": "Depósitos en moneda extranjera (MM USD)",
    "ahorro_me": "Ahorro en moneda extranjera (MM USD)",
    "base_monetaria": "Base monetaria (MM Bs)",
    "ipc": "IPC (2016=100)",
    "inflacion_12m": "Inflación a 12 meses (%)",
    "bolivianizacion_depositos": "Bolivianización de depósitos (%)",
    "bolivianizacion_ahorro": "Bolivianización del ahorro (%)",
    "tc_oficial": "Tipo de cambio oficial (Bs/USD)",
    "tcr": "Tipo de cambio real (dic-2022=100)",
}


def load_monthly(path: Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or PROCESSED / "monthly_key.csv", parse_dates=["date"], index_col="date")
    df.index = pd.DatetimeIndex(df.index).normalize()
    return df.sort_index()


def load_daily_key(path: Path | None = None) -> pd.DataFrame:
    p = path or PROCESSED / "daily_key.csv"
    if not Path(p).exists():
        return pd.DataFrame()
    return pd.read_csv(p, parse_dates=["date"])


def data_status(m: pd.DataFrame) -> dict:
    return {"ultimo_mes": m.index.max(), "n_meses": len(m), "primer_mes": m.index.min()}


def regimen(date: pd.Timestamp) -> str:
    if date >= FECHA_FLEXIBLE:
        return "flexible"
    if date >= FECHA_REFERENCIAL:
        return "referencial"
    return "fijo"


def tc_efectivo(m: pd.DataFrame) -> pd.Series:
    """Tipo de cambio de referencia mensual: oficial flexible > referencial > fijo (Bolsín)."""
    s = m["tc_oficial"].copy()
    for alt in ("tc_referencial_venta", "tc_fijo_bolsin"):
        if alt in m:
            s = s.fillna(m[alt])
    return s.dropna().rename("tc_efectivo")


def official_daily(m: pd.DataFrame, d: pd.DataFrame | None = None,
                   collector: pd.DataFrame | None = None) -> pd.Series:
    """Serie diaria del tipo de cambio de referencia (venta), por relleno hacia adelante."""
    pts = tc_efectivo(m)
    if d is not None and len(d) and "tc_oficial" in d:
        extra = d.dropna(subset=["tc_oficial"]).set_index("date")["tc_oficial"]
        pts = pd.concat([pts, extra]).groupby(level=0).last()
    if collector is not None and len(collector) and "of_venta" in collector:
        pts = pd.concat([pts, collector["of_venta"].dropna()]).groupby(level=0).last()
    pts = pts.sort_index()
    idx = pd.date_range(pts.index.min(), pts.index.max(), freq="D")
    return pts.reindex(idx).ffill().rename("oficial")


P2P_CSV = ROOT / "data" / "p2p" / "quotes.csv"


def load_p2p(db_path: Path | None = None, csv_path: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (collector_diario, bcb_pdf_diario) leyendo SQLite y/o CSV. Vacíos si no hay datos."""
    db_path, csv_path = Path(db_path or P2P_DB), Path(csv_path or P2P_CSV)
    empty = pd.DataFrame()
    q, b = empty, empty
    if db_path.exists():
        con = sqlite3.connect(db_path)
        try:
            q = pd.read_sql("SELECT * FROM quotes", con)
            b = pd.read_sql("SELECT * FROM bcb_usdt", con, parse_dates=["date"])
        except Exception:  # noqa: BLE001
            q, b = empty, empty
        finally:
            con.close()
    if csv_path.exists():
        c = pd.read_csv(csv_path)
        q = pd.concat([q, c], ignore_index=True) if len(q) else c
    if len(q):
        q = q.drop_duplicates("ts_utc", keep="last")
        q["ts_utc"] = pd.to_datetime(q["ts_utc"], utc=True, errors="coerce")
        q = q.dropna(subset=["ts_utc"])
        q["date"] = q["ts_utc"].dt.tz_convert("America/La_Paz").dt.tz_localize(None).dt.normalize()
        q = q.groupby("date")[["p2p_compra", "p2p_venta", "of_compra", "of_venta"]].mean()
    if len(b):
        b = b.set_index("date").sort_index()
    return (q if len(q) else empty), (b if len(b) else empty)


def build_gap(m: pd.DataFrame, d: pd.DataFrame | None, collector: pd.DataFrame,
              bcb_pdf: pd.DataFrame) -> pd.DataFrame:
    """Brecha diaria = USDT venta / oficial de referencia − 1 (en %).
    Prioridad de fuente para el USDT: recolector propio > PDF del BCB."""
    par = pd.Series(dtype=float, name="paralelo")
    if len(bcb_pdf):
        par = bcb_pdf["usdt_venta"].rename("paralelo")
    if len(collector) and "p2p_venta" in collector:
        par = pd.concat([par, collector["p2p_venta"].dropna()]).groupby(level=0).last().rename("paralelo")
    if par.empty:
        return pd.DataFrame(columns=["paralelo", "oficial", "brecha_pct"])
    of = official_daily(m, d, collector if len(collector) else None)
    df = pd.concat([par, of], axis=1, sort=True).dropna()
    df["brecha_pct"] = (df["paralelo"] / df["oficial"] - 1) * 100
    return df


def official_points(m: pd.DataFrame, d: pd.DataFrame | None = None, since: str = "2026-08-01") -> pd.Series:
    """Observaciones (irregulares) del tipo de cambio OFICIAL flexible desde `since`.
    Por defecto excluye el salto de transición jun→jul-2026 (9,76→12,15), que no es volatilidad recurrente."""
    pts = m["tc_oficial"].dropna() if "tc_oficial" in m else pd.Series(dtype=float)
    if d is not None and len(d) and "tc_oficial" in d:
        extra = d.dropna(subset=["tc_oficial"]).set_index("date")["tc_oficial"]
        pts = pd.concat([pts, extra]).groupby(level=0).last()
    pts = pts.sort_index()
    return pts[pts.index >= since].rename("oficial")


def tc_conversion(m: pd.DataFrame) -> pd.Series:
    """Tipo de cambio con el que el BCB convierte saldos en Bs a USD en sus cuadros:
    6,96 (Bolsín) hasta may-2026 y el oficial flexible desde jun-2026. El 'referencial' NO se usa
    (verificado: el saldo en MN en USD no cae en dic-2025→may-2026)."""
    return m["tc_oficial"].fillna(m["tc_fijo_bolsin"]).rename("tc_conversion")


def bolivianizacion_neutral_change(m: pd.DataFrame, lag: int = 6) -> pd.Series:
    """Cambio (pp) de la bolivianización de depósitos en `lag` meses, SIN efecto de valoración:
    ambos saldos se valoran al tipo de cambio del inicio de la ventana."""
    tc = tc_conversion(m).to_numpy()
    mn_bs = (m["depositos_mn"] * tc_conversion(m)).to_numpy()
    me = m["depositos_me"].to_numpy()
    out = np.full(len(m), np.nan)
    for i in range(lag, len(m)):
        e0 = tc[i - lag]
        r_now = mn_bs[i] / (mn_bs[i] + me[i] * e0)
        r_then = mn_bs[i - lag] / (mn_bs[i - lag] + me[i - lag] * e0)
        out[i] = 100 * (r_now - r_then)
    return pd.Series(out, index=m.index, name="boliv_cambio_neutral")


def bolivianizacion_tc_fijo(m: pd.DataFrame, tc_ref: float = TC_FIJO) -> pd.Series:
    """Bolivianización de depósitos a tipo de cambio constante (por defecto 6,96). Solo comparable desde 2012."""
    mn_bs = m["depositos_mn"] * tc_conversion(m)
    return (100 * mn_bs / (mn_bs + m["depositos_me"] * tc_ref)).rename("boliv_tc_fijo")


def bolivianizacion_tc_vigente(m: pd.DataFrame) -> pd.Series:
    """MN/(MN+ME) con los saldos de los cuadros (MN convertida al TC vigente). Difiere de la cifra oficial
    (fila 95 del Excel), que usa otra definición (hasta ~4 pp en 2023-24); aquí se usa para comparar
    con la versión a tipo de cambio constante SIN mezclar definiciones."""
    return (100 * m["depositos_mn"] / (m["depositos_mn"] + m["depositos_me"])).rename("boliv_tc_vigente")
