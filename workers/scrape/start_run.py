"""Create a worker_runs row for the scrape and print its run_id. Usage: start_run.py <market_id>"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.db import start_run
print(start_run("scrape", {"market_id": sys.argv[1] if len(sys.argv) > 1 else None}))
