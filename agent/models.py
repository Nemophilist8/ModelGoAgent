"""
数据模型定义
"""
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional, TypedDict, Dict, Annotated, Any, Literal

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


# 定义消息类，用于封装API接口返回数据
class Message(BaseModel):
    role: str
    content: str

@dataclass
class Work:
    name: str
    standard_name: str
    code: str = None

# 自定义 State 类型，包含解析后的输入字段
class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    raw_info: str
    structure_input: str  # 结构化输入
    original_analysis: str  # 原始分析内容
    known_works: List[Work]
    unknown_works: List[Work]
    reuse_method: List[Any]
    open_policy: Literal["sell", "share", "personal"]
    open_type: Literal["raw", "binary", "saas"]


# 许可证 Agent 状态
class LicenseAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    # --- 输入字段 ---
    component_name: str      # 组件/作品名称（如 "tencent/HunyuanVideo-1.5"）
    license_name: str        # 许可证名称（可选，若已知则跳过识别）
    license_text: str        # 许可证全文（可选）
    license_url: str         # 许可证 URL（可选）
    readme_content: str      # README 内容（可选，用于从 README 推断许可证）
    # --- 中间状态 ---
    identified_license: str  # 识别出的许可证名称
    # --- 输出字段 ---
    license_data: Dict       # 结构化许可证数据（YAML 格式对应的 dict）
    analysis_result: str     # 最终格式化分析文本
    error_message: str       # 错误信息


# 定义ChatCompletionRequest类
class ChatCompletionRequest(BaseModel):
    messages: List[Message]
    stream: Optional[bool] = False
    userId: Optional[str] = None
    conversationId: Optional[str] = None


# 定义ChatCompletionResponseChoice类
class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: Message
    finish_reason: Optional[str] = None


# 定义ChatCompletionResponse类
class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    choices: List[ChatCompletionResponseChoice]
    system_fingerprint: Optional[str] = None

