from __future__ import annotations

import os

import requests
import streamlit as st

API_URL = os.getenv("MARKET_FIT_API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Market Fit Trace Agent", layout="wide")

st.title("Market Fit Trace Agent")
st.caption("Arize track - OpenInference traces - Phoenix eval loop")

default_thesis = (
    "Google TPU progress means Gemini closes the frontier-model gap in 2026."
)

left, center, right = st.columns([0.9, 1.25, 0.85])

with left:
    thesis = st.text_area("Thesis / source", default_thesis, height=320)
    prompt_version = st.selectbox("Prompt version", ["v1_lenient", "v2_trace_inspected"])
    run_clicked = st.button("Run agent", use_container_width=True)

if "run" not in st.session_state:
    st.session_state.run = None

if run_clicked:
    response = requests.post(
        f"{API_URL}/api/runs",
        json={"thesis": thesis, "prompt_version": prompt_version},
        timeout=90,
    )
    response.raise_for_status()
    st.session_state.run = response.json()

run = st.session_state.run

with center:
    st.subheader("Claim lifecycle")
    if not run:
        st.info("No run yet.")
    else:
        st.markdown(f"### {run['claim']['claim_text']}")
        st.code(run["fit"]["semantic_fit_class"], language=None)
        st.write(run["fit"]["fit_reason"])
        st.write("Recommended market:", run["fit"]["recommended_market_id"] or "None")
        st.write("Misses:", run["fit"]["misses"])

        verdict_cols = st.columns(4)
        verdicts = ["verify", "reject", "needs_review", "corrected"]
        for col, verdict in zip(verdict_cols, verdicts, strict=True):
            if col.button(verdict, use_container_width=True):
                payload = {
                    "claim_id": run["claim_id"],
                    "verdict": verdict,
                    "corrected_fit_class": "weak_proxy" if verdict == "corrected" else None,
                    "reviewer_note": "Recorded from Streamlit UI.",
                }
                response = requests.post(f"{API_URL}/api/verdicts", json=payload, timeout=30)
                response.raise_for_status()
                st.session_state.ledger = response.json()["ledger"]
                st.rerun()

        if st.button("Inspect trace and rerun", use_container_width=True):
            response = requests.post(f"{API_URL}/api/runs/{run['run_id']}/improve", timeout=120)
            response.raise_for_status()
            improved = response.json()
            st.session_state.improved = improved
            st.session_state.run = improved["after"]
            st.rerun()

with right:
    st.subheader("Eval and trace")
    if not run:
        st.info("No eval recorded.")
    else:
        st.code(run["phoenix_trace_id"], language=None)
        st.json(run["eval"]["metrics"])
        if run["eval"]["failure_summary"]:
            st.error(run["eval"]["failure_summary"])
        else:
            st.success("Eval passed for this seed case.")
        ledger = st.session_state.get("ledger", run["ledger"])
        st.subheader("Ledger events")
        for event in ledger["events"]:
            st.caption(event["event_type"])
            st.write(event["summary"])
