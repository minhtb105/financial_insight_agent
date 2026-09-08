import pytest
import yaml

from application.prompts import (
    PromptRegistry,
    PromptRegistryError,
    get_registry,
    reset_registry,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_registry()
    yield
    reset_registry()


class TestBuiltinTemplates:
    def test_all_three_prompts_load(self):
        registry = get_registry()
        assert set(registry.names()) >= {
            "agent_system", "response_synthesis", "query_splitter",
        }

    def test_default_version_is_pinned(self):
        registry = get_registry()
        # agent_system is now 1.2 (MCP minimal), others stay 1.0
        assert registry.get_entry("agent_system")["version"] == "1.2"
        for name in ("response_synthesis", "query_splitter"):
            entry = registry.get_entry(name)
            assert entry["version"] == "1.0"
            assert entry["status"] == "stable"

    def test_agent_system_text_matches_baseline(self):
        text = get_registry().render("agent_system").text
        assert text.startswith(
            "You are a professional stock analysis assistant for the Vietnamese market."
        )
        # v1.2 is MCP-minimal: citation guidance moved to tools/list descriptions
        assert "Tools are provided via MCP tools/list" in text
        assert "[TICKER: value, nguồn: tool_name]" not in text
        assert len(text) > 500

    def test_unknown_prompt_raises(self):
        with pytest.raises(PromptRegistryError, match="Unknown prompt"):
            get_registry().render("does_not_exist")

    def test_unknown_version_raises(self):
        with pytest.raises(PromptRegistryError, match="no version"):
            get_registry().render("agent_system", version="9.9")


class TestRegistryLoading:
    def _write(self, path, name, versions, default=None):
        data = {"name": name, "versions": versions}
        if default:
            data["default_version"] = default
        (path / f"{name}.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")

    def test_duplicate_versions_rejected(self, tmp_path):
        self._write(tmp_path, "dup", [
            {"version": "1", "template": "a"},
            {"version": "1", "template": "b"},
        ])
        with pytest.raises(PromptRegistryError, match="duplicate version"):
            PromptRegistry(base_dir=tmp_path)

    def test_empty_template_rejected(self, tmp_path):
        self._write(tmp_path, "empty", [{"version": "1", "template": "  "}])
        with pytest.raises(PromptRegistryError, match="empty template"):
            PromptRegistry(base_dir=tmp_path)

    def test_latest_stable_wins_without_pin(self, tmp_path):
        self._write(tmp_path, "multi", [
            {"version": "1.0", "template": "v1 {x}"},
            {"version": "2.0", "status": "draft", "template": "v2 {x}"},
            {"version": "1.5", "template": "v15 {x}"},
        ])
        registry = PromptRegistry(base_dir=tmp_path)
        assert registry.render("multi", x=1).text == "v15 1"

    def test_default_version_pin_respected(self, tmp_path):
        self._write(tmp_path, "pinned", [
            {"version": "1.0", "template": "one {x}"},
            {"version": "2.0", "template": "two {x}"},
        ], default="1.0")
        registry = PromptRegistry(base_dir=tmp_path)
        assert registry.render("pinned", x="?").version == "1.0"

    def test_explicit_draft_version_selectable(self, tmp_path):
        self._write(tmp_path, "draft_ok", [
            {"version": "1.0", "template": "stable"},
            {"version": "2.0", "status": "draft", "template": "experimental {x}"},
        ])
        registry = PromptRegistry(base_dir=tmp_path)
        rendered = registry.render("draft_ok", version="2.0", x=1)
        assert rendered.text == "experimental 1"


class TestRendering:
    def _registry_with_vars(self, tmp_path):
        self._write_yaml(tmp_path)
        return PromptRegistry(base_dir=tmp_path)

    @staticmethod
    def _write_yaml(tmp_path):
        (tmp_path / "withvars.yaml").write_text(
            yaml.safe_dump({
                "name": "withvars",
                "versions": [{
                    "version": "1.0",
                    "template": "Hello {user}, today is {date}. Score: {score}",
                }],
            }),
            encoding="utf-8",
        )

    def test_missing_variables_raise(self, tmp_path):
        registry = self._registry_with_vars(tmp_path)
        with pytest.raises(PromptRegistryError, match="missing variables"):
            registry.render("withvars", user="an")

    def test_render_substitutes_all_variables(self, tmp_path):
        registry = self._registry_with_vars(tmp_path)
        rendered = registry.render(
            "withvars", user="An", date="2026-08-25", score=99
        )
        assert rendered.text == "Hello An, today is 2026-08-25. Score: 99"
        assert rendered.variables_used == {"date": "2026-08-25", "score": 99, "user": "An"}

    def test_extra_variables_ignored(self, tmp_path):
        registry = self._registry_with_vars(tmp_path)
        rendered = registry.render(
            "withvars", user="A", date="d", score=1, unused="ignored"
        )
        assert "ignored" not in rendered.text

    def test_malformed_placeholder_raises(self, tmp_path):
        (tmp_path / "bad.yaml").write_text(
            yaml.safe_dump({
                "name": "bad",
                "versions": [{"version": "1.0", "template": "oops {broken"}],
            }),
            encoding="utf-8",
        )
        with pytest.raises(PromptRegistryError, match="malformed placeholder"):
            PromptRegistry(base_dir=tmp_path)
