"""
work_resolver 节点辅助函数
"""
import re
from typing import Any, List, Optional

from agent.config import logger
from agent.knowledge import KNOWN_WORK_REGISTRY, WORK_ALIASES
from agent.models import ComponentDraft, LICENSE_UNKNOWN_TRIGGER, Work

LICENSE_ALIASES = {
    "mit license": "MIT",
    "mit": "MIT",
    "apache 2.0": "Apache-2.0",
    "apache-2.0": "Apache-2.0",
    "apache-2": "Apache-2.0",
    "apache 2": "Apache-2.0",
    "apache": "Apache-2.0",
    "gpl-3.0": "GPL-3.0",
    "gpl 3": "GPL-3.0",
    "gplv3": "GPL-3.0",
    "cc-by-sa-4.0": "CC-BY-SA-4.0",
    "cc-by-4.0": "CC-BY-4.0",
    "cc-by-nc-4.0": "CC-BY-NC-4.0",
    "cc0": "CC0-1.0",
    "cc0-1.0": "CC0-1.0",
    "unlicense": "Unlicense",
    "bsd-3-clause": "BSD-3-Clause",
}

# 从自然语言续答中抽取 SPDX 风格许可名（不用 \\b 前缀：中文「…许可是CC-BY」前无 ASCII 词界）
_SPDX_LICENSE_RE = re.compile(
    r"(?i)("
    r"CC-BY-SA(?:-[\d.]+)?|CC-BY-NC(?:-[\d.]+)?|CC-BY(?:-[\d.]+)?|"
    r"CC0(?:-[\d.]+)?|GPL(?:-[\d.]+)?|LGPL(?:-[\d.]+)?|"
    r"Apache(?:-[\d.]+)?|BSD(?:-[\w-]+)?|"
    r"(?<![A-Za-z])MIT(?![A-Za-z])|Unlicense"
    r")"
)

_MENTION_SUFFIXES = ("数据集", "数据", "语料", "模型", "软件", "算法")


def normalize_license_name(raw: Optional[str]) -> Optional[str]:
    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip()
    if text.upper() in ("TBD", "UNKNOWN", "UNKNOW", "N/A"):
        return None
    low = text.lower()
    if low in LICENSE_ALIASES:
        return LICENSE_ALIASES[low]
    return text


def extract_all_licenses_from_text(text: str) -> List[str]:
    """从文本中提取全部 SPDX 许可（去重保序）。"""
    if not text:
        return []
    seen: set[str] = set()
    out: List[str] = []
    for m in _SPDX_LICENSE_RE.finditer(str(text)):
        lic = normalize_license_name(m.group(1))
        if lic and lic not in seen:
            seen.add(lic)
            out.append(lic)
    return out


def extract_license_from_text(text: str) -> Optional[str]:
    """从整句续答（含中文说明）中解析许可证，避免把整句写入 Work。"""
    found = extract_all_licenses_from_text(text)
    if found:
        return found[0]
    stripped = str(text).strip()
    if len(stripped) <= 32 and not re.search(r"[\u4e00-\u9fff]{2,}", stripped):
        return normalize_license_name(stripped)
    return None


def _should_use_rule_license_merge(pending_lic: List[ComponentDraft], text: str) -> bool:
    """多组件或多 SPDX 时不做「单许可广播」，交给 LLM / 表单。"""
    if len(pending_lic) > 1:
        return False
    if len(extract_all_licenses_from_text(text)) > 1:
        return False
    return True


def derive_canonical_from_mention(mention: str) -> Optional[str]:
    """用户说了「happy数据集」等但未填 canonical 时，从 mention 推导标准名。"""
    m = (mention or "").strip()
    if not m or m == "未命名组件":
        return None
    for suffix in _MENTION_SUFFIXES:
        if m.endswith(suffix) and len(m) > len(suffix):
            base = m[: -len(suffix)].strip()
            if is_retrievable_name(base):
                return base
    if is_retrievable_name(m):
        return m
    return None


def _draft_matches_reply(draft: ComponentDraft, text: str) -> bool:
    low = (text or "").lower()
    for part in (draft.mention, draft.canonical_name):
        if part and len(part) >= 2 and part.lower() in low:
            return True
    derived = derive_canonical_from_mention(draft.mention)
    if derived and derived.lower() in low:
        return True
    return False


def extract_explicit_name_from_reply(text: str) -> Optional[str]:
    """续答中的正式名称（排除「…的许可是 CC-BY…」类整句）。"""
    text = (text or "").strip()
    if not text or parse_user_confirm(text) is not None:
        return None
    if extract_license_from_text(text) and len(text) > 15:
        return None
    if "/" in text:
        return text.split("\n")[0].strip()[:120]
    if len(text) < 80 and not extract_license_from_text(text):
        line = text.split("\n")[0].strip()
        if line and is_retrievable_name(line):
            return line
    return None


def normalize_work_type(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    t = str(raw).strip().lower()
    if t in ("data", "dataset", "corpus", "语料", "数据集"):
        return "data"
    if t in ("model", "software", "算法", "模型"):
        return "model"
    return None


def normalize_work_form(raw: Optional[str], description: str = "") -> Optional[str]:
    if raw:
        f = str(raw).strip().lower()
        if f in ("raw", "binary", "saas"):
            return f
    desc = (description or "").lower()
    if any(k in desc for k in ("api 服务", "api服务", "saas", "在线服务", "托管服务")):
        return "saas"
    return None


def _normalize_match_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def resolve_registry_key(name: Optional[str]) -> Optional[str]:
    """将用户说法 / LLM 输出映射到 KNOWN_WORK_REGISTRY 的 key。"""
    if not name:
        return None
    raw = str(name).strip()
    if raw in KNOWN_WORK_REGISTRY:
        return raw
    low = raw.lower()
    if low in WORK_ALIASES:
        key = WORK_ALIASES[low]
        if key in KNOWN_WORK_REGISTRY:
            return key
    for reg_name in KNOWN_WORK_REGISTRY:
        if reg_name.lower() == low:
            return reg_name
    norm = _normalize_match_key(raw)
    if not norm:
        return None
    for reg_name in KNOWN_WORK_REGISTRY:
        if _normalize_match_key(reg_name) == norm:
            return reg_name
    for alias, reg_name in WORK_ALIASES.items():
        if _normalize_match_key(alias) == norm and reg_name in KNOWN_WORK_REGISTRY:
            return reg_name
    return None


def resolve_registry_from_mention_and_canonical(
    mention: str, canonical: Optional[str]
) -> Optional[str]:
    """优先 canonical，再尝试 mention（LLM 常把 canonical 留空）。"""
    for candidate in (canonical, mention):
        key = resolve_registry_key(candidate)
        if key:
            return key
    return None


def parse_fields_from_registry_code(code: str) -> dict:
    m = re.search(
        r"Work\('([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)'\)",
        code or "",
    )
    if not m:
        return {}
    return {
        "work_name": m.group(1),
        "work_type": m.group(2),
        "work_form": m.group(3),
        "license_name": m.group(4),
    }


def draft_from_registry(mention: str, reg_key: str) -> ComponentDraft:
    code = KNOWN_WORK_REGISTRY[reg_key]
    fields = parse_fields_from_registry_code(code)
    return ComponentDraft(
        mention=mention,
        canonical_name=fields.get("work_name") or reg_key,
        is_named=True,
        work_type=fields.get("work_type") or "model",
        work_form=fields.get("work_form") or "raw",
        license_name=fields.get("license_name") or "TBD",
        license_source="registry",
        code=code,
        registry_hit=True,
    )


def is_retrievable_name(name: str) -> bool:
    """有名：可检索的官方名 / org/repo 等"""
    if not name or name.startswith("inferred_"):
        return False
    if "/" in name:
        return True
    if len(name) >= 2 and not name.startswith("inferred"):
        return True
    return False


def sanitize_var_name(canonical_name: str) -> str:
    base = re.sub(r"[^0-9a-zA-Z_]+", "_", canonical_name)
    base = re.sub(r"_+", "_", base).strip("_").lower()
    if not base:
        base = "work"
    if base[0].isdigit():
        base = f"w_{base}"
    return base


def build_work_code(draft: ComponentDraft) -> str:
    var = sanitize_var_name(draft.canonical_name)
    return (
        f"{var} = Work('{draft.canonical_name}', "
        f"'{draft.work_type}', '{draft.work_form}', '{draft.license_name}')"
    )


def allocate_auto_name(existing: List[str], work_type: str) -> str:
    prefix = "inferred_data" if work_type == "data" else "inferred_model"
    idx = 1
    while f"{prefix}_{idx}" in existing:
        idx += 1
    return f"{prefix}_{idx}"


def parse_user_confirm(text: str) -> Optional[bool]:
    """解析「继续/取消」类短指令；勿把许可澄清句（如「许可是 CC-BY…」）误判为确认。"""
    if not text:
        return None
    t = str(text).strip().lower()
    if extract_license_from_text(text):
        return None
    if re.search(r"许可证|license|spdx|cc-by|gpl|apache|mit", t, re.I):
        return None
    # 较长中文叙述句视为成分/许可说明，不是按钮式确认
    if len(t) > 12 and re.search(r"[\u4e00-\u9fff]{2,}", t):
        return None

    yes_exact = {
        "继续", "是的", "是", "好", "同意", "确认",
        "yes", "y", "ok", "continue", "true", "1",
    }
    no_exact = {
        "不", "否", "不要", "取消", "停止",
        "no", "n", "cancel", "false", "0", "中止", "退出",
    }
    if t in yes_exact:
        return True
    if t in no_exact:
        return False
    if len(t) <= 12:
        yes_phrases = ("继续", "是的", "同意", "确认")
        no_phrases = ("取消", "不要", "中止", "退出", "停止")
        if any(p in t for p in yes_phrases) and not any(p in t for p in no_phrases):
            return True
        if any(p in t for p in no_phrases):
            return False
    return None


def drafts_from_extract_items(items: list, description: str) -> List[ComponentDraft]:
    drafts: List[ComponentDraft] = []
    used_names: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        mention = str(item.get("mention") or "").strip() or "未命名组件"
        canonical = item.get("canonical_name")
        if canonical is not None and str(canonical).strip().lower() in ("null", "none", ""):
            canonical = None
        canonical = str(canonical).strip() if canonical else None

        is_named = bool(item.get("is_named", bool(canonical)))

        reg_key = resolve_registry_from_mention_and_canonical(mention, canonical)
        if reg_key:
            draft = draft_from_registry(mention, reg_key)
            drafts.append(draft)
            used_names.append(draft.canonical_name)
            continue

        if canonical:
            is_named = is_retrievable_name(canonical)
        else:
            is_named = False

        wtype = normalize_work_type(item.get("user_stated_type")) or "model"
        wform = normalize_work_form(item.get("user_stated_form"), description) or "raw"
        license_name = normalize_license_name(item.get("user_stated_license")) or "TBD"

        if not canonical:
            derived = derive_canonical_from_mention(mention)
            if derived:
                canonical = derived
                is_named = True
            else:
                canonical = allocate_auto_name(used_names, wtype)
                is_named = False

        used_names.append(canonical)
        drafts.append(ComponentDraft(
            mention=mention,
            canonical_name=canonical,
            is_named=is_named,
            work_type=wtype,
            work_form=wform,
            license_name=license_name,
            license_source="user" if license_name != "TBD" else "inferred",
        ))
    return drafts


def apply_type_form_defaults(drafts: List[ComponentDraft], notices: List[str]) -> None:
    for d in drafts:
        if d.registry_hit:
            continue
        if not d.work_type:
            d.work_type = "model"
            notices.append(f"组件「{d.canonical_name}」类型未明确，已默认按 model 处理。")
        if not d.work_form:
            d.work_form = "raw"
            notices.append(f"组件「{d.canonical_name}」发布形式未明确，已默认按 raw 处理。")


def finalize_works(drafts: List[ComponentDraft]) -> List[Work]:
    works: List[Work] = []
    for d in drafts:
        if not d.code:
            d.code = build_work_code(d)
        works.append(Work(
            name=d.mention,
            standard_name=d.canonical_name,
            code=d.code,
            license_assumed=d.license_assumed,
            is_auto_named=not d.is_named or d.canonical_name.startswith("inferred_"),
        ))
    return works


def validate_license_for_merge(raw: Optional[str]) -> Optional[str]:
    """校验许可名：须为 SPDX 风格标识，拒绝中文说明句。"""
    lic = normalize_license_name(raw)
    if not lic:
        return None
    if re.search(r"[\u4e00-\u9fff]", lic) or len(lic) > 64:
        return None
    if _SPDX_LICENSE_RE.search(lic) or lic in set(LICENSE_ALIASES.values()):
        return lic
    logger.warning("validate_license_for_merge: 拒绝无效许可 %r", lic)
    return None


def _format_pending_for_clarify_prompt(drafts: List[ComponentDraft]) -> str:
    lines = []
    for d in drafts:
        if d.registry_hit:
            continue
        missing = []
        if d.canonical_name.startswith("inferred_"):
            missing.append("正式名称")
        if d.license_name == "TBD":
            missing.append("许可证")
        if missing:
            lines.append(
                f"- mention={d.mention!r}, canonical_name={d.canonical_name!r}, "
                f"缺少: {', '.join(missing)}"
            )
    return "\n".join(lines) if lines else "（无）"


def _find_draft_for_patch(drafts: List[ComponentDraft], patch: dict) -> Optional[ComponentDraft]:
    mention = (patch.get("mention") or "").strip()
    canonical = patch.get("canonical_name")
    if canonical is not None and str(canonical).strip().lower() in ("null", "none", ""):
        canonical = None
    else:
        canonical = str(canonical).strip() if canonical else None

    candidates = [d for d in drafts if not d.registry_hit]
    if canonical:
        for d in candidates:
            if d.canonical_name.lower() == canonical.lower():
                return d
    if mention:
        for d in candidates:
            if mention.lower() in (d.mention.lower(), d.canonical_name.lower()):
                return d
            derived = derive_canonical_from_mention(mention)
            if derived and derived.lower() == d.canonical_name.lower():
                return d
    return None


def parse_clarification_reply_with_llm(
    llm: Any,
    prompt_template: Any,
    reply: str,
    drafts: List[ComponentDraft],
) -> List[dict]:
    """正则失败时，用 LLM 从续答中提取结构化补充信息。"""
    pending = [
        d for d in drafts
        if not d.registry_hit
        and (d.canonical_name.startswith("inferred_") or d.license_name == "TBD")
    ]
    if not pending or not llm or not prompt_template:
        return []

    from agent.utils import build_stage_prompt
    from .helpers import safe_json_loads

    user_prompt = prompt_template.template.format(
        pending_components=_format_pending_for_clarify_prompt(drafts),
        user_reply=reply.strip(),
    )
    prompt = build_stage_prompt("", user_prompt)
    try:
        resp = llm.invoke(prompt)
        items = safe_json_loads(resp.content)
    except Exception as e:
        logger.warning("parse_clarification_reply_with_llm 调用失败: %s", e)
        return []

    if not isinstance(items, list):
        logger.warning(
            "parse_clarification_reply_with_llm: 输出非 JSON 数组: %s",
            (getattr(resp, "content", "") or "")[:200],
        )
        return []
    return [x for x in items if isinstance(x, dict)]


def apply_llm_clarification_patches(drafts: List[ComponentDraft], patches: List[dict]) -> None:
    """将 LLM 解析结果写入 drafts（写入前校验许可名）。"""
    for patch in patches:
        d = _find_draft_for_patch(drafts, patch)
        if not d:
            continue

        lic = validate_license_for_merge(patch.get("license_name"))
        if lic and d.license_name == "TBD":
            d.license_name = lic
            d.license_source = "user"

        new_name = patch.get("canonical_name")
        if new_name is not None and str(new_name).strip().lower() not in ("null", "none", ""):
            new_name = str(new_name).strip()
            if d.canonical_name.startswith("inferred_") and is_retrievable_name(new_name):
                d.canonical_name = new_name
                d.is_named = True

        wtype = normalize_work_type(patch.get("work_type"))
        if wtype:
            d.work_type = wtype
        wform = normalize_work_form(patch.get("work_form"))
        if wform:
            d.work_form = wform


def normalize_interrupt_reply(reply) -> str:
    """将 interrupt() 返回值规范为用户的纯文本续答。"""
    if reply is None:
        return ""
    if isinstance(reply, str):
        return reply.strip()
    if isinstance(reply, dict):
        # LangGraph 有时回传 interrupt 时传入的 payload，而非用户输入
        if reply.get("kind") in ("clarify_attributes", "confirm_unlicense") and "message" in reply:
            for key in ("resume", "content", "value", "answer"):
                val = reply.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
            return ""
        for key in ("resume", "content", "value", "answer", "message"):
            val = reply.get(key)
            if isinstance(val, str) and val.strip() and key != "message":
                return val.strip()
    return str(reply).strip()


def _merge_clarification_reply_rules(drafts: List[ComponentDraft], text: str) -> None:
    """规则/正则解析续答（优先路径）。"""
    lic = extract_license_from_text(text)
    wtype = normalize_work_type(text)
    wform = normalize_work_form(text, text)
    explicit_name = extract_explicit_name_from_reply(text)

    pending_lic = [
        d for d in drafts
        if not d.registry_hit and d.license_name == "TBD"
    ]
    if lic and _should_use_rule_license_merge(pending_lic, text):
        lic = validate_license_for_merge(lic) or lic
        matched = [d for d in pending_lic if _draft_matches_reply(d, text)]
        targets = matched if matched else pending_lic
        for d in targets:
            d.license_name = lic
            d.license_source = "user"
    elif lic and len(pending_lic) > 1:
        logger.info(
            "merge rules: 跳过单许可广播 (pending=%s, licenses=%s)",
            [d.canonical_name for d in pending_lic],
            extract_all_licenses_from_text(text),
        )

    for d in drafts:
        if d.registry_hit or not d.canonical_name.startswith("inferred_"):
            continue
        if explicit_name and (len(pending_lic) <= 1 or _draft_matches_reply(d, text)):
            d.canonical_name = explicit_name
            d.is_named = is_retrievable_name(explicit_name)

    for d in drafts:
        if d.registry_hit:
            continue
        if wtype and (len(pending_lic) <= 1 or _draft_matches_reply(d, text)):
            d.work_type = wtype
        if wform and (len(pending_lic) <= 1 or _draft_matches_reply(d, text)):
            d.work_form = wform


def merge_clarification_reply(
    drafts: List[ComponentDraft],
    reply: str,
    *,
    llm: Any = None,
    prompt_template_clarify: Any = None,
) -> None:
    """
    合并用户澄清续答：先规则/正则，仍缺信息且提供 llm 时再走 LLM 解析并校验后写入。
    """
    text = (reply or "").strip()
    if not text:
        return
    confirm = parse_user_confirm(text)
    if confirm is not None and not extract_license_from_text(text):
        return

    pending_lic_pre = [d for d in drafts if not d.registry_hit and d.license_name == "TBD"]
    multi_pending = len(pending_lic_pre) > 1

    if not multi_pending:
        _merge_clarification_reply_rules(drafts, text)

    still_need = [
        d for d in drafts
        if not d.registry_hit
        and (d.license_name == "TBD" or d.canonical_name.startswith("inferred_"))
    ]
    if not still_need:
        return

    if multi_pending and llm and prompt_template_clarify:
        logger.info("merge_clarification_reply: 多组件待澄清，优先 LLM 解析")
        patches = parse_clarification_reply_with_llm(llm, prompt_template_clarify, text, drafts)
        if patches:
            apply_llm_clarification_patches(drafts, patches)
        still_need = [
            d for d in drafts
            if not d.registry_hit
            and (d.license_name == "TBD" or d.canonical_name.startswith("inferred_"))
        ]
        if not still_need:
            logger.info(
                "merge_clarification_reply: LLM(多组件) 合并后 drafts=%s",
                [(d.canonical_name, d.license_name) for d in drafts],
            )
            return

    if not llm or not prompt_template_clarify:
        pending_lic = [d for d in still_need if d.license_name == "TBD"]
        if pending_lic:
            logger.warning(
                "merge_clarification_reply: 规则未解析完且未配置 LLM, pending=%s, reply=%r",
                [d.canonical_name for d in pending_lic],
                text[:120],
            )
        return

    logger.info(
        "merge_clarification_reply: 规则未完全解析，尝试 LLM, still_need=%s",
        [(d.canonical_name, d.license_name) for d in still_need],
    )
    patches = parse_clarification_reply_with_llm(llm, prompt_template_clarify, text, drafts)
    if not patches:
        logger.warning("merge_clarification_reply: LLM 未返回有效补丁, reply=%r", text[:120])
        return

    apply_llm_clarification_patches(drafts, patches)
    logger.info(
        "merge_clarification_reply: LLM 合并后 drafts=%s",
        [(d.canonical_name, d.license_name) for d in drafts],
    )


def build_clarify_message(drafts: List[ComponentDraft]) -> str:
    lines = ["以下组件信息不完整，请补充（可在一句话中说明）："]
    for d in drafts:
        if d.registry_hit:
            continue
        missing = []
        if d.canonical_name.startswith("inferred_"):
            missing.append("正式名称或来源（如 HuggingFace 路径）")
        if d.license_name == "TBD":
            missing.append("许可证")
        if missing:
            lines.append(f"- 「{d.mention}」：缺少 {', '.join(missing)}")
    return "\n".join(lines)


def build_unlicense_confirm_message(draft: ComponentDraft) -> str:
    return (
        f"组件「{draft.mention}」（系统暂命名为 {draft.canonical_name}）的许可信息缺失。\n"
        "是否继续分析？若继续，将按 **Unlicense** 作为许可假设参与推理，"
        "**分析结果仅供参考**，报告中将注明该假设。\n"
        "请回复「继续」或「取消」。"
    )


def named_unknown_notice(name: str) -> str:
    return (
        f"检测到您的组件「{name}」许可证未知，系统将尽力为您查找对应许可。"
    )


def unlicense_assumption_note(name: str) -> str:
    return (
        f"**假设说明**：组件「{name}」无法确认许可，经您同意已按 Unlicense 假设参与分析；"
        "该段结论未经核实，仅供参考，请补充组件来源与许可后再做决策。"
    )
