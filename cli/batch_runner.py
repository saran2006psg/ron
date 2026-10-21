"""Submit a JSON file or directory of JSON files to a running API and save responses."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("input", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--base-url", default="http://localhost:8000")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
files = [args.input] if args.input.is_file() else sorted(args.input.glob("*.json"))
for index, source in enumerate(files, 1):
    data = source.read_bytes()
    request = urllib.request.Request(args.base_url + "/api/v1/broll/jobs", data=data, method="POST",
        headers={"Content-Type":"application/json", "Idempotency-Key": f"batch-{source.stem}-{index}"})
    try:
        with urllib.request.urlopen(request) as response: body = response.read().decode()
    except Exception as exc: body = json.dumps({"error": str(exc)})
    (args.output / f"{source.stem}.response.json").write_text(body, encoding="utf-8")