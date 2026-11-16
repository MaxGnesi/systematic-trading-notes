"""Build a lecture's slide deck as a PDF from a short Markdown source.

Usage: python tools/slides/build_slides.py lectures/16-the-final-portfolio
Reads <lecture>/slides/slides.md, writes <lecture>/slides/<NN>_slides.pdf, one PNG per slide in slides/pages/ and
slides/README.md, which shows the slides on GitHub with a download link to the PDF (the intermediate .html is not committed).

Source format: slides separated by a line '---'. In each slide:
  '# Title'                       the slide title (the first slide is the title slide)
  '> text'                        the key message, shown in a box under the title
  '- text' / '1. text'            bullets
  '![caption](path)'              an image, path relative to the slides folder
  '| a | b |' lines               a small table
  '<!-- note -->'                 ignored
  other lines                     a paragraph
Inline: **bold**, *italic*. Layout is chosen from the content: text only; image only; text beside an image.
Printed with a local Chrome or Edge in headless mode (no other software needed).
"""
from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

INK, MUTED, GRID, SURFACE, ACCENT = "#0b0b0b", "#6b6963", "#e1e0d9", "#fcfcfb", "#2a78d6"
BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "google-chrome", "chromium", "chromium-browser", "msedge"]

CSS = f"""
@page {{ size: 13.333in 7.5in; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: {SURFACE}; color: {INK};
  font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.slide {{ width: 13.333in; height: 7.5in; padding: 0.55in 0.7in 0.5in; position: relative; overflow: hidden;
  page-break-after: always; break-after: page; display: flex; flex-direction: column; }}
.slide:last-child {{ page-break-after: auto; break-after: auto; }}
h1 {{ font-size: 30pt; font-weight: 650; margin: 0 0 0.16in; letter-spacing: -0.01em; }}
.key {{ border-left: 6px solid {ACCENT}; background: #eef4fc; padding: 0.14in 0.22in; font-size: 19pt; line-height: 1.32;
  margin: 0 0 0.22in; border-radius: 0 4px 4px 0; }}
.body {{ flex: 1; display: flex; gap: 0.35in; min-height: 0; }}
.text {{ flex: 1 1 0; font-size: 20pt; line-height: 1.4; min-width: 0; }}
.split .text {{ flex: 0 0 34%; font-size: 18pt; }}
.fig {{ flex: 1 1 0; display: flex; flex-direction: column; align-items: center; justify-content: center; min-width: 0; min-height: 0; }}
.fig img {{ max-width: 100%; max-height: 100%; object-fit: contain; min-height: 0; }}
.fig .cap {{ font-size: 12pt; color: {MUTED}; margin-top: 0.06in; text-align: center; }}
ul, ol {{ margin: 0; padding-left: 1.1em; }} li {{ margin: 0 0 0.11in; }}
p {{ margin: 0 0 0.13in; }}
table {{ border-collapse: collapse; font-size: 17pt; margin: 0.05in 0 0.15in; }}
th, td {{ border-bottom: 1px solid {GRID}; padding: 0.05in 0.14in; text-align: left; vertical-align: top; }}
th {{ color: {MUTED}; font-weight: 600; }}
.foot {{ position: absolute; left: 0.7in; right: 0.7in; bottom: 0.22in; display: flex; justify-content: space-between;
  font-size: 10pt; color: {MUTED}; }}
.title {{ justify-content: center; }}
.title .body {{ flex: 0 0 auto; }}
.title h1 {{ font-size: 40pt; margin-bottom: 0.25in; }}
.title .key {{ font-size: 20pt; }}
.title .text {{ font-size: 15pt; color: {MUTED}; flex: 0 0 auto; }}
"""


def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<i>\1</i>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def render_slide(block: str, first: bool, footer: str, page: int) -> str:
    title, key, text, figs = "", "", [], []
    lines = [l for l in block.strip("\n").split("\n") if not l.strip().startswith("<!--")]
    i, mode = 0, None
    while i < len(lines):
        l = lines[i].rstrip()
        if l.startswith("# "):
            title = inline(l[2:])
        elif l.startswith("> "):
            key += (" " if key else "") + inline(l[2:])
        elif m := re.match(r"!\[(.*?)\]\((.+?)\)", l.strip()):
            figs.append((m.group(2), inline(m.group(1))))
        elif l.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells): rows.append(cells)
                i += 1
            head, *rest = rows
            t = "<table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr>"
            t += "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rest) + "</table>"
            if mode: text.append(f"</{mode}>"); mode = None
            text.append(t); continue
        elif m := re.match(r"(-|\d+\.)\s+(.*)", l):
            want = "ul" if m.group(1) == "-" else "ol"
            if mode != want:
                if mode: text.append(f"</{mode}>")
                text.append(f"<{want}>"); mode = want
            text.append(f"<li>{inline(m.group(2))}</li>")
        elif l.strip():
            if mode: text.append(f"</{mode}>"); mode = None
            text.append(f"<p>{inline(l)}</p>")
        i += 1
    if mode: text.append(f"</{mode}>")
    has_text = any(t.strip() for t in text)
    layout = "split" if (figs and has_text) else ""
    out = [f'<section class="slide{" title" if first else ""}">', f"<h1>{title}</h1>" if title else ""]
    if key: out.append(f'<div class="key">{key}</div>')
    out.append(f'<div class="body {layout}">')
    if has_text: out.append('<div class="text">' + "\n".join(text) + "</div>")
    for path, cap in figs:
        out.append(f'<div class="fig"><img src="{html.escape(path)}">' + (f'<div class="cap">{cap}</div>' if cap else "") + "</div>")
    out.append("</div>")
    if not first: out.append(f'<div class="foot"><span>{footer}</span><span>{page}</span></div>')
    out.append("</section>")
    return "\n".join(out)


def build(lecture_dir: Path) -> Path:
    sdir = lecture_dir / "slides"
    src = (sdir / "slides.md").read_text(encoding="utf-8")
    blocks = [b for b in re.split(r"^---\s*$", src, flags=re.M) if b.strip()]
    num = lecture_dir.name.split("-")[0]
    footer = re.search(r"^# (.+)$", blocks[0], re.M).group(1)
    footer = html.escape(footer) + " · Systematic Trading: Lecture Notes (MSc)"
    slides = [render_slide(b, k == 0, footer, k + 1) for k, b in enumerate(blocks)]
    page = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>" + "\n".join(slides) + "</body></html>"
    html_path = sdir / f"{num}_slides.html"; html_path.write_text(page, encoding="utf-8")
    pdf = sdir / f"{num}_slides.pdf"
    browser = next((b for b in BROWSERS if Path(b).exists() or shutil.which(b)), None)
    if not browser: raise SystemExit("No Chrome or Edge found to print the PDF.")
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf.resolve()}",
                    "--virtual-time-budget=5000", html_path.resolve().as_uri()], capture_output=True, timeout=120, check=False)
    pages = page_images(browser, html_path, len(blocks), sdir / "pages", num)
    title = re.search(r"^# (.+)$", blocks[0], re.M).group(1)
    view = [f"# Slides · {title}", "", f"**[Download the slides as PDF]({pdf.name}?raw=1)** · [Back to the lecture](../lecture.md)", ""]
    view += [f"![Slide {k + 1}](pages/{p.name})\n" for k, p in enumerate(pages)]
    (sdir / "README.md").write_text("\n".join(view), encoding="utf-8")
    print(f"{len(blocks)} slides -> {pdf}, {len(pages)} page images, slides/README.md")
    return pdf


def page_images(browser: str, html_path: Path, n: int, out: Path, num: str) -> list[Path]:
    """One PNG per slide, for viewing on GitHub: a screenshot of the whole deck, cut into pages."""
    from PIL import Image
    out.mkdir(exist_ok=True)
    for old in out.glob("*.png"): old.unlink()
    shot = out / "_all.png"
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size=1280,{720 * n}",
                    "--virtual-time-budget=5000", f"--screenshot={shot.resolve()}", html_path.resolve().as_uri()],
                   capture_output=True, timeout=120, check=False)
    im = Image.open(shot); paths = []
    for k in range(n):
        p = out / f"{num}_slide_{k + 1:02d}.png"
        im.crop((0, 720 * k, 1280, 720 * (k + 1))).convert("RGB").save(p, optimize=True); paths.append(p)
    im.close(); shot.unlink()
    return paths


if __name__ == "__main__":
    for d in sys.argv[1:]:
        build(Path(d))
