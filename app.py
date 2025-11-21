# app.py
import streamlit as st
import pandas as pd

from engine1_text import extract_text_from_pdf, engine1_run
from engine2_context import build_context_features
from engine3_model import predict_approval_probability

st.set_page_config(
    page_title="Bayes Plan Checker – Prototype",
    layout="wide",
)

st.title("Bayes ‘Plan Checker’ System – Prototype")
st.caption("Engine 0–3 | Multi-document analysis (PS, Committee/Officer, Appeal)")

# ---------------- Sidebar – 파일 업로드 ----------------
st.sidebar.header("1. Upload planning documents (PDF)")

ps_file = st.sidebar.file_uploader("Planning Statement (PS)", type=["pdf"])
cr_file = st.sidebar.file_uploader("Committee / Officer Report (CR)", type=["pdf"])
ap_file = st.sidebar.file_uploader("Appeal Decision (optional)", type=["pdf"])
other_file = st.sidebar.file_uploader("Other Supporting Doc (optional)", type=["pdf"])

# ---------------- Sidebar – Context 입력 ----------------
st.sidebar.header("2. Context / LPA Inputs (Engine 2)")

housing_pressure = st.sidebar.slider(
    "Housing Pressure (0=low, 3=very high)", 0.0, 3.0, 1.5, 0.5
)

tb_status = st.sidebar.select_slider(
    "Tilted Balance Status (TB)",
    options=[0, 1, 2],
    value=1,
    help="0=Not engaged, 1=Arguable, 2=Clearly engaged",
)

plan_age = st.sidebar.select_slider(
    "Local Plan Age",
    options=[0, 1, 2],
    value=1,
    help="0=Up-to-date, 1=Mid, 2=Old/out-of-date",
)

committee_attitude = st.sidebar.slider(
    "Committee Attitude (0=very restrictive, 3=very permissive)",
    0.0,
    3.0,
    1.5,
    0.5,
)

gb_flag = st.sidebar.selectbox(
    "Green Belt designation?",
    options=[0, 1],
    format_func=lambda x: "No" if x == 0 else "Yes",
)

floodzone_level = st.sidebar.select_slider(
    "Flood Zone level",
    options=[0, 1, 2, 3],
    value=0,
    help="0=None/1, 2=Zone 2, 3=Zone 3",
)

run_button = st.sidebar.button("Run full Engine 1–3")


# ---------------- 메인 로직 ----------------
if run_button:
    if not (ps_file or cr_file):
        st.error("⚠️ 최소한 Planning Statement 또는 Committee/Officer Report 중 하나는 업로드해야 합니다.")
        st.stop()

    # 1) 텍스트 추출
    with st.spinner("Reading PDFs..."):
        ps_text = extract_text_from_pdf(ps_file) if ps_file else None
        cr_text = extract_text_from_pdf(cr_file) if cr_file else None
        ap_text = extract_text_from_pdf(ap_file) if ap_file else None

    # 2) Engine 1
    with st.spinner("Running Engine 1 – Evidence extraction..."):
        ps_scores, cr_scores, doc_features = engine1_run(ps_text, cr_text, ap_text)

    # 3) Engine 2
    ctx_features = build_context_features(
        housing_pressure=housing_pressure,
        tb_status=tb_status,
        plan_age=plan_age,
        committee_attitude=committee_attitude,
        gb_flag=gb_flag,
        floodzone_level=floodzone_level,
    )

    # 4) Engine 1 + 2 합치기
    X_all = {}
    X_all.update(doc_features)
    X_all.update(ctx_features)

    # 5) Engine 3 – 예측
    with st.spinner("Running Engine 3 – Predictive model..."):
        pred = predict_approval_probability(X_all)
        prob = pred["probability"]
        rating = pred["rating"]

    # ---------------- Summary 카드 ----------------
    st.subheader("Overall Planning Risk Assessment")

    col_main, col_side = st.columns([2, 1])

    with col_main:
        st.metric(
            label="Predicted Approval Probability",
            value=f"{prob*100:.1f}%",
        )
        st.write(f"**Risk rating:** :{ 'green_circle' if rating=='Green' else 'orange_circle' if rating=='Amber' else 'red_circle' }: **{rating}**")

        st.progress(min(max(prob, 0.01), 0.99))

    with col_side:
        st.markdown("**Context snapshot**")
        st.write(
            f"""
            • Housing pressure: `{housing_pressure}`  
            • Tilted balance: `{tb_status}`  
            • Plan age: `{plan_age}`  
            • Committee attitude: `{committee_attitude}`  
            • Green Belt: `{'Yes' if gb_flag else 'No'}`  
            • Flood zone: `{floodzone_level}`  
            """
        )

    # ---------------- 탭: Summary / Documents / Context ----------------
    tab_summary, tab_docs, tab_ctx = st.tabs(["Summary drivers", "Documents comparison", "Context details"])

    # ---- Tab 1: Summary drivers ----
    with tab_summary:
        st.markdown("### Key numerical drivers (X-variables)")

        # 핵심 변수만 테이블로 표시
        key_vars = [
            "X1_Heritage_Harm",
            "X2_Design_Quality",
            "X3_Amenity_Harm",
            "X4_Ecology_Harm",
            "X5_GB_Harm",
            "X6_Flood_Risk",
            "X7_Economic_Benefit",
            "X8_Social_Benefit",
            "X9_Policy_Compliance",
            "X10_Spin_Index",
            "X11_Housing_Pressure",
            "X12_TB_Status",
            "X14_Committee_Attitude",
        ]
        data = {k: [X_all.get(k, 0)] for k in key_vars}
        df = pd.DataFrame(data, index=["Value"])
        st.dataframe(df.T)

        st.markdown("### Interaction effects (Z-variables)")
        st.json(pred["interactions"])

    # ---- Tab 2: Documents comparison ----
    with tab_docs:
        st.markdown("### Document-based scoring (Engine 1)")

        docs_table = []

        def _row(name: str, scores: dict):
            if not scores:
                return
            docs_table.append(
                {
                    "Document": name,
                    "Heritage": scores.get("Heritage_Harm", 0),
                    "Design": scores.get("Design_Quality", 0),
                    "Amenity": scores.get("Amenity_Harm", 0),
                    "Ecology": scores.get("Ecology_Harm", 0),
                    "GB Harm": scores.get("GB_Harm", 0),
                    "Flood": scores.get("Flood_Risk", 0),
                    "Economic": scores.get("Economic_Benefit", 0),
                    "Social": scores.get("Social_Benefit", 0),
                    "Policy": scores.get("Policy_Compliance", 0),
                }
            )

        _row("Planning Statement", ps_scores)
        _row("Committee / Officer Report", cr_scores)
        _row("Appeal Decision", doc_features.get("Appeal_Scores", {}))

        if docs_table:
            df_docs = pd.DataFrame(docs_table)
            st.dataframe(df_docs)

            st.markdown("#### Heritage / Design / Benefits comparison")
            if len(df_docs) > 1:
                chart_data = df_docs.set_index("Document")[["Heritage", "Design", "Economic", "Social"]]
                st.bar_chart(chart_data)
        else:
            st.info("No document scores available.")

    # ---- Tab 3: Context ----
    with tab_ctx:
        st.markdown("### Engine 2 – Context inputs")
        st.json(ctx_features)

else:
    st.info("👈 왼쪽 사이드바에서 문서 업로드와 컨텍스트 값을 설정한 뒤 **Run full Engine 1–3** 버튼을 눌러줘.")
