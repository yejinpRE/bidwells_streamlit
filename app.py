# app.py

import streamlit as st
import pandas as pd

from engine1_text import (
    extract_text_from_pdf,
    engine1_run,
    base_scores_from_text,  # used in repository tab
)
from engine2_context import build_context_features
from engine3_model import predict_approval_probability

# ---------------------------------------------------------
# Page config
# ---------------------------------------------------------
st.set_page_config(
    page_title="Bayes Plan Checker – Prototype",
    layout="wide",
)

st.title("Bayes ‘Plan Checker’ System – Prototype")
st.caption("Engine 0–3 | Multi-document, context-aware planning risk engine")


# ---------------------------------------------------------
# Initialise session state
# ---------------------------------------------------------
for key in [
    "ps_text",
    "cr_text",
    "ap_text",
    "ps_scores",
    "cr_scores",
    "doc_features",
    "ctx_features",
    "prediction",
    "repo_df",
]:
    if key not in st.session_state:
        st.session_state[key] = None


# ---------------------------------------------------------
# Tabs for each Engine + Repository
# ---------------------------------------------------------
tab_engine01, tab_engine2, tab_engine3, tab_repo = st.tabs(
    [
        "Engine 0 & 1 – Documents",
        "Engine 2 – Context",
        "Engine 3 – Output",
        "Repository / Batch",
    ]
)


# =========================================================
# TAB 1 – ENGINE 0 & 1: Documents (Rulebook + Extraction)
# =========================================================
with tab_engine01:
    st.header("Engine 0 & 1 – Document analysis")

    st.markdown(
        """
        **Purpose**  
        This tab runs Engine 0 (rulebook scoring) and Engine 1 (multi-document analysis).  
        Upload the documents for the case you want to analyse:
        - Planning Statement (PS)  
        - Committee / Officer Report (CR)  
        - Appeal Decision (optional)
        """
    )

    col_ps, col_cr, col_ap = st.columns(3)

    with col_ps:
        ps_file = st.file_uploader(
            "Planning Statement (PS)",
            type=["pdf"],
            key="ps_uploader",
        )
    with col_cr:
        cr_file = st.file_uploader(
            "Committee / Officer Report (CR)",
            type=["pdf"],
            key="cr_uploader",
        )
    with col_ap:
        ap_file = st.file_uploader(
            "Appeal Decision (optional)",
            type=["pdf"],
            key="ap_uploader",
        )

    run_engine01 = st.button("Run Engine 0 & 1 on uploaded documents")

    if run_engine01:
        if not (ps_file or cr_file):
            st.error("Please upload at least a Planning Statement or a Committee/Officer Report.")
        else:
            with st.spinner("Reading PDFs and running Engine 0 & 1..."):
                ps_text = extract_text_from_pdf(ps_file) if ps_file else None
                cr_text = extract_text_from_pdf(cr_file) if cr_file else None
                ap_text = extract_text_from_pdf(ap_file) if ap_file else None

                st.session_state["ps_text"] = ps_text
                st.session_state["cr_text"] = cr_text
                st.session_state["ap_text"] = ap_text

                ps_scores, cr_scores, doc_features = engine1_run(ps_text, cr_text, ap_text)

                st.session_state["ps_scores"] = ps_scores
                st.session_state["cr_scores"] = cr_scores
                st.session_state["doc_features"] = doc_features

            st.success("Engine 0 & 1 completed for this case.")

    # Show results if available
    if st.session_state["doc_features"] is not None:
        st.subheader("Engine 0 & 1 – Outputs for this case")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Planning Statement – Rulebook scores**")
            if st.session_state["ps_scores"]:
                st.json(st.session_state["ps_scores"])
            else:
                st.info("No Planning Statement uploaded.")

            st.markdown("**Appeal Decision – Scores (if any)**")
            ap_scores = st.session_state["doc_features"].get("Appeal_Scores", {})
            if ap_scores:
                st.json(ap_scores)
            else:
                st.info("No Appeal Decision uploaded.")

        with col2:
            st.markdown("**Committee / Officer Report – Rulebook scores**")
            if st.session_state["cr_scores"]:
                st.json(st.session_state["cr_scores"])
            else:
                st.info("No Committee/Officer Report uploaded.")

            st.markdown("**Aggregated X-variables used by later engines**")
            st.json(st.session_state["doc_features"])

        st.markdown("**Spin Index (difference between PS and CR)**")
        spin_index = st.session_state["doc_features"].get("X10_Spin_Index", 0.0)
        st.metric("X10 – Spin Index", f"{spin_index:.2f}")
    else:
        st.info("Upload documents and click the button to run Engine 0 & 1.")


# =========================================================
# TAB 2 – ENGINE 2: Context (Sliders)
# =========================================================
with tab_engine2:
    st.header("Engine 2 – Context inputs")

    st.markdown(
        """
        **Purpose**  
        Engine 2 captures the planning context that is not directly in the documents, such as:
        - Housing pressure  
        - Tilted balance status  
        - Local plan age  
        - Committee attitude  
        - Green Belt flag  
        - Flood zone level
        """
    )

    with st.form("context_form"):
        housing_pressure = st.slider(
            "Housing pressure (0 = low, 3 = very high)",
            0.0,
            3.0,
            1.5,
            0.5,
        )

        tb_status = st.select_slider(
            "Tilted balance status",
            options=[0, 1, 2],
            value=1,
            help="0 = Not engaged, 1 = Arguable, 2 = Clearly engaged",
        )

        plan_age = st.select_slider(
            "Local plan age",
            options=[0, 1, 2],
            value=1,
            help="0 = Up-to-date, 1 = Mid, 2 = Old / out-of-date",
        )

        committee_attitude = st.slider(
            "Committee attitude (0 = very restrictive, 3 = very permissive)",
            0.0,
            3.0,
            1.5,
            0.5,
        )

        gb_flag = st.selectbox(
            "Green Belt?",
            options=[0, 1],
            format_func=lambda x: "No" if x == 0 else "Yes",
        )

        floodzone_level = st.select_slider(
            "Flood zone level",
            options=[0, 1, 2, 3],
            value=0,
            help="0 = None / Zone 1, 2 = Zone 2, 3 = Zone 3",
        )

        submit_ctx = st.form_submit_button("Save Engine 2 context inputs")

    if submit_ctx:
        ctx_features = build_context_features(
            housing_pressure=housing_pressure,
            tb_status=tb_status,
            plan_age=plan_age,
            committee_attitude=committee_attitude,
            gb_flag=gb_flag,
            floodzone_level=floodzone_level,
        )
        st.session_state["ctx_features"] = ctx_features
        st.success("Context inputs saved for this case.")

    if st.session_state["ctx_features"] is not None:
        st.subheader("Current Engine 2 context features")
        st.json(st.session_state["ctx_features"])
    else:
        st.info("Set and save context inputs to use Engine 2.")


# =========================================================
# TAB 3 – ENGINE 3: Output (Prediction)
# =========================================================
with tab_engine3:
    st.header("Engine 3 – Predictive output")

    st.markdown(
        """
        **Purpose**  
        Engine 3 combines:
        - Engine 0 & 1 document variables (X1–X10)  
        - Engine 2 context variables (X11–X16)  
        - Interaction terms (Z-variables)  
        
        …into a logit-style model to estimate the probability of planning approval and
        to show the contribution of each variable.
        """
    )

    if st.session_state["doc_features"] is None:
        st.error("Please run Engine 0 & 1 first (upload documents in the first tab).")
    elif st.session_state["ctx_features"] is None:
        st.error("Please set and save context inputs in Engine 2 tab.")
    else:
        run_engine3 = st.button("Run Engine 3 – Compute probability")
        if run_engine3:
            X_all = {}
            X_all.update(st.session_state["doc_features"])
            X_all.update(st.session_state["ctx_features"])

            with st.spinner("Running Engine 3..."):
                pred = predict_approval_probability(X_all)

            st.session_state["prediction"] = pred
            st.success("Engine 3 completed for this case.")

        if st.session_state["prediction"] is not None:
            pred = st.session_state["prediction"]
            prob = pred["probability"]
            rating = pred["rating"]

            st.subheader("Overall risk result")

            col_main, col_side = st.columns([2, 1])
            with col_main:
                st.metric(
                    label="Predicted approval probability",
                    value=f"{prob*100:.1f}%",
                )
                st.write(f"**Risk rating:** {rating}")

                st.progress(min(max(prob, 0.01), 0.99))

            with col_side:
                st.markdown("**Linear score (Z_total)**")
                st.write(f"{pred['linear_score']:.3f}")

            st.markdown("---")
            st.markdown("### Coefficients & contributions")

            contrib_rows = pred.get("contributions", [])
            if contrib_rows:
                df_contrib = pd.DataFrame(contrib_rows)
                df_contrib = df_contrib.sort_values(
                    by="abs_contribution", ascending=False
                )

                st.write("Top drivers (by absolute contribution to Z_total):")
                st.dataframe(
                    df_contrib.head(12)[
                        ["name", "type", "value", "coefficient", "contribution"]
                    ]
                )

                with st.expander("Show all variables and contributions"):
                    st.dataframe(
                        df_contrib[
                            ["name", "type", "value", "coefficient", "contribution"]
                        ]
                    )

                st.caption(
                    "Each row shows a variable, its coefficient, its current value for this case, "
                    "and its contribution to the linear score Z_total (β × X)."
                )
            else:
                st.info("No contribution table available from Engine 3 yet.")


# =========================================================
# TAB 4 – REPOSITORY / BATCH (Prototype)
# =========================================================
with tab_repo:
    st.header("Repository / Batch processing (prototype)")

    st.markdown(
        """
        **Purpose**  
        This tab is the starting point for a future repository-based workflow:
        - Upload multiple documents  
        - Run Engine 0 & 1 in batch  
        - Build a table of X-variables for many cases  
        - (Later) attach outcomes and fit a real logistic regression model
        
        At the moment this tab only runs Engine 0 & 1 in batch and shows
        the resulting feature table.
        """
    )

    repo_files = st.file_uploader(
        "Upload multiple Planning Statements to build a simple repository",
        type=["pdf"],
        accept_multiple_files=True,
        key="repo_files",
    )

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        run_batch = st.button("Run Engine 0 & 1 in batch for uploaded PDFs")
    with col_btn2:
        clear_repo = st.button("Clear repository table")

    if clear_repo:
        st.session_state["repo_df"] = None
        st.success("Repository table cleared.")

    if run_batch and repo_files:
        all_rows = []
        with st.spinner("Running Engine 0 & 1 in batch for all uploaded PDFs..."):
            for f in repo_files:
                text = extract_text_from_pdf(f)
                scores = base_scores_from_text(text)
                row = {
                    "CaseID": f.name,
                    **scores,
                }
                all_rows.append(row)

        if all_rows:
            df_repo = pd.DataFrame(all_rows)
            st.session_state["repo_df"] = df_repo
            st.success("Repository table updated from uploaded documents.")

    if st.session_state["repo_df"] is not None:
        st.subheader("Current repository (Engine 0 & 1 features per case)")
        st.dataframe(st.session_state["repo_df"])
        st.caption(
            "This is a prototype repository. In a future stage, we could attach outcomes "
            "and use this as the basis for a real data-trained logistic regression model."
        )
    else:
        st.info("No repository table yet. Upload multiple PDFs and run the batch engine.")

