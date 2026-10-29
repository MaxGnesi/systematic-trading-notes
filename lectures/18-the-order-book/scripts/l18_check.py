"""Lecture 18 §4.2-§4.3: check the rebuilt book of one day. The book is rebuilt from the Parquet table segment by segment, and compared level by level
with every snapshot that follows continuous data; pauses of the feed are reported as gaps. Output: L18_OUT/l18_check_DAY.json.
Usage: python l18_check.py YYYY-MM-DD"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l18 as L
from bybit_to_parquet import check_book

DAY = sys.argv[1]
res = check_book(L.BOOK / f"{DAY}.parquet", None)
(L.OUT / f"l18_check_{DAY}.json").write_text(json.dumps(res, indent=1))
print(DAY, "PASS" if res["ok"] else "FAIL", {k: v for k, v in res.items() if k != "ok"})
