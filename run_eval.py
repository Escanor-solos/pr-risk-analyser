import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("RISK_DISABLE_EMBEDDINGS", "1")

from src.diff_parser import parse_unified_diff
from src.scorer import SEVERITY_ORDER, analyze

CRITICAL_RECALL_MIN = float(os.environ.get("EVAL_CRITICAL_RECALL_MIN", "0.9"))
DATA_DIR = Path(__file__).parent / "tests" / "data" / "sample_diffs"
LABELS = Path(__file__).parent / "eval" / "labeled_diffs.jsonl"


def load_cases():
    for line in LABELS.read_text().splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        diff_path = DATA_DIR / case["file"]
        if not diff_path.exists():
            continue
        yield case["label"], case["file"], case.get("note", ""), parse_unified_diff(diff_path.read_text())


def is_dangerous(label):
    return label in ("high", "critical")


def main() -> int:
    total = 0
    correct = 0
    dangerous_total = dangerous_caught = 0
    safe_total = safe_correct = 0
    conf = defaultdict(lambda: defaultdict(int))
    failures = []

    for label, name, _, files in load_cases():
        total += 1
        pred = analyze(files, use_embeddings=os.environ.get("RISK_DISABLE_EMBEDDINGS") != "1").severity
        conf[label][pred] += 1
        gap = abs(SEVERITY_ORDER[pred] - SEVERITY_ORDER[label])
        if gap <= 1:
            correct += 1
        if is_dangerous(label):
            dangerous_total += 1
            if is_dangerous(pred):
                dangerous_caught += 1
            else:
                failures.append((name, label, pred))
        else:
            safe_total += 1
            if pred in ("low", "medium"):
                safe_correct += 1

    print(f"cases: {total}")
    print(f"within-1-severity accuracy: {correct}/{total} ({correct / total:.0%})")
    print(f"dangerous recall (high+critical): {dangerous_caught}/{dangerous_total}")
    print(f"safe specificity (low+medium):    {safe_correct}/{safe_total}")

    print("\nconfusion (rows=truth, cols=prediction):")
    order = ["low", "medium", "high", "critical"]
    print(f"{'':>10}" + "".join(f"{c:>10}" for c in order))
    for t in order:
        print(f"{t:>10}" + "".join(f"{conf[t][p]:>10}" for p in order))

    if failures:
        print("\nmissed dangerous diffs:")
        for name, truth, pred in failures:
            print(f"  {name}: expected {truth}, got {pred}")

    ok = True
    if dangerous_total and (dangerous_caught / dangerous_total) < CRITICAL_RECALL_MIN:
        print(f"\nFAIL: dangerous recall below {CRITICAL_RECALL_MIN}")
        ok = False
    if total == 0:
        print("\nWARN: no eval cases found")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
