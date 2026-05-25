"""
可交互的多轮测试客户端：支持 clarify_form 结构化表单 + 自由文本续答。

用法：
  python agent/test/test_workflow_interactive.py
  python agent/test/test_workflow_interactive.py --case multi
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid

import requests

DEFAULT_API_URL = "http://127.0.0.1:8012/v1/chat/completions"

CASE5_INPUT = """
将stocksnap、midjourney、thingverse三个数据集进行融合，记作数据集A。
将ccmixter输入由whisper、baize、stable diffusion、i2vgen-xl几个模型依次组成的生成链得到输出，前一个模型的输出作为后一个模型的输入，记作数据集B。
将数据集B与vimeo融合得到数据集C。
将数据集A与数据集C组合后销售。请问违反了什么许可证问题？
""".strip()

CASE_FAKE_WORK = "将 fake_work3 和 baize 打包出售，请问违反了什么许可证问题？"

CASE_MULTI = "把light模型和dark模型打包出售"


def read_multiline_prompt(label: str) -> str:
    print(label)
    print("（输入空行结束；仅输入 quit 退出）")
    lines = []
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            print()
            return ""
        if line.strip().lower() == "quit":
            return "quit"
        if line.strip() == "" and lines:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def call_api(
    url: str,
    user_content: str,
    *,
    user_id: str,
    conversation_id: str,
    resume=None,
    timeout: int = 600,
) -> dict:
    payload = {
        "messages": [{"role": "user", "content": user_content}],
        "stream": False,
        "userId": user_id,
        "conversationId": conversation_id,
    }
    if resume is not None:
        payload["resume"] = resume

    resp = requests.post(url, json=payload, timeout=timeout)
    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise RuntimeError(f"HTTP {resp.status_code}: {detail}")

    return resp.json()


def prompt_clarify_form(clarify_form: dict) -> dict:
    """CLI 逐项填写 clarify_form，返回 resume 载荷。"""
    fields_meta = clarify_form.get("fields") or {}
    answers = []

    print("\n【结构化表单】请按组件填写（直接回车可跳过非必填项）")
    for comp in clarify_form.get("components") or []:
        mention = comp.get("mention", "")
        canonical = comp.get("canonical_name", "")
        print(f"\n--- 组件: {mention} ({canonical}) ---")
        row = {"canonical_name": canonical, "mention": mention}

        for field_key in comp.get("missing") or []:
            meta = fields_meta.get(field_key, {})
            label = meta.get("label", field_key)
            hint = meta.get("hint") or meta.get("enum") or ""
            prompt = f"  {label}"
            if hint:
                prompt += f" ({hint})"
            prompt += "> "
            val = input(prompt).strip()
            if val:
                row[field_key] = val

        answers.append(row)

    return {"kind": "clarify_form", "answers": answers}


def print_assistant(data: dict) -> tuple[str, dict | None]:
    choice = data.get("choices", [{}])[0]
    finish = choice.get("finish_reason", "stop")
    content = choice.get("message", {}).get("content", "")
    pending_kind = data.get("pending_kind")
    clarify_form = data.get("clarify_form")

    print("\n" + "=" * 60)
    print("【助手】")
    if pending_kind:
        print(f"（待处理类型: {pending_kind}）")
    print(content or "（无正文）")
    if clarify_form:
        print("\n【澄清表单 clarify_form】")
        print(json.dumps(clarify_form, ensure_ascii=False, indent=2))
        print("（CLI 将自动进入逐项填写；也可自行构造 resume JSON）")
    print("=" * 60)
    print(f"finish_reason: {finish}")
    if data.get("conversationId"):
        print(f"conversationId: {data['conversationId']}")
    return finish, clarify_form


def run_session(
    url: str,
    initial_query: str,
    user_id: str,
    conversation_id: str | None,
    *,
    prefer_form: bool = True,
) -> None:
    conversation_id = conversation_id or str(uuid.uuid4())
    print(f"\n会话 ID: {conversation_id}")
    print(f"用户 ID: {user_id}")
    print("\n====== 首轮请求 ======")
    print(initial_query[:500] + ("..." if len(initial_query) > 500 else ""))

    data = call_api(url, initial_query, user_id=user_id, conversation_id=conversation_id)
    finish, clarify_form = print_assistant(data)

    round_no = 1
    while finish == "need_user_input":
        round_no += 1
        print(f"\n------ 第 {round_no} 轮续答 ------")

        resume_payload = None
        if prefer_form and clarify_form and clarify_form.get("components"):
            use_form = input("使用结构化表单填写? [Y/n] > ").strip().lower()
            if use_form in ("", "y", "yes"):
                resume_payload = prompt_clarify_form(clarify_form)
            else:
                reply = input("请输入自由文本回复 > ").strip()
                if reply.lower() in ("quit", "exit", "q"):
                    print("用户退出。")
                    return
                resume_payload = reply
        else:
            reply = input("请输入回复 > ").strip()
            if reply.lower() in ("quit", "exit", "q"):
                print("用户退出。")
                return
            if reply.startswith("{"):
                try:
                    resume_payload = json.loads(reply)
                except json.JSONDecodeError:
                    resume_payload = reply
            else:
                resume_payload = reply

        print("\n====== 续跑请求 (resume) ======")
        display = (
            json.dumps(resume_payload, ensure_ascii=False)
            if isinstance(resume_payload, dict)
            else resume_payload
        )
        print(display[:300] + ("..." if len(display) > 300 else ""))

        data = call_api(
            url,
            display if isinstance(display, str) else "clarify_form_submit",
            user_id=user_id,
            conversation_id=conversation_id,
            resume=resume_payload,
        )
        finish, clarify_form = print_assistant(data)

    if finish == "stop":
        print("\n====== 分析完成 ======")
    else:
        print(f"\n====== 结束（finish_reason={finish}）======")


def main() -> int:
    parser = argparse.ArgumentParser(description="ModelGo Agent 可交互多轮测试")
    parser.add_argument("--url", default=DEFAULT_API_URL)
    parser.add_argument("--user-id", default="interactive_test_user")
    parser.add_argument("--conversation-id", default=None)
    parser.add_argument(
        "--case",
        choices=("5", "fake", "multi", "custom"),
        default="custom",
    )
    parser.add_argument(
        "--no-form",
        action="store_true",
        help="禁用结构化表单，仅自由文本",
    )
    args = parser.parse_args()

    if args.case == "5":
        initial = CASE5_INPUT
    elif args.case == "fake":
        initial = CASE_FAKE_WORK
    elif args.case == "multi":
        initial = CASE_MULTI
    else:
        initial = read_multiline_prompt("请输入场景描述：")
        if initial == "quit" or not initial:
            return 0

    try:
        run_session(
            args.url,
            initial,
            args.user_id,
            args.conversation_id,
            prefer_form=not args.no_form,
        )
    except requests.ConnectionError:
        print(f"无法连接 {args.url}，请先运行: python agent/main.py", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
