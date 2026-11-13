"""Descarga de los Excel de 'Estadísticas Semanales' del Banco Central de Bolivia.

Idea clave: cada archivo semanal contiene TODA la historia mensual (desde 1987)
más las semanas/días recientes. Para la serie mensual basta el archivo más
reciente; para armar series semanales/diarias largas hay que juntar varios archivos.
"""
from __future__ import annotations

import re
import time
import urllib.parse as up
from dataclasses import dataclass
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://www.bcb.gob.bo"
LIST_URL = BASE + "/?q=estad-sticas-semanales"
HEADERS = {"User-Agent": "Mozilla/5.0 (proyecto-academico-series-tiempo )"}

LINK_RE = re.compile(r"""href=["']([^"']*05_estadisticassemanales/[^"']+?\.xlsx)["']""", re.I)
NAME_RE = re.compile(r"Semanal\s*0*(\d{1,2})_(\d{4})", re.I)


@dataclass(frozen=True)
class RemoteFile:
    year: int
    week: int
    url: str

    @property
    def filename(self) -> str:
        return f"Semanal_{self.year}_{self.week:02d}.xlsx"


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    retry = Retry(total=4, backoff_factor=1.5, status_forcelist=(429, 500, 502, 503, 504))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s


def extract_links(html: str) -> list[RemoteFile]:
    """Extrae (año, semana, url) de una página del listado. Orden = orden en la página."""
    out: list[RemoteFile] = []
    for href in LINK_RE.findall(html):
        full = up.urljoin(BASE + "/", href)
        decoded = up.unquote(full)
        m = NAME_RE.search(decoded.rsplit("/", 1)[-1])
        if not m:
            continue
        safe_url = up.quote(decoded, safe=":/")
        out.append(RemoteFile(year=int(m.group(2)), week=int(m.group(1)), url=safe_url))
    return out


def list_remote(session: requests.Session, max_pages: int = 120, since_year: int | None = None,
                delay: float = 1.0) -> list[RemoteFile]:
    """Recorre el listado paginado (más nuevo primero). Si dos archivos comparten
    semana/año (p. ej. 'Semanal 45_2026 (1).xlsx'), se conserva el primero listado."""
    seen: dict[tuple[int, int], RemoteFile] = {}
    for page in range(max_pages):
        url = LIST_URL if page == 0 else f"{LIST_URL}&page={page}"
        r = session.get(url, timeout=60)
        r.raise_for_status()
        links = extract_links(r.text)
        if not links:
            break
        for f in links:
            seen.setdefault((f.year, f.week), f)
        if since_year is not None and max(f.year for f in links) < since_year:
            break
        time.sleep(delay)
    files = sorted(seen.values(), key=lambda f: (f.year, f.week), reverse=True)
    if since_year is not None:
        files = [f for f in files if f.year >= since_year]
    return files


def download_file(session: requests.Session, f: RemoteFile, raw_dir: Path, force: bool = False) -> Path | None:
    dest = raw_dir / f.filename
    if dest.exists() and not force:
        return None
    r = session.get(f.url, timeout=120)
    r.raise_for_status()
    if not r.content.startswith(b"PK") or len(r.content) < 10_000:
        raise ValueError(f"{f.url} no parece un .xlsx válido ({len(r.content)} bytes)")
    tmp = dest.with_suffix(".tmp")
    tmp.write_bytes(r.content)
    tmp.replace(dest)
    return dest


def run_download(raw_dir: Path, mode: str = "latest", since_year: int | None = None,
                 force: bool = False, delay: float = 1.5) -> list[Path]:
    """mode: 'latest' (solo el más reciente), 'since' (desde since_year) o 'all'."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    s = make_session()
    if mode == "latest":
        files = list_remote(s, max_pages=1)[:1]
    elif mode == "since":
        files = list_remote(s, since_year=since_year, delay=delay)
    else:
        files = list_remote(s, delay=delay)
    print(f"{len(files)} archivo(s) en el listado")
    new: list[Path] = []
    for f in files:
        try:
            p = download_file(s, f, raw_dir, force=force)
        except Exception as e:  # noqa: BLE001 - seguimos con el resto
            print(f"  ! {f.filename}: {e}")
            continue
        if p:
            print(f"  + {p.name}")
            new.append(p)
            time.sleep(delay)
    print(f"Descargados: {len(new)} | ya existentes: {len(files) - len(new)}")
    return new
