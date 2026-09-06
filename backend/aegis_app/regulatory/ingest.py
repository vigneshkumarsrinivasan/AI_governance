"""CLI: python -m aegis_app.regulatory.ingest [framework_key ...] [--all] [--report]"""

from __future__ import annotations

import json
import sys

from aegis_app.regulatory.db import create_all, session_scope
from aegis_app.regulatory.pipeline import ingest_framework, ingest_all
from aegis_app.regulatory.report import build_readiness_report


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    create_all()

    if "--inventory" in flags:
        from aegis_app.regulatory.inventory import write_manifest, build_manifest
        path = write_manifest()
        man = build_manifest()
        print(f"wrote {path}")
        print(f"  documents found: {man['documents_found']}, unidentified: {man['unidentified']}")
        for fk, files in man["by_framework"].items():
            print(f"  {fk:22} {files}")
        if not args:
            return 0

    if "--report" in flags and not args and "--all" not in flags:
        with session_scope() as s:
            print(json.dumps(build_readiness_report(s), indent=2, default=str))
        return 0

    with session_scope() as s:
        if "--all" in flags or not args:
            results = ingest_all(s)
        else:
            results = {k: ingest_framework(s, k) for k in args}

    for key, r in results.items():
        status = r.get("status")
        cov = r.get("coverage", {})
        print(f"\n=== {key} -> {status} ===")
        if "error" in r:
            print(f"   error: {r['error']}")
        if cov:
            print("   coverage: " + ", ".join(f"{k}={v}" for k, v in cov.items()))
        if r.get("expected_counts"):
            print(f"   expected: {r['expected_counts']}")
        if r.get("counts"):
            print(f"   ingested: {r['counts']}")
        for b in r.get("blocking_reasons", [])[:8]:
            print(f"   blocker: {b}")

    if "--report" in flags:
        with session_scope() as s:
            print("\n" + json.dumps(build_readiness_report(s), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
