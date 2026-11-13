"""Importa la 'Tabla de precios de activos virtuales' del BCB (PDF) a SQLite.

Formato verificado (HISTORICO.pdf, 2024): cada fila es
  FECHA  TETHER_compra  TETHER_venta  BITCOIN  ETHEREUM
  17/10/2024 10,40 10,62 67.372,26 2.603,70
Tether (Bs/USDT) = promedio ponderado por volumen del comercio diario en P2P (nota del BCB).
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pandas as pd

from .collector import DEFAULT_DB, connect

ROW_RE = re.compile(
    r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s*$", re.M)


def _num(s: str) -> float:
    s = s.strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return float(s)


def parse_text(text: str) -> pd.DataFrame:
    rows = []
    for d, m, y, c, v, btc, eth in ROW_RE.findall(text):
        rows.append({"date": pd.Timestamp(int(y), int(m), int(d)),
                     "usdt_compra": _num(c), "usdt_venta": _num(v),
                     "btc_usd": _num(btc), "eth_usd": _num(eth)})
    df = pd.DataFrame(rows, columns=["date", "usdt_compra", "usdt_venta", "btc_usd", "eth_usd"])
    return df.drop_duplicates("date").sort_values("date").reset_index(drop=True)


def read_pdf_text(path: Path) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except ImportError:
        return subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True,
                              text=True, check=True).stdout


def import_pdfs(paths: list[Path], db_path: Path = DEFAULT_DB) -> int:
    total = 0
    with connect(db_path) as con:
        for p in paths:
            df = parse_text(read_pdf_text(Path(p)))
            if df.empty:
                print(f"! {p}: no se encontraron filas con el formato esperado")
                continue
            for r in df.itertuples():
                con.execute("INSERT OR REPLACE INTO bcb_usdt VALUES (?,?,?,?,?,?)",
                            (r.date.strftime("%Y-%m-%d"), r.usdt_compra, r.usdt_venta,
                             r.btc_usd, r.eth_usd, Path(p).name))
            print(f"{Path(p).name}: {len(df)} filas ({df.date.min().date()} -> {df.date.max().date()})")
            total += len(df)
    return total
