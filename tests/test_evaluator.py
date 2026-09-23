"""
Automated unit test suite for the Cadence AI Evaluation & Regression System.
Tests metrics engine, semantic comparison, dataset schema, regression detection,
no-api deterministic execution, and mandatory prerequisite/completion cases.
"""

from types import SimpleNamespace
import unittest

from ai_helper import parse_update
from evaluation.metrics import (
    compare_status_change,
    compute_aggregate_metrics,
    compute_group_breakdowns,
    evaluate_example,
    normalize_string,
)
from evaluation.runner import load_dataset, run_evaluation, MAX_ALLOWED_F1_DROP


class TestAIEvaluatorSystem(unittest.TestCase):
    """Test suite verifying AI Evaluator metrics, schema, and regression engine."""

    def setUp(self):
        self.dataset = load_dataset()

    def test_01_dataset_schema_and_size(self):
        """Verify dataset loads successfully with 100+ items and valid schema."""
        self.assertGreaterEqual(len(self.dataset), 100, "Dataset should contain at least 100 labeled examples")
        
        required_keys = {
            "id", "project_id", "input_text", "milestones",
            "expected_no_change", "expected_status_changes",
            "expected_affected_milestones", "expected_risks",
            "difficulty", "category"
        }

        all_ids = set()
        categories = set()
        for item in self.dataset:
            self.assertTrue(required_keys.issubset(item.keys()), f"Missing keys in {item.get('id')}")
            self.assertNotIn(item["id"], all_ids, f"Duplicate ID: {item['id']}")
            all_ids.add(item["id"])
            categories.add(item["category"])

        self.assertGreaterEqual(len(categories), 15, "Dataset must cover all 15 required categories")

    def test_02_semantic_status_change_comparison(self):
        """Verify normalized semantic comparison of status changes."""
        exp = {"entity_name": "Firewall Rules Configuration", "proposed_status": "Done"}
        pred = {"entity_name": "firewall rules configuration ", "proposed_status": "done"}
        self.assertTrue(compare_status_change(exp, pred))

        pred_wrong = {"entity_name": "Firewall Rules Configuration", "proposed_status": "Blocked"}
        self.assertFalse(compare_status_change(exp, pred_wrong))

    def test_03_no_change_evaluation_logic(self):
        """Verify expected_no_change logic: PASS iff 0 status changes proposed."""
        example = {
            "id": "test_nc",
            "category": "prerequisite_completion",
            "difficulty": "hard",
            "expected_no_change": True,
            "expected_status_changes": [],
            "expected_affected_milestones": ["Firewall Rules Configuration"],
            "expected_risks": []
        }

        # Correct case: zero status changes
        pred_correct = {"status_changes": [], "affected_milestones": ["Firewall Rules Configuration"], "overall_confidence": 0.9}
        res_correct = evaluate_example(example, pred_correct)
        self.assertTrue(res_correct["is_correct"])
        self.assertTrue(res_correct["no_change_correct"])
        self.assertIsNone(res_correct["error_type"])

        # False Positive case: unauthorized status change proposed
        pred_fp = {
            "status_changes": [{"entity_name": "Firewall Rules Configuration", "proposed_status": "Done"}],
            "affected_milestones": ["Firewall Rules Configuration"],
            "overall_confidence": 0.9
        }
        res_fp = evaluate_example(example, pred_fp)
        self.assertFalse(res_fp["is_correct"])
        self.assertFalse(res_fp["no_change_correct"])
        self.assertEqual(res_fp["error_type"], "FALSE_POSITIVE")

    def test_04_precision_recall_f1_calculation(self):
        """Verify status precision, recall, and F1 calculation formulas."""
        eval_results = [
            {"is_correct": True, "error_type": None, "expected_no_change": False, "no_change_correct": False,
             "tp_status": 1, "fp_status": 0, "fn_status": 0, "entity_accuracy": 1.0,
             "risk_tp": 0, "risk_fp": 0, "risk_fn": 0, "confidence": 0.9, "latency": 0.1, "pipeline_error": False},
            {"is_correct": False, "error_type": "FALSE_POSITIVE", "expected_no_change": True, "no_change_correct": False,
             "tp_status": 0, "fp_status": 1, "fn_status": 0, "entity_accuracy": 1.0,
             "risk_tp": 0, "risk_fp": 0, "risk_fn": 0, "confidence": 0.8, "latency": 0.1, "pipeline_error": False},
        ]
        metrics = compute_aggregate_metrics(eval_results)
        
        # TP = 1, FP = 1, FN = 0 -> Precision = 1 / 2 = 0.5, Recall = 1 / 1 = 1.0, F1 = 2*0.5*1.0 / 1.5 = 0.6667
        self.assertEqual(metrics["status_precision"], 0.5)
        self.assertEqual(metrics["status_recall"], 1.0)
        self.assertEqual(metrics["status_f1"], 0.6667)

    def test_05_false_positive_and_false_negative_rates(self):
        """Verify false-positive and false-negative rate calculations."""
        eval_results = [
            {"is_correct": True, "error_type": None, "expected_no_change": True, "no_change_correct": True,
             "tp_status": 0, "fp_status": 0, "fn_status": 0, "entity_accuracy": 1.0,
             "risk_tp": 0, "risk_fp": 0, "risk_fn": 0, "confidence": 0.9, "latency": 0.1, "pipeline_error": False},
            {"is_correct": False, "error_type": "FALSE_POSITIVE", "expected_no_change": True, "no_change_correct": False,
             "tp_status": 0, "fp_status": 1, "fn_status": 0, "entity_accuracy": 1.0,
             "risk_tp": 0, "risk_fp": 0, "risk_fn": 0, "confidence": 0.8, "latency": 0.1, "pipeline_error": False},
            {"is_correct": False, "error_type": "FALSE_NEGATIVE", "expected_no_change": False, "no_change_correct": False,
             "tp_status": 0, "fp_status": 0, "fn_status": 1, "entity_accuracy": 0.0,
             "risk_tp": 0, "risk_fp": 0, "risk_fn": 0, "confidence": 0.7, "latency": 0.1, "pipeline_error": False},
        ]
        metrics = compute_aggregate_metrics(eval_results)

        # 2 negative ground truth examples, 1 FP -> FPR = 1/2 = 0.5
        self.assertEqual(metrics["false_positive_rate"], 0.5)
        # 1 positive ground truth example, 1 FN -> FNR = 1/1 = 1.0
        self.assertEqual(metrics["false_negative_rate"], 1.0)

    def test_06_group_breakdowns_and_confidence_analysis(self):
        """Verify breakdown grouping by category, difficulty, and confidence."""
        eval_results = [
            {"is_correct": True, "error_type": None, "category": "explicit_completion", "difficulty": "easy", "confidence": 0.95},
            {"is_correct": False, "error_type": "FALSE_POSITIVE", "category": "ambiguous_update", "difficulty": "hard", "confidence": 0.55},
        ]
        breakdowns = compute_group_breakdowns(eval_results)

        self.assertIn("explicit_completion", breakdowns["category_breakdown"])
        self.assertEqual(breakdowns["category_breakdown"]["explicit_completion"]["accuracy"], 1.0)
        self.assertEqual(breakdowns["difficulty_breakdown"]["easy"]["accuracy"], 1.0)
        self.assertEqual(breakdowns["difficulty_breakdown"]["hard"]["accuracy"], 0.0)
        self.assertEqual(breakdowns["confidence_analysis"]["high_confidence_bucket"]["accuracy"], 1.0)

    def test_07_empty_dataset_handling(self):
        """Verify compute_aggregate_metrics handles empty lists safely."""
        metrics = compute_aggregate_metrics([])
        self.assertEqual(metrics["total_examples"], 0)
        self.assertEqual(metrics["overall_accuracy"], 0.0)
        self.assertEqual(metrics["status_f1"], 0.0)

    def test_08_malformed_prediction_handling(self):
        """Verify evaluation engine handles malformed or errored predictions without throwing exceptions."""
        example = self.dataset[0]
        malformed_pred = {"status_changes": None, "affected_milestones": None, "error": "Internal Error", "overall_confidence": None}
        res = evaluate_example(example, malformed_pred)
        self.assertIsInstance(res, dict)
        self.assertTrue(res["pipeline_error"])

    def test_09_runner_deterministic_no_api_mode(self):
        """Verify evaluation runner executes in --no-api mode and produces valid report structure."""
        report = run_evaluation(dataset=self.dataset[:10], no_api=True)
        
        self.assertIn("overall_metrics", report)
        self.assertIn("category_breakdown", report)
        self.assertIn("difficulty_breakdown", report)
        self.assertIn("confidence_analysis", report)
        self.assertIn("regression_check", report)
        self.assertEqual(report["run_info"]["mode"], "deterministic_no_api")
        self.assertEqual(len(report["eval_results"]), 10)

    def test_10_mandatory_regression_case_a_prerequisite_completion(self):
        """
        PERMANENT REGRESSION CASE A:
        'Firewall approval has been completed, clearing a prerequisite for firewall rules configuration.'
        Expected: NO automatic milestone status change (expected_no_change = true).
        """
        case_a = next(d for d in self.dataset if d["id"] == "eval_002")
        self.assertTrue(case_a["expected_no_change"])
        self.assertEqual(len(case_a["expected_status_changes"]), 0)

        # Test deterministic mock prediction behavior
        ms_list = [SimpleNamespace(title="Firewall Rules Configuration", status="Blocked", internal_only=False)]
        mock_pred = {"status_changes": [], "affected_milestones": ["Firewall Rules Configuration"], "overall_confidence": 0.9}
        eval_res = evaluate_example(case_a, mock_pred)
        self.assertTrue(eval_res["is_correct"])

    def test_11_mandatory_regression_case_b_explicit_completion(self):
        """
        PERMANENT REGRESSION CASE B:
        'Firewall Rules Configuration is now complete and has been verified by the security team.'
        Expected: Firewall Rules Configuration -> Done.
        """
        case_b = next(d for d in self.dataset if d["id"] == "eval_001")
        self.assertFalse(case_b["expected_no_change"])
        self.assertEqual(len(case_b["expected_status_changes"]), 1)
        self.assertEqual(case_b["expected_status_changes"][0]["proposed_status"], "Done")

        mock_pred = {
            "status_changes": [
                {"entity_type": "Milestone", "entity_name": "Firewall Rules Configuration", "proposed_status": "Done"}
            ],
            "affected_milestones": ["Firewall Rules Configuration"],
            "overall_confidence": 0.95
        }
        eval_res = evaluate_example(case_b, mock_pred)
        self.assertTrue(eval_res["is_correct"])


if __name__ == "__main__":
    unittest.main()
