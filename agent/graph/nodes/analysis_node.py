"""
分析节点
"""
from config import logger
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from models import GraphState
from utils import build_stage_prompt


def analysis_node(state: GraphState, config: RunnableConfig, *, store: BaseStore, llm=None, prompt_template_system=None, prompt_template_analysis=None):
    """
    Stage 2：分析节点
    """
    # structure 节点输出内容
    structured_output = state["messages"][-1].content
    logger.info(f'新作品的结构为：\n{structured_output}')

    # 从 state 获取 original_analysis
    original_analysis = state["original_analysis"]

    # 组合成 analysis 需要的 prompt
    system_prompt = prompt_template_system.template
    user_prompt = prompt_template_analysis.template.format(
        original_analysis=original_analysis,
        structure=structured_output
    )
    prompt = build_stage_prompt(system_prompt, user_prompt)

    resp = llm.invoke(prompt)
    return {"messages": [resp]}
