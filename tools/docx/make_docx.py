#!/usr/bin/env python3
"""LaTeX skripsi -> Word (.docx) mengikuti Template Format Penulisan Skripsi V.2024.10.

Langkah:
  1. Pra-proses bab/*.tex: nomor bab/sub bab, rujukan, caption "Tabel x.y"/"Gambar x.y",
     gambar TikZ dirender ke PNG 300 dpi, tabel, persamaan, Keterangan, Source Code.
  2. pandoc LaTeX -> JSON (AST), sisipkan daftar pustaka di bawah judul DAFTAR PUSTAKA,
     lalu JSON -> DOCX dengan citeproc (APA 7th).
  3. python-docx: gaya (TNR 12, spasi 1,5, indentasi 1 cm, margin 3/3/2,5/2,5),
     tabel (header abu-abu 25 %, ulang header), bagian awal (sampul s.d. abstract),
     daftar isi/tabel/gambar otomatis, nomor halaman romawi lalu arab di kanan bawah.

Pakai:  cd tex && make && python3 ../tools/docx/make_docx.py
Keluaran: tex/skripsi.docx
"""
import copy, json, os, re, subprocess, sys
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.abspath(os.path.join(HERE, '..', '..', 'tex'))
BUILD = os.path.join(TEX, 'docx-build')
FIG = os.path.join(BUILD, 'fig')
os.makedirs(FIG, exist_ok=True)
OUT = os.path.join(TEX, 'skripsi.docx')

def rd(p): return open(os.path.join(TEX, p), encoding='utf-8').read()

# ------------------------------------------------------------------ data
main = rd('skripsi.tex')
def meta(cmd):
    m = re.search(r'\\%s\{(.*?)\}(?:\{(.*?)\})?%%?' % cmd, main)
    return m.group(1) if m else ''
JUDUL_TEX = re.search(r'\\judul\{(.*)\}\n', main).group(1)
PENULIS = meta('penulis'); NIM = meta('nim')
PB1 = re.search(r'\\pembimbingsatu\{(.*?)\}\{(.*?)\}', main).groups()
PB2 = re.search(r'\\pembimbingdua\{(.*?)\}\{(.*?)\}', main).groups()
TANGGAL = meta('tanggalpernyataan')
JUDUL = re.sub(r'\\textit\{(.*?)\}', r'\1', JUDUL_TEX)

labels = {}
for m in re.finditer(r'\\newlabel\{([^}]+)\}\{\{([^}]*)\}', rd('skripsi.aux')):
    labels.setdefault(m.group(1), m.group(2))

def balanced(t, i):
    d = 0
    for j in range(i, len(t)):
        if t[j] == '{': d += 1
        elif t[j] == '}':
            d -= 1
            if d == 0: return j + 1
    raise ValueError('unbalanced')

def strip_comments(t):
    return re.sub(r'(?<!\\)%.*', '', t)

WGR = r'\textit{Process-Aware Workflow} GraphRAG'
def macros(t):
    t = t.replace(r'\wgr{}', WGR).replace(r'\wgr', WGR)
    t = t.replace(r'\eoffice{}', 'E-Office')
    t = re.sub(r'\\code\{', r'\\texttt{', t)
    t = re.sub(r'Persamaan~\\ref\{([^}]+)\}', lambda m: 'Persamaan ' + labels[m.group(1)], t)
    t = re.sub(r'\\ref\{([^}]+)\}', lambda m: labels[m.group(1)], t)
    t = t.replace('~', ' ')
    return t

# ------------------------------------------------------------------ figures
FIGPRE = r"""\documentclass[12pt,border=2pt]{standalone}
\usepackage{fontspec}
\IfFontExistsTF{Times New Roman}{\setmainfont{Times New Roman}}{\setmainfont{TeX Gyre Termes}}
\IfFontExistsTF{Courier New}{\setmonofont{Courier New}}{\setmonofont{TeX Gyre Cursor}}
\usepackage{amsmath,amssymb}\usepackage{unicode-math}\setmathfont{STIXTwoMath-Regular.otf}
\usepackage{setspace}\usepackage[table]{xcolor}\usepackage{tikz}
\usetikzlibrary{positioning,arrows.meta,fit,backgrounds,shapes.geometric,shapes.misc,calc}
""" + "\n".join(r"\definecolor{g%d}{gray}{%.3f}" % (n, 1 - n / 100 * 0.5) for n in [6, 8, 10, 15, 20, 25, 55, 60]) + r"""
\newlength{\figlw}\setlength{\figlw}{15.5cm}
\begin{document}
"""

def render_fig(name, tikz):
    tikz = tikz.replace(r'\linewidth', r'\figlw')
    base = os.path.join(FIG, name)
    open(base + '.tex', 'w').write(FIGPRE + tikz + '\n\\end{document}\n')
    if not os.path.exists(base + '.pdf') or os.path.getmtime(base + '.pdf') < os.path.getmtime(base + '.tex'):
        r = subprocess.run(['xelatex', '-interaction=nonstopmode', '-output-directory', FIG, base + '.tex'],
                           capture_output=True, text=True)
        if not os.path.exists(base + '.pdf'):
            sys.exit('render gagal: ' + name + '\n' + r.stdout[-2000:])
        subprocess.run(['pdftoppm', '-r', '300', '-png', '-singlefile', base + '.pdf', base], check=True)
    w = float(re.search(r'Page size:\s+([\d.]+)', subprocess.run(['pdfinfo', base + '.pdf'],
              capture_output=True, text=True).stdout).group(1))
    return base + '.png', min(w / 72 * 2.54, 15.5)

def fig_sub(m):
    body = m.group(1)
    lab = re.search(r'\\label\{([^}]+)\}', body).group(1)
    k = body.index(r'\caption{'); cap = body[k + 9:balanced(body, k + 8) - 1]
    tikz = re.search(r'\\begin\{tikzpicture\}.*\\end\{tikzpicture\}', body, re.S).group(0)
    png, wcm = render_fig(lab.replace(':', '_'), tikz)
    return '\n\\begin{figure}\n\\includegraphics[width=%.2fcm]{%s}\n\\caption{Gambar %s %s}\n\\end{figure}\n' % (
        wcm, png, labels[lab], cap)

# ------------------------------------------------------------------ tables
TABLE_WIDTHS = []      # per tabel: daftar lebar kolom (cm) atau None
def colspec(spec):
    toks = re.findall(r'[LCp]\{([^}]*)\}|([lcrY])', spec.replace('|', ''))
    ws = []
    for a, b in toks:
        if a: ws.append(float(a.replace('cm', '')) if 'cm' in a else None)
        else: ws.append(None)
    return ws

def table_sub(m):
    body = m.group(1)
    lab = re.search(r'\\label\{([^}]+)\}', body).group(1)
    k = body.index(r'\caption{'); cap = body[k + 9:balanced(body, k + 8) - 1]
    tm = re.search(r'\\begin\{(tabularx|tabular)\}(\{\\linewidth\})?\{', body)
    a = tm.end() - 1; b = balanced(body, a)
    spec = body[a + 1:b - 1]
    end = body.index(r'\end{%s}' % tm.group(1))
    rows = body[b:end]
    ws = colspec(spec); TABLE_WIDTHS.append(ws)
    rows = re.sub(r'\\(hdr|hrow|hline)\b', '', rows)
    rows = rows.replace(r'\x', '§')
    rows = re.sub(r'\\multicolumn\{(\d)\}\{[^}]*\}', r'\\multicolumn{\1}{l}', rows)
    return ('\n\\begin{table}\n\\caption{Tabel %s %s}\n\\begin{tabular}{%s}\n%s\n\\end{tabular}\n\\end{table}\n'
            % (labels[lab], cap, 'l' * len(ws), rows.strip()))

# ------------------------------------------------------------------ others
EQN = {}
def eq_sub(m):
    inner = m.group(1)
    lab = re.search(r'\\label\{([^}]+)\}', inner).group(1)
    inner = re.sub(r'\\label\{[^}]+\}', '', inner).strip()
    return '\n\\[\n%s\n\\]\n\nEQNUM@@%s\n\n' % (inner, labels[lab])

def ket_sub(m):
    rows = [r.strip() for r in m.group(1).split('\\\\') if r.strip()]
    out = ['KETERANGAN@@']
    for r in rows:
        s, d = r.split('&', 1)
        out.append('KET@@ %s @@ %s' % (s.strip(), d.strip()))
    return '\n\n' + '\n\n'.join(out) + '\n\n'

def src_sub(m):
    title, lab, code = m.group(1), m.group(2), m.group(3)
    return '\n\nSRC@@Source Code %s:@@%s\n\n\\begin{verbatim}\n%s\n\\end{verbatim}\n\nSRCEND@@\n\n' % (
        labels[lab], title, code.strip('\n'))

ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI']
def number_headings(t, ch):
    c = [ch, 0, 0, 0]
    out = []
    for line in t.split('\n'):
        mm = re.match(r'\\(chapter|section|subsection|subsubsection)\{(.*)\}\s*$', line)
        if mm:
            lvl = ['chapter', 'section', 'subsection', 'subsubsection'].index(mm.group(1))
            title = mm.group(2)
            if lvl == 0:
                line = r'\chapter*{BAB %s@@%s}' % (ROMAN[ch], title.upper())
            else:
                c[lvl] += 1
                for j in range(lvl + 1, 4): c[j] = 0
                num = '.'.join(str(x) for x in c[:lvl + 1])
                line = '\\%s*{%s %s}' % (mm.group(1), num, title)
        out.append(line)
    return '\n'.join(out)

def prep_chapter(path, ch):
    t = strip_comments(rd(path))
    t = re.sub(r'\\label\{[^}]+\}', lambda m: m.group(0), t)
    t = macros(t)
    t = re.sub(r'\\begin\{figure\}\[[^\]]*\](.*?)\\end\{figure\}', fig_sub, t, flags=re.S)
    t = re.sub(r'\\begin\{table\}\[[^\]]*\](.*?)\\end\{table\}', table_sub, t, flags=re.S)
    t = re.sub(r'\\begin\{equation\}(.*?)\\end\{equation\}', eq_sub, t, flags=re.S)
    t = re.sub(r'\\begin\{keterangan\}(.*?)\\end\{keterangan\}', ket_sub, t, flags=re.S)
    t = re.sub(r'\\begin\{sourcecode\}\{(.*?)\}\{(.*?)\}\n(.*?)\\end\{sourcecode\}', src_sub, t, flags=re.S)
    t = re.sub(r'\\label\{[^}]+\}', '', t)
    t = number_headings(t, ch)
    return t

body = ''
for i in range(1, 6):
    body += prep_chapter('bab/bab%d.tex' % i, i) + '\n'
body += '\n\\chapter*{DAFTAR PUSTAKA}\n\nREFS@@\n\n'
lamp = strip_comments(rd('bab/lampiran.tex'))
n = [0]
def lamp_sub(m):
    n[0] += 1
    return r'\chapter*{LAMPIRAN %d. %s}' % (n[0], m.group(1).upper())
body += re.sub(r'\\lampiran\{(.*?)\}', lamp_sub, macros(lamp))
open(os.path.join(BUILD, 'body.tex'), 'w', encoding='utf-8').write(
    '\\documentclass{report}\n\\begin{document}\n' + body + '\n\\end{document}\n')

# ------------------------------------------------------------------ pandoc
ast = json.loads(subprocess.run(['pandoc', '-f', 'latex', '-t', 'json', os.path.join(BUILD, 'body.tex')],
                                capture_output=True, text=True, check=True).stdout)
blocks = ast['blocks']
for i, b in enumerate(blocks):
    if b['t'] == 'Para' and len(b['c']) == 1 and b['c'][0].get('c') == 'REFS@@':
        blocks[i] = {'t': 'Div', 'c': [['refs', [], []], []]}
ast['meta']['link-citations'] = {'t': 'MetaBool', 'c': False}
open(os.path.join(BUILD, 'body.json'), 'w').write(json.dumps(ast))
mid = os.path.join(BUILD, 'body.docx')
subprocess.run(['pandoc', '-f', 'json', '-t', 'docx', '--citeproc',
                '--bibliography', os.path.join(TEX, 'references.bib'),
                '--csl', os.path.join(HERE, 'apa.csl'),
                '-M', 'lang=id-ID', '-o', mid, os.path.join(BUILD, 'body.json')], check=True)

# ================================================================== python-docx
doc = Document(mid)
W = lambda tag: qn('w:' + tag)

def set_font(style, size=12, bold=None, italic=None, color=True):
    f = style.font; f.name = 'Times New Roman'; f.size = Pt(size)
    if bold is not None: f.bold = bold
    if italic is not None: f.italic = italic
    if color: f.color.rgb = RGBColor(0, 0, 0)
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(W('rFonts'))
    if rf is None: rf = OxmlElement('w:rFonts'); rpr.insert(0, rf)
    for a in ('ascii', 'hAnsi', 'cs', 'eastAsia'): rf.set(W(a), 'Times New Roman')
    for a in ('asciiTheme', 'hAnsiTheme', 'cstheme', 'eastAsiaTheme'):
        if rf.get(W(a)) is not None: del rf.attrib[W(a)]

def para_fmt(pf, indent=True, before=0, after=0, align=WD_ALIGN_PARAGRAPH.JUSTIFY, spacing=1.5):
    pf.space_before = Pt(before); pf.space_after = Pt(after)
    pf.line_spacing = spacing
    pf.first_line_indent = Cm(1) if indent else Cm(0)
    pf.left_indent = Cm(0)
    pf.alignment = align

st0 = doc.styles
class _St:
    def __getitem__(self, k):
        for s in st0:
            if s.name == k or s.name.lower() == k.lower() or s.style_id == k.replace(' ', ''): return s
        raise KeyError(k)
    def __iter__(self): return iter(st0)
    def add_style(self, *a): return st0.add_style(*a)
st = _St()
for name in ['Normal', 'Body Text', 'First Paragraph', 'Compact']:
    if any(s.name.lower() == name.lower() or s.style_id == name.replace(' ', '') for s in st0):
        set_font(st[name]); para_fmt(st[name].paragraph_format, indent=name != 'Compact')
for name, lvl in [('Heading 1', 1), ('Heading 2', 2), ('Heading 3', 3), ('Heading 4', 4)]:
    s = st[name]; set_font(s, 14 if lvl == 1 else 12, bold=True, italic=False)
    para_fmt(s.paragraph_format, indent=False, before=0 if lvl == 1 else 12,
             align=WD_ALIGN_PARAGRAPH.CENTER if lvl == 1 else WD_ALIGN_PARAGRAPH.LEFT)
    s.paragraph_format.keep_with_next = True
    s.paragraph_format.page_break_before = lvl == 1
    if lvl == 1: s.paragraph_format.space_after = Pt(20.7)
for name in ['Table Caption', 'Image Caption', 'Captioned Figure']:
    if any(s.name.lower() == name.lower() or s.style_id == name.replace(' ', '') for s in st0):
        set_font(st[name], italic=False)
        para_fmt(st[name].paragraph_format, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
if any(s.style_id == 'Bibliography' for s in st0):
    s = st['Bibliography']; set_font(s)
    para_fmt(s.paragraph_format, indent=False, align=WD_ALIGN_PARAGRAPH.LEFT)
    s.paragraph_format.left_indent = Cm(1.27); s.paragraph_format.first_line_indent = Cm(-1.27)
for name in ['Source Code', 'Verbatim Char']:
    if any(s.name.lower() == name.lower() or s.style_id == name.replace(' ', '') for s in st0):
        set_font(st[name], 10)
        rf = st[name].element.get_or_add_rPr().find(W('rFonts'))
        for a in ('ascii', 'hAnsi', 'cs'): rf.set(W(a), 'Courier New')
for s_ in st0:
    if s_.style_id == 'Hyperlink': s_.font.color.rgb = RGBColor(0, 0, 0); s_.font.underline = False
# Caption khusus untuk daftar tabel / daftar gambar
from docx.enum.style import WD_STYLE_TYPE
for nm in ['Caption Tabel', 'Caption Gambar']:
    s = st.add_style(nm, WD_STYLE_TYPE.PARAGRAPH); s.base_style = st['Normal']
    set_font(s); para_fmt(s.paragraph_format, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    s.paragraph_format.keep_with_next = nm == 'Caption Tabel'

body_el = doc.element.body
paras = list(doc.paragraphs)

def text(p): return ''.join(r.text for r in p.runs) if p.runs else p.text

# ---- judul bab: "BAB I" baris 1, judul baris 2
for p in paras:
    if p.style.style_id == 'Heading1' and '@@' in p.text:
        a, b = p.text.split('@@', 1)
        for r in p.runs[1:]: r._r.getparent().remove(r._r)
        p.runs[0].text = a
        p.runs[0].add_break()
        p.add_run(b)
    if p.style.style_id == 'Heading1':
        for r in p.runs: r.font.bold = True; r.font.size = Pt(14)

# ---- caption
for p in doc.paragraphs:
    if p.style.style_id == 'TableCaption':
        p.style = st['Caption Tabel']
    elif p.style.style_id == 'ImageCaption':
        p.style = st['Caption Gambar']
for p in doc.paragraphs:  # gambar di tengah, tanpa indentasi
    if p._p.xpath('.//w:drawing'):
        p.paragraph_format.first_line_indent = Cm(0); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True

# ---- persamaan rata kiri
for mp in body_el.iter(qn('m:oMathPara')):
    ppr = mp.find(qn('m:oMathParaPr'))
    if ppr is None: ppr = OxmlElement('m:oMathParaPr'); mp.insert(0, ppr)
    jc = OxmlElement('m:jc'); jc.set(qn('m:val'), 'left'); ppr.append(jc)
    par = mp.getparent()
    if par.tag == W('p'):
        pPr = par.find(W('pPr'))
        if pPr is None: pPr = OxmlElement('w:pPr'); par.insert(0, pPr)
        ind = OxmlElement('w:ind'); ind.set(W('left'), '567'); ind.set(W('firstLine'), '0'); pPr.append(ind)

# ---- tabel
def cell_shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement('w:shd'); sh.set(W('val'), 'clear'); sh.set(W('color'), 'auto'); sh.set(W('fill'), fill)
    tcPr.append(sh)

def borders(tbl, on=True):
    tblPr = tbl._tbl.tblPr
    for old in tblPr.findall(W('tblBorders')): tblPr.remove(old)
    b = OxmlElement('w:tblBorders')
    for e in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        x = OxmlElement('w:' + e)
        x.set(W('val'), 'single' if on else 'nil'); x.set(W('sz'), '4'); x.set(W('space'), '0'); x.set(W('color'), 'auto')
        b.append(x)
    tblPr.append(b)

def cell_paras(tbl, size=11, spacing=1.0):
    for row in tbl.rows:
        for c in row.cells:
            for p in c.paragraphs:
                pf = p.paragraph_format; pf.first_line_indent = Cm(0); pf.line_spacing = spacing
                pf.space_before = Pt(1); pf.space_after = Pt(1)
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for r in p.runs: r.font.size = Pt(size); r.font.name = r.font.name or 'Times New Roman'

def set_widths(tbl, ws_cm):
    grid = tbl._tbl.tblGrid
    for gc, w in zip(grid.findall(W('gridCol')), ws_cm): gc.set(W('w'), str(int(w * 567)))
    for row in tbl.rows:
        for c, w in zip(row.cells, ws_cm): c.width = Cm(w)
    tblPr = tbl._tbl.tblPr
    for old in tblPr.findall(W('tblW')): tblPr.remove(old)
    tw = OxmlElement('w:tblW'); tw.set(W('w'), str(int(sum(ws_cm) * 567))); tw.set(W('type'), 'dxa'); tblPr.append(tw)
    lay = OxmlElement('w:tblLayout'); lay.set(W('type'), 'fixed'); tblPr.append(lay)

TEXTW = 15.5
ti = 0
for tbl in doc.tables:
    ws = TABLE_WIDTHS[ti] if ti < len(TABLE_WIDTHS) else None; ti += 1
    borders(tbl, True); cell_paras(tbl)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = tbl.rows[0]
    trPr = hdr._tr.get_or_add_trPr()
    th = OxmlElement('w:tblHeader'); trPr.append(th)
    h = OxmlElement('w:trHeight'); h.set(W('val'), '567'); h.set(W('hRule'), 'atLeast'); trPr.append(h)
    for c in hdr.cells:
        cell_shade(c, 'BFBFBF')
        for p in c.paragraphs:
            for r in p.runs: r.font.bold = True
    for row in tbl.rows[1:]:
        for c in row.cells:
            if c.text.strip() == '§':
                cell_shade(c, '8C8C8C')
                for p in c.paragraphs:
                    for r in p.runs: r.text = ''
    if ws:
        ws = [max(w, 1.0) if (w and k == 0) else w for k, w in enumerate(ws)]  # kolom No min. 1 cm
        free = [k for k, w in enumerate(ws) if w is None]
        fixed = sum(w for w in ws if w)
        if free:
            # bobot kolom bebas menurut panjang isi terpanjang
            lens = []
            for k in free:
                mx = max((len(r.cells[k].text) for r in tbl.rows), default=4)
                lens.append(max(mx, 4))
            avail = max(TEXTW - fixed, 1.5 * len(free))
            full = list(ws)
            if len(free) == len(ws):  # semua kolom bebas: lebar menurut isi
                for k in free:
                    mx = max((len(r.cells[k].text) for r in tbl.rows), default=4)
                    full[k] = 1.0 if k == 0 else max(1.8, min(0.21 * mx + 0.5, 9.0))
                tot = sum(full)
                if tot > TEXTW: full = [w * TEXTW / tot for w in full]
            else:
                tot = sum(lens) or 1
                for k, l in zip(free, lens):
                    full[k] = avail * l / tot
        else:
            full = ws
        if len(full) == len(tbl.columns): set_widths(tbl, full)

# ---- Keterangan -> tabel tanpa garis
def new_table_after(p, rows, cols):
    t = doc.add_table(rows=rows, cols=cols)
    p._p.addnext(t._tbl)
    return t

def runs_copy(src_p, dst_p, part_text=None):
    for r in src_p._p.xpath('./w:r|./m:oMath'):
        dst_p._p.append(copy.deepcopy(r))

i = 0
plist = list(doc.paragraphs)
while i < len(plist):
    p = plist[i]
    if text(p).strip() == 'KETERANGAN@@':
        for r in p.runs[1:]: r._r.getparent().remove(r._r)
        p.runs[0].text = 'Keterangan:'
        p.paragraph_format.first_line_indent = Cm(0); p.paragraph_format.keep_with_next = True
        items = []
        j = i + 1
        while j < len(plist) and text(plist[j]).lstrip().startswith('KET@@'):
            items.append(plist[j]); j += 1
        t = new_table_after(p, len(items), 3); borders(t, False)
        set_widths(t, [3.0, 0.5, 12.0])
        for k, it in enumerate(items):
            # pisahkan simbol dan deskripsi pada penanda @@
            parts = [[], []]; side = -1
            for el in list(it._p):
                if el.tag == W('pPr'): continue
                txt = ''.join(x.text or '' for x in el.findall(W('t'))) if el.tag == W('r') else None
                if txt is not None and '@@' in txt:
                    segs = txt.split('@@')
                    for si, sg in enumerate(segs):
                        if si > 0: side += 1
                        if sg.strip() and 0 <= side <= 1:
                            r = copy.deepcopy(el); [x.getparent().remove(x) for x in r.findall(W('t'))]
                            tt = OxmlElement('w:t'); tt.text = sg.strip() if side == 0 else sg.lstrip(); tt.set(qn('xml:space'), 'preserve')
                            r.append(tt); parts[side].append(r)
                elif 0 <= side <= 1:
                    parts[side].append(copy.deepcopy(el))
            cells = t.rows[k].cells
            cells[1].paragraphs[0].add_run(':')
            for ci, part in ((0, parts[0]), (2, parts[1])):
                cp = cells[ci].paragraphs[0]
                for el in part: cp._p.append(el)
            it._p.getparent().remove(it._p)
        cell_paras(t, 12)
        for row in t.rows:
            row.cells[0].paragraphs[0].paragraph_format.left_indent = Cm(1.0)
        i = j; continue
    i += 1

# ---- Source Code -> tabel 2 baris 1 kolom
plist = list(doc.paragraphs)
for i, p in enumerate(plist):
    if text(p).startswith('SRC@@'):
        _, head, title = text(p).split('@@')
        code_ps = []
        j = i + 1
        while j < len(plist) and not text(plist[j]).startswith('SRCEND@@'):
            code_ps.append(plist[j]); j += 1
        t = new_table_after(p, 2, 1); borders(t, True); set_widths(t, [15.5])
        c0 = t.rows[0].cells[0].paragraphs[0]; c0.add_run(head); c0.add_run().add_break(); c0.add_run(title)
        lines = '\n'.join(text(cp) for cp in code_ps).split('\n')
        c1 = t.rows[1].cells[0]; first = True
        for ln in lines:
            cp = c1.paragraphs[0] if first else c1.add_paragraph(); first = False
            r = cp.add_run(ln); r.font.name = 'Courier New'; r.font.size = Pt(10)
            r._r.get_or_add_rPr().get_or_add_rFonts().set(W('hAnsi'), 'Courier New')
        cell_paras(t, 12)
        for cp in c1.paragraphs:
            for r in cp.runs: r.font.size = Pt(10)
        for cp in code_ps: cp._p.getparent().remove(cp._p)
        p._p.getparent().remove(p._p)
        if j < len(plist): plist[j]._p.getparent().remove(plist[j]._p)

# ---- nomor persamaan: tabel 2 kolom tanpa garis, nomor rata kanan
plist = list(doc.paragraphs)
for p in plist:
    if text(p).startswith('EQNUM@@'):
        num = text(p).split('@@')[1].strip()
        prev = p._p.getprevious()
        t = new_table_after(p, 1, 2); borders(t, False); set_widths(t, [13.5, 2.0])
        c0, c1 = t.rows[0].cells
        if prev is not None and prev.tag == W('p') and prev.findall('.//' + qn('m:oMathPara')):
            mps = prev.findall('.//' + qn('m:oMathPara'))
            has_text = any((x.text or '').strip() for x in prev.findall('./' + W('r') + '/' + W('t')))
            if has_text:   # kalimat pengantar + persamaan dalam satu paragraf: pisahkan
                newp = OxmlElement('w:p')
                for mp in mps: newp.append(mp)
                # hapus spasi/run kosong di akhir paragraf pengantar
                prev = newp
            c0._tc.remove(c0.paragraphs[0]._p); c0._tc.append(prev)
        r = c1.paragraphs[0].add_run('(%s)' % num); c1.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT as VA
        c0.vertical_alignment = VA.CENTER; c1.vertical_alignment = VA.CENTER
        for c in (c0, c1):
            for cp in c.paragraphs: cp.paragraph_format.first_line_indent = Cm(0)
        p._p.getparent().remove(p._p)

# ---- paragraf dengan baris baru manual: rata kiri agar tidak meregang
for p in doc.paragraphs:
    if p._p.xpath('./w:r/w:br[not(@w:type)]') and p.style.style_id != 'Heading1':
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT

# ---- daftar (enumerate) tanpa indentasi baris pertama
for p in doc.paragraphs:
    if p._p.pPr is not None and p._p.pPr.numPr is not None:
        il = p._p.pPr.numPr.find(W('ilvl'))
        lvl = int(il.get(W('val'))) if il is not None else 0
        p.paragraph_format.left_indent = Cm(0.75 * (lvl + 1))
        p.paragraph_format.first_line_indent = Cm(-0.75)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if not p._p.xpath('./w:r/w:br[not(@w:type)]') else WD_ALIGN_PARAGRAPH.LEFT
# baris tabel tidak terpotong antarhalaman
for tbl in doc.tables:
    for row in tbl.rows:
        trPr = row._tr.get_or_add_trPr(); trPr.append(OxmlElement('w:cantSplit'))

# ================================================================== bagian awal
first_body = body_el[0]
def P(txt='', align=WD_ALIGN_PARAGRAPH.JUSTIFY, bold=False, indent=False, size=12, style='Normal',
      spacing=1.5, before=0, italic_parts=None):
    p = doc.add_paragraph(style=style)
    first_body.addprevious(p._p)
    pf = p.paragraph_format; pf.alignment = align; pf.line_spacing = spacing
    pf.first_line_indent = Cm(1) if indent else Cm(0); pf.space_before = Pt(before)
    if txt:
        for k, seg in enumerate(re.split(r'(\*[^*]+\*)', txt)):
            if not seg: continue
            r = p.add_run(seg.strip('*') if seg.startswith('*') else seg)
            r.bold = bold; r.font.size = Pt(size); r.italic = seg.startswith('*')
    return p

def H(txt, toc=True):
    p = P(txt, WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=14)
    p.paragraph_format.space_after = Pt(20.7)
    if toc:  # masuk daftar isi sebagai entri tingkat 1 tanpa gaya Heading
        pPr = p._p.get_or_add_pPr(); ol = OxmlElement('w:outlineLvl'); ol.set(W('val'), '0'); pPr.append(ol)
    return p

def pagebreak():
    p = P(); p.add_run().add_break(WD_BREAK.PAGE)

def kv_table(rows, w1=3.2):
    t = doc.add_table(rows=len(rows), cols=3); first_body.addprevious(t._tbl)
    borders(t, False); set_widths(t, [w1, 0.4, 15.5 - w1 - 0.4])
    for k, (a, b) in enumerate(rows):
        c = t.rows[k].cells; c[0].text = a; c[1].text = ':'; c[2].text = b
    cell_paras(t, 12, 1.5)
    return t

def sign_block(lines, left=9.0):
    for k, (ln, ul) in enumerate(lines):
        p = P(ln if not ul else '', WD_ALIGN_PARAGRAPH.LEFT)
        p.paragraph_format.left_indent = Cm(left)
        if ul: r = p.add_run(ln); r.underline = True

def two_col(rows, gap_rows=()):
    t = doc.add_table(rows=len(rows), cols=2); first_body.addprevious(t._tbl)
    borders(t, False); set_widths(t, [8.0, 7.5])
    for k, (a, b, ul) in enumerate(rows):
        for ci, v in enumerate((a, b)):
            cp = t.rows[k].cells[ci].paragraphs[0]; r = cp.add_run(v); r.underline = ul and bool(v.strip(' .'))
        if k in gap_rows:
            for c in t.rows[k].cells: c.paragraphs[0].paragraph_format.space_after = Pt(62)
    cell_paras(t, 12, 1.5)
    for k in gap_rows:
        for c in t.rows[k].cells: c.paragraphs[0].paragraph_format.space_after = Pt(62)

JUDUL_I = re.sub(r'\\textit\{(.*?)\}', r'*\1*', JUDUL_TEX)
# --- sampul
_samp = rd('front/sampul.tex')
_samp = _samp.split('\\setstretch{1.43}\n', 1)[1].split('\\vfill', 1)[0]
COVER = [re.sub(r'\\textit\{(.*?)\}', r'*\1*', l.replace('\\\\', '').strip()) for l in _samp.strip().split('\n') if l.strip()]
for ln in COVER:
    P(ln, WD_ALIGN_PARAGRAPH.CENTER, bold=True)
P(); lp = P(align=WD_ALIGN_PARAGRAPH.CENTER)
lp.add_run().add_picture(os.path.join(TEX, 'img', 'logo-undip.png'), width=Cm(4.0), height=Cm(4.4))
P()
P('SKRIPSI', WD_ALIGN_PARAGRAPH.CENTER, bold=True); P()
for ln in ['Disusun Sebagai Salah Satu Syarat', 'untuk Memperoleh Gelar Sarjana Komputer', 'pada Program Studi Informatika']:
    P(ln, WD_ALIGN_PARAGRAPH.CENTER, bold=True)
P()
for ln in ['Disusun oleh:', PENULIS, NIM]: P(ln, WD_ALIGN_PARAGRAPH.CENTER, bold=True)
P()
for ln in ['DEPARTEMEN INFORMATIKA', 'FAKULTAS SAINS DAN MATEMATIKA', 'UNIVERSITAS DIPONEGORO', '2026']:
    P(ln, WD_ALIGN_PARAGRAPH.CENTER, bold=True)
pagebreak()
# --- pernyataan keaslian
H('HALAMAN PERNYATAAN KEASLIAN SKRIPSI')
P('Saya yang bertanda tangan di bawah ini :')
kv_table([('Nama', PENULIS), ('NIM', NIM), ('Judul', JUDUL)], 1.6)
P('Dengan ini saya menyatakan bahwa dalam skripsi ini tidak terdapat karya yang pernah diajukan untuk memperoleh gelar kesarjanaan di suatu Perguruan Tinggi, dan sepanjang pengetahuan saya juga tidak terdapat karya atau pendapat yang pernah ditulis atau diterbitkan oleh orang lain, kecuali yang secara tertulis diacu dalam naskah ini dan disebutkan di dalam daftar pustaka.', indent=True, before=6)
P()
sign_block([('Semarang, ' + TANGGAL, False), ('', False), ('Materai Rp 10.000,-', False), ('', False), (PENULIS, True), (NIM, False)])
pagebreak()
# --- pengesahan
H('HALAMAN PENGESAHAN')
kv_table([('Judul', JUDUL), ('Nama', PENULIS), ('NIM', NIM)], 1.6)
P('Telah diujikan pada sidang tugas akhir dan dinyatakan lulus pada tanggal …………………', before=6)
P()
two_col([('', 'Semarang, ................ 2026', False), ('Pembimbing 1,', 'Pembimbing 2,', False),
         (PB1[0], PB2[0], True), (PB1[1], PB2[1], False)], gap_rows=(1,))
P('Mengetahui,', WD_ALIGN_PARAGRAPH.CENTER, before=12)
two_col([('Ketua', 'Ketua', False), ('Departemen Informatika', 'Panitia Penguji Tugas Akhir', False),
         ('Dr. Aris Sugiharto, S.Si., M.Kom.', '………………………………..', True),
         ('NIP. 19710811 199702 1 004', 'NIP.', False)], gap_rows=(1,))
pagebreak()

# --- kata pengantar, persetujuan, abstrak: ambil teks dari berkas LaTeX
def latex_plain(t):
    t = strip_comments(t)
    t = t.replace(r'\thejudul', JUDUL_TEX).replace(r'\thepenulis', PENULIS).replace(r'\thenim', NIM)
    t = macros(t)
    t = re.sub(r'\\texttt\{(.*?)\}', r'\1', t)
    t = re.sub(r'\\textit\{(.*?)\}', r'*\1*', t)
    t = t.replace('``', '“').replace("''", '”').replace(r'\%', '%').replace('---', '—').replace('--', '–')
    return t

kp = latex_plain(rd('front/kata-pengantar.tex'))
H('KATA PENGANTAR')
intro = kp.split(r'\frontchapter{KATA PENGANTAR}')[1].split(r'\begin{enumerate}')[0]
for par in [x.strip() for x in intro.split('\n\n') if x.strip()]:
    P(re.sub(r'\s+', ' ', par), indent=True)
items = re.findall(r'\\item (.*)', kp)
for k, it in enumerate(items):
    p = P('%d.\t%s' % (k + 1, it.strip()))
    p.paragraph_format.left_indent = Cm(0.75); p.paragraph_format.first_line_indent = Cm(-0.75)
tail = kp.split(r'\end{enumerate}')[1].split(r'\vspace')[0]
for par in [x.strip() for x in tail.split('\n\n') if x.strip()]:
    P(re.sub(r'\s+', ' ', par), indent=True)
P(); sign_block([('Semarang, .. ........ 2026', False), ('', False), ('', False), ('Penulis', False)], 10.5)
pagebreak()

pp = latex_plain(rd('front/persetujuan-publikasi.tex'))
H('HALAMAN PERNYATAAN PERSETUJUAN PUBLIKASI SKRIPSI').paragraph_format.space_after = Pt(0)
P('UNTUK KEPENTINGAN AKADEMIS', WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=14).paragraph_format.space_after = Pt(20.7)
P('Sebagai civitas akademik Universitas Diponegoro, saya yang bertanda tangan di bawah ini:')
kv_table([('Nama', PENULIS), ('NIM', NIM), ('Program Studi', 'Informatika'), ('Departemen', 'Informatika'),
          ('Fakultas', 'Sains dan Matematika'), ('Jenis Karya', 'Skripsi')], 3.2)
segs = re.findall(r'\\noindent (demi.*?|beserta.*?)\n\n', pp, re.S)
P(re.sub(r'\s+', ' ', segs[0]))
P(JUDUL_I, WD_ALIGN_PARAGRAPH.CENTER)
P(re.sub(r'\s+', ' ', segs[1]))
P('Demikian pernyataan ini saya buat dengan sebenarnya.', indent=True)
P(); sign_block([('Semarang, .. ........ 2026', False), ('', False), ('', False), (PENULIS, True), (NIM, False)])
pagebreak()

for fn, title, kw in [('front/abstrak.tex', 'ABSTRAK', 'Kata kunci'), ('front/abstract.tex', 'ABSTRACT', 'Keywords')]:
    a = latex_plain(rd(fn))
    txt = a.split(r'\setlength{\parindent}{0pt}')[1].split(r'\vspace')[0]
    kws = re.search(kw + r' : (.*)', a).group(1).strip()
    H(title)
    P(re.sub(r'\s+', ' ', txt.strip()), spacing=1.0)
    P(spacing=1.0)
    p = P(kw + ' : ' + kws, spacing=1.0, align=WD_ALIGN_PARAGRAPH.LEFT)
    pagebreak()

# --- daftar isi / tabel / gambar (field Word; diperbarui saat dokumen dibuka)
def field_para(instr, placeholder):
    p = P(align=WD_ALIGN_PARAGRAPH.LEFT)
    def fc(t):
        r = OxmlElement('w:r'); f = OxmlElement('w:fldChar'); f.set(W('fldCharType'), t); r.append(f); p._p.append(r)
    fc('begin')
    r = OxmlElement('w:r'); it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve'); it.text = instr
    r.append(it); p._p.append(r)
    fc('separate'); p.add_run(placeholder); fc('end')

H('DAFTAR ISI'); field_para(r'TOC \o "1-4" \h \z \u', 'Klik kanan → Update Field untuk menampilkan daftar isi.'); pagebreak()
H('DAFTAR TABEL'); field_para(r'TOC \h \z \t "Caption Tabel,1"', 'Klik kanan → Update Field.'); pagebreak()
H('DAFTAR GAMBAR'); field_para(r'TOC \h \z \t "Caption Gambar,1"', 'Klik kanan → Update Field.')

# ---- pemisah bagian: romawi kecil (bagian awal), arab mulai 1 (isi)
def footer_page_num(section):
    section.footer.is_linked_to_previous = False
    fp = section.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for t, val in (('begin', None), ('instr', 'PAGE'), ('separate', None), ('text', '1'), ('end', None)):
        r = OxmlElement('w:r')
        if t == 'instr':
            x = OxmlElement('w:instrText'); x.set(qn('xml:space'), 'preserve'); x.text = val
        elif t == 'text':
            x = OxmlElement('w:t'); x.text = val
        else:
            x = OxmlElement('w:fldChar'); x.set(W('fldCharType'), t)
        rpr = OxmlElement('w:rPr'); rf = OxmlElement('w:rFonts'); rf.set(W('ascii'), 'Times New Roman'); rf.set(W('hAnsi'), 'Times New Roman')
        sz = OxmlElement('w:sz'); sz.set(W('val'), '24'); rpr.append(rf); rpr.append(sz); r.append(rpr)
        r.append(x); fp._p.append(r)

def pg_setup(sectPr, fmt, start=None, title_pg=False):
    for tag in ('pgSz', 'pgMar', 'pgNumType', 'titlePg'):
        for o in sectPr.findall(W(tag)): sectPr.remove(o)
    sz = OxmlElement('w:pgSz'); sz.set(W('w'), '11906'); sz.set(W('h'), '16838')
    mar = OxmlElement('w:pgMar')
    for k, v in (('top', 1701), ('left', 1701), ('right', 1418), ('bottom', 1418), ('header', 709), ('footer', 709), ('gutter', 0)):
        mar.set(W(k), str(v))
    pn = OxmlElement('w:pgNumType'); pn.set(W('fmt'), fmt)
    if start: pn.set(W('start'), str(start))
    sectPr.append(sz); sectPr.append(mar); sectPr.append(pn)
    if title_pg: sectPr.append(OxmlElement('w:titlePg'))

# sectPr bagian awal ditempel pada paragraf terakhir sebelum BAB I
last_front = first_body.getprevious()
pPr = last_front.find(W('pPr'))
if pPr is None: pPr = OxmlElement('w:pPr'); last_front.insert(0, pPr)
front_sect = copy.deepcopy(doc.sections[-1]._sectPr)
for o in front_sect.findall(W('footerReference')) + front_sect.findall(W('headerReference')): front_sect.remove(o)
pg_setup(front_sect, 'lowerRoman', 1, title_pg=True)
pPr.append(front_sect)
pg_setup(doc.sections[-1]._sectPr, 'decimal', 1)
doc.sections[0].different_first_page_header_footer = True
footer_page_num(doc.sections[0]); footer_page_num(doc.sections[1])
# halaman pertama bab juga bernomor: footer halaman pertama sama dengan biasa (hanya sampul kosong)
s1 = doc.sections[1]; s1.different_first_page_header_footer = False


# ---- urutan elemen sesuai skema OOXML (Word ketat terhadap urutan)
ORDER = {
 'pPr': 'pStyle keepNext keepLines pageBreakBefore framePr widowControl numPr suppressLineNumbers pBdr shd tabs suppressAutoHyphens kinsoku wordWrap overflowPunct topLinePunct autoSpaceDE autoSpaceDN bidi adjustRightInd snapToGrid spacing ind contextualSpacing mirrorIndents suppressOverlap jc textDirection textAlignment textboxTightWrap outlineLvl divId cnfStyle rPr sectPr pPrChange',
 'tblPr': 'tblStyle tblpPr tblOverlap bidiVisual tblStyleRowBandSize tblStyleColBandSize tblW jc tblCellSpacing tblInd tblBorders shd tblLayout tblCellMar tblLook tblCaption tblDescription',
 'trPr': 'cnfStyle divId gridBefore gridAfter wBefore wAfter cantSplit trHeight tblHeader tblCellSpacing jc hidden',
 'tcPr': 'cnfStyle tcW gridSpan hMerge vMerge tcBorders shd noWrap tcMar textDirection tcFitText vAlign hideMark',
 'sectPr': 'headerReference footerReference footnotePr endnotePr type pgSz pgMar paperSrc pgBorders lnNumType pgNumType cols formProt vAlign noEndnote titlePg textDirection bidi rtlGutter docGrid printerSettings',
}
def reorder(root):
    for tag, seq in ORDER.items():
        rank = {n: i for i, n in enumerate(seq.split())}
        for el in root.iter(W(tag)):
            kids = list(el)
            seen = {}
            for k in kids:  # buang duplikat (yang terakhir menang), kecuali header/footer reference
                nm = k.tag.split('}')[1]
                if nm in ('headerReference', 'footerReference'): continue
                if nm in seen: el.remove(seen[nm])
                seen[nm] = k
            kids = sorted(list(el), key=lambda k: rank.get(k.tag.split('}')[1], 999))
            for k in kids: el.remove(k)
            for k in kids: el.append(k)
    for ppr in root.iter(qn('m:oMathParaPr')):
        jcs = ppr.findall(qn('m:jc'))
        for j in jcs[:-1]: ppr.remove(j)
reorder(doc.element.body)
for sec in doc.sections:
    for part in (sec.footer, sec.first_page_footer):
        reorder(part._element)

# minta Word memperbarui field saat dibuka
settings = doc.settings.element
uf = OxmlElement('w:updateFields'); uf.set(W('val'), 'true')
anchor = None
for nm in ('hdrShapeDefaults', 'footnotePr', 'endnotePr', 'compat', 'docVars', 'rsids', 'mathPr', 'themeFontLang', 'clrSchemeMapping', 'shapeDefaults', 'decimalSymbol', 'listSeparator'):
    anchor = settings.find(W(nm))
    if anchor is not None: break
if anchor is not None: anchor.addprevious(uf)
else: settings.append(uf)

doc.core_properties.title = JUDUL; doc.core_properties.author = PENULIS
doc.save(OUT)
print('OK ->', OUT, '| tabel:', len(doc.tables), '| gambar:', len([f for f in os.listdir(FIG) if f.endswith('.png')]))
