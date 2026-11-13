"""Convierte el Excel 'ancho' del BCB (una fila por variable, una columna por fecha)
a formato largo (tidy), separando frecuencia anual/mensual/semanal/diaria."""
from __future__ import annotations

import datetime as dt
import math
import re
from pathlib import Path

import openpyxl
import pandas as pd

FIRST_DATA_COL = 5           # columna E
HDR_ROW_A, HDR_ROW_B = 3, 4  # fila 3: fecha mensual o "Semana n"; fila 4: fecha semanal/diaria
FIRST_ROW = 6
LABEL_COL, SECTION_COL = 4, 3

# Variables clave: nombre -> (fila en el layout de 2026, regex que debe cumplir la etiqueta).
# Si el BCB mueve filas, validate_layout() avisa y se ajusta aquí.
KEY_VARIABLES: dict[str, tuple[int, str]] = {
    "base_monetaria": (8, r"base monetaria"),
    "ipc": (70, r".*"),
    "inflacion_12m": (73, r".*"),
    "ahorro_mn": (87, r"moneda nacional"),
    "ahorro_me": (89, r"moneda extranjera"),
    "bolivianizacion_ahorro": (90, r"bolivianizaci"),
    "depositos_mn": (92, r"moneda nacional"),
    "depositos_me": (94, r"moneda extranjera"),
    "bolivianizacion_depositos": (95, r"bolivianizaci"),
    "rib": (141, r"reservas internacionales brutas"),
    "rin": (158, r"reservas internacionales netas"),
    "bolsin_sf": (167, r"bols[ií]n - sistema financiero"),
    "ventas_directas_sf": (169, r"ventas directas - sistema financiero"),
    "compras_bcb_sf": (171, r"compras de d[oó]lares"),
    "tc_fijo_bolsin": (177, r"bols[ií]n"),
    "tc_referencial_venta": (180, r"referencial de venta"),
    "tc_oficial": (179, r"tipo de cambio"),
    "tcr": (182, r"tipo de cambio real"),
}


def _clean(s) -> str | None:
    if s is None:
        return None
    return re.sub(r"\s+", " ", str(s)).strip() or None


def classify_column(h3, h4) -> tuple[str | None, dt.datetime | None]:
    """Devuelve (frecuencia, fecha). M=mensual, W=semanal, D=diaria, A=anual (<=1988)."""
    if isinstance(h3, dt.datetime):
        return ("A" if h3.year <= 1988 else "M"), h3
    if isinstance(h3, str) and h3.strip().lower().startswith("semana") and isinstance(h4, dt.datetime):
        return "W", h4
    if h3 is None and isinstance(h4, dt.datetime):
        return "D", h4
    return None, None


def _last_data_row(ws) -> int:
    for r in range(FIRST_ROW + 1, ws.max_row + 1):
        if _clean(ws.cell(r, SECTION_COL).value) in {"*", "a/", "1", "p"}:
            return r - 1
    return min(ws.max_row, 184)


def parse_workbook(path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (largo, catalogo).
    largo: date, freq, row, value, source_file
    catalogo: row, section, label
    """
    path = Path(path)
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    last_row = _last_data_row(ws)

    cat, section = [], None
    for r in range(FIRST_ROW, last_row + 1):
        sec, lab = _clean(ws.cell(r, SECTION_COL).value), _clean(ws.cell(r, LABEL_COL).value)
        if sec and not lab:
            section = sec
            continue
        if lab:
            cat.append({"row": r, "section": section, "label": lab})
    catalog = pd.DataFrame(cat, columns=["row", "section", "label"])
    valid_rows = list(catalog["row"])

    records = []
    for c in range(FIRST_DATA_COL, ws.max_column + 1):
        freq, date = classify_column(ws.cell(HDR_ROW_A, c).value, ws.cell(HDR_ROW_B, c).value)
        if freq is None:
            continue
        for r in valid_rows:
            v = ws.cell(r, c).value
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                continue
            if isinstance(v, float) and math.isnan(v):
                continue
            records.append((date, freq, r, float(v)))
    long = pd.DataFrame(records, columns=["date", "freq", "row", "value"])
    long["date"] = pd.to_datetime(long["date"])
    long["source_file"] = path.name
    wb.close()
    return long.sort_values(["row", "freq", "date"]).reset_index(drop=True), catalog


def validate_layout(catalog: pd.DataFrame) -> list[str]:
    """Avisa si las filas de KEY_VARIABLES ya no coinciden con las etiquetas esperadas."""
    labels = dict(zip(catalog["row"], catalog["label"]))
    issues = []
    for name, (row, rx) in KEY_VARIABLES.items():
        lab = labels.get(row)
        if lab is None:
            issues.append(f"{name}: fila {row} no existe")
        elif not re.search(rx, lab, re.I):
            issues.append(f"{name}: fila {row} tiene '{lab}' (se esperaba /{rx}/)")
    return issues
