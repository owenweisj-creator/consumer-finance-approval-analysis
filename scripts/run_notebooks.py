from __future__ import annotations

import sys
import argparse
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    paths = sorted((ROOT / "notebooks").glob("*.ipynb"))
    if args.limit:
        paths = paths[: args.limit]
    for path in paths:
        print("executing", path.name)
        nb = nbformat.read(path, as_version=4)
        client = NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}})
        client.execute()
        nbformat.write(nb, path)
        print("ok", path.name)


if __name__ == "__main__":
    main()
