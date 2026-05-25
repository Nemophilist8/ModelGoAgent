"""
数据模型定义
"""
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Optional, TypedDict, Dict, Annotated, Any, Literal

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

# 与 license_parser.register_license 中未知许可查找触发一致
LICENSE_UNKNOWN_TRIGGER = "Unknow"


# 定义消息类，用于封装API接口返回数据
class Message(BaseModel):
    role: str
    content: str


@dataclass
class Work:
    name: str
    standard_name: str
    code: str = None
    license_assumed: bool = False
    is_auto_named: bool = False
    # 从 code 解析得到，不在构造函数中传入
    component_type: str = field(init=False, default='')
    component_form: str = field(init=False, default='')
    license: str = field(init=False, default='')

    def __post_init__(self):
        if self.code:
            m = re.search(
                r"Work\('([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)'\)",
                self.code
            )
            if m:
                self.component_type = m.group(2)
                self.component_form = m.group(3)
                self.license = m.group(4)


@dataclass
class ComponentDraft:
    """动态 Work 建档过程中的组件草稿"""
    mention: str
    canonical_name: str
    is_named: bool = True
    work_type: str = "model"
    work_form: str = "raw"
    license_name: str = "TBD"
    license_source: str = "inferred"
    license_assumed: bool = False
    user_confirmed_unlicense: bool = False
    code: Optional[str] = None
    registry_hit: bool = False
    needs_clarification: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ComponentDraft":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# 自定义 State 类型，包含解析后的输入字段
class GraphState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    raw_info: str
    structure_input: str
    original_analysis: str
    known_works: List[Work]
    unknown_works: List[Work]
    reuse_method: List[Any]
    open_policy: Literal["sell", "share", "personal"]
    open_type: Literal["raw", "binary", "saas"]
    component_drafts: List[dict]
    work_resolution_status: Literal["in_progress", "need_user_input", "aborted", "ready"]
    pending_prompt: Optional[str]
    pending_prompt_kind: Optional[str]
    user_notices: List[str]
    assumption_notes: List[str]
    clarify_attempted: bool
    clarify_user_reply: Optional[str]
    clarify_form_answers: Optional[List[dict]]
    clarify_form: Optional[dict]
    unlicense_confirmed: bool
    analysis_report: str


# 许可证 Agent 状态
class LicenseAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    component_name: str
    license_name: str
    license_text: str
    license_url: str
    readme_content: str
    identified_license: str
    license_data: Dict
    analysis_result: str
    error_message: str


class ChatCompletionRequest(BaseModel):
    messages: List[Message]
    stream: Optional[bool] = False
    userId: Optional[str] = None
    conversationId: Optional[str] = None
    resume: Optional[Any] = None


class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: Message
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    choices: List[ChatCompletionResponseChoice]
    system_fingerprint: Optional[str] = None
    conversationId: Optional[str] = None
    pending_kind: Optional[str] = None
    clarify_form: Optional[dict] = None
