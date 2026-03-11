"""
许可证 Agent 子图构建逻辑
"""
from langgraph.graph import StateGraph, START, END

from agent.models import LicenseAgentState
from agent.graph.license.nodes import (
    license_input_node,
    license_identify_node,
    license_analyze_node,
    license_output_node,
)


def create_license_graph(checkpointer=None) -> StateGraph:
    """
    构建许可证智能识别与分析子图。

    工作流：
      START
        → license_input_node     （校验/规范化输入）
        → license_identify_node  （识别许可证名称）
        → license_analyze_node   （两阶段审计完整分析）
        → license_output_node    （格式化输出报告）
      → END

    Args:
        checkpointer: LangGraph checkpointer（与主图共享或独立使用均可）

    Returns:
        已编译的 CompiledStateGraph
    """
    builder = StateGraph(LicenseAgentState)

    builder.add_node("license_input_node", license_input_node)
    builder.add_node("license_identify_node", license_identify_node)
    builder.add_node("license_analyze_node", license_analyze_node)
    builder.add_node("license_output_node", license_output_node)

    builder.add_edge(START, "license_input_node")
    builder.add_edge("license_input_node", "license_identify_node")
    builder.add_edge("license_identify_node", "license_analyze_node")
    builder.add_edge("license_analyze_node", "license_output_node")
    builder.add_edge("license_output_node", END)

    return builder.compile(checkpointer=checkpointer)
