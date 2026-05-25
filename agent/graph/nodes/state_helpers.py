"""
GraphState 读取辅助（防御 None、从 component_drafts 恢复 Work）
"""
from agent.models import ComponentDraft, Work
from .work_resolver_helpers import finalize_works


def last_user_message_text(state) -> str:
    """从 messages 中取最近一条用户文本（用于 interrupt 续答兜底）。"""
    for m in reversed(state.get("messages") or []):
        if isinstance(m, dict):
            if m.get("role") == "user" and m.get("content"):
                return str(m["content"]).strip()
        else:
            role = getattr(m, "type", None) or getattr(m, "role", None)
            if role in ("human", "user"):
                content = getattr(m, "content", "")
                if content:
                    return str(content).strip()
    return ""


def get_known_works(state) -> list[Work]:
    works = state.get("known_works")
    if works:
        return works
    drafts = state.get("component_drafts") or []
    if drafts:
        return finalize_works([ComponentDraft.from_dict(d) for d in drafts])
    return []


def get_reuse_method(state) -> list:
    rm = state.get("reuse_method")
    return rm if isinstance(rm, list) else []


def get_open_policy(state) -> str:
    return state.get("open_policy") or "sell"


def get_open_type(state) -> str:
    return state.get("open_type") or "raw"
