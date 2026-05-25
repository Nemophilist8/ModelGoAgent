"""
复用方法节点
"""
from agent.config import logger
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from agent.models import GraphState
from agent.utils import build_stage_prompt
from .helpers import safe_json_loads, validate_reuse_method_resp
from .state_helpers import get_known_works


def reuse_method_node(state: GraphState, config: RunnableConfig, *, store: BaseStore,llm=None, prompt_template_work=None):
    known_works = get_known_works(state)
    if not known_works:
        logger.error("reuse_node: known_works 为空，请检查 work_finalize 是否完成")
        return {
            "work_resolution_status": "aborted",
            "messages": [{"role": "assistant", "content": "内部错误：未识别到任何组件，无法分析复用关系。"}],
            "reuse_method": [],
        }
    raw_info = state["raw_info"]
    user_prompt = prompt_template_work.template.format(description = raw_info, works = [i.standard_name for i in known_works])
    prompt = build_stage_prompt('', user_prompt)
    resp = llm.invoke(prompt)
    result = safe_json_loads(resp.content)
    if not isinstance(result, list):
        logger.warning("[格式错误] reuse LLM 输出无法解析为 JSON 数组: %s", resp.content[:500])
        result = []
    print(f'第一次reuse输出：{result}')

    if not validate_reuse_method_resp(result):
        logger.warning("[格式错误] LLM 输出不符合规范")
    else:
        logger.warning("reuse method输出格式符合要求")

    return {
        "raw_info": state['raw_info'],
        "messages": state["messages"],
        "known_works": known_works,
        "unknown_works": state.get("unknown_works") or [],
        "reuse_method": result,
    }
