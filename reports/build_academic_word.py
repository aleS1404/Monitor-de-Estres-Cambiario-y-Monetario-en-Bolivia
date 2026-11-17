"""Genera el informe académico editable en Word desde INFORME_ACADEMICO.md.

Ejecutar desde la raíz: python reports/build_academic_word.py
El texto académico se mantiene en Markdown; este programa lo maqueta, incorpora
las figuras existentes y representa las fórmulas como imágenes de alta resolución.
"""
from __future__ import annotations

import io
import re
from functools import lru_cache
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mistune
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from PIL import Image

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "INFORME_ACADEMICO.md"
OUTPUT = HERE / "INFORME_ACADEMICO.docx"

INK = RGBColor(27, 47, 66)
BLUE = RGBColor(24, 67, 101)
MUTED = RGBColor(88, 104, 118)
PALE = "EFF4F8"
WHITE = RGBColor(255, 255, 255)
INLINE_MATH = re.compile(r"(?<!\$)\$([^$\n]+)\$(?!\$)")

FIGURES = {
    "2.3. Base monetaria, depósitos y bolivianización": [
        ("fig_valoracion.png", "Bolivianización calculada al tipo vigente y a tipo constante; fuente: BCB y cálculos del proyecto.")],
    "2.5. Brecha cambiaria y transmisión de información": [
        ("fig_brecha.png", "Precio P2P, referencia BCB y brecha observada; corte de datos: 13-nov-2026.")],
    "3.1. Fuentes primarias y archivos del proyecto": [
        ("fig_series.png", "Series económicas seleccionadas del BCB.")],
    "5.3. ACF, PACF y dependencia temporal": [
        ("fig_acf_rib.png", "Autocorrelación de variaciones logarítmicas de RIB.")],
    "6.2. Estados, transición y permanencia": [
        ("fig_markov_estados.png", "Índice mensual y estados obtenidos por cuantiles."),
        ("fig_markov_matriz.png", "Matriz de transición mensual estimada de la cadena de tres estados.")],
    "7. Capítulo 4: descomposición y suavizamiento exponencial": [
        ("fig_descomposicion_ipc.png", "Descomposición clásica del IPC.")],
    "8.2. Análisis espectral de reservas": [
        ("fig_espectro_rib.png", "Periodograma de variaciones logarítmicas de RIB.")],
    "9.2. Diagnóstico residual y anomalías": [
        ("fig_anomalias.png", "Anomalías detectadas mediante residuos estandarizados del SARIMA.")],
    "9.3. Validación temporal y H4": [
        ("fig_pronosticos.png", "Pronósticos SARIMA de las cuatro series modeladas.")],
    "10.2. Escenario de reservas": [
        ("fig_montecarlo_rib.png", "Bandas percentilares de las simulaciones de RIB a seis meses.")],
}


def shade(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def cell_margins(cell, top: int = 70, start: int = 70, bottom: int = 70, end: int = 70) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    mar = tc_pr.first_child_found_in("w:tcMar")
    if mar is None:
        mar = OxmlElement("w:tcMar")
        tc_pr.append(mar)
    for side, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = mar.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def no_row_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:cantSplit"))


def add_page_field(paragraph) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar"); begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve"); instr.text = " PAGE "
    sep = OxmlElement("w:fldChar"); sep.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t"); text.text = "1"
    end = OxmlElement("w:fldChar"); end.set(qn("w:fldCharType"), "end")
    for element in (begin, instr, sep, text, end):
        run._r.append(element)


def add_hyperlink(paragraph, label: str, url: str) -> None:
    part = paragraph.part
    rel = part.relate_to(url, RT.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink"); link.set(qn("r:id"), rel)
    run = OxmlElement("w:r")
    props = OxmlElement("w:rPr")
    color = OxmlElement("w:color"); color.set(qn("w:val"), "17668D")
    underline = OxmlElement("w:u"); underline.set(qn("w:val"), "single")
    props.extend((color, underline)); run.append(props)
    txt = OxmlElement("w:t"); txt.text = label; run.append(txt)
    link.append(run); paragraph._p.append(link)


@lru_cache(maxsize=256)
def math_png(formula: str, display: bool) -> tuple[bytes, int, int]:
    """Representa MathText; preserva el contenido LaTeX si falla el render."""
    formula = formula.strip().replace("\\le", "\\leq")
    fig = plt.figure(figsize=(1, 1), dpi=240)
    try:
        fig.text(0, 0, f"${formula}$", fontsize=14 if display else 11.5, color="#1B2F42")
        out = io.BytesIO()
        fig.savefig(out, format="png", dpi=240, bbox_inches="tight", pad_inches=0.07 if display else 0.015,
                    transparent=True)
        data = out.getvalue()
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
        return data, width, height
    finally:
        plt.close(fig)


def add_math(paragraph, formula: str, display: bool = False) -> None:
    try:
        data, width, height = math_png(formula, display)
        max_width_pt = 465 if display else 440
        natural_width_pt = width * 72 / 240
        picture_width_pt = min(max_width_pt, natural_width_pt * (1.12 if display else 1.0))
        paragraph.add_run().add_picture(io.BytesIO(data), width=Pt(picture_width_pt))
    except Exception:
        run = paragraph.add_run(formula)
        run.font.name = "Cambria Math"
        run.font.size = Pt(10.5)


def plain(nodes: list[dict]) -> str:
    result = []
    for node in nodes:
        if node["type"] in {"text", "codespan"}:
            result.append(node.get("raw", ""))
        elif node["type"] in {"softbreak", "linebreak"}:
            result.append(" ")
        elif "children" in node:
            result.append(plain(node["children"]))
    return "".join(result)


def add_text_with_math(paragraph, value: str, *, bold: bool = False, italic: bool = False,
                       code: bool = False) -> None:
    offset = 0
    for match in INLINE_MATH.finditer(value):
        if match.start() > offset:
            run = paragraph.add_run(value[offset:match.start()])
            run.bold = bold; run.italic = italic
            if code:
                run.font.name = "Consolas"; run.font.size = Pt(9)
        add_math(paragraph, match.group(1))
        offset = match.end()
    if offset < len(value):
        run = paragraph.add_run(value[offset:])
        run.bold = bold; run.italic = italic
        if code:
            run.font.name = "Consolas"; run.font.size = Pt(9)


def inline(paragraph, nodes: list[dict], *, bold: bool = False, italic: bool = False) -> None:
    for node in nodes:
        kind = node["type"]
        if kind == "text":
            add_text_with_math(paragraph, node.get("raw", ""), bold=bold, italic=italic)
        elif kind == "codespan":
            add_text_with_math(paragraph, node.get("raw", ""), bold=bold, italic=italic, code=True)
        elif kind == "strong":
            inline(paragraph, node["children"], bold=True, italic=italic)
        elif kind == "emphasis":
            inline(paragraph, node["children"], bold=bold, italic=True)
        elif kind == "link":
            label, url = plain(node["children"]), node["attrs"]["url"]
            if url.startswith(("https://", "http://")):
                add_hyperlink(paragraph, label, url)
            else:
                add_text_with_math(paragraph, label, bold=bold, italic=italic)
        elif kind in {"softbreak", "linebreak"}:
            paragraph.add_run().add_break()
        elif "children" in node:
            inline(paragraph, node["children"], bold=bold, italic=italic)


def is_display_math(node: dict) -> bool:
    children = node.get("children", [])
    return (node["type"] == "paragraph" and len(children) >= 3
            and children[0].get("raw") == "$$" and children[-1].get("raw") == "$$")


def make_table(document: Document, token: dict) -> None:
    head = token["children"][0]["children"]
    body = token["children"][1]["children"]
    cols = len(head)
    table = document.add_table(rows=1, cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for i, item in enumerate(head):
        cell = table.rows[0].cells[i]
        cell.text = plain(item.get("children", []))
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        shade(cell, "184365"); cell_margins(cell)
        for run in cell.paragraphs[0].runs:
            run.bold = True; run.font.color.rgb = WHITE; run.font.size = Pt(8.6)
    header_pr = table.rows[0]._tr.get_or_add_trPr()
    header_pr.append(OxmlElement("w:tblHeader"))
    no_row_split(table.rows[0])
    for number, row in enumerate(body):
        cells = table.add_row().cells
        for i, item in enumerate(row["children"]):
            cell = cells[i]
            cell.text = ""
            inline(cell.paragraphs[0], item.get("children", []))
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            cell_margins(cell)
            for para in cell.paragraphs:
                para.paragraph_format.space_after = Pt(0)
                for run in para.runs:
                    run.font.size = Pt(8.2 if cols >= 5 else 8.8)
            if number % 2:
                shade(cell, PALE)
        no_row_split(table.rows[-1])
    document.add_paragraph().paragraph_format.space_after = Pt(1)


def add_figure(document: Document, filename: str, caption: str, number: int) -> None:
    path = HERE / "figures" / filename
    if not path.exists():
        raise FileNotFoundError(path)
    with Image.open(path) as image:
        w, h = image.size
    max_w, max_h = 6.75, 7.2
    scale = min(max_w / w, max_h / h)
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Inches(w * scale))
    c = document.add_paragraph(style="Caption")
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.add_run(f"Figura {number}. {caption}")


def build() -> Path:
    source = SOURCE.read_text(encoding="utf-8")
    ast = mistune.create_markdown(renderer="ast", plugins=["table", "strikethrough"])(source)
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.27); section.page_height = Inches(11.69)
    section.top_margin = Inches(0.73); section.bottom_margin = Inches(0.67)
    section.left_margin = Inches(0.70); section.right_margin = Inches(0.70)
    section.header_distance = Inches(0.32); section.footer_distance = Inches(0.32)
    section.different_first_page_header_footer = True

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"; normal.font.size = Pt(10.5); normal.font.color.rgb = INK
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.15
    normal.paragraph_format.widow_control = True
    for level, size in ((1, 16), (2, 13), (3, 11.3)):
        style = styles[f"Heading {level}"]
        style.font.name = "Aptos Display"; style.font.size = Pt(size); style.font.bold = True
        style.font.color.rgb = BLUE
        style.paragraph_format.space_before = Pt(14 if level == 1 else 10)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.keep_with_next = True
        if level == 1:
            style.paragraph_format.page_break_before = True
    caption = styles["Caption"]
    caption.font.name = "Aptos"; caption.font.size = Pt(8.5); caption.font.italic = True
    caption.font.color.rgb = MUTED
    caption.paragraph_format.space_after = Pt(10)

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = header.add_run("DAT 262  |  Monitor de estrés cambiario y monetario de Bolivia")
    run.font.size = Pt(8); run.font.color.rgb = MUTED
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = footer.add_run("Informe académico  ·  pág. ")
    run.font.size = Pt(8); run.font.color.rgb = MUTED
    add_page_field(footer)

    # Portada: evita repetir los dos primeros encabezados del Markdown.
    for _ in range(4): doc.add_paragraph()
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("MONITOR DE ESTRÉS\nCAMBIARIO Y MONETARIO\nDE BOLIVIA")
    run.bold = True; run.font.name = "Aptos Display"; run.font.size = Pt(26); run.font.color.rgb = BLUE
    p.paragraph_format.space_after = Pt(22)
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Informe académico integral del proyecto")
    run.font.size = Pt(16); run.font.color.rgb = INK
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Procesos Estocásticos y Series de Tiempo · DAT 262")
    run.font.size = Pt(12); run.font.color.rgb = MUTED
    for _ in range(4): doc.add_paragraph()
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("Fecha de redacción: 17 de noviembre de 2026\n").bold = True
    p.add_run("Corte: Excel BCB hasta octubre de 2026; series diarias al 13 de noviembre de 2026")
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(20)
    r = p.add_run("Trabajo académico descriptivo · No es asesoría financiera")
    r.italic = True; r.font.color.rgb = MUTED
    doc.add_page_break()

    toc = doc.add_heading("Contenido", level=1)
    toc.paragraph_format.page_break_before = False
    for token in ast:
        if token["type"] == "heading" and token["attrs"]["level"] == 2:
            title = plain(token["children"])
            if title != "Informe académico integral del proyecto DAT 262":
                p = doc.add_paragraph(title)
                p.paragraph_format.left_indent = Inches(0.22)
                p.paragraph_format.space_after = Pt(3)
                p.runs[0].font.size = Pt(10.5)
    doc.add_page_break()

    figure_number = 0
    skipped_headings = 0
    for token in ast:
        kind = token["type"]
        if kind == "blank_line":
            continue
        if kind == "heading":
            if skipped_headings < 2:
                skipped_headings += 1
                continue
            text = plain(token["children"])
            level = token["attrs"]["level"]
            doc.add_heading(text, level=max(1, level - 1))
            for file, caption_text in FIGURES.get(text, []):
                figure_number += 1
                add_figure(doc, file, caption_text, figure_number)
        elif kind == "paragraph":
            if is_display_math(token):
                formula = " ".join(child.get("raw", "") for child in token["children"][1:-1]
                                   if child["type"] == "text")
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(3)
                p.paragraph_format.space_after = Pt(7)
                add_math(p, formula, display=True)
            else:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                inline(p, token["children"])
        elif kind == "table":
            make_table(doc, token)
        elif kind == "list":
            ordered = token.get("attrs", {}).get("ordered", False)
            for i, item in enumerate(token["children"], start=1):
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(0.32)
                p.paragraph_format.first_line_indent = Inches(-0.20)
                p.add_run(f"{i}. " if ordered else "• ")
                for child in item.get("children", []):
                    inline(p, child.get("children", []))
        elif kind == "block_quote":
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.24)
            p.paragraph_format.right_indent = Inches(0.24)
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(10)
            for child in token.get("children", []):
                inline(p, child.get("children", []))
            pPr = p._p.get_or_add_pPr()
            shd = OxmlElement("w:shd"); shd.set(qn("w:fill"), PALE); pPr.append(shd)
        elif kind == "block_code":
            for line in token.get("raw", "").strip().splitlines():
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(0.23)
                p.paragraph_format.space_after = Pt(0)
                r = p.add_run(line)
                r.font.name = "Consolas"; r.font.size = Pt(8.3)
                shd = OxmlElement("w:shd"); shd.set(qn("w:fill"), PALE)
                p._p.get_or_add_pPr().append(shd)

    doc.core_properties.title = "Monitor de estrés cambiario y monetario de Bolivia: informe académico integral"
    doc.core_properties.subject = "Proyecto universitario DAT 262 · Procesos Estocásticos y Series de Tiempo"
    doc.core_properties.keywords = "Bolivia, tipo de cambio, series de tiempo, Markov, SARIMA, P2P, Monte Carlo"
    doc.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"Generado: {path}")
