"""One-off: renumber the lectures to the structure of COURSE_GUIDE.md §0 (2026-11-16).
Old -> new: 1-9 unchanged; 10 (merged, references meant the portfolio question) -> 13; 11 -> 10; 25-27 -> 11-13; 28-30 -> 14-16; 12-24 -> 18-30.
Renames folders (two phases, via temporary names) and notebooks; rewrites, in every .md, .py and .ipynb file:
  - "Lecture N" / "Lectures N-M, N and M, ..." (numbers mapped one by one),
  - "LN" short forms in Markdown outside code spans,
  - folder names in paths.
Usage: python tools/renumber_lectures.py [--apply]   (without --apply: dry run, prints a sample of the changes and the counts)."""
import re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; LEC = ROOT / "lectures"
MAP = {**{i: i for i in range(1, 10)}, 10: 13, 11: 10, 25: 11, 26: 12, 27: 13, 28: 14, 29: 15, 30: 16, **{i: i + 6 for i in range(12, 25)}}
APPLY = "--apply" in sys.argv


def m(n):
    return MAP.get(n, n)


LECT = re.compile(r"\b([Ll]ectures?)(\s+)(\d+(?:\s*(?:[-–]|,|\band\b|\bor\b|\bto\b)\s*\d+)*)")
SHORT = re.compile(r"(?<![\w.`/])L(\d{1,2})\b")


BLOCK = lambda n: 0 if n <= 9 else (2 if 12 <= n <= 24 else 1)        # old 25-30 map to the contiguous 11-16, so only the high-frequency block can break a range
CROSS = []


def lect(match):
    nums = [int(x) for x in re.findall(r"\d+", match.group(3))]
    if re.search(r"[-–]|\bto\b", match.group(3)) and len({BLOCK(x) for x in nums}) > 1: CROSS.append(match.group(0))
    return match.group(1) + match.group(2) + re.sub(r"\d+", lambda d: str(m(int(d.group()))), match.group(3))


SKIP = [("## 0. The course structure", "## 1. Roadmap"), ("### The arc", "### How every lecture works"), ("### How these notes were made", "## Lectures")]


def md_text_skipping(s):
    """Leave untouched the passages already written in the new numbering (course guide §0, README's arc and disclosure)."""
    out, pos = [], 0
    for a, b in SKIP:
        i = s.find(a, pos)
        if i < 0: continue
        j = s.find(b, i)
        if j < 0: continue
        out.append(md_text(s[pos:i])); out.append(s[i:j]); pos = j
    out.append(md_text(s[pos:])); return "".join(out)


def md_text(s):
    parts = s.split("`")                                                     # odd parts are inside code spans
    for i in range(0, len(parts), 2):
        parts[i] = LECT.sub(lect, parts[i])
        parts[i] = SHORT.sub(lambda x: "L" + str(m(int(x.group(1)))) if 1 <= int(x.group(1)) <= 30 else x.group(0), parts[i])
    return "`".join(parts)


folders = sorted(p.name for p in LEC.iterdir() if p.is_dir() and re.match(r"\d\d-", p.name))
REN = {}
for f in folders:
    n = int(f[:2]); REN[f] = f"{m(n):02d}{f[2:]}"
NB = {}
for f, g in REN.items():
    for nb in (LEC / f).glob("*.ipynb"):
        mm = re.match(r"(\d\d)(b?_.*)", nb.name)
        if mm: NB[nb.name] = f"{m(int(mm.group(1))):02d}{mm.group(2)}"


def paths_text(s):
    for f in sorted(REN, key=len, reverse=True):
        if REN[f] != f: s = s.replace(f, "\x00" + REN[f] + "\x01")
    for a, b in NB.items():
        if a != b: s = s.replace(a, "\x00" + b + "\x01")
    return s.replace("\x00", "").replace("\x01", "")


files = [p for p in ROOT.rglob("*") if p.suffix in (".md", ".py", ".ipynb") and ".git" not in p.parts and "__pycache__" not in p.parts
         and p.name != "renumber_lectures.py"]
changed, sample = 0, []
for p in files:
    s = p.read_text(encoding="utf-8"); t = paths_text(s)
    t = md_text_skipping(t) if p.suffix == ".md" else LECT.sub(lect, t)
    if t != s:
        changed += 1
        if len(sample) < 25:
            a, b = s.splitlines(), t.splitlines()
            for x, y in zip(a, b):
                if x != y: sample.append((p.relative_to(ROOT), x.strip()[:110], y.strip()[:110])); break
        if APPLY: p.write_text(t, encoding="utf-8")
print("folders:", {a: b for a, b in REN.items() if a != b})
print("notebooks:", {a: b for a, b in NB.items() if a != b})
print("files changed:", changed, "of", len(files))
for f, x, y in sample[:6]: print(f"\n{f}\n  - {x}\n  + {y}")
print("\nranges crossing blocks (review by hand):", sorted(set(CROSS)))
if APPLY:
    for f in REN:
        if REN[f] != f: subprocess.run(["git", "mv", str(LEC / f), str(LEC / ("_tmp_" + f))], check=True, cwd=ROOT)
    for f in REN:
        if REN[f] != f: subprocess.run(["git", "mv", str(LEC / ("_tmp_" + f)), str(LEC / REN[f])], check=True, cwd=ROOT)
    for f, g in REN.items():
        for nb in list((LEC / g).glob("*.ipynb")):
            if nb.name in NB and NB[nb.name] != nb.name: subprocess.run(["git", "mv", str(nb), str(nb.with_name(NB[nb.name]))], check=True, cwd=ROOT)
    print("applied")
