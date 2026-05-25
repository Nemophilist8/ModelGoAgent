"""
work_resolver 纯函数单元测试 —— 行为 / 不变量导向。

分层说明（避免「测试通过 ≠ 系统可用」的错觉）：
  - 本文件：检验解析规则在多种输入下应满足的**可推广性质**（不调用 LLM、不跑整图）。
  - 端到端：test_workflow_interactive.py / 真实 API，才检验「系统」整体。

原则：
  - 断言「性质」（许可像 SPDX、整句中文不会进 Work、有名组件不用 inferred_*），
    而不是死记某一个业务名词。
  - 用多组参数覆盖不同组件名 / 许可 / 句式，减少只对单例子过拟合。
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from agent.graph.nodes.work_resolver_helpers import (
    apply_llm_clarification_patches,
    build_work_code,
    derive_canonical_from_mention,
    drafts_from_extract_items,
    extract_license_from_text,
    merge_clarification_reply,
    normalize_interrupt_reply,
    parse_user_confirm,
    resolve_registry_from_mention_and_canonical,
    resolve_registry_key,
    validate_license_for_merge,
)
from agent.models import ComponentDraft

# 与 work_resolver_helpers._SPDX_LICENSE_RE 意图一致：许可字段应是标识符，不是说明句
_SPDX_IN_LICENSE_FIELD = re.compile(
    r"(?i)(CC-|GPL|LGPL|Apache|BSD|MIT|Unlicense|CC0)",
)


def assert_license_field_is_identifier(license_name: str) -> None:
    """许可写入 Work 前必须像 SPDX/常用短名，不能是中文说明句。"""
    assert license_name and license_name != "TBD"
    assert "许可是" not in license_name
    assert "许可证" not in license_name
    assert not re.search(r"[\u4e00-\u9fff]{3,}", license_name), (
        f"许可字段不应含长中文说明: {license_name!r}"
    )
    assert _SPDX_IN_LICENSE_FIELD.search(license_name), (
        f"许可字段应含可识别的 SPDX 风格标识: {license_name!r}"
    )


def assert_work_code_uses_license(draft: ComponentDraft, expected_license: str) -> None:
    code = build_work_code(draft)
    assert f"'{expected_license}'" in code
    assert "许可是" not in code


# --- 注册表 / 确认（知识库契约，仍用具体 key 因 registry 是显式配置）---


def test_registry_hit_from_canonical():
    items = [{"mention": "wiki", "canonical_name": "Wikipedia", "is_named": True}]
    drafts = drafts_from_extract_items(items, "")
    assert len(drafts) == 1
    assert drafts[0].registry_hit
    assert "Wikipedia" in drafts[0].code


@pytest.mark.parametrize(
    "mention,expected_key",
    [
        ("midjourney", "Midjourney_gen"),
        ("i2vgen-xl", "I2VGen-XL"),
        ("bert", "BERT"),
    ],
)
def test_registry_resolve_by_mention_alias(mention, expected_key):
    assert resolve_registry_from_mention_and_canonical(mention, None) == expected_key
    drafts = drafts_from_extract_items(
        [{"mention": mention, "canonical_name": None, "is_named": False}],
        "",
    )
    assert drafts[0].registry_hit


@pytest.mark.parametrize(
    "reply,expected",
    [
        ("继续", True),
        ("取消", False),
        ("yes", True),
        ("no", False),
        ("happy数据集的许可是CC-BY-SA-4.0", None),
    ],
)
def test_parse_user_confirm(reply, expected):
    assert parse_user_confirm(reply) is expected


def test_merge_license_reply_with_shi_char_not_treated_as_confirm():
    drafts = [
        ComponentDraft(
            mention="happy数据集",
            canonical_name="happy",
            is_named=True,
            work_type="data",
            work_form="raw",
            license_name="TBD",
        ),
    ]
    merge_clarification_reply(drafts, "happy数据集的许可是CC-BY-SA-4.0")
    assert drafts[0].license_name == "CC-BY-SA-4.0"


# --- derive_canonical_from_mention：后缀剥离 + 可检索名 ---


@pytest.mark.parametrize(
    "mention,expected_base",
    [
        ("alpha数据集", "alpha"),
        ("beta模型", "beta"),
        ("gamma", "gamma"),
        ("org/repo-name", "org/repo-name"),
    ],
)
def test_derive_canonical_strips_suffix_or_keeps_name(mention, expected_base):
    assert derive_canonical_from_mention(mention) == expected_base


@pytest.mark.parametrize(
    "mention",
    ["某输出", "未命名组件", "", "它"],
)
def test_derive_canonical_returns_none_for_vague_mention(mention):
    assert derive_canonical_from_mention(mention) is None


# --- extract_license_from_text：从自然语言抽出标识符，拒绝整句 ---


@pytest.mark.parametrize(
    "reply,expected_license",
    [
        ("CC-BY-SA-4.0", "CC-BY-SA-4.0"),
        ("许可为 MIT", "MIT"),
        ("组件 foo 使用 Apache-2.0 许可", "Apache-2.0"),
        ("bar数据集的许可是 GPL-3.0", "GPL-3.0"),
        ("采用 CC-BY-NC-4.0 发布", "CC-BY-NC-4.0"),
        # 中文「是」与 CC 之间无 ASCII 词界，旧版 \\b 会匹配失败
        ("happy数据集的许可是CC-BY-SA-4.0", "CC-BY-SA-4.0"),
    ],
)
def test_extract_license_from_varied_phrases(reply, expected_license):
    got = extract_license_from_text(reply)
    assert got == expected_license
    assert_license_field_is_identifier(got)


@pytest.mark.parametrize(
    "reply",
    [
        "这是一段很长的说明，但没有写出任何 SPDX 风格许可证名称。",
        "继续",
        "",
    ],
)
def test_extract_license_returns_none_without_spdx(reply):
    assert extract_license_from_text(reply) is None


# --- drafts_from_extract_items：有名 mention 不应落到 inferred_* ---


@pytest.mark.parametrize(
    "mention,work_type",
    [
        ("customset数据集", "data"),
        ("my_model模型", "model"),
        ("zephyr", "model"),
    ],
)
def test_drafts_use_derived_name_not_inferred_when_mention_is_specific(mention, work_type):
    items = [{
        "mention": mention,
        "canonical_name": None,
        "is_named": False,
        "user_stated_type": work_type,
    }]
    drafts = drafts_from_extract_items(items, "用户描述略")
    d = drafts[0]
    assert not d.canonical_name.startswith("inferred_"), (
        f"具体 mention {mention!r} 不应被分配为 {d.canonical_name}"
    )
    assert d.is_named


def test_drafts_allocate_inferred_for_vague_mention():
    items = [{
        "mention": "某输出",
        "canonical_name": None,
        "is_named": False,
        "user_stated_type": "data",
    }]
    drafts = drafts_from_extract_items(items, "")
    assert drafts[0].canonical_name.startswith("inferred_data")
    assert "Work(" in build_work_code(drafts[0])


# --- merge_clarification_reply：续答只更新许可字段，不污染名称 ---


@pytest.mark.parametrize(
    "component_label,canonical,reply,expected_license",
    [
        (
            "foo数据集",
            "foo",
            "foo数据集的许可是 CC-BY-SA-4.0",
            "CC-BY-SA-4.0",
        ),
        (
            "bar",
            "bar",
            "bar 用 MIT",
            "MIT",
        ),
        (
            "baz模型",
            "baz",
            "GPL-3.0",
            "GPL-3.0",
        ),
    ],
)
@pytest.mark.parametrize(
    "raw_reply,expected_text",
    [
        ("happy数据集的许可是CC-BY-SA-4.0", "happy数据集的许可是CC-BY-SA-4.0"),
        ({"kind": "clarify_attributes", "message": "请补充"}, ""),
        ({"content": "GPL-3.0"}, "GPL-3.0"),
    ],
)
def test_normalize_interrupt_reply(raw_reply, expected_text):
    assert normalize_interrupt_reply(raw_reply) == expected_text


@pytest.mark.parametrize(
    "raw,ok",
    [
        ("CC-BY-SA-4.0", "CC-BY-SA-4.0"),
        ("MIT", "MIT"),
        ("happy数据集的许可是CC-BY-SA-4.0", None),
        ("随便写的许可", None),
    ],
)
def test_validate_license_for_merge(raw, ok):
    assert validate_license_for_merge(raw) == ok


def test_apply_llm_clarification_patches():
    drafts = [
        ComponentDraft(
            mention="happy数据集",
            canonical_name="happy",
            is_named=True,
            work_type="data",
            work_form="raw",
            license_name="TBD",
        ),
    ]
    apply_llm_clarification_patches(
        drafts,
        [{"mention": "happy数据集", "canonical_name": "happy", "license_name": "CC-BY-SA-4.0"}],
    )
    assert drafts[0].license_name == "CC-BY-SA-4.0"
    assert drafts[0].license_source == "user"


def test_merge_clarification_sets_spdx_license_not_full_sentence(
    component_label, canonical, reply, expected_license
):
    drafts = [
        ComponentDraft(
            mention=component_label,
            canonical_name=canonical,
            is_named=True,
            work_type="data",
            work_form="raw",
            license_name="TBD",
        ),
    ]
    merge_clarification_reply(drafts, reply)
    d = drafts[0]
    assert d.canonical_name == canonical, "仅补许可时不应改掉已有标准名"
    assert d.license_name == expected_license
    assert_license_field_is_identifier(d.license_name)
    assert_work_code_uses_license(d, expected_license)
