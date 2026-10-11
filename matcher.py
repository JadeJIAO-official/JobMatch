"""可解释的岗位要求拆解与简历证据匹配逻辑。"""

from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any


CONCEPTS: OrderedDict[str, tuple[str, ...]] = OrderedDict(
    [
        ("SQL", ("sql",)),
        ("Python", ("python",)),
        ("Excel", ("excel",)),
        ("Tableau", ("tableau",)),
        ("Power BI", ("power bi", "powerbi")),
        ("Pandas", ("pandas",)),
        ("数据分析", ("数据分析", "数据分析能力", "data analysis")),
        ("用户研究", ("用户研究", "用户调研", "user research")),
        ("需求分析", ("需求分析", "需求梳理", "需求挖掘")),
        ("产品设计", ("产品设计", "产品方案", "功能设计")),
        ("PRD", ("prd", "产品需求文档")),
        ("原型设计", ("原型设计", "交互原型", "axure", "figma")),
        ("竞品分析", ("竞品分析", "竞争产品分析")),
        ("产品运营", ("产品运营", "活动运营", "内容运营")),
        ("用户增长", ("用户增长", "增长策略", "拉新", "促活")),
        ("指标体系", ("指标体系", "指标设计", "核心指标")),
        ("漏斗分析", ("漏斗分析", "转化漏斗", "转化分析")),
        ("A/B测试", ("a/b测试", "ab测试", "实验设计", "实验分析")),
        ("数据可视化", ("数据可视化", "可视化", "数据看板", "dashboard")),
        ("机器学习", ("机器学习", "machine learning", "sklearn", "scikit-learn")),
        ("沟通协作", ("沟通协作", "沟通协调", "跨部门协作", "跨团队协作")),
        ("项目推进", ("项目推进", "项目管理", "推动项目", "进度跟进")),
        ("文档撰写", ("文档撰写", "撰写文档", "方案撰写", "汇报材料")),
    ]
)

MUST_MARKERS = ("必须", "必备", "熟练", "精通", "掌握", "熟悉", "了解", "至少", "要求", "具备", "required", "must have")
NICE_MARKERS = ("加分", "优先", "优先考虑", "最好", "nice to have", "preferred")
RESPONSIBILITY_MARKERS = ("负责", "协助", "参与", "推动", "跟进", "搭建", "优化", "设计", "分析", "运营")
WEIGHTS = {"必备技能": 3.0, "岗位职责": 2.0, "加分项": 1.0}


def _contains_alias(text: str, alias: str) -> bool:
    text_lower = text.casefold()
    alias_lower = alias.casefold()
    if re.fullmatch(r"[a-z0-9 +#./_-]+", alias_lower):
        pattern = rf"(?<![a-z0-9]){re.escape(alias_lower)}(?![a-z0-9])"
        return re.search(pattern, text_lower) is not None
    return alias_lower in text_lower


def find_concepts(text: str) -> list[str]:
    """按词典识别岗位描述或简历文本中的技能、产品能力。"""
    found: list[str] = []
    for concept, aliases in CONCEPTS.items():
        if any(_contains_alias(text, alias) for alias in aliases):
            found.append(concept)
    return found


def _clean_clause(clause: str) -> str:
    clause = re.sub(r"^\s*(?:[-*•▪‣]+|\d+[.)、．])\s*", "", clause)
    clause = re.sub(r"^(?:岗位职责|工作职责|任职要求|职位要求|加分项|优先条件)\s*[:：]\s*", "", clause, flags=re.I)
    return clause.strip(" \t\r\n；;。")


def classify_requirement(text: str) -> str:
    text_lower = text.casefold()
    if any(marker.casefold() in text_lower for marker in NICE_MARKERS):
        return "加分项"
    if any(marker.casefold() in text_lower for marker in MUST_MARKERS):
        return "必备技能"
    if any(marker.casefold() in text_lower for marker in RESPONSIBILITY_MARKERS):
        return "岗位职责"
    # 没有明显分类词时，作为职责展示，方便用户在界面中手动调整。
    return "岗位职责"


def extract_requirements(job_description: str) -> dict[str, list[str]]:
    """用标点和分类提示词拆分 JD；规则结果需要用户复核。"""
    result: dict[str, list[str]] = {"必备技能": [], "岗位职责": [], "加分项": []}
    section_headers = {
        "岗位职责": "岗位职责",
        "工作职责": "岗位职责",
        "任职要求": "必备技能",
        "职位要求": "必备技能",
        "岗位要求": "必备技能",
        "加分项": "加分项",
        "优先条件": "加分项",
    }
    current_section: str | None = None
    for index, raw in enumerate(re.split(r"[\n\r；;。]+", job_description)):
        raw_title = raw.strip().strip("：:")
        if raw_title in section_headers:
            current_section = section_headers[raw_title]
            continue
        if (
            index == 0
            and current_section is None
            and re.search(r"实习生|招聘岗位|职位名称", raw_title)
            and not any(marker in raw_title for marker in MUST_MARKERS + NICE_MARKERS + RESPONSIBILITY_MARKERS)
        ):
            continue
        raw_prefix = raw.strip()
        for header, category in section_headers.items():
            if raw_prefix.startswith(header + "：") or raw_prefix.startswith(header + ":"):
                current_section = category
                raw = re.split(r"[：:]", raw, maxsplit=1)[-1]
                break
        item = _clean_clause(raw)
        if len(item) < 3:
            continue
        bucket = current_section or classify_requirement(item)
        if item not in result[bucket]:
            result[bucket].append(item)
    return result


def parse_requirement_lines(text: str) -> list[str]:
    """解析用户编辑后的逐行要求。"""
    items: list[str] = []
    for raw in re.split(r"[\n\r]+", text):
        item = _clean_clause(raw)
        if len(item) >= 2 and item not in items:
            items.append(item)
    return items


def split_resume_lines(resume_text: str) -> list[str]:
    lines: list[str] = []
    for raw in re.split(r"[\n\r。；;]+", resume_text):
        line = re.sub(r"^\s*(?:[-*•▪‣]+|\d+[.)、．])\s*", "", raw).strip()
        if line and line not in lines:
            lines.append(line)
    return lines


def _evidence_for_concept(concept: str, resume_lines: list[str]) -> list[str]:
    aliases = CONCEPTS[concept]
    return [line for line in resume_lines if any(_contains_alias(line, alias) for alias in aliases)]


def _analyze_item(text: str, category: str, resume_lines: list[str]) -> dict[str, Any]:
    concepts = find_concepts(text)
    if not concepts:
        return {
            "requirement": text,
            "category": category,
            "concepts": [],
            "matched_concepts": [],
            "missing_concepts": [],
            "ratio": None,
            "status": "待人工核对",
            "evidence": [],
            "weight": WEIGHTS[category],
        }

    matched: list[str] = []
    evidence: list[str] = []
    for concept in concepts:
        concept_evidence = _evidence_for_concept(concept, resume_lines)
        if concept_evidence:
            matched.append(concept)
            evidence.extend(concept_evidence)
    missing = [concept for concept in concepts if concept not in matched]
    ratio = len(matched) / len(concepts)
    if ratio >= 0.999:
        status = "已匹配"
    elif ratio > 0:
        status = "部分匹配"
    else:
        status = "未找到证据"
    return {
        "requirement": text,
        "category": category,
        "concepts": concepts,
        "matched_concepts": matched,
        "missing_concepts": missing,
        "ratio": ratio,
        "status": status,
        "evidence": list(dict.fromkeys(evidence)),
        "weight": WEIGHTS[category],
    }


def analyze_match(requirements: dict[str, list[str]], resume_text: str) -> dict[str, Any]:
    resume_lines = split_resume_lines(resume_text)
    rows = [
        _analyze_item(item, category, resume_lines)
        for category in ("必备技能", "岗位职责", "加分项")
        for item in requirements.get(category, [])
    ]
    scorable = [row for row in rows if row["ratio"] is not None]
    denominator = sum(row["weight"] for row in scorable)
    score = (
        sum(row["weight"] * row["ratio"] for row in scorable) / denominator * 100
        if denominator
        else None
    )
    return {"rows": rows, "score": score, "scorable_count": len(scorable), "total_count": len(rows)}


def suggestions_for_row(row: dict[str, Any]) -> str:
    if row["status"] == "待人工核对":
        return "该要求未命中当前词典中的能力词，请手动判断是否有对应经历；可在要求编辑区补充更具体的关键词。"
    if row["status"] == "已匹配":
        return "已有相关证据。可把最贴近岗位的任务、个人动作和真实结果写得更具体，并将相关经历前置。"
    if row["status"] == "部分匹配":
        missing = "、".join(row["missing_concepts"])
        return f"已有部分相关证据；检查是否存在能证明“{missing}”的真实经历，若没有，不要在简历中补写。"
    missing = "、".join(row["missing_concepts"])
    return f"当前简历没有找到“{missing}”相关证据。若确有课程或项目经历，可补充具体任务与产出；若没有，可将其列为学习计划，不要编造经历。"


def interview_question_for_row(row: dict[str, Any]) -> str:
    requirement = row["requirement"]
    if row["status"] == "已匹配":
        return f"请结合简历中的具体经历，说明你如何完成“{requirement}”，你负责的部分和结果是什么？"
    if row["status"] == "部分匹配":
        return f"对于“{requirement}”，你已有的相关经验是什么？还没有覆盖的部分你会怎样补齐？"
    if row["status"] == "待人工核对":
        return f"你如何理解岗位要求“{requirement}”？如果入职，你会怎样开始这项工作？"
    return f"目前简历没有体现“{requirement}”的直接经验。你会如何拆解并完成这项任务？"


def export_markdown(role_name: str, result: dict[str, Any]) -> str:
    score = "暂无可计算项" if result["score"] is None else f"{result['score']:.1f}%（规则覆盖度参考值）"
    lines = [
        f"# 岗位匹配分析：{role_name or '未命名岗位'}",
        "",
        f"- 规则覆盖度：{score}",
        f"- 要求条目：{result['total_count']} 条；可按词典计算：{result['scorable_count']} 条",
        "- 说明：规则结果用于自查，不代表岗位录用概率。",
        "",
    ]
    for row in result["rows"]:
        lines.extend([f"## [{row['category']}] {row['requirement']}", f"**状态：** {row['status']}"])
        if row["evidence"]:
            lines.append("**简历证据：** " + "；".join(row["evidence"]))
        else:
            lines.append("**简历证据：** 未找到直接证据")
        lines.append("**建议：** " + suggestions_for_row(row))
        lines.append("**面试准备：** " + interview_question_for_row(row))
        lines.append("")
    return "\n".join(lines)
