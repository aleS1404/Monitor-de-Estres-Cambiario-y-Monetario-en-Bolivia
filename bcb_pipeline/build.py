"""Une todos los Excel descargados en tablas listas para modelar."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .parse import KEY_VARIABLES, parse_workbook, validate_layout

FILE_RE = re.compile(r"Semanal_(\d{4})_(\d{2})\.xlsx$")


def _sorted_files(raw_dir: Path) -> list[Path]:
    items = []
    for p in raw_dir.glob("Semanal_*.xlsx"):
        m = FILE_RE.search(p.name)
        if m:
            items.append(((int(m.group(1)), int(m.group(2))), p))
    return [p for _, p in sorted(items)]


def build(raw_dir: Path, out_dir: Path, keep_vintages: bool = False) -> dict[str, Path]:
    """Genera en out_dir:
      catalog.csv            filas/etiquetas del archivo más reciente
      monthly_long.csv       historia anual+mensual (del archivo MÁS RECIENTE)
      weekly_daily_long.csv  semanas y días de todos los archivos (última versión de cada dato)
      monthly_key.csv        variables clave en formato ancho (fecha x variable)
      daily_key.csv          variables clave diarias/semanales (ancho)
      vintages.csv.gz        (opcional) todas las versiones, para estudiar revisiones
    """
    files = _sorted_files(raw_dir)
    if not files:
        raise FileNotFoundError(f"No hay archivos Semanal_*.xlsx en {raw_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    latest = files[-1]
    long_latest, catalog = parse_workbook(latest)
    for issue in validate_layout(catalog):
        print(f"  ! layout: {issue}")

    monthly = long_latest[long_latest["freq"].isin(["A", "M"])].copy()

    wd_parts = []
    for p in files:
        try:
            lg, _ = parse_workbook(p) if p != latest else (long_latest, None)
        except Exception as e:  # noqa: BLE001
            print(f"  ! no se pudo leer {p.name}: {e}")
            continue
        wd = lg[lg["freq"].isin(["W", "D"])].copy()
        wd["vintage"] = p.name
        wd_parts.append(wd)
    wd_all = pd.concat(wd_parts, ignore_index=True) if wd_parts else pd.DataFrame()
    if len(wd_all):
        wd_last = (wd_all.sort_values("vintage")
                   .drop_duplicates(["row", "freq", "date"], keep="last")
                   .drop(columns="vintage"))
    else:
        wd_last = wd_all

    prev_path = out_dir / "weekly_daily_long.csv"
    if prev_path.exists() and len(wd_last):      # acumula entre ejecuciones (CI no conserva los Excel crudos)
        prev = pd.read_csv(prev_path, parse_dates=["date"])
        wd_last = (pd.concat([prev, wd_last], ignore_index=True)
                   .drop_duplicates(["row", "freq", "date"], keep="last")
                   .sort_values(["row", "freq", "date"]).reset_index(drop=True))

    paths = {}
    catalog.to_csv(paths.setdefault("catalog", out_dir / "catalog.csv"), index=False)
    monthly.to_csv(paths.setdefault("monthly_long", out_dir / "monthly_long.csv"), index=False)
    wd_last.to_csv(paths.setdefault("weekly_daily_long", out_dir / "weekly_daily_long.csv"), index=False)

    rows = {name: r for name, (r, _) in KEY_VARIABLES.items()}
    inv = {r: n for n, r in rows.items()}
    mk = monthly[monthly["row"].isin(inv)].assign(var=lambda d: d["row"].map(inv))
    mk = mk[mk["freq"] == "M"].pivot(index="date", columns="var", values="value").sort_index()
    mk.to_csv(paths.setdefault("monthly_key", out_dir / "monthly_key.csv"))

    if len(wd_last):
        dk = wd_last[wd_last["row"].isin(inv)].assign(var=lambda d: d["row"].map(inv))
        dk = dk.pivot_table(index=["freq", "date"], columns="var", values="value").sort_index()
        dk.to_csv(paths.setdefault("daily_key", out_dir / "daily_key.csv"))

    if keep_vintages and len(wd_all):
        wd_all.to_csv(paths.setdefault("vintages", out_dir / "vintages.csv.gz"), index=False)

    print(f"Archivos usados: {len(files)} (más reciente: {latest.name})")
    print(f"Mensual: {mk.index.min().date()} -> {mk.index.max().date()} | filas weekly/daily: {len(wd_last)}")
    return paths
