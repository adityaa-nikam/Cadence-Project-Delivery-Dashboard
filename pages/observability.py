"""
AI Observability & Reliability Operations Center for Cadence Enterprise Platform.
Includes production LLM telemetry, structured JSON logs, and AI Evaluation & Regression System.
"""

import json
import os
import pandas as pd
import streamlit as st
from utils.database import get_db
from utils.db_models import ActivityEventDB, AIEventDB, ProposalDB


REPORT_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "evaluation", "reports", "latest.json")


def render_observability_page() -> None:
    """Render the high-end enterprise AI Observability & Telemetry Center."""
    # Top Header
    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px 24px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <div>
                <div style="font-size: 11px; font-weight: 700; color: #6366F1; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 2px;">
                    AI TELEMETRY & RELIABILITY OPERATIONS
                </div>
                <h1 style="font-size: 26px; font-weight: 800; color: #0F172A; margin: 0; letter-spacing: -0.02em;">
                    AI Observability & Evaluation Center
                </h1>
                <div style="font-size: 13px; color: #64748B; margin-top: 4px;">
                    Real-time execution metrics, LLM latency, confidence signals, human approvals, and benchmark AI evaluation & regression reporting.
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Fetch real telemetry from database
    with get_db() as session:
        ai_events = session.query(AIEventDB).order_by(AIEventDB.created_at.desc()).all()
        activities = session.query(ActivityEventDB).all()
        proposals = session.query(ProposalDB).all()

    total_events = len(ai_events)
    successful = sum(1 for e in ai_events if e.confidence and e.confidence >= 0.6)
    success_rate = (successful / total_events * 100) if total_events > 0 else 100.0

    latencies = [e.latency_ms for e in ai_events if e.latency_ms]
    avg_latency = round(sum(latencies) / len(latencies), 0) if latencies else 0

    confidences = [e.confidence for e in ai_events if e.confidence is not None]
    avg_conf = round((sum(confidences) / len(confidences)) * 100, 1) if confidences else 90.0

    # 1. Top Metrics Bar (Production LLM Telemetry)
    st.markdown("<div style='font-size:14px; font-weight:800; color:#0F172A; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:12px;'>⚡ Production LLM Telemetry</div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("AI EVENTS", total_events)
    m2.metric("SUCCESS RATE", f"{success_rate:.1f}%")
    m3.metric("AVG LATENCY", f"{avg_latency:.0f} ms")
    m4.metric("AVG CONFIDENCE SIGNAL", f"{avg_conf:.1f}%")

    st.markdown("<hr style='border-color:#E2E8F0; margin: 24px 0;'>", unsafe_allow_html=True)

    # 2. AI EVALUATION & REGRESSION SYSTEM DASHBOARD
    st.markdown("<div style='font-size:14px; font-weight:800; color:#0F172A; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:12px;'>🎯 AI Extraction Pipeline Benchmark Evaluation</div>", unsafe_allow_html=True)

    if not os.path.exists(REPORT_JSON_PATH):
        st.info("No benchmark evaluation report found yet. Run `python -m evaluation.runner --no-api` to generate initial evaluation metrics.")
    else:
        try:
            with open(REPORT_JSON_PATH, "r", encoding="utf-8") as f:
                report = json.load(f)

            run_info = report.get("run_info", {})
            metrics = report.get("overall_metrics", {})
            reg = report.get("regression_check", {})
            cat_breakdown = report.get("category_breakdown", {})
            diff_breakdown = report.get("difficulty_breakdown", {})
            conf_analysis = report.get("confidence_analysis", {})
            eval_results = report.get("eval_results", [])

            # KPI Summary Cards for AI Evaluation
            e1, e2, e3, e4 = st.columns(4)
            e1.metric("EVALUATION ACCURACY", f"{metrics.get('overall_accuracy', 0.0) * 100:.1f}%")
            e2.metric("STATUS F1 SCORE", f"{metrics.get('status_f1', 0.0):.4f}")
            e3.metric("FALSE POSITIVE RATE", f"{metrics.get('false_positive_rate', 0.0) * 100:.1f}%")
            e4.metric("BENCHMARK LATENCY", f"{metrics.get('average_latency', 0.0):.3f} s")

            # Regression Status Banner
            passed = reg.get("passed", True)
            reg_status_str = "✅ No significant regression" if passed else "⚠️ Regression Warning Detected"
            reg_bg = "#F0FDF4" if passed else "#FEF2F2"
            reg_fg = "#15803D" if passed else "#B91C1C"
            reg_border = "#BBF7D0" if passed else "#FCA5A5"

            st.markdown(f"""
            <div style="background:{reg_bg}; border:1px solid {reg_border}; border-radius:10px; padding:14px 20px; margin: 16px 0; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="font-weight:800; font-size:15px; color:{reg_fg};">{reg_status_str}</span>
                    <span style="font-size:12px; color:#64748B; margin-left:12px;">Model: <b>{run_info.get('model')}</b> | Prompt: <b>{run_info.get('prompt_version')}</b> | Dataset: <b>{run_info.get('dataset_version')}</b> ({run_info.get('total_evaluated')} items)</span>
                </div>
                <div style="font-size:13px; font-weight:700; color:{reg_fg};">
                    Baseline F1: {reg.get('baseline_f1', 0.0):.4f} | Current F1: {reg.get('current_f1', 0.0):.4f} (Δ {reg.get('delta_f1', 0.0):+.4f})
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Performance Tabs
            tab_cat, tab_diff, tab_conf, tab_failures = st.tabs([
                "📂 Performance by Category",
                "⚡ Performance by Difficulty",
                "📈 Model Confidence Signal Analysis",
                "❌ Failed Example Inspector"
            ])

            with tab_cat:
                cat_data = []
                for cat_name, c_info in cat_breakdown.items():
                    cat_data.append({
                        "Category": cat_name,
                        "Examples": c_info.get("count", 0),
                        "Correct": c_info.get("correct", 0),
                        "Accuracy (%)": f"{c_info.get('accuracy', 0.0) * 100:.1f}%",
                        "False Positives": c_info.get("fp_count", 0),
                        "False Negatives": c_info.get("fn_count", 0),
                    })
                df_cat = pd.DataFrame(cat_data)
                st.dataframe(df_cat, use_container_width=True, hide_index=True)

            with tab_diff:
                diff_data = []
                for diff_name, d_info in diff_breakdown.items():
                    diff_data.append({
                        "Difficulty Level": diff_name.capitalize(),
                        "Total Examples": d_info.get("count", 0),
                        "Correct Predictions": d_info.get("correct", 0),
                        "Accuracy (%)": f"{d_info.get('accuracy', 0.0) * 100:.1f}%",
                    })
                df_diff = pd.DataFrame(diff_data)
                st.dataframe(df_diff, use_container_width=True, hide_index=True)

            with tab_conf:
                high_b = conf_analysis.get("high_confidence_bucket", {})
                med_b = conf_analysis.get("medium_confidence_bucket", {})
                low_b = conf_analysis.get("low_confidence_bucket", {})

                conf_df = pd.DataFrame([
                    {"Confidence Signal Range": "High (>= 0.85)", "Examples": high_b.get("count", 0), "Accuracy (%)": f"{high_b.get('accuracy', 0.0) * 100:.1f}%"},
                    {"Confidence Signal Range": "Medium (0.60 - 0.84)", "Examples": med_b.get("count", 0), "Accuracy (%)": f"{med_b.get('accuracy', 0.0) * 100:.1f}%"},
                    {"Confidence Signal Range": "Low (< 0.60)", "Examples": low_b.get("count", 0), "Accuracy (%)": f"{low_b.get('accuracy', 0.0) * 100:.1f}%"},
                ])
                st.dataframe(conf_df, use_container_width=True, hide_index=True)

                c_avg1, c_avg2 = st.columns(2)
                c_avg1.info(f"💡 **Avg Confidence for Correct Predictions:** `{conf_analysis.get('avg_confidence_correct', 0.0):.4f}`")
                c_avg2.warning(f"⚠️ **Avg Confidence for Incorrect Predictions:** `{conf_analysis.get('avg_confidence_incorrect', 0.0):.4f}`")

            with tab_failures:
                failed_list = [r for r in eval_results if not r.get("is_correct")]
                if not failed_list:
                    st.success("🎉 Zero evaluation failures detected! All benchmark cases passed.")
                else:
                    st.markdown(f"**Inspecting {len(failed_list)} Failed Evaluation Cases:**")
                    for fc in failed_list:
                        with st.expander(f"❌ CASE {fc.get('id')} — {fc.get('category')} ({fc.get('difficulty')}) | Error: {fc.get('error_type')}"):
                            st.markdown(f"**Input Update Text:** *\"{fc.get('input_text')}\"*")
                            col_exp, col_pred = st.columns(2)
                            with col_exp:
                                st.markdown("**Expected Ground Truth:**")
                                st.code(json.dumps(fc.get("expected_status_changes"), indent=2))
                            with col_pred:
                                st.markdown("**AI Model Prediction:**")
                                st.code(json.dumps(fc.get("predicted_status_changes"), indent=2))

                            st.markdown(f"**AI Reasoning / Summary:** *{fc.get('predicted_summary')}*")

        except Exception as err:
            st.error(f"Error loading evaluation report: {err}")

    st.markdown("<hr style='border-color:#E2E8F0; margin: 24px 0;'>", unsafe_allow_html=True)

    # 3. Recent AI Execution Telemetry Table & Inspection
    st.markdown("<div style='font-size:14px; font-weight:800; color:#0F172A; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:12px;'>🔍 Live Production AI Execution Logs & JSON Telemetry</div>", unsafe_allow_html=True)

    if not ai_events:
        st.markdown("<div class='cadence-empty-state'>No AI telemetry events recorded yet. Log an AI update to populate live execution logs.</div>", unsafe_allow_html=True)
        return

    for event in ai_events[:15]:
        conf_pct = (event.confidence or 0.85) * 100
        conf_bg = "#F0FDF4" if conf_pct >= 85 else ("#FFFBEB" if conf_pct >= 60 else "#FEF2F2")
        conf_fg = "#15803D" if conf_pct >= 85 else ("#B45309" if conf_pct >= 60 else "#B91C1C")
        ts_date = str(event.created_at)[:19].replace("T", " ") if event.created_at else "Recent"

        header_str = f"⚡ {ts_date} | Task: {event.event_type} | Model: {event.model or 'qwen/qwen3.8-27b'} | Latency: {event.latency_ms:.0f}ms | Confidence: {conf_pct:.0f}%"

        with st.expander(header_str):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**Event ID:** `{event.id}`")
                st.markdown(f"**Project Target:** `{event.project_id}`")
                st.markdown(f"**Input Summary:** {event.input_summary or 'Raw update analysis request'}")
            with c2:
                st.markdown(f"""
                <span style="background:{conf_bg}; color:{conf_fg}; padding:4px 12px; border-radius:999px; font-size:12px; font-weight:700;">
                    ● Confidence: {conf_pct:.0f}%
                </span>
                """, unsafe_allow_html=True)

            st.markdown("**Structured Output JSON Payload:**")
            try:
                st.json(json.loads(event.structured_output))
            except Exception:
                st.code(event.structured_output or "{}")
