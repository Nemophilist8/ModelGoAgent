"""
发布策略节点
"""
import json
from agent.config import logger
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from agent.models import GraphState
from agent.utils import build_stage_prompt


def release_policy_node(state: GraphState, config: RunnableConfig, *, store: BaseStore, llm=None, prompt_template_work=None):
    user_input = state['raw_info']
    prompt = build_stage_prompt('', prompt_template_work.template.format(input=user_input))
    resp = llm.invoke(prompt)
    try:
        result = json.loads(resp.content)
        open_policy = result['open_policy']
        open_type = result['open_type']

        logger.info(f'new work的发布方式为{open_policy}，发布形式为{open_type}')
        return GraphState(
            messages=[{"role": "assistant", "content": f'new work的发布方式为{open_policy}，发布形式为{open_type}'}],
            open_policy=open_policy,
            open_type=open_type
        )
    except Exception as e:
        logger.error("release_policy 解析失败，使用默认值 sell/raw: %s", e)
        return {
            "messages": [{"role": "assistant", "content": "new work的发布方式为sell，发布形式为raw（默认值）"}],
            "open_policy": "sell",
            "open_type": "raw",
        }
