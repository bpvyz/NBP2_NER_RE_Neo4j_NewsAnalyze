import asyncio
import sys
import time
from colorama import Fore, init
import subprocess

init(autoreset=True)


async def run_script(script: str) -> bool:
    try:
        print(Fore.YELLOW + f"\n=== Starting {script} ===\n")
        process = await asyncio.create_subprocess_exec(
            sys.executable, script,
            # Remove the PIPE captures to let output through
            stdout=None,  # Output directly to terminal
            stderr=None   # Errors directly to terminal
        )
        await process.wait()
        return process.returncode == 0
    except Exception as e:
        print(Fore.RED + f"\n!!! Error running {script}: {str(e)} !!!\n")
        return False


async def run_scrapers_concurrently():
    """Run both scraper scripts concurrently"""
    scrapers = ["news_scraper_pink.py", "news_scraper_novas.py"]
    tasks = [run_script(scraper) for scraper in scrapers]
    return await asyncio.gather(*tasks)


def run_script_sync(script: str) -> bool:
    """Run a script synchronously (for non-scraper scripts)"""
    try:
        print(Fore.YELLOW + f"\n=== Starting {script} ===\n")
        result = subprocess.run([sys.executable, script], check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError:
        print(Fore.RED + f"\n!!! {script} failed !!!\n")
        return False


async def main():
    start_time = time.time()
    print(Fore.YELLOW + "\n=== Starting script sequence ===\n")

    # 1. First run delete_graphs.py synchronously
    if not run_script_sync("delete_graphs.py"):
        return False

    # 2. Run both scrapers concurrently
    scraper_results = await run_scrapers_concurrently()
    if not all(scraper_results):
        return False

    # 3. Run remaining scripts synchronously
    remaining_scripts = ["nlp.py", "populate_graph.py", "app.py"]
    for script in remaining_scripts:
        if not run_script_sync(script):
            return False

    return True


if __name__ == "__main__":
    start_time = time.time()

    try:
        success = asyncio.run(main())
    except Exception as e:
        print(Fore.RED + f"\n!!! Fatal error: {str(e)} !!!\n")
        success = False

    total_time = time.time() - start_time
    print(Fore.YELLOW + f"\n=== Total execution time: {total_time:.2f} seconds ===")

    if not success:
        print(Fore.RED + "\n!!! Script sequence stopped due to errors !!!\n")
        sys.exit(1)