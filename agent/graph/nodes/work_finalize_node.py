"""
组件许可确认、动态 code 生成、合并为 known_works
"""
from agent.models import ComponentDraft, GraphState, LICENSE_UNKNOWN_TRIGGER
from agent.utils import build_stage_prompt
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from langgraph.types import interrupt

from .work_resolver_helpers import (
    build_work_code,
    finalize_works,
    merge_clarification_reply,
    named_unknown_notice,
    parse_user_confirm,
    unlicense_assumption_note,
)


def work_finalize_node(
    state: GraphState,
    config: RunnableConfig,
    *,
    store: BaseStore,
):
    if state.get("work_resolution_status") == "aborted":
        return {}

    draft_dicts = state.get("component_drafts") or []
    if not draft_dicts:
        return {
            "work_resolution_status": "aborted",
            "messages": [{"role": "assistant", "content": "内部错误：缺少组件草稿，请重试。"}],
            "known_works": [],
        }

    drafts = [ComponentDraft.from_dict(d) for d in draft_dicts]
    user_notices: list[str] = list(state.get("user_notices") or [])
    assumption_notes: list[str] = list(state.get("assumption_notes") or [])

    # 兜底：若 clarify 节点未成功合并续答，在此再尝试一次
    clarify_reply = (state.get("clarify_user_reply") or "").strip()
    if clarify_reply:
        merge_clarification_reply(drafts, clarify_reply)

    # 许可：有名且仍缺失 → Unknow（用户已明确提供的许可不再覆盖）
    for d in drafts:
        if d.registry_hit or d.license_name != "TBD":
            continue
        if d.license_source == "user":
            continue
        if d.is_named:
            d.license_name = LICENSE_UNKNOWN_TRIGGER
            d.license_source = "unknown_lookup"
            user_notices.append(named_unknown_notice(d.canonical_name))

    # 无名 + 许可缺失 → 一次性确认 Unlicense
    unnamed_pending = [
        d for d in drafts
        if not d.registry_hit and d.license_name == "TBD" and not d.is_named and not d.user_confirmed_unlicense
    ]
    if unnamed_pending and not state.get("unlicense_confirmed"):
        lines = [
            "以下组件无法确认许可信息：",
            *[f"- 「{d.mention}」（{d.canonical_name}）" for d in unnamed_pending],
            "",
            "是否继续分析？若继续，将按 **Unlicense** 作为许可假设参与推理，"
            "**分析结果仅供参考**，报告中将注明该假设。",
            "请回复「继续」或「取消」。",
        ]
        msg = "\n".join(lines)
        reply = interrupt({"kind": "confirm_unlicense", "message": msg})
        confirmed = parse_user_confirm(str(reply) if reply is not None else "")
        if confirmed is False:
            return {
                "work_resolution_status": "aborted",
                "component_drafts": [x.to_dict() for x in drafts],
                "user_notices": user_notices,
                "messages": [{
                    "role": "assistant",
                    "content": "已根据您的选择中止分析。请补充组件名称或许可信息后再试。",
                }],
                "known_works": [],
            }
        if confirmed is True:
            for d in unnamed_pending:
                d.license_name = "Unlicense"
                d.license_assumed = True
                d.user_confirmed_unlicense = True
                d.license_source = "assumed"
                assumption_notes.append(unlicense_assumption_note(d.canonical_name))
                user_notices.append(
                    f"组件「{d.mention}」许可信息缺失；已按您的确认使用 Unlicense 假设，分析结果仅供参考。"
                )
            return {
                "component_drafts": [d.to_dict() for d in drafts],
                "unlicense_confirmed": True,
                "user_notices": user_notices,
                "assumption_notes": assumption_notes,
            }
        return {
            "work_resolution_status": "need_user_input",
            "pending_prompt": msg,
            "pending_prompt_kind": "confirm_unlicense",
            "component_drafts": [x.to_dict() for x in drafts],
            "user_notices": user_notices,
            "messages": [{"role": "assistant", "content": msg}],
        }

    for d in drafts:
        if not d.code:
            d.code = build_work_code(d)

    known_works = finalize_works(drafts)
    names = [w.standard_name for w in known_works]
    summary = f"已识别 {len(known_works)} 个组件：{', '.join(names)}"
    if user_notices:
        summary += "\n\n" + "\n".join(user_notices)

    return {
        # 同时保留可序列化的 drafts，避免 checkpoint 丢失 dataclass 列表
        "known_works": known_works,
        "unknown_works": [],
        "component_drafts": [d.to_dict() for d in drafts],
        "work_resolution_status": "ready",
        "user_notices": user_notices,
        "assumption_notes": assumption_notes,
        "pending_prompt": None,
        "pending_prompt_kind": None,
        "messages": [{"role": "assistant", "content": summary}],
    }
