from __future__ import annotations

import argparse
from pathlib import Path

from .build import build
from .collector import DEFAULT_DB, collect_loop, collect_once, export_csv
from .virtual_assets import import_pdfs
from .download import run_download
from .parse import parse_workbook, validate_layout


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="bcb_pipeline", description=__doc__)
    ap.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    ap.add_argument("--out-dir", type=Path, default=Path("data/processed"))
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("download", help="Descargar Excel del BCB")
    g = d.add_mutually_exclusive_group()
    g.add_argument("--latest", action="store_true", help="solo el más reciente (default)")
    g.add_argument("--since-year", type=int, help="todos desde ese año")
    g.add_argument("--all", action="store_true", help="todo el historial (~1000 archivos)")
    d.add_argument("--force", action="store_true")
    d.add_argument("--delay", type=float, default=1.5, help="segundos entre descargas")

    b = sub.add_parser("build", help="Procesar los Excel ya descargados")
    b.add_argument("--keep-vintages", action="store_true")

    u = sub.add_parser("update", help="download + build (para correr cada semana)")
    u.add_argument("--since-year", type=int, default=None)
    u.add_argument("--keep-vintages", action="store_true")

    c = sub.add_parser("check-layout", help="Verificar que un Excel conserva el formato esperado")
    c.add_argument("file", type=Path)

    k = sub.add_parser("collect", help="Guardar cotización P2P/oficial (DolarApi) en SQLite")
    k.add_argument("--loop", action="store_true", help="repetir indefinidamente")
    k.add_argument("--every", type=int, default=3600, help="segundos entre consultas (con --loop)")
    k.add_argument("--db", type=Path, default=DEFAULT_DB)
    k.add_argument("--csv", type=Path, default=None, help="además (o en vez de SQLite) acumular en este CSV")
    k.add_argument("--csv-only", action="store_true", help="no usar SQLite (para GitHub Actions)")

    e = sub.add_parser("export-p2p", help="Exportar la tabla de cotizaciones a CSV")
    e.add_argument("--db", type=Path, default=DEFAULT_DB)

    v = sub.add_parser("import-pdf", help="Importar PDF(s) de 'activos virtuales' del BCB")
    v.add_argument("pdfs", type=Path, nargs="+")
    v.add_argument("--db", type=Path, default=DEFAULT_DB)

    a = ap.parse_args(argv)
    if a.cmd == "download":
        mode, yr = ("all", None) if a.all else (("since", a.since_year) if a.since_year else ("latest", None))
        run_download(a.raw_dir, mode, yr, a.force, a.delay)
    elif a.cmd == "build":
        build(a.raw_dir, a.out_dir, a.keep_vintages)
    elif a.cmd == "update":
        if a.since_year:
            run_download(a.raw_dir, "since", a.since_year)
        else:
            run_download(a.raw_dir, "latest")
        build(a.raw_dir, a.out_dir, a.keep_vintages)
    elif a.cmd == "collect":
        db = None if a.csv_only else a.db
        collect_loop(a.db, a.every) if a.loop else collect_once(db, a.csv)
    elif a.cmd == "export-p2p":
        print(export_csv(a.db))
    elif a.cmd == "import-pdf":
        import_pdfs(a.pdfs, a.db)
    elif a.cmd == "check-layout":
        _, cat = parse_workbook(a.file)
        issues = validate_layout(cat)
        print("Layout OK" if not issues else "\n".join(issues))


if __name__ == "__main__":
    main()
