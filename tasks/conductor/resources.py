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
        # Element types before any set operation: an unhashable element
        # (a nested list, say) would raise a raw TypeError from set().
        if not isinstance(manifest, (list, tuple)):
            raise InfrastructureError("manifest must be a list of handles")
        for handle in manifest:
            if not isinstance(handle, str) or not is_handle(handle):
                raise InfrastructureError(f"malformed handle {handle!r}")
        # Cardinality before set comparison: a manifest repeating a handle
        # compares equal as a set but would render its payload twice.
        if len(set(manifest)) != len(manifest):
            raise InfrastructureError(f"duplicate handles in manifest "
                                      f"{manifest}")
        if not isinstance(registry_json, dict) \
                or set(manifest) != set(registry_json):
            raise InfrastructureError("manifest keys != registry keys")
        self.manifest = list(manifest)
        # A null or incomplete resource object would otherwise surface as a
        # raw AttributeError/KeyError from the deserializer, without saying
        # which handle was at fault.
        resources = {}
        for handle, obj in registry_json.items():
            if not isinstance(obj, dict):
                raise InfrastructureError(
                    f"{handle}: resource must be an object, got {obj!r}")
            try:
                resources[handle] = resource_from_json(obj)
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                raise InfrastructureError(
                    f"{handle}: malformed resource ({exc})") from exc
        self._resources = resources

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
