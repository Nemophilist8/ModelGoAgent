"""
许可证输出格式化节点

将结构化的 license_data（dict）格式化为可读文本，
并生成供用户阅读的最终分析报告。
"""
import yaml

from agent.config import logger
from agent.models import LicenseAgentState


def license_output_node(state: LicenseAgentState) -> dict:
    """将 license_data 格式化为人类可读的分析报告。"""
    if state.get("error_message"):
        result = f"[许可证分析失败]\n{state['error_message']}"
        return {"analysis_result": result, "messages": [{"role": "assistant", "content": result}]}

    license_data = state.get("license_data")
    if not license_data:
        result = "[许可证分析未产生结果，请检查输入或 API Key 配置。]"
        return {"analysis_result": result, "messages": [{"role": "assistant", "content": result}]}

    lines = []
    lines.append("=" * 60)
    lines.append(f"  许可证分析报告：{license_data.get('short_id', state.get('identified_license', ''))}")
    lines.append("=" * 60)

    lines.append(f"\n【基本信息】")
    lines.append(f"  全称：{license_data.get('full_name', 'N/A')}")
    lines.append(f"  标识：{license_data.get('short_id', 'N/A')}")
    lines.append(f"  版本：{license_data.get('version', 'N/A')}")
    lines.append(f"  URL ：{license_data.get('url', 'N/A')}")

    categories = license_data.get("categories", [])
    if categories:
        lines.append(f"\n【许可证类别】")
        lines.append(f"  {', '.join(categories)}")

    rights = license_data.get("rights", [])
    if rights:
        lines.append(f"\n【授权权利】")
        lines.append(f"  {', '.join(rights)}")

    reserved = license_data.get("reserved_rights", [])
    if reserved:
        lines.append(f"\n【保留权利】")
        lines.append(f"  {', '.join(reserved)}")

    redistribute = license_data.get("redistribute", [])
    if redistribute:
        lines.append(f"\n【再分发条件】")
        lines.append(f"  {', '.join(redistribute)}")

    terms = license_data.get("terms", [])
    if terms:
        lines.append(f"\n【使用条款（Terms）】")
        for i, term in enumerate(terms, 1):
            usages = ", ".join(term.get("usages", []))
            forms = ", ".join(term.get("forms", []))
            result_val = term.get("result", "N/A")
            restrictions = ", ".join(term.get("restrictions", []))
            lines.append(f"  [{i}] 使用方式: {usages} | 形式: {forms} | 结果: {result_val}"
                         + (f" | 限制: {restrictions}" if restrictions else ""))

    lines.append("\n【原始结构化数据（YAML）】")
    lines.append(yaml.dump(license_data, allow_unicode=True, sort_keys=False))

    result = "\n".join(lines)
    logger.info("license_output_node: 报告生成完毕，长度 %d 字符", len(result))
    return {"analysis_result": result, "messages": [{"role": "assistant", "content": result}]}
