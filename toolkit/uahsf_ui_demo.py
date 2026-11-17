from __future__ import annotations

import json
from pathlib import Path
import sys

try:
    import streamlit as st
except Exception as exc:  # pragma: no cover
    raise SystemExit("Please install streamlit first: pip install streamlit") from exc

try:
    from .demo_engine import analyze_demo_report
except Exception:
    sys.path.append(str(Path(__file__).resolve().parent))
    from demo_engine import analyze_demo_report


SAMPLES = {
    "Potential SBR": "Chrome crashes when opening a crafted file URL. The file handler allows unauthorized read access and may expose local credentials.",
    "Likely NSBR": "The settings page crashes after clicking the button twice. No stack trace is shown and the issue seems related to UI loading.",
    "Ambiguous": "Memory leak in session restore after opening multiple tabs. The browser becomes slow and sometimes crashes.",
}


def main() -> None:
    st.set_page_config(page_title="UAHSF SBR Demo", page_icon="🛡️", layout="wide")

    st.title("🛡️ UAHSF SBR Detection Demo")
    st.caption(
        "A lightweight UI for visualizing UAHSF-style uncertainty-aware SBR detection. "
    )

    with st.sidebar:
        st.header("Demo settings")
        sample_name = st.selectbox("Load sample", list(SAMPLES.keys()), index=0)
        threshold = st.slider("Decision threshold", 0.1, 0.9, 0.5, 0.05)
        beta = st.slider("Fusion beta", 0.0, 1.0, 0.5, 0.05)
        k = st.slider("Fusion sharpness k", 2.0, 20.0, 8.0, 0.5)
        st.info("The values are computed by a transparent heuristic proxy for demo purposes.")

    text = st.text_area(
        "Bug report text",
        value=SAMPLES[sample_name],
        height=180,
        placeholder="Paste summary + description here...",
    )

    if st.button("Analyze report", type="primary"):
        result = analyze_demo_report(text, beta=beta, k=k)
        label = "SBR" if result.p_final >= threshold else "NSBR"

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Final decision", label)
        c2.metric("P_final", f"{result.p_final:.3f}")
        c3.metric("Local conflict", f"{result.local_conflict:.3f}")
        c4.metric("Global completeness", f"{result.global_completeness:.3f}")

        st.subheader("Fusion trace")
        trace_cols = st.columns(4)
        trace_cols[0].metric("P_BERT", f"{result.p_bert:.3f}")
        trace_cols[1].metric("P_LLM", f"{result.p_llm:.3f}")
        trace_cols[2].metric("α_BERT", f"{result.alpha_bert:.3f}")
        trace_cols[3].metric("Uncertainty", f"{result.uncertainty:.3f}")

        st.subheader("Matched security terms")
        st.write(result.matched_terms or "No security terms matched.")

        left, right = st.columns(2)
        with left:
            st.subheader("Local contradiction terms")
            if result.contradiction_terms:
                st.dataframe([x.__dict__ for x in result.contradiction_terms], use_container_width=True)
            else:
                st.write("No ambiguous security terms detected.")

        with right:
            st.subheader("Low-coverage CWE patterns")
            st.dataframe([x.__dict__ for x in result.low_coverage_patterns], use_container_width=True)

        st.subheader("Brief rationale")
        st.write(result.rationale)

        with st.expander("JSON output"):
            st.code(json.dumps(result.to_dict(), indent=2), language="json")


if __name__ == "__main__":
    main()
