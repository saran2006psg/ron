"""Submit a JSON file or directory of JSON files to a running API and poll to completion."""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def submit_and_poll(file_path: Path, base_url: str, output_dir: Path, timeout_seconds: int = 180) -> dict:
    stem = file_path.stem
    idempotency_key = f"batch-{stem}-{int(time.time())}"
    data = file_path.read_bytes()

    # Step 1: Submit job
    req = urllib.request.Request(
        f"{base_url}/api/v1/broll/jobs",
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            submit_data = json.loads(resp.read().decode())
    except Exception as exc:
        err_res = {"error": f"Submission failed: {exc}", "file": stem}
        (output_dir / f"{stem}.error.json").write_text(json.dumps(err_res, indent=2), encoding="utf-8")
        return err_res

    job_id = submit_data.get("job_id")
    if not job_id:
        (output_dir / f"{stem}.error.json").write_text(json.dumps(submit_data, indent=2), encoding="utf-8")
        return submit_data

    # Step 2: Poll job until completion
    start = time.time()
    final_status = submit_data
    while time.time() - start < timeout_seconds:
        time.sleep(2)
        try:
            poll_req = urllib.request.Request(f"{base_url}/api/v1/jobs/{job_id}", method="GET")
            with urllib.request.urlopen(poll_req, timeout=15) as resp:
                status_data = json.loads(resp.read().decode())
                final_status = status_data
                state = status_data.get("status")
                if state in {"succeeded", "failed"}:
                    break
        except Exception as poll_exc:
            final_status["poll_warning"] = str(poll_exc)

    # Step 3: Write out final job status
    (output_dir / f"{stem}.status.json").write_text(json.dumps(final_status, indent=2), encoding="utf-8")

    # Step 4: Download any linked artifacts (timeline, manifest, captions, videos)
    result_links = final_status.get("result_links", {})
    for name, link in result_links.items():
        try:
            with urllib.request.urlopen(link, timeout=15) as resp:
                ext = Path(urllib.parse.urlparse(link).path).suffix or ".dat"
                (output_dir / f"{stem}.{name}{ext}").write_bytes(resp.read())
        except Exception:
            pass

    return final_status


def main():
    parser = argparse.ArgumentParser(description="IncuBrix Batch Job Runner")
    parser.add_argument("input", type=Path, help="JSON file or directory of JSON files")
    parser.add_argument("output", type=Path, help="Directory to save execution results")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of running IncuBrix API")
    parser.add_argument("--timeout", type=int, default=180, help="Max wait seconds per job")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    files = [args.input] if args.input.is_file() else sorted(args.input.glob("*.json"))

    print(f"Found {len(files)} test input fixture(s) in {args.input}")
    summary = []
    for index, source in enumerate(files, 1):
        print(f"[{index}/{len(files)}] Submitting {source.name}...")
        result = submit_and_poll(source, args.base_url.rstrip("/"), args.output, args.timeout)
        state = result.get("status", "unknown")
        print(f"    Status: {state} (Progress: {result.get('progress', 0)}%)")
        summary.append({"file": source.name, "job_id": result.get("job_id"), "status": state})

    (args.output / "batch_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nBatch complete. Output saved to {args.output}")


if __name__ == "__main__":
    main()