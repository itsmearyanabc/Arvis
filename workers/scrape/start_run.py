"""Create a worker_runs row for the scrape and write its id to run_id.txt. Usage: start_run.py <market_id>"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common.db import start_run
rid = start_run("scrape", {"market_id": sys.argv[1] if len(sys.argv) > 1 else None})
open("run_id.txt", "w").write(rid)
print("run_id", rid)
