#!/usr/bin/env python3
"""Bounded Semgrep runner for the Python application tree.

The full ``p/python`` + ``p/owasp-top-ten`` rule set is fast on the smaller
Python modules but repeatedly times out on ``src/python/server.py`` when run as
one 151-rule pass. This runner:

* fetches the two registry rule sets;
* keeps only Python/generic rules and deduplicates them by rule id;
* scans every other Python file once with the combined rule set;
* scans ``server.py`` in small batches, four batches at a time;
* retries a failed batch rule-by-rule with a larger per-rule timeout; and
* writes valid JSON plus a merged report, returning non-zero for findings or
  scan errors.

Usage:
    python3 scripts/semgrep_scan.py --reports-dir reports
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

CONFIG_URLS = {
    "python": "https://semgrep.dev/c/p/python",
    "owasp-top-ten": "https://semgrep.dev/c/p/owasp-top-ten",
}
SERVER = "src/python/server.py"
# These taint rules take about five minutes each on the 11k-line server file.
# Run them concurrently as single-rule jobs so they are scanned once instead of
# serializing behind a batch and triggering a rule-by-rule retry.
SLOW_RULES = {
    "python.lang.security.audit.dangerous-code-run-tainted-env-args.dangerous-interactive-code-run-tainted-env-args",
    "python.lang.security.audit.dangerous-os-exec-tainted-env-args.dangerous-os-exec-tainted-env-args",
}


def find_semgrep(explicit: str | None) -> str | None:
    candidates = [
        explicit,
        os.environ.get("SEMGREP_BIN"),
        shutil.which("semgrep"),
        str(Path(".tools/sec-venv/bin/semgrep")),
        str(Path(".tools/bin/semgrep")),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def fetch_rules(url: str) -> list[dict]:
    with urllib.request.urlopen(url, timeout=30) as response:
        document = yaml.safe_load(response.read().decode("utf-8"))
    rules = document.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError(f"{url} did not return a rules list")
    return rules


def python_rules() -> list[dict]:
    selected: dict[str, dict] = {}
    for url in CONFIG_URLS.values():
        for rule in fetch_rules(url):
            languages = rule.get("languages") or []
            if "python" not in languages and "generic" not in languages:
                continue
            rule_id = rule.get("id")
            if rule_id and rule_id not in selected:
                selected[rule_id] = rule
    return list(selected.values())


def python_targets(server: str) -> tuple[list[str], list[str]]:
    try:
        tracked = subprocess.check_output(
            ["git", "ls-files", "src/python/*.py"], text=True
        ).splitlines()
    except (OSError, subprocess.CalledProcessError):
        tracked = [str(p) for p in Path("src/python").rglob("*.py")]
    small = [path for path in tracked if path != server and Path(path).is_file()]
    return ([server] if Path(server).is_file() else []), small


def run_scan(
    semgrep: str,
    config: Path,
    targets: list[str],
    output: Path,
    rule_timeout: int,
    jobs: int,
    wall_timeout: int,
) -> dict:
    output.unlink(missing_ok=True)
    command = [
        semgrep,
        "scan",
        "--config",
        str(config),
        "--metrics=off",
        "--disable-version-check",
        "--timeout",
        str(rule_timeout),
        "--timeout-threshold",
        "0",
        "--jobs",
        str(jobs),
        "--json",
        "--output",
        str(output),
        *targets,
    ]
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=wall_timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        stdout, stderr = process.communicate()
    elapsed = time.monotonic() - started

    result = {
        "command": command,
        "elapsed": round(elapsed, 1),
        "returncode": process.returncode,
        "timed_out": timed_out,
        "stdout": stdout[-2000:],
        "stderr": stderr[-4000:],
        "results": [],
        "errors": [],
        "output": str(output),
    }
    if output.is_file() and output.stat().st_size:
        try:
            payload = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            result["errors"] = [{"type": "InvalidJson", "message": str(exc)}]
        else:
            result["results"] = payload.get("results", [])
            result["errors"] = payload.get("errors", [])
    elif not timed_out:
        result["errors"] = [{"type": "MissingJson", "message": "Semgrep wrote no JSON output"}]
    return result


def summarize(result: dict) -> str:
    if result["timed_out"]:
        return f"TIMEOUT after {result['elapsed']}s"
    if result["errors"]:
        kinds = sorted({str(error.get("type", "error")) for error in result["errors"]})
        return f"ERROR {','.join(kinds)} after {result['elapsed']}s"
    if result["results"]:
        return f"FINDINGS {len(result['results'])} after {result['elapsed']}s"
    return f"PASS after {result['elapsed']}s"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semgrep", help="path to the pinned Semgrep binary")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--rule-timeout", type=int, default=120)
    parser.add_argument("--batch-timeout", type=int, default=240)
    args = parser.parse_args()

    semgrep = find_semgrep(args.semgrep)
    if not semgrep:
        print("[semgrep] ERROR: semgrep is not installed; install semgrep==1.184.0", file=sys.stderr)
        return 2

    rules = python_rules()
    if not rules:
        print("[semgrep] ERROR: no Python rules fetched", file=sys.stderr)
        return 2

    reports = Path(args.reports_dir)
    reports.mkdir(parents=True, exist_ok=True)
    server_targets, small_targets = python_targets(SERVER)
    failures: list[str] = []
    all_results: list[dict] = []
    all_errors: list[dict] = []
    scan_summary: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="einvite-semgrep-") as temp_dir:
        temp = Path(temp_dir)
        combined = temp / "all-python-rules.yml"
        combined.write_text(yaml.safe_dump({"rules": rules}, sort_keys=False), encoding="utf-8")

        if small_targets:
            result = run_scan(
                semgrep,
                combined,
                small_targets,
                reports / "semgrep-python-small-ci.json",
                args.rule_timeout,
                args.workers,
                args.batch_timeout,
            )
            result["label"] = "small-files"
            scan_summary.append(result)
            all_results.extend(result["results"])
            all_errors.extend(result["errors"])
            print(f"[semgrep] small-files: {summarize(result)}", flush=True)

        slow_batches = [[rule] for rule in rules if rule.get("id") in SLOW_RULES]
        normal_rules = [rule for rule in rules if rule.get("id") not in SLOW_RULES]
        normal_batches = [
            normal_rules[i:i + args.batch_size]
            for i in range(0, len(normal_rules), args.batch_size)
        ]
        batches = slow_batches + normal_batches
        batch_paths: list[Path] = []
        for index, batch in enumerate(batches):
            path = temp / f"batch-{index:03d}.yml"
            path.write_text(yaml.safe_dump({"rules": batch}, sort_keys=False), encoding="utf-8")
            batch_paths.append(path)

        def scan_batch(index: int) -> tuple[int, dict]:
            is_slow = len(batches[index]) == 1 and batches[index][0].get("id") in SLOW_RULES
            return index, run_scan(
                semgrep,
                batch_paths[index],
                server_targets,
                temp / f"batch-{index:03d}.json",
                360 if is_slow else args.rule_timeout,
                1,
                420 if is_slow else args.batch_timeout,
            )

        completed: dict[int, dict] = {}
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            futures = {executor.submit(scan_batch, i): i for i in range(len(batches))}
            for future in as_completed(futures):
                index, result = future.result()
                completed[index] = result
                print(f"[semgrep] server batch {index + 1}/{len(batches)}: {summarize(result)}", flush=True)

        # A slow rule should not make the whole batch unusable. Retry only the
        # batches that timed out, one rule at a time, with twice the limit.
        retry_limit = max(args.rule_timeout * 2, 300)
        for index, result in sorted(completed.items()):
            if not result["timed_out"] and not result["errors"] and result["returncode"] in (0, 1):
                continue
            print(f"[semgrep] retrying batch {index + 1} rule-by-rule", flush=True)

            def retry_one(position: int, rule: dict) -> dict:
                rule_path = temp / f"retry-{index:03d}-{position:02d}.yml"
                rule_path.write_text(yaml.safe_dump({"rules": [rule]}, sort_keys=False), encoding="utf-8")
                single = run_scan(
                    semgrep,
                    rule_path,
                    server_targets,
                    temp / f"retry-{index:03d}-{position:02d}.json",
                    retry_limit,
                    1,
                    retry_limit + 60,
                )
                single["label"] = rule.get("id", "unknown")
                return single

            retried: list[dict] = []
            with ThreadPoolExecutor(max_workers=max(1, min(args.workers, len(batches[index])))) as retry_executor:
                retry_futures = [
                    retry_executor.submit(retry_one, position, rule)
                    for position, rule in enumerate(batches[index])
                ]
                for future in as_completed(retry_futures):
                    single = future.result()
                    retried.append(single)
                    print(f"[semgrep] retry {single['label']}: {summarize(single)}", flush=True)
            completed[index] = {
                "label": f"batch-{index + 1}",
                "elapsed": round(sum(item["elapsed"] for item in retried), 1),
                "timed_out": any(item["timed_out"] for item in retried),
                "returncode": 0 if not any(item["returncode"] for item in retried) else 1,
                "results": [finding for item in retried for finding in item["results"]],
                "errors": [error for item in retried for error in item["errors"]],
            }

        for index, result in sorted(completed.items()):
            result.setdefault("label", f"batch-{index + 1}")
            scan_summary.append(result)
            all_results.extend(result["results"])
            all_errors.extend(result["errors"])
            if result.get("timed_out") or result.get("errors") or result.get("returncode") not in (0, 1):
                failures.append(str(result.get("label", f"batch-{index + 1}")))

    merged = {
        "tool": "semgrep",
        "configs": list(CONFIG_URLS),
        "rules": len(rules),
        "targets": {"server": server_targets, "small_files": len(small_targets)},
        "results": all_results,
        "errors": all_errors,
        "scans": scan_summary,
    }
    merged_path = reports / "semgrep-python-ci.json"
    merged_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")

    print(
        f"[semgrep] RESULT: rules={len(rules)} batches={len(batches)} "
        f"findings={len(all_results)} errors={len(all_errors)} failed_batches={len(failures)}",
        flush=True,
    )
    if all_errors or failures:
        return 1
    if all_results:
        print("[semgrep] findings require triage", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
