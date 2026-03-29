from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.config import settings
from app.services.adapters.base import BasePlatformAdapter


@dataclass
class PlatformPackage:
    platform_id: str
    root: Path
    meta: dict[str, Any]
    knowledge_docs: list[dict[str, Any]]
    rules: dict[str, Any]
    prompts: dict[str, str]
    workflows: dict[str, list[str]]
    adapter: BasePlatformAdapter | None = None

    @property
    def enabled_routes(self) -> list[str]:
        return list(self.meta.get("enabled_routes", []))


@dataclass
class PlatformRegistry:
    platforms_dir: Path
    default_platform: str
    packages: dict[str, PlatformPackage] = field(default_factory=dict)

    def load(self) -> None:
        self.packages = {}
        if not self.platforms_dir.exists():
            raise RuntimeError(f"platforms directory not found: {self.platforms_dir}")
        for root in self.platforms_dir.iterdir():
            if not root.is_dir():
                continue
            config_path = root / "platform.yaml"
            if not config_path.exists():
                continue
            package = self._load_package(root)
            self.packages[package.platform_id] = package
        if not self.packages:
            raise RuntimeError("no platform packages were loaded")
        if self.default_platform not in self.packages:
            self.default_platform = next(iter(self.packages))

    def get(self, platform_id: str | None = None) -> PlatformPackage:
        if not self.packages:
            self.load()
        target = platform_id or self.default_platform
        return self.packages[target]

    def _load_package(self, root: Path) -> PlatformPackage:
        meta = yaml.safe_load(root.joinpath("platform.yaml").read_text(encoding="utf-8")) or {}
        platform_id = meta.get("id") or root.name
        self._validate_platform_layout(root, meta)
        knowledge_docs = self._load_knowledge(root / "knowledge", platform_id)
        rules = self._load_rule_bundle(root / "rules")
        prompts = self._load_prompts(root / "prompts")
        workflows = meta.get("workflow_nodes", {})
        adapter = self._load_adapter(root, platform_id)
        return PlatformPackage(
            platform_id=platform_id,
            root=root,
            meta=meta,
            knowledge_docs=knowledge_docs,
            rules=rules,
            prompts=prompts,
            workflows=workflows,
            adapter=adapter,
        )

    def _validate_platform_layout(self, root: Path, meta: dict[str, Any]) -> None:
        required_meta = ("id", "name", "default_locale", "enabled_routes", "workflow_nodes")
        missing_meta = [field for field in required_meta if not meta.get(field)]
        if missing_meta:
            raise RuntimeError(f"platform package {root.name} is missing required metadata: {', '.join(missing_meta)}")

        required_dirs = ("knowledge", "rules", "schemas", "prompts", "examples")
        missing_dirs = [name for name in required_dirs if not root.joinpath(name).exists()]
        if missing_dirs:
            raise RuntimeError(f"platform package {root.name} is missing required directories: {', '.join(missing_dirs)}")

        enabled_routes = set(meta.get("enabled_routes", []))
        workflow_nodes = meta.get("workflow_nodes", {})
        missing_workflows = [route for route in enabled_routes if route not in workflow_nodes]
        if missing_workflows:
            raise RuntimeError(
                f"platform package {root.name} is missing workflow node definitions for routes: {', '.join(missing_workflows)}"
            )

    def _load_knowledge(self, directory: Path, platform_id: str) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        if not directory.exists():
            return docs
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix == ".jsonl":
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    doc = json.loads(line)
                    doc.setdefault("platform", platform_id)
                    docs.append(doc)
            elif path.suffix in {".md", ".txt"}:
                content = path.read_text(encoding="utf-8")
                title = content.splitlines()[0].lstrip("# ").strip() if content.splitlines() else path.stem
                docs.append(
                    {
                        "id": f"{platform_id}-{path.stem}",
                        "title": title,
                        "content": content,
                        "tags": [path.stem],
                        "source_url": str(path.as_posix()),
                        "updated_at": None,
                        "platform": platform_id,
                    }
                )
        return docs

    def _load_rule_bundle(self, directory: Path) -> dict[str, Any]:
        bundle: dict[str, Any] = {}
        if not directory.exists():
            return bundle
        for path in sorted(directory.glob("*")):
            if path.suffix not in {".yaml", ".yml", ".json"}:
                continue
            if path.suffix == ".json":
                bundle[path.stem] = json.loads(path.read_text(encoding="utf-8"))
            else:
                bundle[path.stem] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return bundle

    def _load_prompts(self, directory: Path) -> dict[str, str]:
        prompts: dict[str, str] = {}
        if not directory.exists():
            return prompts
        for path in sorted(directory.glob("*")):
            if path.is_file():
                prompts[path.stem] = path.read_text(encoding="utf-8")
        return prompts

    def _load_adapter(self, root: Path, platform_id: str) -> BasePlatformAdapter | None:
        adapter_path = root / "adapters" / "status_adapter.py"
        if not adapter_path.exists():
            return None
        module_name = f"platform_adapter_{platform_id}"
        spec = importlib.util.spec_from_file_location(module_name, adapter_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"failed to load adapter for platform {platform_id}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        builder = getattr(module, "build_adapter", None)
        if builder is None:
            raise RuntimeError(f"adapter {adapter_path} does not export build_adapter()")
        return builder(platform_id)


registry = PlatformRegistry(settings.platforms_dir, settings.default_platform)
