from __future__ import annotations

import html
import json
import os
import time
from typing import Any

import httpx
import streamlit as st

from app.core.auth import create_demo_token

DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
RENDER_COLD_START_MESSAGE = (
    "The backend likely timed out while waking up on Render. "
    "Wait 30-90 seconds and try again."
)
EXAMPLE_QUESTIONS = [
    "Why did delivery success rate drop in Region 3 on 2026-03-31?",
    "What does the escalation policy say about low-confidence cases?",
    "Why did delivery success rate drop in Region 3 and what does the SOP suggest we do next?",
    "Explain the return rate spike in Region 4.",
]
ROLES = [
    "operations_analyst",
    "regional_manager",
    "exec_viewer",
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
    st.session_state.setdefault("metrics_payload", None)
    st.session_state.setdefault("dashboard_payload", None)
    st.session_state.setdefault("history_payload", None)
    st.session_state.setdefault("health_payload", None)
    st.session_state.setdefault("backend_status", "Unknown")
    st.session_state.setdefault("role", "operations_analyst")
    st.session_state.setdefault("backend_url", DEFAULT_BACKEND_URL)


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

        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] div {
            color: #f8f6f1 !important;
        }

        section[data-testid="stSidebar"] [data-testid="stTextInput"] input {
            background: rgba(12, 20, 34, 0.92) !important;
            color: #f8f6f1 !important;
            -webkit-text-fill-color: #f8f6f1 !important;
            border: 1px solid rgba(255, 255, 255, 0.18) !important;
            border-radius: 14px !important;
            box-shadow: none !important;
        }

        section[data-testid="stSidebar"] [data-testid="stTextInput"] input::placeholder {
            color: rgba(248, 246, 241, 0.55) !important;
        }

        section[data-testid="stSidebar"] [data-testid="stSelectbox"] > div[data-baseweb="select"] > div {
            background: rgba(12, 20, 34, 0.92) !important;
            color: #f8f6f1 !important;
            border: 1px solid rgba(255, 255, 255, 0.18) !important;
            border-radius: 14px !important;
        }

        section[data-testid="stSidebar"] [data-testid="stSelectbox"] * {
            color: #f8f6f1 !important;
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

        .hero-shell .chip {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.08);
            color: #f8f1e7;
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

        .stTabs [data-baseweb="tab-list"] button {
            color: var(--ink) !important;
        }

        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
            color: var(--accent-strong) !important;
        }

        [data-testid="stTextArea"] textarea {
            min-height: 130px;
            border-radius: 18px;
            border: 1px solid rgba(22, 33, 47, 0.12);
            background: rgba(255, 255, 255, 0.86);
            color: var(--ink) !important;
            -webkit-text-fill-color: var(--ink) !important;
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

        .dashboard-shell {
            background: rgba(255, 251, 245, 0.76);
            border: 1px solid rgba(22, 33, 47, 0.08);
            border-radius: 28px;
            box-shadow: var(--shadow);
            padding: 1.4rem 1.5rem 1.2rem;
        }

        .dashboard-header {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: flex-start;
            margin-bottom: 1rem;
        }

        .dashboard-title {
            font-family: "Space Grotesk", sans-serif;
            font-size: 1.65rem;
            font-weight: 700;
            color: var(--ink);
        }

        .dashboard-copy {
            color: var(--muted);
            font-size: 0.95rem;
            margin-top: 0.25rem;
        }

        .dashboard-meta {
            color: var(--muted);
            font-size: 0.82rem;
            text-align: right;
        }

        .alert-banner {
            border-radius: 18px;
            padding: 0.95rem 1rem;
            margin-bottom: 0.8rem;
            border-left: 4px solid transparent;
        }

        .alert-banner.red {
            background: rgba(180, 35, 24, 0.08);
            border-left-color: rgba(180, 35, 24, 0.88);
        }

        .alert-banner.amber {
            background: rgba(183, 121, 31, 0.11);
            border-left-color: rgba(183, 121, 31, 0.88);
        }

        .alert-banner-title {
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 0.2rem;
        }

        .alert-banner-copy,
        .alert-banner-reco {
            color: var(--muted);
            font-size: 0.95rem;
        }

        .dashboard-section {
            margin-top: 1.3rem;
        }

        .dashboard-section-title {
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--muted);
            font-size: 0.8rem;
            margin-bottom: 0.65rem;
            font-weight: 600;
        }

        .dashboard-card {
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid rgba(22, 33, 47, 0.08);
            border-radius: 20px;
            padding: 1rem;
            min-height: 138px;
            box-shadow: 0 10px 28px rgba(23, 30, 38, 0.05);
        }

        .dashboard-card-label {
            color: var(--muted);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-weight: 600;
        }

        .dashboard-card-value {
            color: var(--ink);
            font-family: "Space Grotesk", sans-serif;
            font-size: 1.85rem;
            line-height: 1.1;
            margin: 0.45rem 0;
            font-weight: 700;
        }

        .dashboard-card-detail {
            color: var(--muted);
            font-size: 0.88rem;
            line-height: 1.45;
        }

        .dashboard-status {
            display: flex;
            align-items: center;
            gap: 0.42rem;
            font-size: 0.82rem;
            font-weight: 600;
            margin-bottom: 0.55rem;
        }

        .status-dot {
            width: 0.65rem;
            height: 0.65rem;
            border-radius: 999px;
            display: inline-block;
        }

        .status-dot.green { background: var(--teal); }
        .status-dot.amber { background: var(--gold); }
        .status-dot.red { background: var(--danger); }

        .restricted-row {
            border: 1px dashed rgba(22, 33, 47, 0.18);
            background: rgba(255, 255, 255, 0.46);
            color: var(--muted);
            border-radius: 18px;
            padding: 0.95rem 1rem;
            margin-top: 0.8rem;
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
    backend_url = st.text_input("Backend URL", key="backend_url")
    selected_role = st.selectbox(
        "Viewer Role",
        options=ROLES,
        index=ROLES.index(st.session_state.get("role", "operations_analyst")),
    )
    st.session_state["role"] = selected_role
    st.markdown(
        "<p class='small-note'>Run the FastAPI service first with "
        "<code>python -m uvicorn app.main:app --reload</code>.</p>",
        unsafe_allow_html=True,
    )

    if st.button("Check Backend Health", use_container_width=True):
        st.session_state["health_payload"] = perform_health_check(backend_url)

    if st.button("Refresh Dashboards", use_container_width=True):
        st.session_state["metrics_payload"] = fetch_metrics(
            backend_url=backend_url,
            role=st.session_state.get("role", "operations_analyst"),
        )
        st.session_state["dashboard_payload"] = fetch_dashboard_metrics(
            backend_url=backend_url,
            role=st.session_state.get("role", "operations_analyst"),
        )
        st.session_state["history_payload"] = fetch_history(
            backend_url=backend_url,
            role=st.session_state.get("role", "operations_analyst"),
        )

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
                <span class="chip">Role-aware access</span>
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

    st.text_area(
        "Question",
        key="question",
        label_visibility="collapsed",
        placeholder="Why did delivery success rate drop in Region 3 on 2026-03-31?",
    )
    question = st.session_state.get("question", "")

    ask_col, reset_col = st.columns([4, 1])
    with ask_col:
        if st.button("Run Investigation", type="primary", use_container_width=True):
            stream_placeholder = st.empty()
            payload = run_investigation(
                backend_url=st.session_state.get("backend_url", DEFAULT_BACKEND_URL),
                question=question,
                role=st.session_state.get("role", "operations_analyst"),
                stream_placeholder=stream_placeholder,
            )
            if payload:
                st.session_state["last_payload"] = payload
                st.session_state["metrics_payload"] = fetch_metrics(
                    backend_url=st.session_state.get("backend_url", DEFAULT_BACKEND_URL),
                    role=st.session_state.get("role", "operations_analyst"),
                )
                st.session_state["dashboard_payload"] = fetch_dashboard_metrics(
                    backend_url=st.session_state.get("backend_url", DEFAULT_BACKEND_URL),
                    role=st.session_state.get("role", "operations_analyst"),
                )
                st.session_state["history_payload"] = fetch_history(
                    backend_url=st.session_state.get("backend_url", DEFAULT_BACKEND_URL),
                    role=st.session_state.get("role", "operations_analyst"),
                )
    with reset_col:
        if st.button("Reset", use_container_width=True):
            st.session_state["last_payload"] = None


def render_workspace() -> None:
    payload = st.session_state.get("last_payload")
    if payload:
        render_summary(payload)

    summary_tab, evidence_tab, trace_tab, daily_metrics_tab, history_tab, metrics_tab, raw_tab = st.tabs(
        ["Summary", "Evidence", "Workflow Trace", "Daily Metrics", "Recent Investigations", "Ops Metrics", "Raw Response"]
    )

    with summary_tab:
        if payload:
            render_outcome_lists(payload)
        else:
            render_empty_workspace()

    with evidence_tab:
        if payload:
            render_citations(payload)
            render_evidence_summary(payload)
        else:
            st.caption("Run an investigation to inspect grounded evidence.")

    with trace_tab:
        if payload:
            render_trace(payload)
        else:
            st.caption("Workflow trace will appear after an investigation runs.")

    with daily_metrics_tab:
        render_daily_metrics_dashboard()

    with history_tab:
        render_investigation_history()

    with metrics_tab:
        render_metrics_dashboard()

    with raw_tab:
        if payload:
            st.json(payload)
        else:
            st.caption("The raw API response will appear here after an investigation.")


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
    timeout = httpx.Timeout(connect=10.0, read=75.0, write=20.0, pool=20.0)

    for attempt in range(2):
        try:
            response = httpx.get(f"{backend_url}/v1/health", timeout=timeout)
            response.raise_for_status()
            return {"ok": True, "payload": response.json()}
        except httpx.ReadTimeout:
            if attempt == 0:
                time.sleep(2)
                continue
            return {"ok": False, "error": RENDER_COLD_START_MESSAGE}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    return {"ok": False, "error": RENDER_COLD_START_MESSAGE}


def build_auth_headers(role: str) -> dict[str, str]:
    auth_token = create_demo_token(role=role)
    return {"Authorization": f"Bearer {auth_token}"}


def fetch_metrics(
    backend_url: str,
    role: str,
) -> dict[str, Any] | None:
    try:
        response = httpx.get(
            f"{backend_url}/v1/debug/metrics",
            headers=build_auth_headers(role),
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.info(f"Ops metrics are not available yet: {exc}")
        return None


def fetch_dashboard_metrics(
    backend_url: str,
    role: str,
) -> dict[str, Any] | None:
    try:
        response = httpx.get(
            f"{backend_url}/v1/metrics/dashboard",
            headers=build_auth_headers(role),
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.info(f"Daily metrics dashboard is not available yet: {exc}")
        return None


def fetch_history(
    backend_url: str,
    role: str,
) -> dict[str, Any] | None:
    try:
        response = httpx.get(
            f"{backend_url}/v1/history",
            headers=build_auth_headers(role),
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.info(f"Investigation history is not available yet: {exc}")
        return None


def run_investigation(
    backend_url: str,
    question: str,
    role: str,
    stream_placeholder,
) -> dict[str, Any] | None:
    if len(question.strip()) < 5:
        st.warning("Please enter a longer question.")
        return None

    with st.spinner("Investigating KPI movement and retrieving supporting evidence..."):
        try:
            assembled_answer = ""
            current_event = None
            stream_timeout = httpx.Timeout(connect=10.0, read=180.0, write=30.0, pool=30.0)
            with httpx.stream(
                "POST",
                f"{backend_url}/v1/ask/stream",
                json={"question": question},
                headers=build_auth_headers(role),
                timeout=stream_timeout,
            ) as response:
                response.raise_for_status()
                for raw_line in response.iter_lines():
                    if not raw_line:
                        continue
                    if raw_line.startswith("event:"):
                        current_event = raw_line.split(":", 1)[1].strip()
                        continue
                    if not raw_line.startswith("data:"):
                        continue
                    payload = json.loads(raw_line.split(":", 1)[1].strip())
                    if current_event == "status":
                        status_message = payload.get("message", "Running...")
                        if status_message == "investigation_started":
                            stream_placeholder.info("Investigation started.")
                        elif status_message == "investigation_running":
                            stream_placeholder.info(
                                "Still gathering evidence. The hosted backend may take a minute on cold start."
                            )
                        elif status_message == "answer_ready":
                            stream_placeholder.info("Answer ready. Streaming response...")
                        else:
                            stream_placeholder.info(status_message)
                    elif current_event == "answer_chunk":
                        assembled_answer += payload.get("token", "")
                        stream_placeholder.markdown(
                            f"**Streaming answer preview**\n\n{assembled_answer}"
                        )
                    elif current_event == "complete":
                        stream_placeholder.empty()
                        return payload
            st.error("Stream ended before the API returned a final payload.")
            return None
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
    blocked_count = len(payload.get("blocked_sources", []))
    request_id = str(payload.get("request_id", "unknown"))
    latency_ms = int(payload.get("latency_ms", 0))
    cache_status = str(payload.get("cache_status", "unknown")).title()
    role = str(payload.get("role", "unknown")).replace("_", " ").title()
    freshness = str(payload.get("freshness_status", "unknown")).title()
    completeness = str(payload.get("completeness_status", "unknown")).title()
    data_as_of = payload.get("data_as_of") or "Unavailable"

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
                        <span class="status-pill status-ready">{html.escape(role)}</span>
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
                <div class="stat-label">Freshness</div>
                <div class="stat-value">{html.escape(freshness)}</div>
            </div>
            <div style="height:0.8rem;"></div>
            <div class="stat-card">
                <div class="stat-label">Completeness</div>
                <div class="stat-value">{html.escape(completeness)}</div>
            </div>
            <div style="height:0.8rem;"></div>
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
                <div class="stat-label">Latency</div>
                <div class="stat-value">{latency_ms} ms</div>
            </div>
            <div style="height:0.8rem;"></div>
            <div class="stat-card">
                <div class="stat-label">Blocked Sources</div>
                <div class="stat-value">{blocked_count}</div>
            </div>
            <div style="height:0.8rem;"></div>
            <div class="stat-card">
                <div class="stat-label">Cache</div>
                <div class="stat-value">{html.escape(cache_status)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    review_reason = payload.get("analyst_review_reason")
    if review_reason:
        st.warning(f"Analyst review reason: {review_reason}")

    st.caption(f"Data as of: {data_as_of}")
    st.caption(f"Request ID: {request_id}")


def render_outcome_lists(payload: dict[str, Any]) -> None:
    breakdown = payload.get("confidence_breakdown", [])
    follow_ups = payload.get("suggested_follow_up_questions", [])
    breakdown_col, causes_col, steps_col, follow_up_col = st.columns([1.1, 1, 1, 1])
    with breakdown_col:
        render_list_card(
            "Confidence Breakdown",
            breakdown,
            empty_message="No confidence rationale was returned.",
        )
    with causes_col:
        render_list_card("Likely Causes", payload.get("likely_causes", []), empty_message="No likely causes returned.")
    with steps_col:
        render_list_card(
            "Recommended Next Steps",
            payload.get("recommended_next_steps", []),
            empty_message="No recommended next steps returned.",
        )
    with follow_up_col:
        render_list_card(
            "Suggested Follow-ups",
            follow_ups,
            empty_message="No follow-up questions were generated.",
        )

    if follow_ups:
        st.markdown("<div class='section-title'>Continue The Investigation</div>", unsafe_allow_html=True)
        suggestion_cols = st.columns(len(follow_ups))
        for index, follow_up in enumerate(follow_ups):
            with suggestion_cols[index]:
                if st.button(
                    follow_up,
                    key=f"follow_up_{payload.get('request_id', 'latest')}_{index}",
                    use_container_width=True,
                ):
                    st.session_state["question"] = follow_up


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

    blocked_sources = payload.get("blocked_sources", [])
    if blocked_sources:
        st.markdown("<div class='section-title'>Blocked Sources</div>", unsafe_allow_html=True)
        for item in blocked_sources:
            st.error(item)


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


def render_daily_metrics_dashboard() -> None:
    backend_url = st.session_state.get("backend_url", DEFAULT_BACKEND_URL)
    role = st.session_state.get("role", "operations_analyst")

    @st.fragment(run_every=60)
    def render_dashboard_fragment() -> None:
        payload = fetch_dashboard_metrics(backend_url=backend_url, role=role)
        if payload:
            st.session_state["dashboard_payload"] = payload

        current_payload = st.session_state.get("dashboard_payload")
        if not current_payload:
            st.caption("Daily metrics will appear here once the backend dashboard endpoint responds.")
            return

        assigned_region = current_payload.get("assigned_region")
        generated_at = str(current_payload.get("generated_at", "unknown")).replace("T", " ")
        st.markdown(
            f"""
            <div class="dashboard-shell">
                <div class="dashboard-header">
                    <div>
                        <div class="dashboard-title">Role-based daily metrics</div>
                        <div class="dashboard-copy">
                            Each role sees only the metrics and alerting surfaces it is authorized to access.
                        </div>
                    </div>
                    <div class="dashboard-meta">
                        <div><strong>Role:</strong> {html.escape(str(current_payload.get("role_label", role)).title())}</div>
                        <div><strong>Scope:</strong> {html.escape(assigned_region or "All visible regions")}</div>
                        <div><strong>Auto-refresh:</strong> every {int(current_payload.get("auto_refresh_seconds", 60))}s</div>
                        <div><strong>Data as of:</strong> {html.escape(generated_at)}</div>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        alerts = current_payload.get("alerts", [])
        if alerts:
            for alert in alerts:
                level = str(alert.get("level", "amber"))
                st.markdown(
                    f"""
                    <div class="alert-banner {html.escape(level)}">
                        <div class="alert-banner-title">{html.escape(str(alert.get('title', 'Alert')))}</div>
                        <div class="alert-banner-copy">{html.escape(str(alert.get('message', '')))}</div>
                        <div class="alert-banner-reco">{html.escape(str(alert.get('recommendation', '')))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        for section in current_payload.get("sections", []):
            st.markdown(
                f"<div class='dashboard-section'><div class='dashboard-section-title'>{html.escape(str(section.get('title', 'Section')))}</div></div>",
                unsafe_allow_html=True,
            )
            metrics = section.get("metrics", [])
            columns = st.columns(min(4, max(1, len(metrics))))
            for index, metric in enumerate(metrics):
                with columns[index % len(columns)]:
                    status = str(metric.get("status", "green"))
                    st.markdown(
                        f"""
                        <div class="dashboard-card">
                            <div class="dashboard-card-label">{html.escape(str(metric.get('label', 'Metric')))}</div>
                            <div class="dashboard-card-value">{html.escape(str(metric.get('display_value', '—')))}</div>
                            <div class="dashboard-status">
                                <span class="status-dot {html.escape(status)}"></span>
                                <span>{html.escape(str(metric.get('status_text', 'Normal')))}</span>
                            </div>
                            <div class="dashboard-card-detail">{html.escape(str(metric.get('detail', '')))}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        for item in current_payload.get("restricted", []):
            st.markdown(
                f"<div class='restricted-row'>{html.escape(str(item))}</div>",
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    render_dashboard_fragment()


def render_investigation_history() -> None:
    backend_url = st.session_state.get("backend_url", DEFAULT_BACKEND_URL)
    role = st.session_state.get("role", "operations_analyst")

    history_payload = fetch_history(backend_url=backend_url, role=role)
    if history_payload:
        st.session_state["history_payload"] = history_payload

    current_payload = st.session_state.get("history_payload")
    if not current_payload or not current_payload.get("items"):
        st.caption("Recent investigations will appear here after you run a few questions.")
        return

    st.markdown("<div class='section-title'>Recent Investigations</div>", unsafe_allow_html=True)
    st.caption("Each record captures who asked, what the system answered, and the confidence assigned.")

    for item in current_payload.get("items", []):
        review_label = "Analyst review required" if item.get("needs_analyst_review") else "Ready to share"
        st.markdown(
            f"""
            <div class="dashboard-card" style="margin-bottom:0.9rem;">
                <div class="dashboard-card-label">{html.escape(str(item.get('created_at', '')))}</div>
                <div class="dashboard-card-value" style="font-size:1.15rem;">{html.escape(str(item.get('question', '')))}</div>
                <div class="dashboard-status">
                    <span class="status-dot {'red' if item.get('needs_analyst_review') else 'green'}"></span>
                    <span>{html.escape(str(item.get('confidence', 'unknown')).title())} confidence</span>
                    <span style="margin-left:0.8rem;">{html.escape(review_label)}</span>
                </div>
                <div class="dashboard-card-detail"><strong>Answer:</strong> {html.escape(str(item.get('answer', '')))}</div>
                <div class="dashboard-card-detail" style="margin-top:0.5rem;">
                    Role: {html.escape(str(item.get('role', 'unknown')).replace('_', ' ').title())} |
                    Cache: {html.escape(str(item.get('cache_status', 'unknown')).title())} |
                    Freshness: {html.escape(str(item.get('freshness_status', 'unknown')).title())} |
                    Blocked sources: {int(item.get('blocked_sources_count', 0))}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_metrics_dashboard() -> None:
    metrics_payload = st.session_state.get("metrics_payload")
    if not metrics_payload:
        st.caption("Run an investigation or refresh ops metrics to populate this dashboard.")
        return

    summary = metrics_payload.get("summary", {})
    summary_col_1, summary_col_2, summary_col_3, summary_col_4 = st.columns(4)
    with summary_col_1:
        st.metric("Requests", summary.get("requests", 0))
    with summary_col_2:
        st.metric("Avg latency", f"{summary.get('avg_latency_ms', 0)} ms")
    with summary_col_3:
        st.metric("P95 latency", f"{summary.get('p95_latency_ms', 0)} ms")
    with summary_col_4:
        st.metric("Cache hit rate", f"{int(summary.get('cache_hit_rate', 0) * 100)}%")

    cost_col_1, cost_col_2, cost_col_3 = st.columns(3)
    with cost_col_1:
        st.metric("Total tokens", summary.get("total_tokens", 0))
    with cost_col_2:
        st.metric("Total est. cost", f"${summary.get('total_cost_usd', 0.0):.4f}")
    with cost_col_3:
        st.metric("Avg est. cost", f"${summary.get('avg_cost_usd', 0.0):.4f}")

    recent_requests = metrics_payload.get("recent_requests", [])
    if recent_requests:
        st.markdown("<div class='section-title'>Recent Requests</div>", unsafe_allow_html=True)
        table_rows = [
            {
                "request_id": item.get("request_id"),
                "role": item.get("role"),
                "confidence": item.get("confidence"),
                "latency_ms": item.get("latency_ms"),
                "cache_status": item.get("cache_status"),
                "total_tokens": item.get("total_tokens"),
                "estimated_cost_usd": item.get("estimated_cost_usd"),
                "freshness_status": item.get("freshness_status"),
                "blocked_sources_count": item.get("blocked_sources_count"),
            }
            for item in recent_requests
        ]
        st.dataframe(table_rows, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
