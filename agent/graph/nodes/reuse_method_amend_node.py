"""
复用方法修正节点
"""
from agent.config import logger
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from agent.models import GraphState
from agent.utils import build_stage_prompt
from .helpers import safe_json_loads, validate_reuse_method_resp, extract_multiple_functions
from .state_helpers import get_known_works, get_reuse_method


def reuse_method_amend_node(state: GraphState, config: RunnableConfig, *, store: BaseStore,llm=None, prompt_template_work=None):
    known_works = get_known_works(state)
    raw_info = state["raw_info"]
    reuse_method = get_reuse_method(state)
    user_prompt = prompt_template_work.template.format(
        description = raw_info,
        works = [i.standard_name for i in known_works],
        reuse_method = reuse_method,
        reuse_code=extract_multiple_functions([i['method'] for i in reuse_method if isinstance(i, dict) and i.get('method')])
    )
    prompt = build_stage_prompt('', user_prompt)
    resp = llm.invoke(prompt)
    result = safe_json_loads(resp.content)
    if not isinstance(result, list):
        logger.warning("[格式错误] reuse_amend LLM 输出无法解析为 JSON 数组")
        result = reuse_method
    print(f'第二次reuse输出：{result}')

    if not validate_reuse_method_resp(result):
        logger.warning("[格式错误] LLM 输出不符合规范")
    else:
        logger.warning("reuse method输出格式符合要求")

    return {
        "raw_info": state['raw_info'],
        "messages": state["messages"],
        "known_works": known_works,
        "unknown_works": state.get("unknown_works") or [],
        "reuse_method": result if isinstance(result, list) else [],
    }
