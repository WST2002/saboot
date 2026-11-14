"""Build report/saboot-final.docx (or <source>.docx) on the official Apart template from report/saboot-final.md.

Keeps the template's styles, title block (title, author table, "With Apart Research",
abstract box, sprint footnote) and section headings; removes the guidance text and the
info box; writes our headings, paragraphs, real Word tables and figures in the
template's own fonts. PDF export is done separately in Word.

Source markup (report/saboot-final.md):
  # Title            -> template title
  AUTHOR: name | affiliation | email
  ABSTRACT: text     -> abstract box
  ## / ###           -> Heading 2 / Heading 3
  plain line         -> body paragraph (**bold**, *italic*)
  - item / 1. item   -> bullet / numbered paragraph
  TABLE: caption, then | a | b | rows (first row = header)
  FIGURE: path | width in inches | caption
  ```...```          -> monospace block
  PAGEBREAK
Usage: python -I -X utf8 scripts/build_paper_docx.py [report/<source>.md]  (writes report/<source>.docx)"""
import copy
import os
import re
import sys

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "apart-submission-template.docx")
SOURCE = os.path.join(ROOT, "report", "saboot-final.md")
OUT = os.path.join(ROOT, "report", "saboot-final.docx")
SERIF = "Old Standard TT"
DEVANAGARI = "Nirmala UI"
TEXT_WIDTH = 6.5
BODY_PT = 10
INLINE = re.compile(r"(\*\*.+?\*\*|\*.+?\*)")
# Devanagari text gets its own runs so the Latin text after it keeps the serif font in Word
DEVANAGARI_RUN = re.compile(r"([ऀ-ॿ]+(?:\s+[ऀ-ॿ]+)*)")


def set_fonts(run, name=SERIF, size=None, mono=False):
    rpr = run._r.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    face = "Consolas" if mono else name
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia"):
        fonts.set(qn(attr), face)
    fonts.set(qn("w:cs"), DEVANAGARI)
    if size:
        run.font.size = Pt(size)
        run.font.complex_script = False
        szcs = OxmlElement("w:szCs")
        szcs.set(qn("w:val"), str(int(size * 2)))
        rpr.append(szcs)


def add_runs(par, text, size=None, bold=False, italic=False):
    for part in INLINE.split(text):
        if not part:
            continue
        b, i = bold, italic
        if part.startswith("**") and part.endswith("**"):
            part, b = part[2:-2], True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            part, i = part[1:-1], True
        for piece in DEVANAGARI_RUN.split(part):
            if not piece:
                continue
            run = par.add_run(piece)
            run.bold, run.italic = b or None, i or None
            set_fonts(run, size=size)
            if DEVANAGARI_RUN.fullmatch(piece):
                run.font.complex_script = True


def clear_runs(par):
    for child in list(par._p):
        if child.tag != qn("w:pPr"):
            par._p.remove(child)


def spacing(par, before=0, after=6, line=1.1):
    pf = par.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(before), Pt(after), line


class Builder:
    def __init__(self):
        self.doc = docx.Document(TEMPLATE)
        body = self.doc.element.body
        heads = [p for p in self.doc.paragraphs if p.style.name == "Heading 2"]
        h3 = [p for p in self.doc.paragraphs if p.style.name == "Heading 3"]
        self.h2_proto = copy.deepcopy(heads[0]._p)
        self.h3_proto = copy.deepcopy(h3[0]._p)
        self.body_proto = copy.deepcopy(self.doc.paragraphs[3]._p)
        # drop the info box and every guidance paragraph after the title block
        title_tbl = self.doc.tables[0]._tbl
        keep = {title_tbl, body.find(qn("w:sectPr"))}
        started = False
        for el in list(body):
            if el is title_tbl:
                started = True
                continue
            if started and el not in keep:
                body.remove(el)
        self.body = body
        self.sect = body.find(qn("w:sectPr"))

    def _insert(self, el):
        self.sect.addprevious(el)
        return el

    def _from_proto(self, proto, text, size=None, bold=None):
        p = self._insert(copy.deepcopy(proto))
        for bm in p.findall(qn("w:bookmarkStart")) + p.findall(qn("w:bookmarkEnd")):
            p.remove(bm)
        par = docx.text.paragraph.Paragraph(p, self.doc._body)
        clear_runs(par)
        add_runs(par, text, size=size, bold=bool(bold))
        return par

    def title(self, text):
        cell = self.doc.tables[0].rows[0].cells[0]
        par = next(p for p in cell.paragraphs if p.style.name == "Title")
        runs = par.runs
        runs[0].text = text
        runs[0].font.size = Pt(17)
        for r in runs[1:]:
            if not r._r.findall(qn("w:footnoteReference")):
                r.text = ""

    def authors(self, name, affiliation, email):
        cell = self.doc.tables[0].rows[1].cells[0]
        outer = cell._tc.find(qn("w:tbl"))
        inner_cell = outer.find(qn("w:tr")).find(qn("w:tc"))
        authors_tbl = inner_cell.find(qn("w:tbl"))
        with_p = next(p for p in inner_cell.findall(qn("w:p")) if "Apart" in "".join(t.text for t in p.iter(qn("w:t"))))
        new = copy.deepcopy(with_p)
        authors_tbl.addprevious(new)
        inner_cell.remove(authors_tbl)
        par = docx.text.paragraph.Paragraph(new, None)
        clear_runs(par)
        r = par.add_run(name)
        r.bold = True
        set_fonts(r)
        for line in (affiliation, email):
            r = par.add_run()
            r.add_break(WD_BREAK.LINE)
            r = par.add_run(line)
            set_fonts(r)

    def abstract(self, text):
        box = self.doc.tables[0].rows[1].cells[0].tables[-1]
        par = box.rows[0].cells[0].paragraphs[0]
        clear_runs(par)
        add_runs(par, text, size=10)
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    def h2(self, text):
        self._from_proto(self.h2_proto, text, size=14, bold=True)

    def h3(self, text):
        par = self._from_proto(self.h3_proto, text, size=11.5, bold=True)
        spacing(par, before=8, after=3)
        par.paragraph_format.keep_with_next = True

    def para(self, text, size=BODY_PT, indent=None, after=4, align_justify=True):
        par = self._from_proto(self.body_proto, text, size=size)
        spacing(par, after=after)
        if indent is not None:
            par.paragraph_format.left_indent = Inches(indent[0])
            par.paragraph_format.first_line_indent = Inches(indent[1])
        if align_justify:
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        return par

    def bullet(self, text, marker="•"):
        return self.para(f"{marker}\t{text}", indent=(0.3, -0.2), after=2, align_justify=False)

    def code(self, lines):
        for i, line in enumerate(lines):
            par = self._from_proto(self.body_proto, "")
            spacing(par, after=0, line=1.0)
            run = par.add_run(line)
            set_fonts(run, size=8, mono=True)
            par.paragraph_format.left_indent = Inches(0.2)
        spacing(par, after=6, line=1.0)

    def caption(self, text):
        par = self.para(text, size=9, after=4)
        return par

    def table(self, caption, rows):
        cap = self.caption(caption)
        cap.paragraph_format.keep_with_next = True
        ncol = len(rows[0])
        t = self.doc.add_table(rows=len(rows), cols=ncol)
        self._insert(t._tbl)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        tblpr = t._tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "bottom", "insideH"):
            b = OxmlElement(f"w:{edge}")
            b.set(qn("w:val"), "single")
            b.set(qn("w:sz"), "6" if edge == "insideH" else "10")
            b.set(qn("w:color"), "BFBFBF" if edge == "insideH" else "000000")
            borders.append(b)
        tblpr.append(borders)
        width = OxmlElement("w:tblW")
        width.set(qn("w:w"), str(int(TEXT_WIDTH * 1440)))
        width.set(qn("w:type"), "dxa")
        tblpr.append(width)
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        tblpr.append(layout)
        weights = [min(max(max(len(r[c]) for r in rows[1:]), int(len(r0) * 1.3), 6), 20) for c, r0 in enumerate(rows[0])]
        col_w = [TEXT_WIDTH * w / sum(weights) for w in weights]
        for c, w in enumerate(col_w):
            t.columns[c].width = Inches(w)
        size = 8 if ncol >= 7 else 8.5
        for ri, row in enumerate(rows):
            tr = t.rows[ri]
            trpr = tr._tr.get_or_add_trPr()
            cant = OxmlElement("w:cantSplit")
            trpr.append(cant)
            if ri == 0:
                hdr = OxmlElement("w:tblHeader")
                trpr.append(hdr)
            for ci, val in enumerate(row):
                cell = tr.cells[ci]
                cell.width = Inches(col_w[ci])
                par = cell.paragraphs[0]
                add_runs(par, val, size=size, bold=ri == 0)
                spacing(par, after=0, line=1.0)
                numeric = ci > 0 and re.match(r"^[+\-]?[\d,.%() /\-CI]+$", val.strip() or "x")
                par.alignment = WD_ALIGN_PARAGRAPH.RIGHT if numeric and ri > 0 else WD_ALIGN_PARAGRAPH.LEFT
                if ri < len(rows) - 1:
                    par.paragraph_format.keep_with_next = True
                tcpr = cell._tc.get_or_add_tcPr()
                mar = OxmlElement("w:tcMar")
                for side, w in (("top", "30"), ("left", "50"), ("bottom", "30"), ("right", "50")):
                    m = OxmlElement(f"w:{side}")
                    m.set(qn("w:w"), w)
                    m.set(qn("w:type"), "dxa")
                    mar.append(m)
                tcpr.append(mar)
        self.para("", size=4, after=2)

    def figure(self, path, width, caption):
        par = self._from_proto(self.body_proto, "")
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.keep_with_next = True
        spacing(par, before=4, after=2, line=1.0)
        par.add_run().add_picture(os.path.join(ROOT, path), width=Inches(width))
        self.caption(caption)

    def pagebreak(self):
        par = self._from_proto(self.body_proto, "")
        par.add_run().add_break(WD_BREAK.PAGE)


def build(source=SOURCE, out=OUT):
    b = Builder()
    with open(source, encoding="utf-8") as f:
        lines = f.read().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            i += 1
            continue
        if line.startswith("# "):
            b.title(line[2:])
        elif line.startswith("AUTHOR:"):
            b.authors(*[x.strip() for x in line[7:].split("|")])
        elif line.startswith("ABSTRACT:"):
            b.abstract(line[9:].strip())
        elif line.startswith("### "):
            b.h3(line[4:])
        elif line.startswith("## "):
            b.h2(line[3:])
        elif line.startswith("TABLE:"):
            cap, rows = line[6:].strip(), []
            while i + 1 < len(lines) and lines[i + 1].startswith("|"):
                i += 1
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.match(r"^:?-+:?$", c) for c in cells):
                    rows.append(cells)
            b.table(cap, rows)
        elif line.startswith("FIGURE:"):
            path, width, cap = [x.strip() for x in line[7:].split("|", 2)]
            b.figure(path, float(width), cap)
        elif line.startswith("```"):
            block = []
            i += 1
            while not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            b.code(block)
        elif line == "PAGEBREAK":
            b.pagebreak()
        elif line.startswith("- "):
            b.bullet(line[2:])
        elif re.match(r"^\d+\. ", line):
            n, rest = line.split(" ", 1)
            b.bullet(rest, marker=n)
        else:
            b.para(line)
        i += 1
    b.doc.save(out)
    print(f"wrote {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    src = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else SOURCE
    build(src, os.path.splitext(src)[0] + ".docx")
