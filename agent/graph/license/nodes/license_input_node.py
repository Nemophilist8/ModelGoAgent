"""
许可证输入解析节点

负责校验和规范化用户输入：
- component_name：组件/作品名称（必填）
- license_name：许可证名称（可选）
- license_text：许可证全文（可选）
- license_url：许可证 URL（可选）
- readme_content：README 内容（可选）
"""
from agent.config import logger
from agent.models import LicenseAgentState


def license_input_node(state: LicenseAgentState) -> dict:
    """
    解析并验证许可证分析请求的输入。
    若 messages 中包含用户消息，则将其内容作为 component_name 的备用来源。
    """
    component_name = state.get("component_name", "").strip()

    # 若未直接提供 component_name，尝试从最后一条用户消息中提取
    if not component_name:
        for msg in reversed(state.get("messages", [])):
            content = getattr(msg, "content", None) or (
                msg.get("content") if isinstance(msg, dict) else None
            )
            role = getattr(msg, "type", None) or (
                msg.get("role") if isinstance(msg, dict) else None
            )
            if content and role in ("human", "user"):
                component_name = content.strip()
                break

    if not component_name:
        logger.warning("license_input_node: 未提供 component_name")
        return {"error_message": "请提供组件名称（component_name）或在消息中描述要分析的许可证/组件。"}

    logger.info("license_input_node: component_name=%s, license_name=%s",
                component_name, state.get("license_name", "（未指定）"))

    return {
        "component_name": component_name,
        "error_message": "",
    }
