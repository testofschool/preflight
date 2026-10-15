"""Rebuild local evidence, retaining every command, exit code and stdout."""

import argparse
import json
from pathlib import Path
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    (root / "logs").mkdir(exist_ok=True)
    (root / "reports").mkdir(exist_ok=True)
    commands = [
        ("build", [sys.executable, "scripts/build_data.py"]),
        ("evaluation", [sys.executable, "scripts/evaluate.py"]),
        ("tests", [sys.executable, "-m", "pytest", "-q", "tests"]),
        ("freshness", [sys.executable, "scripts/check_freshness.py", "--reference", str(args.reference.resolve())]),
        ("secrets", [sys.executable, "scripts/check_secrets.py"]),
    ]
    receipts = []
    for label, command in commands:
        result = subprocess.run(command, cwd=root, text=True, capture_output=True)
        output = result.stdout + result.stderr
        (root / "logs" / f"{label}.txt").write_text(output)
        receipt = {"name": label, "command": command, "exit_code": result.returncode,
                   "stdout_file": f"logs/{label}.txt"}
        receipts.append(receipt)
        print(json.dumps(receipt), flush=True)
        print(output, end="", flush=True)
        # Evaluation prints literal statistical FAILs independently of a successful execution.
        if result.returncode and label in ("build", "evaluation"):
            break
    (root / "reports" / "commands.json").write_text(json.dumps(receipts, indent=2) + "\n")
    return int(any(row["exit_code"] != 0 for row in receipts))


if __name__ == "__main__":
    raise SystemExit(main())
