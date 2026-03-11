"""
许可证识别节点

在用户未提供明确许可证名称时，通过以下渠道依次尝试识别：
1. 直接使用 state.license_name（已知）
2. 使用 LLMLicenseHelper.query_license_by_component_name 通过 GitHub/HF API 查询
3. 使用 LLMLicenseHelper.analyze_license_from_readme 从 README 内容推断
4. 使用 LLMLicenseHelper.analyze_license_text_for_component 从许可证原文推断
"""
from agent.config import logger, LICENSE_LLM_API_KEY, LICENSE_LLM_MODEL, GITHUB_TOKEN
from agent.license import LLMLicenseHelper
from agent.models import LicenseAgentState


def license_identify_node(state: LicenseAgentState) -> dict:
    """识别组件的许可证名称。"""
    if state.get("error_message"):
        return {}

    # 若已明确提供许可证名称，直接使用
    if state.get("license_name"):
        logger.info("license_identify_node: 使用已知许可证名称 %s", state["license_name"])
        return {"identified_license": state["license_name"]}

    component_name = state["component_name"]
    helper = LLMLicenseHelper(
        api_key=LICENSE_LLM_API_KEY,
        model=LICENSE_LLM_MODEL,
        github_token=GITHUB_TOKEN,
    )

    identified = None

    # 优先从 README 推断
    if state.get("readme_content"):
        logger.info("license_identify_node: 从 README 推断许可证...")
        identified = helper.analyze_license_from_readme(component_name, state["readme_content"])

    # 从许可证原文推断
    if not identified and state.get("license_text"):
        logger.info("license_identify_node: 从许可证原文推断...")
        identified = helper.analyze_license_text_for_component(component_name, state["license_text"])

    # 通过组件名查询（GitHub / HuggingFace API）
    if not identified:
        logger.info("license_identify_node: 通过 API 查询组件许可证...")
        identified = helper.query_license_by_component_name(component_name)

    if not identified:
        logger.warning("license_identify_node: 无法识别许可证，将以组件名作为许可证标识继续")
        identified = component_name

    logger.info("license_identify_node: 识别结果 = %s", identified)
    return {"identified_license": identified}
