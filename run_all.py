
import subprocess
import sys
import time
from typing import List
from colorama import Fore, init

SCRIPTS_TO_RUN = [
    "delete_graphs.py",
    "news_scraper.py",
    "nlp.py",
    "populate_graph.py",
    "app.py"
]

init(autoreset=True)

def run_scripts(scripts: List[str]) -> bool:
    """Run all scripts in sequence, return True if all succeeded"""
    overall_success = True

    for script in scripts:
        try:
            print(Fore.YELLOW + f"\n=== Starting {script} ===\n")
            subprocess.run([sys.executable, script], check=True)
        except subprocess.CalledProcessError:
            print(Fore.RED + f"\n!!! {script} failed !!!\n")
            overall_success = False
            break

    return overall_success


if __name__ == "__main__":
    start_time = time.time()

    print(Fore.YELLOW + f"\n=== Running script sequence ===\n")
    success = run_scripts(SCRIPTS_TO_RUN)

    total_time = time.time() - start_time
    print(Fore.YELLOW + f"\n=== Total execution time: {total_time:.2f} seconds ===\n")

    if not success:
        print(Fore.RED + "\n!!! Script sequence stopped due to errors !!!\n")
        sys.exit(1)