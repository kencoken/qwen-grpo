"""Instance-scoped resource registry and disclosure — plan contract 2.

Registries are instance-scoped: foreign handles never resolve. Disclosure is
action-controlled only; nothing here consults the reference program.
"""

from __future__ import annotations

from typing import Any

from .types import InfrastructureError, Resource, is_handle, resource_from_json


class InstanceRegistry:
    """One instance's private registry keyed by its public manifest."""

    def __init__(self, manifest: list[str],
                 registry_json: dict[str, dict[str, Any]]) -> None:
        if set(manifest) != set(registry_json):
            raise InfrastructureError("manifest keys != registry keys")
        for handle in manifest:
            if not is_handle(handle):
                raise InfrastructureError(f"malformed handle {handle!r}")
        self.manifest = list(manifest)
        self._resources = {h: resource_from_json(obj)
                           for h, obj in registry_json.items()}

    def resolve(self, handle: str) -> Resource | None:
        """None for any handle outside this instance (world failure, 0.5)."""
        return self._resources.get(handle)

    def payload_text(self, handle: str) -> str:
        resource = self._resources[handle]
        return resource.payload_text(handle)

    def union_payload_texts(self, handles: list[str] | None = None) -> list[str]:
        """Harness-only plural block (B3/B5, §1.11) in manifest order."""
        selected = self.manifest if handles is None else handles
        return [self.payload_text(h) for h in selected]
