#!/usr/bin/env python3
"""S5 proof: Python-encrypted rows read in Node, Node-encrypted rows read in
Python, plus rotation, tampering and the exact `hash_for_lookup` values.

Each phase runs the real modules in a subprocess so key caches cannot leak
between phases: `core.crypto` for Python and `lib/crypto.mjs` for Node.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from cryptography.fernet import Fernet

REPO = Path(__file__).resolve().parent.parent
NODE_DIR = REPO / "services" / "api-node"
PY = str(REPO / ".venv" / "bin" / "python")
if not Path(PY).exists():  # pragma: no cover - fallback for a bare interpreter
    PY = sys.executable

SAMPLES = [
    "user@example.com",
    "café@exämple.com",
    "  padded value  ",
    "emoji 🙂 and a\ttab",
    "x" * 4096,
    "",
]
PREFIX_VALUE = "gAAAAA-not-a-real-token"
HASH_VALUES = [
    "user@example.com",
    "  User@Example.COM  ",
    "ΣΣ",
    "ΑΣ",
    "İstanbul@example.com",
    "café@exämple.com",
    "",  # empty guard, not sha256("")
    None,
    "\ufeffbom@example.com",
]


def run(args: list[str], *, env_extra: dict[str, str] | None = None, stdin: str | None = None) -> str:
    env = dict(os.environ)
    env.pop("EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS", None)
    env.update(env_extra or {})
    result = subprocess.run(args, input=stdin, capture_output=True, text=True, env=env, check=False)
    if result.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(args)}\n{result.stderr}")
    return result.stdout


def python_protect(key: str, values: list[str]) -> list[str]:
    # core.db.protect, not core.crypto.encrypt_field: the shape rule (a value
    # already starting with gAAAAA is left alone) lives in protect().
    script = (
        "import json,sys;from core.db import protect;"
        "print(json.dumps([protect(v) for v in json.loads(sys.argv[1])]))"
    )
    stdout = run(
        [PY, "-c", script, json.dumps(values)],
        env_extra={"PYTHONPATH": str(REPO / "src" / "python"), "EINVITE_FIELD_ENCRYPTION_KEY": key},
    )
    return json.loads(stdout)


def python_reveal(key: str, previous: str, values: list[str]) -> list[str]:
    script = (
        "import json,sys;from core.crypto import decrypt_field;"
        "print(json.dumps([decrypt_field(v) for v in json.loads(sys.argv[1])]))"
    )
    stdout = run(
        [PY, "-c", script, json.dumps(values)],
        env_extra={
            "PYTHONPATH": str(REPO / "src" / "python"),
            "EINVITE_FIELD_ENCRYPTION_KEY": key,
            "EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS": previous,
        },
    )
    return json.loads(stdout)


def python_hashes(values: list) -> list:
    script = "import json,sys;from core.crypto import hash_for_lookup;print(json.dumps([hash_for_lookup(v) for v in json.loads(sys.argv[1])]))"
    stdout = run([PY, "-c", script, json.dumps(values)], env_extra={"PYTHONPATH": str(REPO / "src" / "python")})
    return json.loads(stdout)


def node_job(key: str, previous: str, samples: list[str], plain: list[str]) -> dict:
    job = json.dumps({"key": key, "previous": previous, "samples": samples, "plain": plain})
    result = subprocess.run(
        ["node", "bin/crypto-parity.mjs"],
        cwd=NODE_DIR,
        input=job,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout:
        raise SystemExit(f"node parity job failed:\n{result.stderr}")
    return json.loads(result.stdout)


def node_hashes(values: list) -> list:
    module = (NODE_DIR / "lib" / "queries.mjs").as_uri()
    script = (
        f"import {{hashForLookup}} from '{module}';"
        "const values = JSON.parse(process.argv[1]);"
        "process.stdout.write(JSON.stringify(values.map((v) => hashForLookup(v))));"
    )
    return json.loads(run(["node", "--input-type=module", "-e", script, json.dumps(values)]))


def main() -> int:
    key_a, key_b = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    checks = 0
    failures = 0

    def check(label: str, actual, expected) -> None:
        nonlocal checks, failures
        checks += 1
        if actual == expected:
            return
        failures += 1
        print(f"FAIL {label}")
        if isinstance(actual, list) and isinstance(expected, list):
            for index, (got, want) in enumerate(zip(actual, expected)):
                if got != want:
                    print(f"     [{index}] expected={str(want)[:60]!r} actual={str(got)[:60]!r}")
        else:
            print(f"     expected={str(expected)[:120]!r}")
            print(f"     actual  ={str(actual)[:120]!r}")

    # 1. Python writes, Node reads.
    python_tokens = python_protect(key_a, SAMPLES)
    node_view = node_job(key_a, "", python_tokens, SAMPLES)
    check("python→node tokens are gAAAAA-shaped", all(t.startswith("gAAAAA") for t in python_tokens[:5]), True)
    check("python→node plaintext round-trip", node_view["revealed"], SAMPLES)
    check("python→node key source", node_view["keySource"], "env")

    # 2. Node writes, Python reads.
    node_tokens = node_view["protected"]
    check("node→python plaintext round-trip", python_reveal(key_a, "", node_tokens), SAMPLES)

    # 3. Rotation: rows under the previous key still read, and are not
    #    reported as current-key ciphertext.
    rotated = node_job(key_b, key_a, python_tokens, SAMPLES)
    check("previous-key rows still decrypt", rotated["revealed"], SAMPLES)
    check("previous-key rows are not rotation candidates", rotated["rotationFlags"][:5], [False] * 5)

    # 4. Tampering is silent: both sides return the input unchanged.
    tampered = python_tokens[0][:-2] + ("AA" if not python_tokens[0].endswith("AA") else "BB")
    check("python leaves a tampered token alone", python_reveal(key_a, "", [tampered]), [tampered])
    check("node leaves a tampered token alone", node_job(key_a, "", [tampered], [""])["revealed"], [tampered])

    # 5. Shape-based idempotence: a plaintext that looks like a token stays put.
    check("python protect() keeps a prefix-shaped plaintext", python_protect(key_a, [PREFIX_VALUE]), [PREFIX_VALUE])
    check(
        "node protect() keeps a prefix-shaped plaintext",
        node_job(key_a, "", [""], [PREFIX_VALUE])["protected"],
        [PREFIX_VALUE],
    )

    # 6. The lookup hash must agree exactly, including non-ASCII.
    check("hash_for_lookup vectors", node_hashes(HASH_VALUES), python_hashes(HASH_VALUES))

    print(f"\nFERNET PARITY {checks - failures}/{checks} identical, {failures} failing")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
