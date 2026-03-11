"""
许可证分析节点

调用 LLMLicenseHelper.get_license_data() 执行完整的两阶段审计分析流程：
  1. 获取许可证原文
  2. 生成基础元数据（含阶段一审计与自动修复）
  3. 生成 terms/ModelGo 映射（含阶段二审计与自动修复）
  4. 返回最终结构化 license_data
"""
from agent.config import logger, LICENSE_LLM_API_KEY, LICENSE_LLM_MODEL, GITHUB_TOKEN, HUGGINGFACE_TOKEN
from agent.license import LLMLicenseHelper
from agent.models import LicenseAgentState


def license_analyze_node(state: LicenseAgentState) -> dict:
    """对识别到的许可证执行完整结构化分析。"""
    if state.get("error_message"):
        return {}

    license_name = state.get("identified_license") or state.get("license_name", "")
    if not license_name:
        return {"error_message": "许可证识别失败，无法执行分析。"}

    helper = LLMLicenseHelper(
        api_key=LICENSE_LLM_API_KEY,
        model=LICENSE_LLM_MODEL,
        github_token=GITHUB_TOKEN,
    )

    # 若用户已提供许可证原文，预先注入缓存，避免重复网络请求
    if state.get("license_text"):
        helper.license_cache[license_name] = state["license_text"]

    logger.info("license_analyze_node: 开始分析许可证 %s ...", license_name)
    try:
        license_data = helper.get_license_data(license_name)
    except Exception as e:
        logger.error("license_analyze_node: 分析失败 - %s", e)
        return {"error_message": f"许可证分析失败：{e}"}

    if not license_data:
        return {"error_message": f"未能生成许可证 '{license_name}' 的结构化数据，请检查 API Key 配置。"}

    logger.info("license_analyze_node: 分析完成，许可证 %s", license_name)
    return {"license_data": license_data}
