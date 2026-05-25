"""
API 路由处理
"""
import json
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager

from agent.config import (
    logger,
    LLM_TYPE,
    LICENSE_LLM_API_KEY,
    LICENSE_LLM_MODEL,
    GITHUB_TOKEN,
)
from scripts.llm_license_helper import set_api_key
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from agent.graph import create_graph
from agent.llms import get_llm
from agent.models import ChatCompletionRequest, ChatCompletionResponse, ChatCompletionResponseChoice, Message
from agent.utils import (
    format_response,
    save_graph_visualization,
    extract_message_content,
    get_final_response_content,
)
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from agent.graph.nodes.clarify_form import parse_resume_to_form_answers

graph = None
connection_pool = None


def _extract_interrupt_payload(result) -> tuple[str | None, str | None, dict | None]:
    """从 invoke/stream 结果中解析 interrupt 载荷。返回 (message, kind, clarify_form)。"""
    interrupts = None
    if isinstance(result, dict) and "__interrupt__" in result:
        interrupts = result["__interrupt__"]
    if not interrupts:
        return None, None, None
    first = interrupts[0] if isinstance(interrupts, (list, tuple)) else interrupts
    value = getattr(first, "value", first)
    if isinstance(value, dict):
        return value.get("message"), value.get("kind"), value.get("clarify_form")
    if isinstance(value, str):
        return value, None, None
    return str(value), None, None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph, connection_pool
    try:
        logger.info("正在初始化模型、定义 Graph...")

        _scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
        if _scripts_dir not in sys.path:
            sys.path.insert(0, _scripts_dir)
        if LICENSE_LLM_API_KEY:
            try:
                set_api_key(
                    api_key=LICENSE_LLM_API_KEY,
                    model=LICENSE_LLM_MODEL,
                    github_token=GITHUB_TOKEN or None,
                )
                logger.info("许可证分析 LLM 已配置: model=%s", LICENSE_LLM_MODEL)
            except Exception as e:
                logger.warning("配置许可证分析 LLM 失败: %s", e)

        llm, _embedding = get_llm(LLM_TYPE)
        checkpointer = MemorySaver()
        graph = create_graph(llm, checkpointer)
        save_graph_visualization(graph)
        logger.info("初始化完成")
    except Exception as e:
        logger.error(f"初始化过程中出错: {str(e)}")
        raise

    yield

    logger.info("正在关闭...")
    if connection_pool:
        connection_pool.close()


app = FastAPI(lifespan=lifespan)


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    if not graph:
        raise HTTPException(status_code=500, detail="服务未初始化")

    try:
        logger.info(
            "收到聊天完成请求: conversationId=%s, has_resume=%s",
            request.conversationId,
            request.resume is not None,
        )

        query_prompt = request.messages[-1].content if request.messages else ""
        conversation_id = request.conversationId or str(uuid.uuid4())
        user_id = request.userId or "default_user"
        config = {"configurable": {"thread_id": f"{user_id}@@{conversation_id}", "user_id": user_id}}

        if request.resume is not None:
            form_answers = parse_resume_to_form_answers(request.resume)
            if form_answers is not None:
                resume_payload = {"kind": "clarify_form", "answers": form_answers}
                invoke_input = Command(
                    resume=resume_payload,
                    update={
                        "clarify_form_answers": form_answers,
                        "clarify_user_reply": None,
                        "messages": [
                            {
                                "role": "user",
                                "content": json.dumps(resume_payload, ensure_ascii=False),
                            }
                        ],
                    },
                )
            else:
                reply_text = (
                    request.resume
                    if isinstance(request.resume, str) and request.resume != ""
                    else query_prompt
                )
                invoke_input = Command(
                    resume=reply_text,
                    update={
                        "clarify_user_reply": reply_text,
                        "clarify_form_answers": None,
                        "messages": [{"role": "user", "content": str(reply_text)}],
                    },
                )
        else:
            invoke_input = {
                "messages": [{"role": m.role, "content": m.content} for m in request.messages],
                "raw_info": query_prompt,
            }

        if request.stream:
            async def generate_stream():
                chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
                interrupted = False
                interrupt_msg = ""
                try:
                    for event in graph.stream(invoke_input, config, stream_mode="updates"):
                        if "__interrupt__" in event:
                            interrupted = True
                            for node_data in event.values():
                                if isinstance(node_data, tuple):
                                    for item in node_data:
                                        msg, _, _ = _extract_interrupt_payload({"__interrupt__": (item,)})
                                        if msg:
                                            interrupt_msg = msg
                        for node_name, node_val in event.items():
                            if node_name == "__interrupt__":
                                continue
                            if isinstance(node_val, dict):
                                if node_val.get("analysis_report"):
                                    content = node_val["analysis_report"]
                                elif node_val.get("messages"):
                                    last = node_val["messages"][-1]
                                    content = extract_message_content(last)
                                else:
                                    content = ""
                                if content:
                                    yield (
                                        f"data: {json.dumps({'id': chunk_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'choices': [{'index': 0, 'delta': {'content': content}, 'finish_reason': None}]})}\n\n"
                                    )
                except Exception as e:
                    logger.error(f"流式处理错误: {e}")
                if interrupted and interrupt_msg:
                    yield (
                        f"data: {json.dumps({'id': chunk_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'choices': [{'index': 0, 'delta': {'content': interrupt_msg}, 'finish_reason': 'need_user_input'}], 'conversationId': conversation_id})}\n\n"
                    )
                yield (
                    f"data: {json.dumps({'id': chunk_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop' if not interrupted else 'need_user_input'}]})}\n\n"
                )

            return StreamingResponse(generate_stream(), media_type="text/event-stream")

        result = graph.invoke(invoke_input, config)
        interrupt_msg, pending_kind, clarify_form = _extract_interrupt_payload(result)
        if not clarify_form and isinstance(result, dict):
            clarify_form = result.get("clarify_form")
        if interrupt_msg:
            return JSONResponse(
                content=ChatCompletionResponse(
                    choices=[
                        ChatCompletionResponseChoice(
                            index=0,
                            message=Message(role="assistant", content=interrupt_msg),
                            finish_reason="need_user_input",
                        )
                    ],
                    conversationId=conversation_id,
                    pending_kind=pending_kind,
                    clarify_form=clarify_form,
                ).model_dump()
            )

        content = get_final_response_content(result)
        if not content:
            logger.warning(
                "最终响应正文为空: analysis_report=%s, messages_count=%s",
                bool(isinstance(result, dict) and result.get("analysis_report")),
                len(result.get("messages") or []) if isinstance(result, dict) else 0,
            )

        formatted_response = format_response(content) if content else ""

        return JSONResponse(
            content=ChatCompletionResponse(
                choices=[
                    ChatCompletionResponseChoice(
                        index=0,
                        message=Message(role="assistant", content=formatted_response),
                        finish_reason="stop",
                    )
                ],
                conversationId=conversation_id,
            ).model_dump()
        )

    except Exception as e:
        logger.exception("处理聊天完成时出错")
        raise HTTPException(status_code=500, detail=str(e))
