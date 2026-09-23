"""
Cadence AI Evaluation Runner CLI & Reporting Engine.

Usage:
  python -m evaluation.runner [--limit N] [--category CAT] [--model MODEL] [--no-api] [--update-baseline]
"""

import argparse
from datetime import datetime
import json
import os
import sys
import time
from types import SimpleNamespace
from typing import Any, Dict, List

from ai_helper import parse_update, GROQ_MODEL
from evaluation.metrics import compute_aggregate_metrics, compute_group_breakdowns, evaluate_example

# Configurable regression threshold
MAX_ALLOWED_F1_DROP = 0.03

DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset.json")
BASELINE_PATH = os.path.join(os.path.dirname(__file__), "baseline.json")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "latest.json")
REPORT_MD_PATH = os.path.join(REPORTS_DIR, "latest.md")


def load_dataset(dataset_path: str = DATASET_PATH) -> List[Dict[str, Any]]:
    """Load benchmark dataset from JSON file."""
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset file not found at {dataset_path}")
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _mock_predict_no_api(example: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic test fixture generator for --no-api evaluator testing.
    Simulates model output with realistic accuracy (approx 91%).
    """
    category = example.get("category", "")
    difficulty = example.get("difficulty", "easy")
    
    # Intentionally simulate realistic errors on specific hard edge cases to exercise metric calculations
    if category in ["ambiguous_update", "negation"] and difficulty == "hard":
        # Simulated false positive
        return {
            "summary": "Simulated ambiguous status change.",
            "affected_milestones": example.get("expected_affected_milestones", []),
            "status_changes": [
                {
                    "entity_type": "Milestone",
                    "entity_name": example.get("expected_affected_milestones", ["Unknown"])[0] if example.get("expected_affected_milestones") else "Unknown",
                    "previous_status": "Blocked",
                    "proposed_status": "Done",
                    "confidence": 0.65
                }
            ],
            "risks": [],
            "overall_confidence": 0.65,
            "latency": 0.05,
            "error": None
        }
    
    # Correct deterministic output for all normal fixture tests
    status_changes = []
    for sc in example.get("expected_status_changes", []):
        status_changes.append({
            "entity_type": "Milestone",
            "entity_name": sc["entity_name"],
            "previous_status": sc.get("previous_status"),
            "proposed_status": sc["proposed_status"],
            "confidence": 0.92
        })

    risks = []
    for r in example.get("expected_risks", []):
        risks.append({
            "title": r["title"],
            "severity": r["severity"],
            "impact": "Potential schedule impact",
            "recommended_action": "Escalate to lead engineer",
            "affected_milestone": r.get("affected_milestone"),
            "confidence": 0.88
        })

    return {
        "summary": f"Executive summary for {example['id']}",
        "affected_milestones": example.get("expected_affected_milestones", []),
        "status_changes": status_changes,
        "risks": risks,
        "overall_confidence": 0.90 if not example.get("expected_no_change") else 0.85,
        "latency": 0.02,
        "error": None
    }


def run_evaluation(
    dataset: List[Dict[str, Any]],
    model_name: str = GROQ_MODEL,
    no_api: bool = False,
    limit: int | None = None,
    category_filter: str | None = None
) -> Dict[str, Any]:
    """
    Run evaluation suite over dataset using production parse_update extraction function or no-api fixtures.
    """
    filtered_dataset = dataset
    if category_filter:
        filtered_dataset = [d for d in filtered_dataset if d.get("category") == category_filter]
    if limit and limit > 0:
        filtered_dataset = filtered_dataset[:limit]

    print(f"\n========================================================")
    print(f"CADENCE AI EVALUATION RUNNER")
    print(f"========================================================")
    print(f"Model: {model_name} | Mode: {'DETERMINISTIC NO-API' if no_api else 'REAL API'}")
    print(f"Dataset size: {len(filtered_dataset)} examples (Total available: {len(dataset)})\n")

    eval_results = []
    
    for idx, example in enumerate(filtered_dataset, 1):
        print(f"[{idx}/{len(filtered_dataset)}] Evaluating {example['id']} ({example['category']} / {example['difficulty']})...", end="", flush=True)

        milestones_struct = [
            SimpleNamespace(title=m["title"], status=m["status"], internal_only=False)
            for m in example.get("milestones", [])
        ]

        start_time = time.time()
        if no_api:
            pred = _mock_predict_no_api(example)
        else:
            try:
                # Call existing production AI extraction pipeline
                pred = parse_update(example["input_text"], milestones_struct)
                pred["latency"] = round(time.time() - start_time, 3)
            except Exception as e:
                pred = {
                    "summary": f"Error: {str(e)}",
                    "affected_milestones": [],
                    "status_changes": [],
                    "risks": [],
                    "overall_confidence": 0.0,
                    "latency": round(time.time() - start_time, 3),
                    "error": str(e)
                }

        result = evaluate_example(example, pred)
        eval_results.append(result)

        status_str = "[PASS]" if result["is_correct"] else f"[FAIL] ({result['error_type']})"
        print(f" {status_str}")

    # Compute Aggregate Metrics & Group Breakdowns
    metrics = compute_aggregate_metrics(eval_results)
    breakdowns = compute_group_breakdowns(eval_results)

    # Perform Baseline Regression Check
    baseline = {}
    regression_status = {"status": "UNKNOWN", "delta_f1": 0.0, "passed": True}
    if os.path.exists(BASELINE_PATH):
        try:
            with open(BASELINE_PATH, "r", encoding="utf-8") as f:
                baseline = json.load(f)
            baseline_f1 = baseline.get("metrics", {}).get("status_f1", 0.0)
            current_f1 = metrics["status_f1"]
            delta_f1 = round(current_f1 - baseline_f1, 4)
            passed = delta_f1 >= -MAX_ALLOWED_F1_DROP
            regression_status = {
                "status": "PASS" if passed else "FAIL",
                "baseline_f1": baseline_f1,
                "current_f1": current_f1,
                "delta_f1": delta_f1,
                "max_allowed_drop": MAX_ALLOWED_F1_DROP,
                "passed": passed
            }
        except Exception as e:
            print(f"Warning: Could not check regression baseline: {e}")

    # Build Final Report Output Object
    report_data = {
        "run_info": {
            "evaluation_version": "v1.0",
            "prompt_version": "update_extraction_v1",
            "schema_version": "ProjectUpdateAnalysis_v2",
            "dataset_version": "dataset_v1",
            "timestamp": datetime.now().isoformat(),
            "model": model_name,
            "mode": "deterministic_no_api" if no_api else "real_api",
            "total_evaluated": len(eval_results),
        },
        "overall_metrics": metrics,
        "category_breakdown": breakdowns["category_breakdown"],
        "difficulty_breakdown": breakdowns["difficulty_breakdown"],
        "confidence_analysis": breakdowns["confidence_analysis"],
        "regression_check": regression_status,
        "eval_results": eval_results,
    }

    return report_data


def save_reports(report_data: Dict[str, Any]):
    """Save machine-readable JSON report and human-readable Markdown report."""
    os.makedirs(REPORTS_DIR, exist_ok=True)

    # 1. Save JSON Report
    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"\nSaved machine-readable report to {REPORT_JSON_PATH}")

    # 2. Generate and Save Markdown Report
    run_info = report_data["run_info"]
    metrics = report_data["overall_metrics"]
    reg = report_data["regression_check"]
    cat_b = report_data["category_breakdown"]
    diff_b = report_data["difficulty_breakdown"]
    conf_a = report_data["confidence_analysis"]
    eval_results = report_data["eval_results"]

    failed_cases = [r for r in eval_results if not r["is_correct"]]

    md_lines = [
        "# Cadence AI Evaluation Report",
        "",
        "## Run Information",
        f"- **Model**: `{run_info['model']}`",
        f"- **Execution Mode**: `{run_info['mode']}`",
        f"- **Prompt Version**: `{run_info['prompt_version']}`",
        f"- **Dataset**: `{run_info['dataset_version']}` ({run_info['total_evaluated']} examples)",
        f"- **Timestamp**: `{run_info['timestamp']}`",
        "",
        "## Overall Metrics",
        f"- **Overall Accuracy**: `{metrics['overall_accuracy'] * 100:.1f}%`",
        f"- **Status Precision**: `{metrics['status_precision']:.4f}`",
        f"- **Status Recall**: `{metrics['status_recall']:.4f}`",
        f"- **Status F1 Score**: `{metrics['status_f1']:.4f}`",
        f"- **No-Change Detection Accuracy**: `{metrics['no_change_accuracy'] * 100:.1f}%`",
        f"- **False Positive Rate**: `{metrics['false_positive_rate'] * 100:.1f}%`",
        f"- **False Negative Rate**: `{metrics['false_negative_rate'] * 100:.1f}%`",
        f"- **Entity Matching Accuracy**: `{metrics['entity_accuracy'] * 100:.1f}%`",
        f"- **Risk Detection Precision**: `{metrics['risk_precision']:.4f}`",
        f"- **Risk Detection Recall**: `{metrics['risk_recall']:.4f}`",
        f"- **Average Confidence**: `{metrics['average_confidence']:.4f}`",
        f"- **Average Latency**: `{metrics['average_latency']:.3f}s`",
        f"- **Pipeline Failure Rate**: `{metrics['failure_rate'] * 100:.1f}%`",
        "",
        "## Regression Check",
        f"- **Status**: `{'✅ PASS' if reg.get('passed', True) else '❌ FAIL'}`",
        f"- **Baseline F1**: `{reg.get('baseline_f1', 0.0):.4f}`",
        f"- **Current F1**: `{reg.get('current_f1', 0.0):.4f}`",
        f"- **Difference**: `{reg.get('delta_f1', 0.0):+.4f}` (Max allowed drop: `{reg.get('max_allowed_drop', 0.03)}`)",
        "",
        "## Difficulty Performance",
        "| Difficulty | Count | Correct | Accuracy |",
        "| :--- | :--- | :--- | :--- |",
    ]

    for diff, val in diff_b.items():
        md_lines.append(f"| {diff.capitalize()} | {val['count']} | {val['correct']} | {val['accuracy'] * 100:.1f}% |")

    md_lines.extend([
        "",
        "## Category Performance",
        "| Category | Count | Correct | Accuracy | False Positives | False Negatives |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    for cat, val in cat_b.items():
        md_lines.append(f"| `{cat}` | {val['count']} | {val['correct']} | {val['accuracy'] * 100:.1f}% | {val['fp_count']} | {val['fn_count']} |")

    md_lines.extend([
        "",
        "## Model Confidence Analysis",
        "| Confidence Range | Count | Accuracy |",
        "| :--- | :--- | :--- |",
        f"| High (>= 0.85) | {conf_a['high_confidence_bucket']['count']} | {conf_a['high_confidence_bucket']['accuracy'] * 100:.1f}% |",
        f"| Medium (0.60 - 0.84) | {conf_a['medium_confidence_bucket']['count']} | {conf_a['medium_confidence_bucket']['accuracy'] * 100:.1f}% |",
        f"| Low (< 0.60) | {conf_a['low_confidence_bucket']['count']} | {conf_a['low_confidence_bucket']['accuracy'] * 100:.1f}% |",
        "",
        f"- **Avg Confidence for Correct Predictions**: `{conf_a['avg_confidence_correct']:.4f}`",
        f"- **Avg Confidence for Incorrect Predictions**: `{conf_a['avg_confidence_incorrect']:.4f}`",
        "",
        "## Error Analysis (Failed Examples)",
    ])

    if failed_cases:
        for fc in failed_cases:
            md_lines.extend([
                f"### ❌ {fc['id']} (`{fc['category']}` / `{fc['difficulty']}`)",
                f"- **Error Type**: `{fc['error_type']}`",
                f"- **Input Text**: *\"{fc['input_text']}\"*",
                f"- **Expected Changes**: `{json.dumps(fc['expected_status_changes'])}`",
                f"- **Predicted Changes**: `{json.dumps(fc['predicted_status_changes'])}`",
                f"- **Predicted Summary**: *\"{fc['predicted_summary']}\"*",
                "",
            ])
    else:
        md_lines.append("🎉 Zero failed cases! 100% evaluation accuracy.")

    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"Saved human-readable report to {REPORT_MD_PATH}\n")


def update_baseline_file(metrics: Dict[str, Any]):
    """Update baseline.json with current run metrics."""
    new_baseline = {
        "evaluation_version": "v1.0",
        "prompt_version": "update_extraction_v1",
        "dataset_version": "dataset_v1",
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics
    }
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(new_baseline, f, indent=2)
    print(f"Updated baseline metrics in {BASELINE_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Cadence AI Evaluation & Regression System")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of dataset examples to evaluate")
    parser.add_argument("--category", type=str, default=None, help="Evaluate specific dataset category")
    parser.add_argument("--model", type=str, default=GROQ_MODEL, help="Model name to evaluate")
    parser.add_argument("--no-api", action="store_true", help="Run deterministic test mode without external API calls")
    parser.add_argument("--update-baseline", action="store_true", help="Overwrite baseline.json with current run metrics")

    args = parser.parse_args()

    dataset = load_dataset()
    report_data = run_evaluation(
        dataset=dataset,
        model_name=args.model,
        no_api=args.no_api,
        limit=args.limit,
        category_filter=args.category
    )

    save_reports(report_data)

    if args.update_baseline:
        update_baseline_file(report_data["overall_metrics"])

    reg = report_data["regression_check"]
    if not reg.get("passed", True):
        print("[REGRESSION WARNING] F1 score dropped beyond configured threshold!")
        sys.exit(1)


if __name__ == "__main__":
    main()
