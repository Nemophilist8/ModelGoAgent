"""
图构建逻辑
"""
from functools import partial

from agent.config import (
    PROMPT_TEMPLATE_TXT_SYS,
    PROMPT_TEMPLATE_TXT_ANA,
    PROMPT_TEMPLATE_TXT_WORK,
    PROMPT_TEMPLATE_TXT_REUSE,
    PROMPT_TEMPLATE_TXT_CODE,
    PROMPT_TEMPLATE_TXT_POLICY,
    PROMPT_TEMPLATE_TXT_REUSE_AMEND,
    PROMPT_TEMPLATE_TXT_WORK_EXTRACT,
    PROMPT_TEMPLATE_TXT_WORK_CLARIFY,
    logger
)
from agent.graph.nodes.input_parser_node import input_parser_node
from agent.graph.nodes.release_policy_node import release_policy_node
from agent.graph.nodes.work_extract_node import work_extract_node
from agent.graph.nodes.work_clarify_node import work_clarify_node
from agent.graph.nodes.work_finalize_node import work_finalize_node
from agent.graph.nodes.reuse_method_node import reuse_method_node
from agent.graph.nodes.reuse_method_amend_node import reuse_method_amend_node
from agent.graph.nodes.generate_code_node import generate_code
from agent.graph.nodes.analysis_node import analysis_node
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, START, END
from agent.models import GraphState


def _route_after_extract(state: GraphState) -> str:
    if state.get("work_resolution_status") == "aborted":
        return END
    return "work_clarify_node"


def _route_after_reuse(state: GraphState) -> str:
    if state.get("work_resolution_status") == "aborted":
        return END
    return "reuse_amend_node"


def _route_after_finalize(state: GraphState) -> str:
    if state.get("work_resolution_status") == "aborted":
        return END
    if state.get("work_resolution_status") == "need_user_input":
        return END
    if state.get("work_resolution_status") == "ready":
        return "reuse_node"
    if state.get("unlicense_confirmed"):
        return "work_finalize_node"
    return END


def create_graph(llm, checkpointer, in_postgres_store=None) -> StateGraph:
    """
    创建和配置 chatbot 的状态图
    """
    try:
        graph_builder = StateGraph(GraphState)

        prompt_template_analysis = PromptTemplate.from_file(PROMPT_TEMPLATE_TXT_ANA, encoding="utf-8")
        prompt_template_work_extract = PromptTemplate.from_file(PROMPT_TEMPLATE_TXT_WORK_EXTRACT, encoding="utf-8")
        prompt_template_work_clarify = PromptTemplate.from_file(PROMPT_TEMPLATE_TXT_WORK_CLARIFY, encoding="utf-8")
        prompt_template_reuse = PromptTemplate.from_file(PROMPT_TEMPLATE_TXT_REUSE, encoding="utf-8")
        prompt_template_reuse_amend = PromptTemplate.from_file(PROMPT_TEMPLATE_TXT_REUSE_AMEND, encoding="utf-8")
        prompt_template_code = PromptTemplate.from_file(PROMPT_TEMPLATE_TXT_CODE, encoding="utf-8")
        prompt_template_policy = PromptTemplate.from_file(PROMPT_TEMPLATE_TXT_POLICY, encoding="utf-8")
        prompt_template_system = PromptTemplate.from_file(PROMPT_TEMPLATE_TXT_SYS, encoding="utf-8")

        graph_builder.add_node('input_parser_node', input_parser_node)
        graph_builder.add_node(
            "release_policy_node",
            partial(release_policy_node, llm=llm, prompt_template_work=prompt_template_policy)
        )
        graph_builder.add_node(
            "work_extract_node",
            partial(work_extract_node, llm=llm, prompt_template_extract=prompt_template_work_extract)
        )
        graph_builder.add_node(
            "work_clarify_node",
            partial(work_clarify_node, llm=llm, prompt_template_clarify=prompt_template_work_clarify),
        )
        graph_builder.add_node("work_finalize_node", work_finalize_node)
        graph_builder.add_node(
            "reuse_node",
            partial(reuse_method_node, llm=llm, prompt_template_work=prompt_template_reuse)
        )
        graph_builder.add_node(
            "reuse_amend_node",
            partial(reuse_method_amend_node, llm=llm, prompt_template_work=prompt_template_reuse_amend)
        )
        graph_builder.add_node(
            "code_node",
            partial(generate_code, llm=llm, prompt_template_work=prompt_template_code)
        )
        graph_builder.add_node(
            "analysis_node",
            partial(
                analysis_node,
                llm=llm,
                prompt_template_system=prompt_template_system,
                prompt_template_analysis=prompt_template_analysis,
            )
        )

        graph_builder.add_edge(START, "input_parser_node")
        graph_builder.add_edge("input_parser_node", "release_policy_node")
        graph_builder.add_edge("release_policy_node", "work_extract_node")
        graph_builder.add_conditional_edges("work_extract_node", _route_after_extract, ["work_clarify_node", END])
        graph_builder.add_edge("work_clarify_node", "work_finalize_node")
        graph_builder.add_conditional_edges(
            "work_finalize_node",
            _route_after_finalize,
            ["reuse_node", "work_finalize_node", END],
        )
        graph_builder.add_conditional_edges(
            "reuse_node",
            _route_after_reuse,
            ["reuse_amend_node", END],
        )
        graph_builder.add_edge('reuse_amend_node', "code_node")
        graph_builder.add_edge('code_node', 'analysis_node')
        graph_builder.add_edge("analysis_node", END)

        return graph_builder.compile(checkpointer=checkpointer, store=in_postgres_store)

    except Exception as e:
        raise RuntimeError(f"创建 graph 失败: {str(e)}")
