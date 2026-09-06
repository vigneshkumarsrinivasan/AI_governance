"""CLI for the regulatory ingestion subsystem.

    python -m aegis_app.regulatory.ingest --inventory        # hash + inventory operator docs
    python -m aegis_app.regulatory.ingest --all              # ingest every framework
    python -m aegis_app.regulatory.ingest eu_ai_act gdpr     # ingest specific frameworks
    python -m aegis_app.regulatory.ingest --report           # print the readiness report
    (flags compose: --inventory --all --report runs all three, in that order)
"""

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

    did_something = False

    if "--inventory" in flags:
        from aegis_app.regulatory.inventory import write_manifest, build_manifest
        path = write_manifest()
        man = build_manifest()
        print(f"wrote {path}")
        print(f"  documents found: {man['documents_found']}, unidentified: {man['unidentified']}")
        for fk, files in man["by_framework"].items():
            print(f"  {fk:22} {files}")
        did_something = True

    if "--all" in flags or args:
        with session_scope() as s:
            results = ingest_all(s) if "--all" in flags else {k: ingest_framework(s, k) for k in args}
        for key, r in results.items():
            cov = r.get("coverage", {})
            print(f"\n=== {key} -> {r.get('status')} ===")
            if "error" in r:
                print(f"   error: {r['error']}")
            if cov:
                print("   coverage: " + ", ".join(f"{k}={v}" for k, v in cov.items()))
            if r.get("counts"):
                print(f"   ingested: {r['counts']}")
            for b in r.get("blocking_reasons", [])[:8]:
                print(f"   blocker: {b}")
        did_something = True

    if "--report" in flags or not did_something:
        with session_scope() as s:
            print(("\n" if did_something else "") + json.dumps(build_readiness_report(s), indent=2, default=str))

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
