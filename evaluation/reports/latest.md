# Cadence AI Evaluation Report

## Run Information
- **Model**: `qwen/qwen3.8-27b`
- **Execution Mode**: `deterministic_no_api`
- **Prompt Version**: `update_extraction_v1`
- **Dataset**: `dataset_v1` (109 examples)
- **Timestamp**: `2026-09-24T03:37:57.176256`

## Overall Metrics
- **Overall Accuracy**: `98.2%`
- **Status Precision**: `0.9615`
- **Status Recall**: `1.0000`
- **Status F1 Score**: `0.9804`
- **No-Change Detection Accuracy**: `97.0%`
- **False Positive Rate**: `3.0%`
- **False Negative Rate**: `0.0%`
- **Entity Matching Accuracy**: `100.0%`
- **Risk Detection Precision**: `1.0000`
- **Risk Detection Recall**: `1.0000`
- **Average Confidence**: `0.8656`
- **Average Latency**: `0.021s`
- **Pipeline Failure Rate**: `0.0%`

## Regression Check
- **Status**: `✅ PASS`
- **Baseline F1**: `0.9057`
- **Current F1**: `0.9804`
- **Difference**: `+0.0747` (Max allowed drop: `0.03`)

## Difficulty Performance
| Difficulty | Count | Correct | Accuracy |
| :--- | :--- | :--- | :--- |
| Easy | 42 | 42 | 100.0% |
| Medium | 39 | 39 | 100.0% |
| Hard | 28 | 26 | 92.9% |

## Category Performance
| Category | Count | Correct | Accuracy | False Positives | False Negatives |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `explicit_completion` | 10 | 10 | 100.0% | 0 | 0 |
| `blocker` | 10 | 10 | 100.0% | 0 | 0 |
| `unblock` | 8 | 8 | 100.0% | 0 | 0 |
| `progress_no_status_change` | 8 | 8 | 100.0% | 0 | 0 |
| `prerequisite_completion` | 8 | 8 | 100.0% | 0 | 0 |
| `ambiguous_update` | 7 | 7 | 100.0% | 0 | 0 |
| `irrelevant_update` | 7 | 7 | 100.0% | 0 | 0 |
| `multiple_changes` | 8 | 8 | 100.0% | 0 | 0 |
| `risk_detection` | 8 | 8 | 100.0% | 0 | 0 |
| `invalid_malformed_input` | 5 | 5 | 100.0% | 0 | 0 |
| `cross_project_references` | 6 | 6 | 100.0% | 0 | 0 |
| `negation` | 6 | 4 | 66.7% | 2 | 0 |
| `conditional_language` | 6 | 6 | 100.0% | 0 | 0 |
| `future_intent` | 6 | 6 | 100.0% | 0 | 0 |
| `false_friend_names` | 6 | 6 | 100.0% | 0 | 0 |

## Model Confidence Analysis
| Confidence Range | Count | Accuracy |
| :--- | :--- | :--- |
| High (>= 0.85) | 107 | 100.0% |
| Medium (0.60 - 0.84) | 2 | 0.0% |
| Low (< 0.60) | 0 | 0.0% |

- **Avg Confidence for Correct Predictions**: `0.8696`
- **Avg Confidence for Incorrect Predictions**: `0.6500`

## Error Analysis (Failed Examples)
### ❌ eval_092 (`negation` / `hard`)
- **Error Type**: `FALSE_POSITIVE`
- **Input Text**: *"Inventory Sync Setup is not blocked, despite rumours circulating on Slack."*
- **Expected Changes**: `[]`
- **Predicted Changes**: `[{"entity_type": "Milestone", "entity_name": "Inventory Sync Setup", "previous_status": "Blocked", "proposed_status": "Done", "confidence": 0.65}]`
- **Predicted Summary**: *"Simulated ambiguous status change."*

### ❌ eval_093 (`negation` / `hard`)
- **Error Type**: `FALSE_POSITIVE`
- **Input Text**: *"Vendor Sandbox Access is not unblocked; we are still waiting on permissions."*
- **Expected Changes**: `[]`
- **Predicted Changes**: `[{"entity_type": "Milestone", "entity_name": "Vendor Sandbox Access", "previous_status": "Blocked", "proposed_status": "Done", "confidence": 0.65}]`
- **Predicted Summary**: *"Simulated ambiguous status change."*
