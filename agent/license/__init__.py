"""
许可证分析模块 —— 对 scripts/llm_license_helper.py 的包装，供 agent 内部使用。
"""
import os
import sys

# 将 scripts/ 目录加入模块搜索路径，以解析 LLMLicenseHelper 内部的相对导入
_SCRIPTS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from llm_license_helper import LLMLicenseHelper, set_api_key  # noqa: E402

__all__ = ["LLMLicenseHelper", "set_api_key"]
