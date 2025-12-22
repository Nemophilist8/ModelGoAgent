"""
代码生成节点
"""
from config import logger, SEPARATOR
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from models import GraphState
from utils import build_stage_prompt
from e2b_code_interpreter import Sandbox
from .helpers import extract_multiple_functions, extract_python_code


def generate_code(state: GraphState, config: RunnableConfig, *, store: BaseStore,llm=None, prompt_template_work=None):
    known_works = state["known_works"]
    raw_info = state["raw_info"]
    reuse_method = state["reuse_method"]
    open_policy = state["open_policy"]
    open_type = state["open_type"]

    logger.info(reuse_method)
    reuse_method_name = [i['method'] for i in reuse_method]

    user_prompt = prompt_template_work.template.format(
        description = raw_info,
        known_work_dict = known_works,
        reuse_method= reuse_method,
        reuse_code=extract_multiple_functions(reuse_method_name))
    prompt = build_stage_prompt('', user_prompt)
    resp = llm.invoke(prompt)
    context = resp.content
    code_list = ['from main_case import *']
    for work in known_works:
        code_list.append(work.code)

    code_list.append("works = [ob for ob in gc.get_objects() if isinstance(ob, Work)]")
    code_list.append("par.register_license(works)")

    code_list.append(extract_python_code(context))
    # code_list.append(context.replace('```', ''))

    code_list.append(f"new_work.form = '{open_type}'")

    code_list.append(f"par.analysis(new_work, open_policy='{open_policy}')")
    code_list.append("new_work.summary()")
    code_list.append(f"print('\\n{SEPARATOR}\\n')")
    code_list.append("print(new_work)")

    code = "\n".join(code_list)
    print(f'生成的代码为\n{code}')

    # 在 E2B 沙盒中运行代码
    try:
        with Sandbox.create('model-go') as sbx:
            sbx.files.write('/home/user/scripts/tmp.py', code)
            result = sbx.commands.run(
                "cd /home/user/scripts && python tmp.py"
            )
            stdout = result.stdout

        parts = stdout.split(SEPARATOR)

        original_analysis = parts[0]
        structure_input = parts[1]

    except Exception as e:
        logger.error(f'E2B 沙盒执行失败: {e}')

    return GraphState(
        messages = state["messages"] + [resp],
        original_analysis = original_analysis,
        structure_input = structure_input,
    )
