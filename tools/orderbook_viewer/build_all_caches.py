"""Build the viewer's cache (minute checkpoints and the per-second summary) for every day, one after another."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import server
for day in server.days():
    t0 = time.time(); server.cached(day, "seconds"); print(day, f"{time.time() - t0:.0f} s", flush=True)
