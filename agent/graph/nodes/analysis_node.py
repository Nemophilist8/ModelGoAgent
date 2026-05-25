"""
分析节点
"""
from agent.config import logger
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from agent.models import GraphState
from agent.utils import build_stage_prompt, normalize_message_content
from .helpers import build_license_clauses_text


def analysis_node(state: GraphState, config: RunnableConfig, *, store: BaseStore, llm=None, prompt_template_system=None, prompt_template_analysis=None):
    """
    Stage 2：分析节点
    """

    original_analysis = state["original_analysis"]
    structure_input = state["structure_input"]
    known_works = state.get("known_works", [])

    license_clauses = build_license_clauses_text(known_works)

    notices = state.get("user_notices") or []
    assumptions = state.get("assumption_notes") or []
    preamble_parts = []
    if notices:
        preamble_parts.append("### 系统提示（请向用户说明）\n" + "\n".join(f"- {n}" for n in notices))
    if assumptions:
        preamble_parts.append(
            "### 许可假设（必须在报告开头单独成节说明，并强调仅供参考）\n"
            + "\n".join(f"- {a}" for a in assumptions)
        )
    preamble = "\n\n".join(preamble_parts)

    system_prompt = prompt_template_system.template
    if preamble:
        system_prompt = system_prompt + "\n\n" + preamble

    user_prompt = prompt_template_analysis.template.format(
        original_analysis=original_analysis,
        structure=structure_input,
        license_clauses=license_clauses,
    )
    prompt = build_stage_prompt(system_prompt, user_prompt)

    resp = llm.invoke(prompt)
    report_text = normalize_message_content(resp.content)
    return {
        "messages": [resp],
        "analysis_report": report_text.strip(),
    }
