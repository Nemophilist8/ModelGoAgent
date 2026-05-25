"""
从用户语言抽取组件草稿（不中断）
"""
from agent.config import logger
from agent.knowledge import KNOWN_WORK_REGISTRY
from agent.models import ComponentDraft, GraphState
from agent.utils import build_stage_prompt
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore

from .helpers import safe_json_loads
from .work_resolver_helpers import apply_type_form_defaults, drafts_from_extract_items


def work_extract_node(
    state: GraphState,
    config: RunnableConfig,
    *,
    store: BaseStore,
    llm=None,
    prompt_template_extract=None,
):
    raw_info = state.get("raw_info") or ""
    user_notices: list[str] = list(state.get("user_notices") or [])

    known_keys = list(KNOWN_WORK_REGISTRY.keys())
    prompt = build_stage_prompt(
        "",
        prompt_template_extract.template.format(description=raw_info, known_works=str(known_keys)),
    )
    resp = llm.invoke(prompt)
    items = safe_json_loads(resp.content)
    if not isinstance(items, list):
        logger.warning("Work 抽取 JSON 非数组: %s", resp.content)
        drafts: list[ComponentDraft] = []
    else:
        drafts = drafts_from_extract_items(items, raw_info)

    if not drafts:
        return {
            "work_resolution_status": "aborted",
            "messages": [{"role": "assistant", "content": "未能从描述中识别任何数据集或模型组件，请补充后重试。"}],
            "known_works": [],
            "component_drafts": [],
        }

    apply_type_form_defaults(drafts, user_notices)

    return {
        "component_drafts": [d.to_dict() for d in drafts],
        "user_notices": user_notices,
        "work_resolution_status": "in_progress",
    }
