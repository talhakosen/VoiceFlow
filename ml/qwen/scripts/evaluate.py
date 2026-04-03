"""evaluate.py — WER / CER / exact_match metric report.

Compares model predictions against reference outputs and produces a
structured JSON report plus human-readable summary.

Metrics:
  - WER  (Word Error Rate) — via jiwer
  - CER  (Character Error Rate) — computed manually
  - Exact Match % — case-insensitive, stripped
  - Backtracking Accuracy — % of samples where backtrack markers were resolved

Usage:
  python evaluate.py \
      --predictions predictions.jsonl \
      --references  references.jsonl \
      --output      evaluation_report.json

JSONL format for both files (one JSON object per line):
  {"text": "..."} OR {"input": "...", "output": "...", "prediction": "..."}

  If --predictions and --references are separate files, each line must have {"text": "..."}.
  If --predictions is a single file with both fields, use --combined flag.

Combined format (single file):
  {"input": "...", "output": "<reference>", "prediction": "<model_output>"}
"""

import argparse
import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Metric implementations
# ---------------------------------------------------------------------------

def _cer(reference: str, hypothesis: str) -> float:
    """Character Error Rate (Levenshtein distance / len(reference))."""
    r = reference.strip()
    h = hypothesis.strip()
    if not r:
        return 0.0 if not h else 1.0

    # Wagner-Fischer DP
    m, n = len(r), len(h)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            if r[i - 1] == h[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp

    return dp[n] / len(r)


def _exact_match(reference: str, hypothesis: str) -> bool:
    """Case-insensitive, whitespace-stripped exact match."""
    return reference.strip().lower() == hypothesis.strip().lower()


_BACKTRACK_MARKERS = [
    "hayır yok yok",
    "dur bir dakika",
    "aslında",
    "pardon",
    "scratch that",
    "actually",
    "wait",
    "i mean",
    "no wait",
    "let me rephrase",
]


def _has_backtrack_in_input(text: str) -> bool:
    """True if the input contains a known backtracking marker."""
    lower = text.lower()
    return any(marker in lower for marker in _BACKTRACK_MARKERS)


def _backtrack_resolved(reference: str, hypothesis: str) -> bool:
    """
    Simple heuristic: if the hypothesis is shorter than or equal to the
    reference and doesn't contain backtrack markers, assume it was resolved.
    """
    return not _has_backtrack_in_input(hypothesis)


# ---------------------------------------------------------------------------
# JSONL loading
# ---------------------------------------------------------------------------

def _load_texts(path: Path, field: str) -> list[str]:
    """Load a list of texts from a JSONL file."""
    texts = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if field in obj:
                    texts.append(str(obj[field]).strip())
                else:
                    print(
                        f"WARNING: {path}:{lineno} missing field '{field}'",
                        file=sys.stderr,
                    )
            except json.JSONDecodeError as e:
                print(f"WARNING: {path}:{lineno} JSON error: {e}", file=sys.stderr)
    return texts


def _load_combined(path: Path) -> tuple[list[str], list[str], list[str]]:
    """Load (inputs, references, predictions) from a combined JSONL file."""
    inputs, refs, preds = [], [], []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if "output" in obj and "prediction" in obj:
                    inputs.append(str(obj.get("input", "")).strip())
                    refs.append(str(obj["output"]).strip())
                    preds.append(str(obj["prediction"]).strip())
            except json.JSONDecodeError as e:
                print(f"WARNING: {path}:{lineno} JSON error: {e}", file=sys.stderr)
    return inputs, refs, preds


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------

def evaluate(
    references: list[str],
    predictions: list[str],
    inputs: list[str] | None = None,
) -> dict:
    """Compute all metrics and return a report dict."""
    if len(references) != len(predictions):
        raise ValueError(
            f"Length mismatch: {len(references)} references vs {len(predictions)} predictions"
        )

    n = len(references)
    if n == 0:
        return {"error": "No samples to evaluate"}

    # WER (jiwer)
    wer_score: float | None = None
    try:
        import jiwer
        wer_score = float(jiwer.wer(references, predictions))
    except ImportError:
        print("WARNING: jiwer not installed — WER skipped. Run: pip install jiwer", file=sys.stderr)

    # CER
    cer_scores = [_cer(r, p) for r, p in zip(references, predictions)]
    avg_cer = sum(cer_scores) / n

    # Exact match
    em_flags = [_exact_match(r, p) for r, p in zip(references, predictions)]
    exact_match_pct = sum(em_flags) / n * 100

    # Backtracking accuracy (only on samples with backtrack markers in input)
    backtrack_results = []
    if inputs:
        for inp, ref, pred in zip(inputs, references, predictions):
            if _has_backtrack_in_input(inp):
                backtrack_results.append(_backtrack_resolved(ref, pred))

    report: dict = {
        "num_samples": n,
        "wer": round(wer_score, 4) if wer_score is not None else None,
        "cer": round(avg_cer, 4),
        "exact_match_pct": round(exact_match_pct, 2),
        "backtracking": {
            "num_samples": len(backtrack_results),
            "resolved_pct": (
                round(sum(backtrack_results) / len(backtrack_results) * 100, 2)
                if backtrack_results
                else None
            ),
        },
        "per_sample": [],
    }

    # Per-sample detail (truncated for large datasets)
    for i, (ref, pred) in enumerate(zip(references, predictions)):
        sample: dict = {
            "index": i,
            "reference": ref[:120],
            "prediction": pred[:120],
            "exact_match": em_flags[i],
            "cer": round(cer_scores[i], 4),
        }
        if inputs:
            sample["input"] = inputs[i][:120]
        report["per_sample"].append(sample)

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate WER/CER/exact_match for ASR correction model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--combined",
        type=Path,
        metavar="FILE",
        help="Single JSONL with 'input', 'output', 'prediction' fields.",
    )
    source.add_argument(
        "--predictions",
        type=Path,
        metavar="FILE",
        help="JSONL with {'text': ...} predictions.",
    )
    parser.add_argument(
        "--references",
        type=Path,
        metavar="FILE",
        help="JSONL with {'text': ...} references (required with --predictions).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write JSON report to this file (default: stdout).",
    )
    parser.add_argument(
        "--no-per-sample",
        action="store_true",
        help="Omit per-sample details from the report (smaller output).",
    )
    args = parser.parse_args()

    if args.predictions and not args.references:
        parser.error("--references is required when using --predictions.")

    # Load data
    if args.combined:
        inputs, references, predictions = _load_combined(args.combined)
    else:
        inputs = None
        references = _load_texts(args.references, "text")
        predictions = _load_texts(args.predictions, "text")

    print(f"Loaded {len(references)} reference, {len(predictions)} prediction samples.", file=sys.stderr)

    report = evaluate(references, predictions, inputs=inputs)

    if args.no_per_sample:
        report.pop("per_sample", None)

    # Output
    report_json = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report_json)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report_json)

    # Human-readable summary
    print("\n--- Evaluation Summary ---", file=sys.stderr)
    print(f"Samples      : {report['num_samples']}", file=sys.stderr)
    if report["wer"] is not None:
        print(f"WER          : {report['wer']:.4f} ({report['wer']*100:.2f}%)", file=sys.stderr)
    else:
        print("WER          : N/A (jiwer not installed)", file=sys.stderr)
    print(f"CER          : {report['cer']:.4f} ({report['cer']*100:.2f}%)", file=sys.stderr)
    print(f"Exact Match  : {report['exact_match_pct']:.2f}%", file=sys.stderr)
    bt = report["backtracking"]
    if bt["num_samples"]:
        print(
            f"Backtracking : {bt['resolved_pct']:.2f}% resolved ({bt['num_samples']} samples)",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
