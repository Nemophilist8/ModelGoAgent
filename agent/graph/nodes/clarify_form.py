"""
澄清表单：结构化 interrupt / resume，支持多组件多字段与局部二次追问。
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

from agent.config import logger
from agent.models import ComponentDraft

from .work_resolver_helpers import (
    derive_canonical_from_mention,
    is_retrievable_name,
    normalize_work_form,
    normalize_work_type,
    validate_license_for_merge,
)

# 字段元数据（第三期：类型 / 发布形式矩阵）
CLARIFY_FIELD_DEFS: dict[str, dict[str, Any]] = {
    "license_name": {
        "label": "许可证",
        "type": "spdx",
        "required": True,
        "hint": "如 MIT、Apache-2.0、GPL-3.0、CC-BY-SA-4.0",
    },
    "canonical_name": {
        "label": "正式名称",
        "type": "text",
        "required": True,
        "hint": "官方名或 HuggingFace 路径 org/model",
    },
    "work_type": {
        "label": "类型",
        "type": "enum",
        "enum": ["data", "model"],
        "required": False,
    },
    "work_form": {
        "label": "发布形式",
        "type": "enum",
        "enum": ["raw", "binary", "saas"],
        "required": False,
    },
}


def get_missing_fields(draft: ComponentDraft) -> List[str]:
    missing: List[str] = []
    if draft.canonical_name.startswith("inferred_"):
        missing.append("canonical_name")
    if draft.license_name == "TBD":
        missing.append("license_name")
    return missing


def build_clarify_form(drafts: List[ComponentDraft]) -> dict:
    """生成 API / 客户端可用的澄清表单 schema。"""
    components = []
    all_missing: set[str] = set()

    for d in drafts:
        if d.registry_hit:
            continue
        missing = get_missing_fields(d)
        if not missing:
            continue
        all_missing.update(missing)
        components.append({
            "id": d.canonical_name,
            "mention": d.mention,
            "canonical_name": d.canonical_name,
            "missing": missing,
            "defaults": {
                "work_type": d.work_type,
                "work_form": d.work_form,
            },
        })

    fields = {k: CLARIFY_FIELD_DEFS[k] for k in sorted(all_missing) if k in CLARIFY_FIELD_DEFS}
    return {
        "version": 1,
        "components": components,
        "fields": fields,
    }


def build_clarify_form_message(form: dict, *, partial: bool = False) -> str:
    lines = [
        "请补充以下组件信息（推荐使用结构化表单；也可在客户端按行填写）。",
        "",
    ]
    if partial:
        lines.insert(0, "【仍有未填项，请继续补充】")
    for comp in form.get("components") or []:
        miss_labels = [
            CLARIFY_FIELD_DEFS[f]["label"]
            for f in comp.get("missing") or []
            if f in CLARIFY_FIELD_DEFS
        ]
        lines.append(f"- 「{comp.get('mention')}」({comp.get('canonical_name')})：{', '.join(miss_labels)}")
    lines.append("")
    lines.append("表单字段说明见响应中的 clarify_form；CLI 将逐项提示输入。")
    return "\n".join(lines)


def _find_draft_for_answer(drafts: List[ComponentDraft], row: dict) -> Optional[ComponentDraft]:
    canonical = (row.get("canonical_name") or row.get("id") or "").strip()
    mention = (row.get("mention") or "").strip()
    candidates = [d for d in drafts if not d.registry_hit]

    if canonical:
        for d in candidates:
            if d.canonical_name.lower() == canonical.lower():
                return d
    if mention:
        for d in candidates:
            if mention.lower() in (d.mention.lower(), d.canonical_name.lower()):
                return d
            derived = derive_canonical_from_mention(mention)
            if derived and derived.lower() == d.canonical_name.lower():
                return d
    return None


def apply_form_answers(
    drafts: List[ComponentDraft],
    answers: List[dict],
) -> List[str]:
    """
    将表单答案写入 drafts。返回仍缺失的「canonical.field」列表（用于局部追问）。
    """
    still_missing: List[str] = []
    if not answers:
        return still_missing

    for row in answers:
        if not isinstance(row, dict):
            continue
        d = _find_draft_for_answer(drafts, row)
        if not d:
            logger.warning("apply_form_answers: 未匹配组件 %r", row)
            continue

        new_name = row.get("canonical_name")
        if new_name and str(new_name).strip().lower() not in ("null", "none", ""):
            new_name = str(new_name).strip()
            if is_retrievable_name(new_name):
                d.canonical_name = new_name
                d.is_named = True

        lic = validate_license_for_merge(row.get("license_name"))
        if lic and d.license_name == "TBD":
            d.license_name = lic
            d.license_source = "user"

        wtype = normalize_work_type(row.get("work_type"))
        if wtype:
            d.work_type = wtype
        wform = normalize_work_form(row.get("work_form"))
        if wform:
            d.work_form = wform

    for d in drafts:
        if d.registry_hit:
            continue
        for field in get_missing_fields(d):
            still_missing.append(f"{d.canonical_name}.{field}")

    return still_missing


def parse_resume_to_form_answers(resume: Any) -> Optional[List[dict]]:
    """从 API resume（字符串 JSON / dict）解析表单答案。"""
    if resume is None:
        return None
    if isinstance(resume, dict):
        if resume.get("kind") == "clarify_form":
            ans = resume.get("answers")
            return ans if isinstance(ans, list) else None
        if isinstance(resume.get("answers"), list):
            return resume["answers"]
        return None
    if isinstance(resume, str):
        text = resume.strip()
        if text.startswith("{"):
            import json
            try:
                data = json.loads(text)
                return parse_resume_to_form_answers(data)
            except json.JSONDecodeError:
                return None
    return None


def is_clarify_form_resume(resume: Any) -> bool:
    return parse_resume_to_form_answers(resume) is not None
