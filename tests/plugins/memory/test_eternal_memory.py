"""Tests for the Eternal Memory provider (plugins/memory/eternal_memory)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import hermes_constants
import plugins.memory.eternal_memory as eternal
from plugins.memory.eternal_memory import EternalMemoryProvider


def _make_provider(tmp_path: Path, session_id: str = "sess-1", **init_kwargs) -> EternalMemoryProvider:
    provider = EternalMemoryProvider(config={})
    provider.initialize(session_id, hermes_home=str(tmp_path), **init_kwargs)
    return provider


def _db_rows(tmp_path: Path, sql: str, params: tuple = ()) -> list:
    conn = sqlite3.connect(str(tmp_path / "memories" / "eternal" / "eternal_memory.db"))
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


_TURKISH_TURN = [
    {"role": "user", "content": "Merhaba! Benim adım Ayşe. Tercih ediyorum: Türkçe cevap ver, kodları tip tanımlı yaz. Ayrıca lütfen hata çıktılarını kısaltma."},
    {"role": "assistant", "content": "Anlaşıldı, Ayşe! Karar verdik: proje FastAPI ve PostgreSQL 15.4 üzerinde çalışacak. Python 3.12 kullanıyoruz."},
    {"role": "assistant", "content": "", "tool_calls": [
        {"function": {"name": "bash", "arguments": "{\"command\": \"pytest -q\"}"}},
    ]},
    {"role": "user", "content": "We decided to use Redis for caching. I prefer dark mode in the dashboard."},
]


def test_register_and_name():
    class Ctx:
        def __init__(self):
            self.provider = None

        def register_memory_provider(self, provider):
            self.provider = provider

    ctx = Ctx()
    eternal.register(ctx)
    assert ctx.provider is not None
    assert ctx.provider.name == "eternal_memory"


def test_is_available_verifies_local_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    token = hermes_constants.set_hermes_home_override(str(tmp_path))
    try:
        provider = EternalMemoryProvider(config={})
        assert provider.is_available() is True
        assert provider.unavailable_reason() == ""
        mem_dir = tmp_path / "memories" / "eternal"
        assert mem_dir.is_dir()
        # Corrupt JSON layer -> unavailable with a user-facing reason.
        (mem_dir / "state.json").write_text("{not json", encoding="utf-8")
        assert provider.is_available() is False
        assert "state.json" in provider.unavailable_reason()
        (mem_dir / "state.json").write_text(json.dumps({"ok": 1}), encoding="utf-8")
        assert provider.is_available() is True
        # Empty Markdown layer -> unavailable.
        (mem_dir / "identity.md").write_text("   \n", encoding="utf-8")
        assert provider.is_available() is False
        assert "identity.md" in provider.unavailable_reason()
    finally:
        hermes_constants.reset_hermes_home_override(token)


def test_initialize_creates_local_environment(tmp_path):
    provider = _make_provider(tmp_path)
    mem_dir = tmp_path / "memories" / "eternal"
    assert (mem_dir / "eternal_memory.db").is_file()
    assert (mem_dir / "state.json").is_file()
    assert (mem_dir / "identity.md").is_file()
    tables = {r[0] for r in _db_rows(tmp_path, "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"memories", "entities", "skills_ledger"} <= tables
    state = json.loads((mem_dir / "state.json").read_text(encoding="utf-8"))
    assert state["provider"] == "eternal_memory"
    assert state["version"] == "1.0.0"
    provider.shutdown()


def test_system_prompt_block_contains_identity_armor(tmp_path):
    provider = _make_provider(tmp_path)
    block = provider.system_prompt_block()
    assert "Çekirdek Kimlik ve Değişmez Prensipler" in block
    assert "Değişmez Prensipler — Model-Değişim Zırhı" in block
    assert "Kimlik sabittir" in block
    assert "Hermes Agent" in block
    # User-edited identity is honored (the file is user-owned, never overwritten).
    identity = tmp_path / "memories" / "eternal" / "identity.md"
    identity.write_text("# Çekirdek Kimlik\n\nÖzel karakter: Sakin ve net.\n", encoding="utf-8")
    assert "Özel karakter: Sakin ve net." in provider.system_prompt_block()
    # Empty file falls back to the built-in default identity.
    identity.write_text("", encoding="utf-8")
    assert "Hermes Agent" in provider.system_prompt_block()
    provider.shutdown()


def test_on_turn_end_extracts_persists_and_dedupes(tmp_path):
    provider = _make_provider(tmp_path)
    provider.on_turn_end(_TURKISH_TURN, "sess-1")
    contents = [c for _, c in _db_rows(tmp_path, "SELECT kind, content FROM memories")]
    assert any("Türkçe cevap" in c for c in contents)      # TR preference
    assert any("Redis" in c for c in contents)             # EN decision
    assert any("dark mode" in c for c in contents)         # EN preference
    assert any(c == "PostgreSQL 15.4" for c in contents)   # version fact
    assert any("FastAPI" in c for c in contents)           # TR decision
    before = _db_rows(tmp_path, "SELECT COUNT(*) FROM memories")[0][0]
    provider.on_turn_end(_TURKISH_TURN, "sess-1")          # replay: must dedupe
    assert _db_rows(tmp_path, "SELECT COUNT(*) FROM memories")[0][0] == before
    ents = _db_rows(tmp_path, "SELECT name, kind FROM entities")
    assert ("Ayşe", "user") in ents
    assert ("PostgreSQL", "tool") in ents
    skills = _db_rows(tmp_path, "SELECT skill_name, use_count FROM skills_ledger")
    assert ("bash", 2) in skills                            # observed on both passes
    provider.shutdown()


def test_non_primary_context_skips_writes(tmp_path):
    provider = _make_provider(tmp_path, agent_context="subagent")
    provider.on_turn_end(_TURKISH_TURN, "sess-1")
    assert _db_rows(tmp_path, "SELECT COUNT(*) FROM memories")[0][0] == 0
    provider.shutdown()


def test_sync_turn_bridge_and_auto_extract_gate(tmp_path):
    provider = _make_provider(tmp_path)
    provider.sync_turn("I always run migrations with alembic", "ok")
    assert _db_rows(tmp_path, "SELECT COUNT(*) FROM memories")[0][0] >= 1
    gated = EternalMemoryProvider(config={"auto_extract": "false"})
    gated.initialize("s", hermes_home=str(tmp_path))
    before = _db_rows(tmp_path, "SELECT COUNT(*) FROM memories")[0][0]
    gated.sync_turn("I always deploy on Fridays", "ok")
    assert _db_rows(tmp_path, "SELECT COUNT(*) FROM memories")[0][0] == before
    provider.shutdown()
    gated.shutdown()


def test_prefetch_keyword_recall_and_trivial_gate(tmp_path):
    provider = _make_provider(tmp_path)
    provider.on_turn_end(_TURKISH_TURN, "sess-1")
    block = provider.prefetch("kaynak kodda Redis cache nasıl yapıldı?")
    assert "Eternal Memory" in block and "Redis" in block
    status = provider.recall_status()
    assert status is not None and status.count >= 1
    # Trivial prompt: no recall, indicator reset.
    assert provider.prefetch("tamam") == ""
    assert provider.recall_status() is None
    # No keyword overlap: no recall.
    assert provider.prefetch("zzzqqqxxx") == ""
    provider.shutdown()


def test_tools_remember_search_forget_list(tmp_path):
    provider = _make_provider(tmp_path)
    out = json.loads(provider.handle_tool_call("eternal_memory", {
        "action": "remember", "content": "Prod sunucusu: eu-west-1",
        "kind": "fact", "importance": 0.9, "entity": "altyapı"}))
    assert out["status"] == "added"
    memory_id = out["memory_id"]
    found = json.loads(provider.handle_tool_call("eternal_memory", {"action": "search", "query": "prod sunucu eu-west"}))
    assert found["count"] >= 1 and found["results"][0]["memory_id"] == memory_id
    dup = json.loads(provider.handle_tool_call("eternal_memory", {
        "action": "remember", "content": "Prod sunucusu: eu-west-1"}))
    assert dup["status"] == "duplicate"
    listed = json.loads(provider.handle_tool_call("eternal_memory", {"action": "list", "kind": "fact"}))
    assert listed["count"] >= 1
    forgotten = json.loads(provider.handle_tool_call("eternal_memory", {"action": "forget", "memory_id": memory_id}))
    assert forgotten["status"] == "forgotten"
    # Soft-deleted rows are excluded from recall.
    found2 = json.loads(provider.handle_tool_call("eternal_memory", {"action": "search", "query": "prod sunucu eu-west"}))
    assert all(r["memory_id"] != memory_id for r in found2["results"])
    assert "Bilinmeyen" in provider.handle_tool_call("eternal_memory", {"action": "bogus"})
    assert "error" in provider.handle_tool_call("other_tool", {}).lower()
    provider.shutdown()


def test_model_swap_persists_identity_and_memories(tmp_path):
    provider = _make_provider(tmp_path)
    provider.on_turn_end(_TURKISH_TURN, "sess-1")
    (tmp_path / "memories" / "eternal" / "identity.md").write_text(
        "# Çekirdek Kimlik\n\nBenim karakterim sabittir.\n", encoding="utf-8")
    provider.shutdown()
    # "New model" = a fresh provider instance on the same profile.
    provider2 = _make_provider(tmp_path, session_id="sess-2")
    assert "Benim karakterim sabittir." in provider2.system_prompt_block()
    assert "Redis" in provider2.prefetch("Redis cache kararı neydi?")
    provider2.shutdown()


def test_corrupt_state_json_is_recovered(tmp_path):
    mem_dir = tmp_path / "memories" / "eternal"
    mem_dir.mkdir(parents=True)
    (mem_dir / "state.json").write_text("{{{corrupt", encoding="utf-8")
    provider = _make_provider(tmp_path)
    state = json.loads((mem_dir / "state.json").read_text(encoding="utf-8"))
    assert state["provider"] == "eternal_memory"
    assert list(mem_dir.glob("state.json.corrupt-*"))
    provider.shutdown()


def test_post_setup_activates_and_prepares_environment(tmp_path):
    token = hermes_constants.set_hermes_home_override(str(tmp_path))
    try:
        provider = EternalMemoryProvider(config={})
        config: dict = {}
        provider.post_setup(str(tmp_path), config)
        assert config["memory"]["provider"] == "eternal_memory"
        assert (tmp_path / "memories" / "eternal" / "eternal_memory.db").is_file()
        assert (tmp_path / "memories" / "eternal" / "identity.md").is_file()
        assert "eternal_memory" in (tmp_path / "config.yaml").read_text(encoding="utf-8")
    finally:
        hermes_constants.reset_hermes_home_override(token)


def test_on_session_end_persists_state(tmp_path):
    provider = _make_provider(tmp_path)
    provider.on_turn_end(_TURKISH_TURN, "sess-1")
    provider.on_session_end(_TURKISH_TURN)
    state = json.loads((tmp_path / "memories" / "eternal" / "state.json").read_text(encoding="utf-8"))
    assert state["last_session_id"] == "sess-1"
    assert state["counts"]["memories"] >= 1
    assert state["identity_sha256"]
    provider.shutdown()
