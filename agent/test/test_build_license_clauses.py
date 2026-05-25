"""build_license_clauses_text 单元测试"""
from dataclasses import dataclass

from agent.graph.nodes.helpers import build_license_clauses_text


@dataclass
class _FakeWork:
    name: str
    license: str


def test_build_license_clauses_uses_fetch_text():
    def fake_fetch(lic: str):
        return f"FULL TEXT FOR {lic}"

    works = [
        _FakeWork("model_a", "MPL-2.0"),
        _FakeWork("data_b", "CC-BY-NC-4.0"),
    ]
    out = build_license_clauses_text(works, fetch_text=fake_fetch)
    assert "FULL TEXT FOR MPL-2.0" in out
    assert "FULL TEXT FOR CC-BY-NC-4.0" in out
    assert "适用作品：model_a" in out
    assert "（原文件未找到" not in out


def test_build_license_clauses_missing_text_placeholder():
    works = [_FakeWork("w1", "Unknown-License-XYZ")]

    out = build_license_clauses_text(works, fetch_text=lambda _: None)
    assert "Unknown-License-XYZ" in out
    assert "（原文件未找到，请查阅官方网站）" in out


def test_build_license_clauses_dedupes_license():
    works = [
        _FakeWork("a", "MIT"),
        _FakeWork("b", "MIT"),
    ]
    calls = []

    def fake_fetch(lic: str):
        calls.append(lic)
        return "mit body"

    out = build_license_clauses_text(works, fetch_text=fake_fetch)
    assert calls == ["MIT"]
    assert out.count("mit body") == 1
    assert "适用作品：a、b" in out or "适用作品：b、a" in out
