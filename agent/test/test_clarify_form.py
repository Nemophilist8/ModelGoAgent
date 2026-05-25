"""clarify_form 与多组件许可合并测试"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from agent.graph.nodes.clarify_form import (
    apply_form_answers,
    build_clarify_form,
    parse_resume_to_form_answers,
)
from agent.graph.nodes.work_resolver_helpers import (
    _should_use_rule_license_merge,
    extract_all_licenses_from_text,
    merge_clarification_reply,
)
from agent.models import ComponentDraft


def _draft(name: str, lic: str = "TBD") -> ComponentDraft:
    return ComponentDraft(
        mention=f"{name}模型",
        canonical_name=name,
        is_named=True,
        work_type="model",
        work_form="raw",
        license_name=lic,
    )


def test_build_clarify_form_multi():
    form = build_clarify_form([_draft("light"), _draft("dark")])
    assert len(form["components"]) == 2
    assert "license_name" in form["fields"]


def test_apply_form_two_licenses():
    drafts = [_draft("light"), _draft("dark")]
    answers = [
        {"canonical_name": "light", "license_name": "GPL-3.0"},
        {"canonical_name": "dark", "license_name": "Apache-2.0"},
    ]
    still = apply_form_answers(drafts, answers)
    assert drafts[0].license_name == "GPL-3.0"
    assert drafts[1].license_name == "Apache-2.0"
    assert still == []


def test_rule_skip_multi_license_broadcast():
    text = "light模型的许可是GPL-3.0，dark模型的许可是Apache-2.0"
    pending = [_draft("light"), _draft("dark")]
    assert not _should_use_rule_license_merge(pending, text)
    assert len(extract_all_licenses_from_text(text)) == 2

    merge_clarification_reply(drafts := [_draft("light"), _draft("dark")], text)
    assert drafts[0].license_name == "TBD"
    assert drafts[1].license_name == "TBD"


def test_parse_resume_form_json():
    raw = '{"kind":"clarify_form","answers":[{"canonical_name":"light","license_name":"MIT"}]}'
    ans = parse_resume_to_form_answers(raw)
    assert len(ans) == 1
    assert ans[0]["license_name"] == "MIT"
