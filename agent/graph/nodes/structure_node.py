"""
结构化节点
"""
from config import logger
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from models import GraphState
from utils import build_stage_prompt


def structure_node(state: GraphState, config: RunnableConfig, *, store: BaseStore, llm=None, prompt_template_system=None, prompt_template_structure=None):
    logger.info("111111111111111111111")
    structure_input = state["structure_input"]
    logger.info(f"structure_input = {structure_input}")

    system_prompt = prompt_template_system.template
    user_prompt = prompt_template_structure.template.format(new_work=structure_input)

    prompt = build_stage_prompt(system_prompt, user_prompt)

    resp = llm.invoke(prompt)

    # 将 structure 内容保存，供下一个节点使用
    return {
        "messages": [resp],
    }
