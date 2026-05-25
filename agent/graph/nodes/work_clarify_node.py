"""
澄清节点：clarify_form 结构化表单 + 自由文本；多组件规则不广播许可，LLM 兜底。
"""
from agent.config import logger
from agent.models import ComponentDraft, GraphState
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from langgraph.types import interrupt

from .clarify_form import (
    apply_form_answers,
    build_clarify_form,
    build_clarify_form_message,
    parse_resume_to_form_answers,
)
from .state_helpers import last_user_message_text
from .work_resolver_helpers import (
    merge_clarification_reply,
    normalize_interrupt_reply,
)


def work_clarify_node(
    state: GraphState,
    config: RunnableConfig,
    *,
    store: BaseStore,
    llm=None,
    prompt_template_clarify=None,
):
    if state.get("work_resolution_status") == "aborted":
        return {}

    draft_dicts = state.get("component_drafts") or []
    if not draft_dicts:
        return {}

    drafts = [ComponentDraft.from_dict(d) for d in draft_dicts]

    def _needs_clarify() -> list[ComponentDraft]:
        return [
            d for d in drafts
            if not d.registry_hit
            and (d.canonical_name.startswith("inferred_") or d.license_name == "TBD")
        ]

    def _finish_or_reinterrupt() -> dict:
        need = _needs_clarify()
        if not need:
            return {
                "component_drafts": [d.to_dict() for d in drafts],
                "clarify_attempted": True,
                "clarify_user_reply": None,
                "clarify_form_answers": None,
                "work_resolution_status": "in_progress",
            }
        form = build_clarify_form(need)
        msg = build_clarify_form_message(form, partial=True)
        interrupt({
            "kind": "clarify_attributes",
            "message": msg,
            "clarify_form": form,
            "partial": True,
        })
        return {
            "component_drafts": [d.to_dict() for d in drafts],
            "clarify_attempted": True,
            "clarify_form": form,
            "pending_prompt": msg,
            "pending_prompt_kind": "clarify_attributes",
            "work_resolution_status": "need_user_input",
            "clarify_user_reply": None,
            "clarify_form_answers": None,
        }

    need = _needs_clarify()
    if not need:
        return {"clarify_attempted": True}

    partial = bool(state.get("clarify_attempted"))
    form = build_clarify_form(need)
    msg = build_clarify_form_message(form, partial=partial)
    reply = interrupt({
        "kind": "clarify_attributes",
        "message": msg,
        "clarify_form": form,
        "partial": partial,
    })

    answers = parse_resume_to_form_answers(reply)
    if not answers:
        answers = state.get("clarify_form_answers")
    if answers:
        still = apply_form_answers(drafts, answers)
        logger.info(
            "work_clarify: 表单合并 drafts=%s, still_missing=%s",
            [(d.canonical_name, d.license_name) for d in drafts],
            still,
        )
    else:
        merged_text = (
            normalize_interrupt_reply(reply)
            or (state.get("clarify_user_reply") or "").strip()
            or last_user_message_text(state)
        )
        if merged_text:
            merge_clarification_reply(
                drafts,
                merged_text,
                llm=llm,
                prompt_template_clarify=prompt_template_clarify,
            )
            logger.info(
                "work_clarify: 文本合并 drafts=%s",
                [(d.canonical_name, d.license_name) for d in drafts],
            )

    return _finish_or_reinterrupt()
