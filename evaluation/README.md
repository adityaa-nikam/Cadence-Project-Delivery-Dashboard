# Cadence AI Evaluation & Regression System

> **"Unit tests verify application behavior. AI evaluations measure model behavior."**

The Cadence AI Evaluation System provides systematic, quantifiable, version-controlled measurement of the accuracy, precision, recall, and reliability of Cadence's AI extraction pipeline (`parse_update` in `ai_helper.py`).

---

## Architectural Principles & Target Workflow

### Production vs Evaluation Workflow

**Production Workflow**:
```
Natural-language update -> LLM extraction -> Pydantic validation -> Application validation -> Human approval -> Database
```

**Evaluation Workflow**:
```
Labeled evaluation dataset -> Same AI extraction pipeline -> Predicted structured output -> Ground Truth -> Comparison Engine -> Metrics & Reports -> Regression Check
```

### Safety & Ground Truth Guarantees
1. **SAME Production Extraction Code**: The evaluation system invokes `parse_update` from `ai_helper.py` — the exact same extraction pipeline used in production.
2. **Database Isolation**: Evaluations run in read-only isolation mode. Production database records (`ProjectDB`, `MilestoneDB`, `ProposalDB`, `ActivityEventDB`) remain 100% untouched.
3. **Independent Ground Truth**: Ground truth expectations are manually defined and version-controlled in `dataset.json`. They are **never** generated dynamically using the evaluation model itself.

---

## Benchmark Dataset (`evaluation/dataset.json`)

The evaluation dataset contains 109 version-controlled, labeled test examples across 15 target categories:

| Category | Description | Target Behavior |
| :--- | :--- | :--- |
| `explicit_completion` | Direct statements of milestone completion | Proposed status -> `Done` |
| `blocker` | Updates indicating work is stuck or obstructed | Proposed status -> `Blocked` |
| `unblock` | Updates indicating blocked work has resumed | Proposed status -> `Open` / `In Progress` |
| `progress_no_status_change` | Ongoing work progress without completion | `expected_no_change: true` |
| `prerequisite_completion` | Completion of prerequisite or dependency | `expected_no_change: true` (**CRITICAL**) |
| `ambiguous_update` | Wording like "expects to finish soon" | `expected_no_change: true` |
| `irrelevant_update` | Non-project text (e.g. office lunches, birthdays) | `expected_no_change: true` |
| `multiple_changes` | Single update affecting multiple milestones | Extract all valid status changes |
| `risk_detection` | Operational or schedule risks mentioned | Extract risk title, severity, milestone |
| `invalid_malformed_input` | Empty strings, noise, extreme lengths | Graceful fallback, zero state mutation |
| `cross_project_references` | Updates referencing other projects | No state change on non-target project |
| `negation` | Wording like "is NOT complete" | `expected_no_change: true` |
| `conditional_language` | Wording like "If security approves tomorrow" | `expected_no_change: true` |
| `future_intent` | Wording like "We plan to complete next week" | `expected_no_change: true` |
| `false_friend_names` | Similar milestone titles across projects | Exact entity name resolution |

### Record Schema Example
```json
{
  "id": "eval_001",
  "project_id": "novabridge",
  "input_text": "Firewall Rules Configuration is now complete and has been verified by the security team.",
  "milestones": [
    {"title": "Database Migration", "status": "Blocked"},
    {"title": "Firewall Rules Configuration", "status": "Blocked"}
  ],
  "expected_no_change": false,
  "expected_status_changes": [
    {
      "entity_name": "Firewall Rules Configuration",
      "previous_status": "Blocked",
      "proposed_status": "Done"
    }
  ],
  "expected_affected_milestones": ["Firewall Rules Configuration"],
  "expected_risks": [],
  "difficulty": "easy",
  "category": "explicit_completion"
}
```

---

## Evaluation Metrics Engine (`evaluation/metrics.py`)

Metrics computed during each evaluation run:

1. **Overall Accuracy**: Percentage of examples where all status changes, no-change expectations, and risks match.
2. **No-Change Detection Accuracy**: Percentage of `expected_no_change = true` examples where zero unauthorized status changes were proposed.
3. **Status-Change Precision**: `TP / (TP + FP)` for proposed status changes.
4. **Status-Change Recall**: `TP / (TP + FN)` for proposed status changes.
5. **Status-Change F1 Score**: Harmonic mean of Precision and Recall (`2 * P * R / (P + R)`).
6. **Milestone Entity Matching Accuracy**: Percentage of target milestone titles correctly identified.
7. **Risk Detection Precision & Recall**: Precision and recall of extracted risk events.
8. **False Positive Rate (FPR)**: `FP / Total Negative Ground Truth Examples`.
9. **False Negative Rate (FNR)**: `FN / Total Positive Ground Truth Examples`.
10. **Average Confidence Signal**: Mean `overall_confidence` score emitted by the LLM pipeline.
11. **Average Latency**: Mean execution time per example in seconds.
12. **Pipeline Failure Rate**: Percentage of evaluation calls resulting in API/unhandled errors.

---

## Running Evaluations

Execute via CLI:

```bash
# 1. Deterministic Cost-Free Mode (Used in CI and local test suites)
python -m evaluation.runner --no-api

# 2. Real Groq API Evaluation (Full Dataset)
python -m evaluation.runner

# 3. Evaluate a Small Subset (API Cost Safety)
python -m evaluation.runner --limit 20

# 4. Filter by Specific Category
python -m evaluation.runner --category prerequisite_completion

# 5. Model Comparison Evaluation
python -m evaluation.runner --model llama-3.3-70b-versatile

# 6. Overwrite Stored Baseline
python -m evaluation.runner --update-baseline
```

---

## Regression Detection (`evaluation/baseline.json`)

The evaluation runner compares the current run's Status F1 Score against `evaluation/baseline.json`.

- **Configurable Drop Threshold**: `MAX_ALLOWED_F1_DROP = 0.03` (3.0 percentage points).
- If `current_f1 < (baseline_f1 - MAX_ALLOWED_F1_DROP)`, the runner exits with code `1` and flags `[REGRESSION WARNING]`.

---

## Reports & Dashboard Integration

Each run generates:
- **Machine-readable JSON**: `evaluation/reports/latest.json`
- **Human-readable Markdown**: `evaluation/reports/latest.md`

The **Cadence AI Observability Center** (`pages/observability.py`) automatically reads `latest.json` to display live KPI summary cards, category/difficulty breakdown tables, model confidence correlation charts, and an interactive **Failed Example Inspector**.

---

## Mandatory Permanent Regression Cases

1. **CASE A (Prerequisite Completion)**:
   - *Input*: `"Firewall approval has been completed, clearing a prerequisite for firewall rules configuration."`
   - *Expected*: `expected_no_change: true` (completing a prerequisite is NOT completing the milestone).

2. **CASE B (Explicit Milestone Completion)**:
   - *Input*: `"Firewall Rules Configuration is now complete and has been verified by the security team."`
   - *Expected*: Proposed status transition `Blocked -> Done`.
