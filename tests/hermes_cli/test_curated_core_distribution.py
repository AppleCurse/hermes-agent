"""Regression coverage for the small, installable Curated Core profile."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from hermes_cli.plugin_dev import doctor_plugin
from hermes_cli.profile_distribution import install_distribution
from tools.plugin_guard import scan_plugin
from tools.skills_guard import scan_skill


PROFILE_SOURCE = Path(__file__).resolve().parents[2] / "profiles" / "curated-core"


@pytest.fixture()
def profile_env(tmp_path, monkeypatch):
    """An isolated default Hermes home, matching profile-distribution tests."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    default_home = tmp_path / ".hermes"
    default_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(default_home))
    return default_home


def test_curated_core_installs_as_a_small_verified_profile(profile_env):
    plan = install_distribution(str(PROFILE_SOURCE), name="core")
    root = plan.target_dir

    config = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
    assert config["memory"]["provider"] == "eternal_memory"
    assert config["memory"]["eternal_memory"]["auto_extract"] is True
    assert config["memory"]["eternal_memory"]["max_results"] == 6
    assert config["browser"] == {
        "backend": "browser-use",
        "cloud_provider": "local",
        "use_real_profile": False,
    }
    assert config["web"] == {
        "backend": "firecrawl",
        "search_backend": "firecrawl",
        "extract_backend": "firecrawl",
        "keyless_fallback": True,
        "keyless_rescue": True,
    }
    assert config["plugins"]["enabled"] == ["ponytail"]
    assert config["plugins"]["entries"]["ponytail"]["allow_tool_override"] is False

    ponytail = root / "plugins" / "ponytail"
    assert (root / ".env.EXAMPLE").is_file()
    assert (root / "skills" / "sherlock" / "SKILL.md").is_file()
    assert (ponytail / "SOURCE.json").is_file()

    scan = scan_plugin(ponytail, source="curated-core")
    assert scan.verdict == "safe", scan.summary
    skill_scan = scan_skill(
        root / "skills" / "sherlock" / "SKILL.md", source="curated-core"
    )
    assert skill_scan.verdict == "safe", skill_scan.summary

    report = doctor_plugin(str(ponytail))
    assert report.ok, report.format_text()
    assert set(report.registered_hooks) == {"pre_llm_call", "pre_gateway_dispatch"}


def test_ponytail_payload_matches_its_recorded_hashes():
    ponytail = PROFILE_SOURCE / "plugins" / "ponytail"
    provenance = json.loads((ponytail / "SOURCE.json").read_text(encoding="utf-8"))

    assert (
        provenance["upstream"]["commit"] == "e3ba2aa6f1e6f0bc4d69eb09c9f0d0a93af56156"
    )
    assert provenance["upstream"]["license"] == "MIT"
    for relative_path, metadata in provenance["files"].items():
        payload = (ponytail / relative_path).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == metadata["sha256"]
