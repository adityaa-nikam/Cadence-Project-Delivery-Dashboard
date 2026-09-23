"""
Cadence AI Evaluation Metrics Engine.

Normalizes predictions, performs semantic comparison against ground truth,
calculates evaluation metrics, error analyses, and breakdown groups.
"""

from typing import Any, Dict, List, Tuple


def normalize_string(s: str) -> str:
    """Normalize string by stripping whitespace and lowercasing."""
    if not s:
        return ""
    return s.strip().lower()


def compare_status_change(expected_change: Dict[str, Any], predicted_change: Dict[str, Any]) -> bool:
    """
    Semantically compare expected vs predicted status change.
    Matches entity_name and proposed_status (case-insensitive).
    """
    exp_entity = normalize_string(expected_change.get("entity_name", ""))
    pred_entity = normalize_string(predicted_change.get("entity_name", ""))
    
    exp_status = normalize_string(expected_change.get("proposed_status", ""))
    pred_status = normalize_string(predicted_change.get("proposed_status", ""))

    return exp_entity == pred_entity and exp_status == pred_status


def evaluate_example(example: Dict[str, Any], prediction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate a single prediction against ground truth example.
    Returns per-example evaluation results and error classification.
    """
    expected_no_change = example.get("expected_no_change", False)
    expected_status_changes = example.get("expected_status_changes", [])
    expected_affected = [normalize_string(m) for m in example.get("expected_affected_milestones", [])]
    expected_risks = example.get("expected_risks", [])

    predicted_status_changes = prediction.get("status_changes", []) or []
    predicted_affected = [normalize_string(m) for m in prediction.get("affected_milestones", []) or []]
    predicted_risks = prediction.get("risks", []) or []
    pipeline_error = prediction.get("error") is not None

    # 1. No-Change Evaluation
    no_change_correct = False
    if expected_no_change:
        # Expected no change -> correct ONLY if zero status changes proposed
        no_change_correct = (len(predicted_status_changes) == 0)

    # 2. Status Changes Precision / Recall / F1 components
    tp_status = 0
    fp_status = 0
    fn_status = 0

    matched_pred_indices = set()
    for exp_sc in expected_status_changes:
        match_found = False
        for idx, pred_sc in enumerate(predicted_status_changes):
            if idx not in matched_pred_indices and compare_status_change(exp_sc, pred_sc):
                tp_status += 1
                matched_pred_indices.add(idx)
                match_found = True
                break
        if not match_found:
            fn_status += 1

    fp_status = len(predicted_status_changes) - len(matched_pred_indices)

    # 3. Affected Milestone Entity Match
    entity_tp = 0
    for m in expected_affected:
        if m in predicted_affected:
            entity_tp += 1
    entity_accuracy = (entity_tp / len(expected_affected)) if expected_affected else (1.0 if not predicted_affected else 0.0)

    # 4. Risk Detection Evaluation
    exp_has_risk = len(expected_risks) > 0
    pred_has_risk = len(predicted_risks) > 0
    risk_tp = 1 if (exp_has_risk and pred_has_risk) else 0
    risk_fp = 1 if (not exp_has_risk and pred_has_risk) else 0
    risk_fn = 1 if (exp_has_risk and not pred_has_risk) else 0

    # 5. Error Classification
    error_type = None
    is_correct = False

    if expected_no_change:
        if len(predicted_status_changes) > 0:
            error_type = "FALSE_POSITIVE"
        else:
            is_correct = True
    else:
        if len(expected_status_changes) > 0 and len(predicted_status_changes) == 0:
            error_type = "FALSE_NEGATIVE"
        elif tp_status == len(expected_status_changes) and fp_status == 0:
            is_correct = True
        else:
            error_type = "MISCLASSIFICATION"

    return {
        "id": example.get("id"),
        "category": example.get("category"),
        "difficulty": example.get("difficulty"),
        "is_correct": is_correct,
        "error_type": error_type,
        "expected_no_change": expected_no_change,
        "no_change_correct": no_change_correct,
        "tp_status": tp_status,
        "fp_status": fp_status,
        "fn_status": fn_status,
        "entity_accuracy": entity_accuracy,
        "risk_tp": risk_tp,
        "risk_fp": risk_fp,
        "risk_fn": risk_fn,
        "confidence": prediction.get("overall_confidence", 0.0),
        "latency": prediction.get("latency", 0.0),
        "pipeline_error": pipeline_error,
        "input_text": example.get("input_text"),
        "expected_status_changes": expected_status_changes,
        "predicted_status_changes": predicted_status_changes,
        "predicted_summary": prediction.get("summary", ""),
        "predicted_risks": predicted_risks,
    }


def compute_aggregate_metrics(eval_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute total aggregate evaluation metrics from a list of per-example evaluation results.
    """
    total = len(eval_results)
    if total == 0:
        return {
            "total_examples": 0,
            "overall_accuracy": 0.0,
            "no_change_accuracy": 0.0,
            "status_precision": 0.0,
            "status_recall": 0.0,
            "status_f1": 0.0,
            "entity_accuracy": 0.0,
            "risk_precision": 0.0,
            "risk_recall": 0.0,
            "false_positive_rate": 0.0,
            "false_negative_rate": 0.0,
            "average_confidence": 0.0,
            "average_latency": 0.0,
            "failure_rate": 0.0,
        }

    correct_count = sum(1 for r in eval_results if r["is_correct"])
    overall_accuracy = correct_count / total

    # No change examples
    no_change_examples = [r for r in eval_results if r["expected_no_change"]]
    no_change_correct_count = sum(1 for r in no_change_examples if r["no_change_correct"])
    no_change_accuracy = (no_change_correct_count / len(no_change_examples)) if no_change_examples else 1.0

    # Status precision / recall / F1
    total_tp = sum(r["tp_status"] for r in eval_results)
    total_fp = sum(r["fp_status"] for r in eval_results)
    total_fn = sum(r["fn_status"] for r in eval_results)

    status_precision = (total_tp / (total_tp + total_fp)) if (total_tp + total_fp) > 0 else 0.0
    status_recall = (total_tp / (total_tp + total_fn)) if (total_tp + total_fn) > 0 else 0.0
    status_f1 = (2 * status_precision * status_recall / (status_precision + status_recall)) if (status_precision + status_recall) > 0 else 0.0

    # Entity accuracy
    entity_accuracy = sum(r["entity_accuracy"] for r in eval_results) / total

    # Risk precision / recall
    risk_tp = sum(r["risk_tp"] for r in eval_results)
    risk_fp = sum(r["risk_fp"] for r in eval_results)
    risk_fn = sum(r["risk_fn"] for r in eval_results)

    risk_precision = (risk_tp / (risk_tp + risk_fp)) if (risk_tp + risk_fp) > 0 else 0.0
    risk_recall = (risk_tp / (risk_tp + risk_fn)) if (risk_tp + risk_fn) > 0 else 0.0

    # False positive / negative rates
    negative_ground_truth_count = len(no_change_examples)
    fp_count = sum(1 for r in eval_results if r["error_type"] == "FALSE_POSITIVE")
    false_positive_rate = (fp_count / negative_ground_truth_count) if negative_ground_truth_count > 0 else 0.0

    positive_ground_truth_count = total - negative_ground_truth_count
    fn_count = sum(1 for r in eval_results if r["error_type"] in ["FALSE_NEGATIVE", "MISCLASSIFICATION"])
    false_negative_rate = (fn_count / positive_ground_truth_count) if positive_ground_truth_count > 0 else 0.0

    # Averages
    avg_confidence = sum(r["confidence"] for r in eval_results) / total
    avg_latency = sum(r["latency"] for r in eval_results) / total
    failure_count = sum(1 for r in eval_results if r["pipeline_error"])
    failure_rate = failure_count / total

    return {
        "total_examples": total,
        "overall_accuracy": round(overall_accuracy, 4),
        "no_change_accuracy": round(no_change_accuracy, 4),
        "status_precision": round(status_precision, 4),
        "status_recall": round(status_recall, 4),
        "status_f1": round(status_f1, 4),
        "entity_accuracy": round(entity_accuracy, 4),
        "risk_precision": round(risk_precision, 4),
        "risk_recall": round(risk_recall, 4),
        "false_positive_rate": round(false_positive_rate, 4),
        "false_negative_rate": round(false_negative_rate, 4),
        "average_confidence": round(avg_confidence, 4),
        "average_latency": round(avg_latency, 4),
        "failure_rate": round(failure_rate, 4),
    }


def compute_group_breakdowns(eval_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute breakdown metrics by category, difficulty, and confidence signal level.
    """
    # Category breakdown
    categories: Dict[str, List[Dict[str, Any]]] = {}
    for r in eval_results:
        cat = r["category"]
        categories.setdefault(cat, []).append(r)

    category_breakdown = {}
    for cat, items in categories.items():
        corr = sum(1 for i in items if i["is_correct"])
        category_breakdown[cat] = {
            "count": len(items),
            "correct": corr,
            "accuracy": round(corr / len(items), 4),
            "fp_count": sum(1 for i in items if i["error_type"] == "FALSE_POSITIVE"),
            "fn_count": sum(1 for i in items if i["error_type"] == "FALSE_NEGATIVE"),
        }

    # Difficulty breakdown
    difficulties: Dict[str, List[Dict[str, Any]]] = {}
    for r in eval_results:
        diff = r["difficulty"]
        difficulties.setdefault(diff, []).append(r)

    difficulty_breakdown = {}
    for diff in ["easy", "medium", "hard"]:
        items = difficulties.get(diff, [])
        if items:
            corr = sum(1 for i in items if i["is_correct"])
            difficulty_breakdown[diff] = {
                "count": len(items),
                "correct": corr,
                "accuracy": round(corr / len(items), 4),
            }

    # Confidence signal analysis
    high_conf = [r for r in eval_results if r["confidence"] >= 0.85]
    med_conf = [r for r in eval_results if 0.60 <= r["confidence"] < 0.85]
    low_conf = [r for r in eval_results if r["confidence"] < 0.60]

    def calc_conf_bucket(items: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not items:
            return {"count": 0, "accuracy": 0.0}
        corr = sum(1 for i in items if i["is_correct"])
        return {"count": len(items), "accuracy": round(corr / len(items), 4)}

    correct_items = [r for r in eval_results if r["is_correct"]]
    incorrect_items = [r for r in eval_results if not r["is_correct"]]

    avg_conf_correct = (sum(r["confidence"] for r in correct_items) / len(correct_items)) if correct_items else 0.0
    avg_conf_incorrect = (sum(r["confidence"] for r in incorrect_items) / len(incorrect_items)) if incorrect_items else 0.0

    confidence_analysis = {
        "high_confidence_bucket": calc_conf_bucket(high_conf),
        "medium_confidence_bucket": calc_conf_bucket(med_conf),
        "low_confidence_bucket": calc_conf_bucket(low_conf),
        "avg_confidence_correct": round(avg_conf_correct, 4),
        "avg_confidence_incorrect": round(avg_conf_incorrect, 4),
    }

    return {
        "category_breakdown": category_breakdown,
        "difficulty_breakdown": difficulty_breakdown,
        "confidence_analysis": confidence_analysis,
    }
