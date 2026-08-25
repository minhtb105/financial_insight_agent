"""YAML-backed prompt registry with explicit versioning.

Each prompt lives in ``templates/<name>.yaml``::

    name: agent_system
    description: ReAct agent system prompt
    default_version: "1.0"
    versions:
      - version: "1.0"
        status: stable
        created: "2026-08-25"
        changelog: Initial import
        template: |
          You are ...

Rendering validates that every ``{placeholder}`` is supplied and records
``prompt_name``/``prompt_version`` onto the active trace span so evaluation
runs can be attributed to an exact prompt revision.
"""

from __future__ import annotations

import string
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class PromptRegistryError(Exception):
    """Raised for registry load/render problems."""


_MAX_TEMPLATE_VARS = 50


def _validate_template_syntax(template: str, context: str) -> None:
    """Fail fast on malformed ``{placeholder}`` syntax."""
    try:
        for _ in string.Formatter().parse(template):
            pass
    except ValueError as exc:
        raise PromptRegistryError(
            f"{context}: malformed placeholder ({exc})"
        ) from exc


@dataclass
class RenderedPrompt:
    """A fully rendered prompt ready to be sent to the LLM."""

    name: str
    version: str
    text: str
    variables_used: dict[str, Any] = field(default_factory=dict)

    def annotate_active_span(self) -> None:
        """Best-effort: stamp prompt identity onto the currently open span."""
        try:
            from infrastructure.observability.tracing import get_tracer
            from infrastructure.observability.tracing.context import span_stack_var

            stack = span_stack_var.get()
            if not stack:
                return
            span = stack[-1]
            span.prompt_name = self.name
            span.prompt_version = self.version
            tracer = get_tracer()
            if tracer.enabled:
                span.attributes.setdefault("prompt_name", self.name)
                span.attributes.setdefault("prompt_version", self.version)
        except Exception:
            pass


@dataclass
class PromptVersionEntry:
    version: str
    status: str
    template: str
    created: str | None = None
    changelog: str | None = None

    @staticmethod
    def _version_key(version: str):
        parts: list[tuple[int, int | str]] = []
        for piece in str(version).split("."):
            try:
                parts.append((0, int(piece)))
            except ValueError:
                parts.append((1, piece))
        return parts


class PromptRegistry:
    """Loads, validates, and renders versioned YAML prompts."""

    def __init__(self, base_dir: str | Path | None = None):
        self.base_dir = (
            Path(base_dir) if base_dir else Path(__file__).parent / "templates"
        )
        self._prompts: dict[str, list[dict[str, Any]]] = {}
        self._defaults: dict[str, str | None] = {}
        self._lock = threading.RLock()
        self.reload()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def reload(self) -> None:
        with self._lock:
            prompts: dict[str, list[dict[str, Any]]] = {}
            defaults: dict[str, str | None] = {}
            if not self.base_dir.exists():
                raise PromptRegistryError(f"Prompt templates dir not found: {self.base_dir}")
            for path in sorted(self.base_dir.glob("*.yaml")):
                try:
                    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
                except yaml.YAMLError as exc:
                    raise PromptRegistryError(f"Invalid YAML in {path.name}: {exc}") from exc
                if not isinstance(raw, dict):
                    raise PromptRegistryError(f"{path.name}: top level must be a mapping")
                name = raw.get("name") or path.stem
                versions_raw = raw.get("versions")
                if not isinstance(versions_raw, list) or not versions_raw:
                    raise PromptRegistryError(f"{path.name}: 'versions' must be a non-empty list")
                entries: list[dict[str, Any]] = []
                seen_versions: set[str] = set()
                for item in versions_raw:
                    entry = self._validate_entry(path.name, item)
                    if entry["version"] in seen_versions:
                        raise PromptRegistryError(
                            f"{path.name}: duplicate version '{entry['version']}'"
                        )
                    seen_versions.add(entry["version"])
                    entries.append(entry)
                entries.sort(
                    key=lambda e: PromptVersionEntry._version_key(e["version"]),
                    reverse=True,
                )
                prompts[name] = entries
                defaults[name] = raw.get("default_version")
            self._prompts = prompts
            self._defaults = defaults

    @staticmethod
    def _validate_entry(filename: str, item: Any) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise PromptRegistryError(f"{filename}: each version must be a mapping")
        version = item.get("version")
        template = item.get("template")
        if version is None or not str(version).strip():
            raise PromptRegistryError(f"{filename}: version missing")
        if not template or not str(template).strip():
            raise PromptRegistryError(f"{filename} v{version}: empty template")
        status = str(item.get("status", "stable")).lower()
        if status not in ("stable", "draft", "deprecated"):
            raise PromptRegistryError(f"{filename} v{version}: invalid status '{status}'")
        template_text = str(template)
        _validate_template_syntax(template_text, f"{filename} v{version}")
        return {
            "version": str(version),
            "status": status,
            "template": template_text,
            "created": item.get("created"),
            "changelog": item.get("changelog"),
        }

    # ------------------------------------------------------------------
    # Lookup & rendering
    # ------------------------------------------------------------------

    def names(self) -> list[str]:
        return sorted(self._prompts.keys())

    def versions(self, name: str) -> list[str]:
        return [e["version"] for e in self._prompts.get(name, [])]

    def get_entry(self, name: str, version: str | None = None) -> dict[str, Any]:
        with self._lock:
            entries = self._prompts.get(name)
        if not entries:
            raise PromptRegistryError(f"Unknown prompt '{name}'. Available: {self.names()}")

        if version is None:
            pinned = self._defaults.get(name)
            chosen = next((e for e in entries if e["version"] == pinned), None)
            if chosen is None:
                chosen = next(
                    (e for e in entries if e["status"] == "stable"), entries[0]
                )
            return chosen

        chosen = next((e for e in entries if e["version"] == str(version)), None)
        if chosen is None:
            available = ", ".join(e["version"] for e in entries)
            raise PromptRegistryError(
                f"Prompt '{name}' has no version '{version}'. Available: {available}"
            )
        return chosen

    def render(
        self,
        name: str,
        *,
        version: str | None = None,
        **variables: Any,
    ) -> RenderedPrompt:
        entry = self.get_entry(name, version)
        template = entry["template"]

        required: set[str] = set()
        try:
            for _, field_name, _, _ in string.Formatter().parse(template):
                if field_name:
                    base = field_name.split(".")[0].split("[")[0]
                    if base:
                        required.add(base)
        except ValueError as exc:
            raise PromptRegistryError(
                f"Prompt '{name}' v{entry['version']}: malformed placeholder ({exc})"
            ) from exc
        if len(required) > _MAX_TEMPLATE_VARS:
            raise PromptRegistryError(f"Prompt '{name}': too many placeholders")

        missing = required - set(variables.keys())
        if missing:
            raise PromptRegistryError(
                f"Prompt '{name}' v{entry['version']}: missing variables: {sorted(missing)}"
            )

        try:
            text = template.format(**variables)
        except (KeyError, IndexError, ValueError) as exc:
            raise PromptRegistryError(
                f"Prompt '{name}' v{entry['version']}: render failed ({exc})"
            ) from exc

        rendered = RenderedPrompt(
            name=name,
            version=entry["version"],
            text=text,
            variables_used={k: variables[k] for k in sorted(required)},
        )
        rendered.annotate_active_span()
        return rendered


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_registry: PromptRegistry | None = None
_registry_lock = threading.Lock()


def get_registry() -> PromptRegistry:
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                import os

                override = os.getenv("PROMPTS_DIR", "").strip()
                _registry = PromptRegistry(override or None)
    return _registry


def reset_registry() -> None:
    global _registry
    with _registry_lock:
        _registry = None
