from __future__ import annotations

from pathlib import Path

import streamlit as st

from matcher import (
    analyze_match,
    export_markdown,
    extract_requirements,
    interview_question_for_row,
    parse_requirement_lines,
    suggestions_for_row,
)


ROOT = Path(__file__).parent
SAMPLE_DIR = ROOT / "sample_data"
CATEGORY_KEYS = {
    "必备技能": "requirements_must",
    "岗位职责": "requirements_responsibilities",
    "加分项": "requirements_nice",
}

st.set_page_config(
    page_title="求职岗位匹配助手",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      html, body, [class*="css"] { font-family: 'DM Sans', 'Noto Sans SC', sans-serif; }
      .stApp { background: #f5f7fb; }
      .block-container { max-width: 1240px; padding-top: 2.1rem; padding-bottom: 3rem; }
      .hero { background: linear-gradient(115deg, #102b54 0%, #225c87 58%, #438a93 100%); padding: 2rem 2.2rem; border-radius: 18px; color: white; margin-bottom: 1.25rem; }
      .hero h1 { color: white; font-size: 2rem; margin: 0 0 .4rem 0; }
      .hero p { color: #dceaf2; margin: 0; font-size: 1rem; }
      .eyebrow { color: #a9d7d2; text-transform: uppercase; letter-spacing: .12em; font-size: .72rem; font-weight: 700; margin-bottom: .55rem; }
      div[data-testid="stMetric"] { background: #fff; border: 1px solid #e4eaf1; padding: 1rem 1.1rem; border-radius: 12px; }
      div[data-testid="stExpander"] { background: #fff; border: 1px solid #e4eaf1; border-radius: 12px; }
      .small-note { color: #667085; font-size: .88rem; }
      .stButton > button[kind="primary"] { background: #176b70; border-color: #176b70; }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_demo() -> None:
    st.session_state["job_description"] = (SAMPLE_DIR / "demo_job_description.txt").read_text(encoding="utf-8")
    st.session_state["resume_text"] = (SAMPLE_DIR / "demo_resume.txt").read_text(encoding="utf-8")
    st.session_state["requirements_ready"] = False
    st.session_state.pop("analysis_result", None)


def clear_inputs() -> None:
    st.session_state["job_description"] = ""
    st.session_state["resume_text"] = ""
    st.session_state["requirements_ready"] = False
    st.session_state.pop("analysis_result", None)
    for key in CATEGORY_KEYS.values():
        st.session_state.pop(key, None)


st.markdown(
    """
    <section class="hero">
      <div class="eyebrow">CAREER TOOLKIT · MVP</div>
      <h1>求职岗位匹配助手</h1>
      <p>把岗位要求拆清楚，找到简历里的真实证据，再决定怎么补强。</p>
    </section>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### 使用说明")
    st.markdown(
        """
        1. 粘贴岗位描述和简历文本。  
        2. 检查并编辑自动拆分的要求。  
        3. 查看匹配依据、差距和面试准备题。
        """
    )
    st.info("当前版本使用本地规则进行匹配，不调用外部 AI 接口，也不把输入写入数据库。")
    st.caption("匹配度是规则覆盖度参考值，不是录用概率。未识别的表达请手动核对。")
    st.markdown("---")
    st.markdown(
        """**当前版本**  
输入：岗位描述、简历文本  
输出：要求拆解、证据匹配、差距建议、面试问题"""
    )

st.text_input("目标岗位名称（用于导出分析摘要）", key="role_name", placeholder="例如：产品经理实习生（用户增长方向）")

left_action, right_action, _ = st.columns([1.1, 1.1, 4])
with left_action:
    st.button("载入演示样例", on_click=load_demo, use_container_width=True)
with right_action:
    st.button("清空内容", on_click=clear_inputs, use_container_width=True)

st.markdown("### 1. 输入岗位与简历")
col_jd, col_resume = st.columns(2, gap="large")
with col_jd:
    st.text_area(
        "岗位描述（JD）",
        key="job_description",
        height=300,
        placeholder="粘贴完整岗位描述，建议保留岗位职责、任职要求和加分项标题。",
    )
with col_resume:
    st.text_area(
        "简历文本",
        key="resume_text",
        height=300,
        placeholder="粘贴简历中的教育、实习、项目和技能内容。建议删去手机号、邮箱等个人信息。",
    )

parse_col, _ = st.columns([1.3, 4])
with parse_col:
    if st.button("拆解岗位要求", type="primary", use_container_width=True):
        jd = st.session_state.get("job_description", "").strip()
        if not jd:
            st.warning("请先粘贴岗位描述。")
        else:
            parsed = extract_requirements(jd)
            for category, key in CATEGORY_KEYS.items():
                st.session_state[key] = "\n".join(parsed[category])
            st.session_state["requirements_ready"] = True
            st.session_state.pop("analysis_result", None)

if st.session_state.get("requirements_ready"):
    st.markdown("### 2. 检查并调整要求分类")
    st.caption("自动拆解依据文本标记词完成。你可以逐行增删或调整内容；分类错误不会自动纠正。")
    requirement_columns = st.columns(3, gap="medium")
    labels = [("必备技能", "requirements_must"), ("岗位职责", "requirements_responsibilities"), ("加分项", "requirements_nice")]
    for column, (label, key) in zip(requirement_columns, labels):
        with column:
            st.text_area(label, key=key, height=190, placeholder="每行一项")
    analyze_col, _ = st.columns([1.5, 4])
    with analyze_col:
        if st.button("生成匹配分析", type="primary", use_container_width=True):
            resume = st.session_state.get("resume_text", "").strip()
            if not resume:
                st.warning("请先粘贴简历文本。")
            else:
                requirements = {
                    category: parse_requirement_lines(st.session_state.get(key, ""))
                    for category, key in CATEGORY_KEYS.items()
                }
                st.session_state["analysis_result"] = analyze_match(requirements, resume)

result = st.session_state.get("analysis_result")
if result:
    st.markdown("---")
    st.markdown("### 3. 匹配结果与行动建议")
    score_label = "—" if result["score"] is None else f"{result['score']:.1f}%"
    score_help = "按可识别要求的权重计算；未识别条目需人工核对。"
    met1, met2, met3 = st.columns(3)
    met1.metric("规则覆盖度参考值", score_label, help=score_help)
    met2.metric("岗位要求条目", result["total_count"])
    met3.metric("可按词典分析", result["scorable_count"])
    if result["score"] is not None:
        st.progress(min(max(result["score"] / 100, 0.0), 1.0))
    st.caption("该分数仅反映当前关键词规则命中情况；请结合实际经历判断，不代表岗位录用概率。")

    rows_by_status = {
        "已匹配": [row for row in result["rows"] if row["status"] == "已匹配"],
        "部分匹配": [row for row in result["rows"] if row["status"] == "部分匹配"],
        "未找到证据": [row for row in result["rows"] if row["status"] == "未找到证据"],
        "待人工核对": [row for row in result["rows"] if row["status"] == "待人工核对"],
    }
    tabs = st.tabs(list(rows_by_status))
    for tab, status in zip(tabs, rows_by_status):
        with tab:
            rows = rows_by_status[status]
            if not rows:
                st.info("当前没有此类条目。")
            for row in rows:
                with st.expander(f"[{row['category']}] {row['requirement']}"):
                    if row["concepts"]:
                        st.markdown("**识别能力：** " + "、".join(row["concepts"]))
                    if row["evidence"]:
                        st.markdown("**简历证据：**")
                        for evidence in row["evidence"]:
                            st.markdown(f"> {evidence}")
                    else:
                        st.markdown("**简历证据：** 未找到直接证据")
                    st.markdown("**建议：** " + suggestions_for_row(row))
                    st.markdown("**面试准备：** " + interview_question_for_row(row))

    export = export_markdown(st.session_state.get("role_name", ""), result)
    st.download_button(
        "下载分析摘要（Markdown）",
        data=export,
        file_name="岗位匹配分析.md",
        mime="text/markdown",
    )

st.markdown("---")
st.markdown(
    '<p class="small-note">隐私提示：本地原型只在当前应用会话中处理输入，不提供自动投递或自动编写经历。请勿粘贴身份证号、手机号等敏感信息。</p>',
    unsafe_allow_html=True,
)
