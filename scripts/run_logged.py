"""Detach-friendly process wrapper that captures stdout/stderr to log files.

Used by the Windows development launcher so Start-Process does not hold
redirect pipes in the parent shell. Stops the child when this wrapper exits.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: run_logged.py <stdout.log> <stderr.log> <command> [args...]", file=sys.stderr)
        return 2

    out_path = Path(sys.argv[1])
    err_path = Path(sys.argv[2])
    command = sys.argv[3:]
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8", errors="replace") as out_f, err_path.open(
        "w", encoding="utf-8", errors="replace"
    ) as err_f:
        proc = subprocess.Popen(
            command,
            stdout=out_f,
            stderr=err_f,
            cwd=None,
        )
        try:
            return int(proc.wait())
        except KeyboardInterrupt:
            proc.terminate()
            try:
                return int(proc.wait(timeout=8))
            except Exception:
                proc.kill()
                return 1


if __name__ == "__main__":
    raise SystemExit(main())
