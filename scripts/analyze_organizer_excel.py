"""CLI: analyze the organizer historical arrears Excel and emit aggregated JSON.

Usage:
    python scripts/analyze_organizer_excel.py --input "data/RescheduleArrears.xlsx"

Outputs (under data/processed/ by default):
    organizer_insights.json   full aggregated insight object
    risk_buckets.json         overdue-month risk bucket distribution
    proactive_scan.json       anonymized high-risk patterns from the risk layer

Everything written is aggregate / anonymized — no raw identifiable record is
saved. Safe to commit the processed JSON for the demo/pitch.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make the backend package importable whether run from repo root or elsewhere.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def _fmt(n) -> str:
    try:
        return f"{float(n):,.0f}"
    except (TypeError, ValueError):
        return str(n)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze the organizer arrears Excel.")
    parser.add_argument(
        "--input",
        default=str(_REPO_ROOT / "data" / "RescheduleArrears.xlsx"),
        help="Path to RescheduleArrears.xlsx",
    )
    parser.add_argument(
        "--outdir",
        default=str(_REPO_ROOT / "data" / "processed"),
        help="Directory to write the aggregated JSON files into.",
    )
    args = parser.parse_args(argv)

    from app.data.organizer_dataset import load_organizer_dataset
    from app.services import historical_insights_service as H
    from app.services import risk_forecaster as R

    ds = load_organizer_dataset(args.input)
    if not ds.loaded:
        print(f"[!] Dataset not loaded: {ds.message}", file=sys.stderr)
        print(f"    Expected file at: {ds.source_path}", file=sys.stderr)
        return 2

    insights = H.compute_insights(ds)
    buckets = H.risk_buckets(ds)
    scan = R.proactive_scan(ds)
    edge = H.policy_edge_cases(ds)
    samples = H.sample_patterns(ds)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    writes = {
        "organizer_insights.json": insights,
        "risk_buckets.json": buckets,
        "proactive_scan.json": scan,
        "policy_edge_cases.json": edge,
        "sample_patterns.json": samples,
    }
    for name, payload in writes.items():
        path = outdir / name
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        print(f"[+] wrote {path}")

    # ── human-readable summary ───────────────────────────────────────────────
    t = insights["totals"]
    m = insights["medians"]
    print("\n" + "=" * 60)
    print("  ORGANIZER HISTORICAL ARREARS — KEY INSIGHTS")
    print("=" * 60)
    print(f"  Source           : {ds.source_path}")
    print(f"  Years covered    : {t['year_span']}  (sheets: {', '.join(t['sheets'])})")
    print(f"  Raw records      : {t['raw_records']:,}")
    print(f"  Usable records   : {t['usable_records']:,}  (dropped {t['dropped_records']:,})")
    print("  ---- medians ----")
    print(f"  Salary           : AED {_fmt(m['current_salary'])}")
    print(f"  Overdue amount   : AED {_fmt(m['over_due_amt'])}")
    print(f"  Overdue months   : {m['over_due_months']}")
    print(f"  Current EMI      : AED {_fmt(m['current_emi_amt'])}")
    print(f"  New EMI          : AED {_fmt(m['new_emi_amt'])}")
    print(f"  Current EMI ratio: {m['current_emi_ratio']}")
    print(f"  Approval days    : {m['approval_duration_days']}")
    print("  ---- request type split ----")
    for k, v in insights["request_type_split"].items():
        print(f"    {k:<22} {v['count']:>5}  ({v['percent']}%)")
    print("  ---- overdue-month risk buckets ----")
    for b in buckets["distribution"]:
        print(f"    {b['label']:<9} {b['range']:<14} {b['count']:>5}  ({b['percent']}%)")
    ec = insights["deduction_cap_edge_cases"]
    print("  ---- 20% deduction-cap edge cases ----")
    print(
        f"    current EMI > cap: {ec['current_emi']['over_cap']:,} "
        f"({ec['current_emi']['over_cap_percent']}% of {ec['current_emi']['evaluated']:,})"
    )
    print(
        f"    new EMI > cap    : {ec['new_emi']['over_cap']:,} "
        f"({ec['new_emi']['over_cap_percent']}% of {ec['new_emi']['evaluated']:,})"
    )
    print("  ---- proactive scan ----")
    bd = scan["band_distribution"]
    print("    band distribution: " + ", ".join(f"{k} {v['count']}" for k, v in bd.items()))
    print(f"    high-risk rows   : {scan['high_risk_count']:,}  ·  patterns: {len(scan['patterns'])}")
    print("=" * 60)
    print(f"  JSON written to: {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
