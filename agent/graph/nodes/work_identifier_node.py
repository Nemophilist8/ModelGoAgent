"""
Work 识别节点
"""
import json
from agent.config import logger
from agent.knowledge import KNOWN_WORK_REGISTRY, registered_work
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from agent.models import GraphState, Work
from agent.utils import build_stage_prompt


def work_identifier_node(state: GraphState, config: RunnableConfig, *, store: BaseStore, llm=None, prompt_template_work=None):
    """
    Stage 0.5：Work 识别节点
    """
    # 获取用户输入
    user_input = state['raw_info']
    prompt = build_stage_prompt('', prompt_template_work.template.format(description=user_input, known_works=str(list(registered_work.keys()))))
    resp = llm.invoke(prompt)

    identified_works_list = []
    unknown_works_list = []

    # 解析 LLM 返回的结果
    try:
        result = json.loads(resp.content)

        for item in result:
            k = list(item.keys())[0]
            v = item[k]
            registry = KNOWN_WORK_REGISTRY
            if v in registry.keys():
                identified_works_list.append(Work(k, v, registry[v]))
            else:
                unknown_works_list.append(Work(k, v))

        logger.info(f"识别出的已知 Work:{identified_works_list}")
        logger.info(f"未知对象列表: {unknown_works_list}")

        # 已由 work_extract / work_finalize 处理动态 Work；此节点仅作兼容保留
        for uw in unknown_works_list:
            identified_works_list.append(uw)
        unknown_works_list = []

        # 返回结果并添加到消息中
        result_message = f"已识别的 Work 对象:\n{[i.name for i in identified_works_list]}\n\n未知对象列表: {unknown_works_list}"

    except:
        logger.warning(f"无法解析 LLM 返回的 JSON: {resp.content}")

    return {
        "raw_info": state['raw_info'],
        "messages": [{"role": "assistant", "content": result_message}],
        "known_works": identified_works_list,
        "unknown_works": unknown_works_list
    }
