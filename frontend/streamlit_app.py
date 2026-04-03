from __future__ import annotations

import html
from typing import Any

import httpx
import streamlit as st


DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
EXAMPLE_QUESTIONS = [
    "Why did delivery success rate drop in Region 3 on 2026-03-31?",
    "What does the escalation policy say about low-confidence cases?",
    "Why did delivery success rate drop in Region 3 and what does the SOP suggest we do next?",
    "Explain the return rate spike in Region 4.",
]


def main() -> None:
    st.set_page_config(
        page_title="Agentic Analytics Copilot",
        page_icon=":bar_chart:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    initialize_session_state()
    inject_styles()

    with st.sidebar:
        render_sidebar()

    render_hero()
    render_control_panel()
    render_workspace()


def initialize_session_state() -> None:
    st.session_state.setdefault("question", EXAMPLE_QUESTIONS[0])
    st.session_state.setdefault("last_payload", None)
    st.session_state.setdefault("health_payload", None)
    st.session_state.setdefault("backend_status", "Unknown")


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

        :root {
            --bg: #f4efe6;
            --paper: rgba(255, 251, 245, 0.82);
            --panel: rgba(255, 255, 255, 0.78);
            --ink: #16212f;
            --muted: #5b6574;
            --line: rgba(22, 33, 47, 0.08);
            --accent: #c85c32;
            --accent-strong: #a7441f;
            --accent-soft: #e6a07e;
            --teal: #0f766e;
            --gold: #b7791f;
            --danger: #b42318;
            --shadow: 0 24px 80px rgba(23, 30, 38, 0.12);
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(200, 92, 50, 0.16), transparent 28%),
                radial-gradient(circle at top right, rgba(15, 118, 110, 0.12), transparent 24%),
                linear-gradient(180deg, #f7f1e7 0%, #efe5d8 100%);
            color: var(--ink);
            font-family: "IBM Plex Sans", sans-serif;
        }

        section[data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(17, 25, 40, 0.95), rgba(27, 41, 61, 0.97));
            border-right: 1px solid rgba(255, 255, 255, 0.06);
        }

        section[data-testid="stSidebar"] * {
            color: #f8f6f1 !important;
            font-family: "IBM Plex Sans", sans-serif;
        }

        section[data-testid="stSidebar"] [data-testid="stTextInput"] input {
            background: rgba(255, 255, 255, 0.08) !important;
            color: #f8f6f1 !important;
            border: 1px solid rgba(255, 255, 255, 0.14) !important;
            border-radius: 14px !important;
            box-shadow: none !important;
        }

        section[data-testid="stSidebar"] [data-testid="stTextInput"] input::placeholder {
            color: rgba(248, 246, 241, 0.55) !important;
        }

        section[data-testid="stSidebar"] [data-testid="stButton"] > button {
            background: rgba(255, 255, 255, 0.08) !important;
            color: #f8f6f1 !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 14px !important;
            transition: background 0.2s ease, transform 0.2s ease !important;
            box-shadow: none !important;
        }

        section[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
            background: rgba(200, 92, 50, 0.2) !important;
            border-color: rgba(200, 92, 50, 0.45) !important;
            transform: translateY(-1px);
        }

        section[data-testid="stSidebar"] [data-testid="stButton"] > button:focus {
            box-shadow: 0 0 0 0.15rem rgba(200, 92, 50, 0.22) !important;
        }

        section[data-testid="stSidebar"] .stAlert {
            background: rgba(255, 255, 255, 0.08) !important;
            color: #f8f6f1 !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
        }

        .block-container {
            max-width: 1200px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3 {
            font-family: "Space Grotesk", sans-serif !important;
            color: var(--ink);
            letter-spacing: -0.03em;
        }

        .hero-shell {
            position: relative;
            overflow: hidden;
            padding: 2.25rem 2rem 1.9rem 2rem;
            border-radius: 28px;
            background:
                linear-gradient(135deg, rgba(15, 32, 52, 0.96), rgba(30, 42, 68, 0.92)),
                linear-gradient(135deg, rgba(200, 92, 50, 0.18), rgba(15, 118, 110, 0.12));
            box-shadow: var(--shadow);
            border: 1px solid rgba(255, 255, 255, 0.08);
            margin-bottom: 1.25rem;
        }

        .hero-shell::after {
            content: "";
            position: absolute;
            right: -40px;
            top: -50px;
            width: 220px;
            height: 220px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(200, 92, 50, 0.28), transparent 65%);
        }

        .hero-kicker {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.35rem 0.75rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.1);
            color: #f7eee3;
            font-size: 0.82rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }

        .hero-title {
            margin: 0.9rem 0 0.5rem 0;
            color: #fff9f1;
            font-size: 3rem;
            line-height: 0.96;
            max-width: 760px;
        }

        .hero-copy {
            margin: 0;
            color: rgba(248, 241, 231, 0.86);
            font-size: 1.06rem;
            line-height: 1.65;
            max-width: 760px;
        }

        .hero-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.85rem;
            margin-top: 1.4rem;
        }

        .hero-metric {
            padding: 1rem 1rem 0.95rem;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(12px);
        }

        .hero-metric-label {
            color: rgba(248, 241, 231, 0.74);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.4rem;
        }

        .hero-metric-value {
            color: #fff9f1;
            font-family: "Space Grotesk", sans-serif;
            font-size: 1.35rem;
            font-weight: 700;
        }

        .panel-shell {
            padding: 1rem 1rem 0.85rem;
            border-radius: 24px;
            background: var(--paper);
            border: 1px solid rgba(255, 255, 255, 0.64);
            box-shadow: var(--shadow);
            backdrop-filter: blur(14px);
            margin-bottom: 1rem;
        }

        .section-title {
            font-family: "Space Grotesk", sans-serif;
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 0.2rem;
        }

        .section-copy {
            color: var(--muted);
            font-size: 0.95rem;
            margin-bottom: 0.9rem;
        }

        .chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-bottom: 0.75rem;
        }

        .chip {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.42rem 0.72rem;
            border-radius: 999px;
            background: rgba(22, 33, 47, 0.05);
            border: 1px solid rgba(22, 33, 47, 0.06);
            color: var(--ink);
            font-size: 0.84rem;
            font-weight: 600;
        }

        .result-shell {
            border-radius: 28px;
            background: var(--panel);
            border: 1px solid rgba(255, 255, 255, 0.7);
            box-shadow: var(--shadow);
            padding: 1.1rem;
        }

        .answer-card {
            padding: 1.25rem 1.3rem;
            border-radius: 22px;
            background:
                radial-gradient(circle at top right, rgba(200, 92, 50, 0.09), transparent 24%),
                linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 244, 238, 0.98));
            border: 1px solid var(--line);
            min-height: 220px;
            position: relative;
            overflow: hidden;
        }

        .answer-card::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            width: 5px;
            height: 100%;
            background: linear-gradient(180deg, var(--accent), var(--teal));
        }

        .eyebrow {
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--muted);
            font-weight: 700;
            margin-bottom: 0.55rem;
        }

        .answer-text {
            color: var(--ink);
            font-size: 1.05rem;
            line-height: 1.8;
        }

        .stat-card {
            padding: 1rem 1rem 1rem 1rem;
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid var(--line);
            min-height: 104px;
            position: relative;
            overflow: hidden;
        }

        .stat-card::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, var(--accent), var(--accent-soft));
            opacity: 0.9;
        }

        .stat-label {
            color: var(--muted);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.4rem;
        }

        .stat-value {
            font-family: "Space Grotesk", sans-serif;
            font-size: 1.35rem;
            color: var(--ink);
            font-weight: 700;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            padding: 0.38rem 0.72rem;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            margin-right: 0.45rem;
        }

        .status-high { background: rgba(15, 118, 110, 0.12); color: var(--teal); }
        .status-medium { background: rgba(183, 121, 31, 0.14); color: var(--gold); }
        .status-low { background: rgba(180, 35, 24, 0.12); color: var(--danger); }
        .status-review { background: rgba(22, 33, 47, 0.08); color: var(--ink); }
        .status-ready { background: rgba(15, 118, 110, 0.12); color: var(--teal); }

        .list-card {
            padding: 1rem 1rem 0.9rem;
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid var(--line);
            height: 100%;
            box-shadow: 0 10px 30px rgba(23, 30, 38, 0.05);
        }

        .list-card ul {
            margin: 0.5rem 0 0 0.9rem;
            padding: 0;
        }

        .list-card li {
            color: var(--ink);
            margin-bottom: 0.55rem;
            line-height: 1.5;
        }

        .trace-card {
            padding: 0.9rem 1rem;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid var(--line);
            margin-bottom: 0.65rem;
        }

        .trace-index {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 1.7rem;
            height: 1.7rem;
            border-radius: 50%;
            background: rgba(200, 92, 50, 0.12);
            color: var(--accent-strong);
            font-weight: 700;
            font-size: 0.8rem;
            margin-right: 0.55rem;
        }

        .citation-shell {
            padding: 0.95rem 1rem;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid var(--line);
            margin-bottom: 0.7rem;
        }

        .citation-title {
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 0.3rem;
        }

        .citation-meta {
            color: var(--muted);
            font-size: 0.82rem;
            margin-bottom: 0.5rem;
        }

        .citation-snippet {
            color: var(--ink);
            line-height: 1.55;
        }

        .placeholder-shell {
            padding: 1.5rem;
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.72);
            border: 1px dashed rgba(22, 33, 47, 0.18);
            color: var(--muted);
        }

        .empty-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.9rem;
            margin-top: 1rem;
        }

        .empty-card {
            padding: 1rem;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid rgba(22, 33, 47, 0.08);
            box-shadow: 0 10px 24px rgba(23, 30, 38, 0.05);
        }

        .empty-card-title {
            font-family: "Space Grotesk", sans-serif;
            font-size: 1rem;
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 0.35rem;
        }

        .empty-card-copy {
            color: var(--muted);
            font-size: 0.92rem;
            line-height: 1.55;
        }

        .console-chip {
            display: inline-flex;
            align-items: center;
            padding: 0.34rem 0.68rem;
            border-radius: 999px;
            margin-right: 0.45rem;
            margin-top: 0.35rem;
            background: rgba(200, 92, 50, 0.1);
            color: var(--accent-strong);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.03em;
        }

        .small-note {
            color: var(--muted);
            font-size: 0.84rem;
        }

        [data-testid="stTextArea"] textarea {
            min-height: 130px;
            border-radius: 18px;
            border: 1px solid rgba(22, 33, 47, 0.12);
            background: rgba(255, 255, 255, 0.86);
        }

        [data-testid="stButton"] > button {
            border-radius: 16px;
            border: 1px solid rgba(22, 33, 47, 0.08);
            font-weight: 700;
        }

        .stButton button[kind="primary"] {
            background: linear-gradient(135deg, #c4663c, #d88047) !important;
            color: #fff9f1 !important;
            border: 1px solid rgba(167, 68, 31, 0.14) !important;
            box-shadow: 0 16px 28px rgba(167, 68, 31, 0.2) !important;
        }

        .stButton button[kind="primary"]:hover {
            background: linear-gradient(135deg, #b7572f, #cf7441) !important;
            transform: translateY(-1px);
        }

        .stButton button[kind="secondary"] {
            background: rgba(255, 255, 255, 0.86) !important;
            color: var(--ink) !important;
            border: 1px solid rgba(22, 33, 47, 0.08) !important;
        }

        @media (max-width: 980px) {
            .hero-grid {
                grid-template-columns: 1fr;
            }
            .hero-title {
                font-size: 2.2rem;
            }
            .empty-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    st.markdown("### Ops Control Room")
    st.caption("Connect the backend, choose a launch question, and run investigations.")
    backend_url = st.text_input("Backend URL", value=DEFAULT_BACKEND_URL, key="backend_url")
    st.markdown(
        "<p class='small-note'>Run the FastAPI service first with "
        "<code>python -m uvicorn app.main:app --reload</code>.</p>",
        unsafe_allow_html=True,
    )

    if st.button("Check Backend Health", use_container_width=True):
        st.session_state["health_payload"] = perform_health_check(backend_url)

    health_payload = st.session_state.get("health_payload")
    if health_payload:
        if health_payload.get("ok"):
            st.success("API reachable")
            st.caption(f"DB: {health_payload['payload'].get('database_path', 'unknown')}")
            st.session_state["backend_status"] = "Online"
        else:
            st.error("API unavailable")
            st.caption(health_payload["error"])
            st.session_state["backend_status"] = "Offline"

    st.divider()
    st.markdown("### Starter Prompts")
    for index, example in enumerate(EXAMPLE_QUESTIONS):
        if st.button(example, key=f"example_{index}", use_container_width=True):
            st.session_state["question"] = example

    st.divider()
    st.markdown("### Demo Highlights")
    st.markdown("- Grounded retrieval")
    st.markdown("- Workflow trace")
    st.markdown("- Confidence and escalation")
    st.markdown("- API-first architecture")


def render_hero() -> None:
    status_label = st.session_state.get("backend_status", "Unknown")
    status_class = "status-ready" if status_label == "Online" else "status-review"
    st.markdown(
        f"""
        <div class="hero-shell">
            <div class="hero-kicker">Operations AI Workspace</div>
            <div class="hero-title">Investigate KPI shifts like an internal analytics platform.</div>
            <p class="hero-copy">
                This demo combines DuckDB-backed operational metrics, ChromaDB retrieval over SOPs and
                runbooks, and a LangGraph workflow that returns grounded answers with citations,
                confidence, and analyst-review fallback.
            </p>
            <div class="chip-row" style="margin-top:1rem;">
                <span class="status-pill {status_class}">Backend {html.escape(status_label)}</span>
                <span class="chip">FastAPI + LangGraph</span>
                <span class="chip">DuckDB + ChromaDB</span>
                <span class="chip">Evidence-backed answers</span>
            </div>
            <div class="hero-grid">
                <div class="hero-metric">
                    <div class="hero-metric-label">Investigation Modes</div>
                    <div class="hero-metric-value">Structured, docs, hybrid</div>
                </div>
                <div class="hero-metric">
                    <div class="hero-metric-label">Quality Signals</div>
                    <div class="hero-metric-value">Tests + eval harness</div>
                </div>
                <div class="hero-metric">
                    <div class="hero-metric-label">Return Payload</div>
                    <div class="hero-metric-value">Answer, citations, trace</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_control_panel() -> None:
    st.markdown(
        """
        <div class="panel-shell">
            <div class="section-title">Investigation Console</div>
            <div class="section-copy">
                Ask a question the way an operations analyst would. The backend will gather KPI,
                incident, and document evidence before synthesizing a response.
            </div>
            <div>
                <span class="console-chip">Root-cause reasoning</span>
                <span class="console-chip">Evidence-backed output</span>
                <span class="console-chip">Analyst-review fallback</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    question = st.text_area(
        "Question",
        value=st.session_state.get("question", EXAMPLE_QUESTIONS[0]),
        key="question",
        label_visibility="collapsed",
        placeholder="Why did delivery success rate drop in Region 3 on 2026-03-31?",
    )

    ask_col, reset_col = st.columns([4, 1])
    with ask_col:
        if st.button("Run Investigation", type="primary", use_container_width=True):
            payload = run_investigation(
                backend_url=st.session_state.get("backend_url", DEFAULT_BACKEND_URL),
                question=question,
            )
            if payload:
                st.session_state["last_payload"] = payload
    with reset_col:
        if st.button("Reset", use_container_width=True):
            st.session_state["last_payload"] = None


def render_workspace() -> None:
    payload = st.session_state.get("last_payload")
    if not payload:
        render_empty_workspace()
        return

    render_summary(payload)
    summary_tab, evidence_tab, trace_tab, raw_tab = st.tabs(
        ["Summary", "Evidence", "Workflow Trace", "Raw Response"]
    )

    with summary_tab:
        render_outcome_lists(payload)

    with evidence_tab:
        render_citations(payload)
        render_evidence_summary(payload)

    with trace_tab:
        render_trace(payload)

    with raw_tab:
        st.json(payload)


def render_empty_workspace() -> None:
    st.markdown(
        """
        <div class="placeholder-shell">
            <div class="section-title">No investigation running yet</div>
            <p class="section-copy" style="margin-bottom:0;">
                Start with one of the example prompts from the sidebar or write your own operations
                question. This workspace will fill with answer summaries, likely causes, citations,
                evidence summaries, and the full orchestration trace.
            </p>
            <div class="empty-grid">
                <div class="empty-card">
                    <div class="empty-card-title">1. Ask an operations question</div>
                    <div class="empty-card-copy">
                        Try a KPI anomaly, escalation-policy, or hybrid investigation prompt.
                    </div>
                </div>
                <div class="empty-card">
                    <div class="empty-card-title">2. Review grounded evidence</div>
                    <div class="empty-card-copy">
                        The app collects KPI data, incidents, and retrieved business knowledge before answering.
                    </div>
                </div>
                <div class="empty-card">
                    <div class="empty-card-title">3. Decide on next action</div>
                    <div class="empty-card-copy">
                        Use the confidence label, citations, and analyst-review flag to decide whether to escalate.
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def perform_health_check(backend_url: str) -> dict[str, Any]:
    try:
        response = httpx.get(f"{backend_url}/health", timeout=20.0)
        response.raise_for_status()
        return {"ok": True, "payload": response.json()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_investigation(backend_url: str, question: str) -> dict[str, Any] | None:
    if len(question.strip()) < 5:
        st.warning("Please enter a longer question.")
        return None

    with st.spinner("Investigating KPI movement and retrieving supporting evidence..."):
        try:
            response = httpx.post(
                f"{backend_url}/ask",
                json={"question": question},
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            st.error(f"Investigation failed: {exc}")
            return None


def render_summary(payload: dict[str, Any]) -> None:
    confidence = str(payload.get("confidence", "unknown")).lower()
    confidence_class = {
        "high": "status-high",
        "medium": "status-medium",
        "low": "status-low",
    }.get(confidence, "status-review")

    review_text = "Analyst review required" if payload.get("needs_analyst_review") else "Ready to share"
    citation_count = len(payload.get("citations", []))
    trace_count = len(payload.get("trace", []))

    answer_col, stats_col = st.columns([2.2, 1.1])
    with answer_col:
        st.markdown(
            f"""
            <div class="result-shell">
                <div class="answer-card">
                    <div class="eyebrow">Investigation Outcome</div>
                    <div class="chip-row">
                        <span class="status-pill {confidence_class}">Confidence {html.escape(confidence.title())}</span>
                        <span class="status-pill status-review">{html.escape(review_text)}</span>
                    </div>
                    <div class="answer-text">{html.escape(payload.get("answer", ""))}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with stats_col:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-label">Citations</div>
                <div class="stat-value">{citation_count}</div>
            </div>
            <div style="height:0.8rem;"></div>
            <div class="stat-card">
                <div class="stat-label">Workflow Steps</div>
                <div class="stat-value">{trace_count}</div>
            </div>
            <div style="height:0.8rem;"></div>
            <div class="stat-card">
                <div class="stat-label">Escalation</div>
                <div class="stat-value">{'Yes' if payload.get('needs_analyst_review') else 'No'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_outcome_lists(payload: dict[str, Any]) -> None:
    causes_col, steps_col = st.columns(2)
    with causes_col:
        render_list_card("Likely Causes", payload.get("likely_causes", []), empty_message="No likely causes returned.")
    with steps_col:
        render_list_card(
            "Recommended Next Steps",
            payload.get("recommended_next_steps", []),
            empty_message="No recommended next steps returned.",
        )


def render_list_card(title: str, items: list[str], empty_message: str) -> None:
    if items:
        body = "".join(f"<li>{html.escape(item)}</li>" for item in items)
        content = f"<ul>{body}</ul>"
    else:
        content = f"<p class='small-note'>{html.escape(empty_message)}</p>"

    st.markdown(
        f"""
        <div class="list-card">
            <div class="section-title">{html.escape(title)}</div>
            {content}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_citations(payload: dict[str, Any]) -> None:
    st.markdown("<div class='section-title'>Citations</div>", unsafe_allow_html=True)
    citations = payload.get("citations", [])
    if not citations:
        st.caption("No citations were returned.")
        return

    for citation in citations:
        st.markdown(
            f"""
            <div class="citation-shell">
                <div class="citation-title">{html.escape(citation['title'])}</div>
                <div class="citation-meta">
                    {html.escape(citation['source_type'].title())} · {html.escape(citation['source_path'])}
                </div>
                <div class="citation-snippet">{html.escape(citation['snippet'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_evidence_summary(payload: dict[str, Any]) -> None:
    st.markdown("<div class='section-title'>Evidence Summary</div>", unsafe_allow_html=True)
    st.code(payload.get("evidence_summary", ""), language="text")


def render_trace(payload: dict[str, Any]) -> None:
    st.markdown("<div class='section-title'>Workflow Trace</div>", unsafe_allow_html=True)
    trace = payload.get("trace", [])
    if not trace:
        st.caption("No workflow trace returned.")
        return

    for index, item in enumerate(trace, start=1):
        st.markdown(
            f"""
            <div class="trace-card">
                <span class="trace-index">{index}</span>
                <span>{html.escape(item)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
