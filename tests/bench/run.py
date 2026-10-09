#!/usr/bin/env python3
"""Build the suite program with --native --opt 3 and run its benchmarks: the Code node's
Stage 1 snippets over 1M points, on one thread and on the pool. Prints a Markdown table
(each figure the best of five runs of the engine; "copy of P" is the host's share of a
whole cook)."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="luce-base", help="the luce-base compiler")
    parser.add_argument("--opt", default="3")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="luce-kernel-bench-") as temporary:
        env = dict(os.environ, LUCE_CACHE=str(Path(temporary) / "cache"))
        binary = Path(temporary) / "suite"
        subprocess.run([args.base, "build", str(ROOT / "tests/suite/main.lucb"), "--native", "--opt", args.opt,
                        "-o", str(binary)], check=True, env=env, timeout=900)
        output = subprocess.run([str(binary), "--bench"], check=True, capture_output=True, text=True,
                                timeout=900).stdout
    rows = {}
    for line in output.splitlines():
        name, threads, spent = line.split("\t")
        rows.setdefault(name, {})["one" if threads == "1" else "pool"] = float(spent)
    print("| Case, 1M points | One thread | Pool |")
    print("|---|---:|---:|")
    for name, times in rows.items():
        pool = f"{times['pool']:.2f} ms" if "pool" in times else ""
        print(f"| {name} | {times['one']:.2f} ms | {pool} |")


if __name__ == "__main__":
    main()
