"""Lecture 26: the 3-month Treasury bill rate (FRED series DTB3, free, no account), written to PORTFOLIO_DATA/DTB3.csv. Used to turn the ETFs'
total returns into excess returns over cash, as a futures position earns."""
import sys, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l26 as L

if __name__ == "__main__":
    urllib.request.urlretrieve("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3", L.RATE); print("saved", L.RATE)
