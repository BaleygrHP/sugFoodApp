from typing import Any, Dict, Optional, List
from datetime import datetime
import hashlib
import json


class PromptVersion:
    """Represents a version of a prompt template."""

    def __init__(
        self,
        template_name: str,
        version: str,
        content_hash: str,
        created_at: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.template_name = template_name
        self.version = version
        self.content_hash = content_hash
        self.created_at = created_at
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "template_name": self.template_name,
            "version": self.version,
            "content_hash": self.content_hash,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptVersion":
        """Create from dictionary representation."""
        return cls(
            template_name=data["template_name"],
            version=data["version"],
            content_hash=data["content_hash"],
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=data.get("metadata", {})
        )


class PromptVersionManager:
    """Manages versions of prompt templates."""

    def __init__(self):
        self.versions: Dict[str, PromptVersion] = {}
        self.version_counter: Dict[str, int] = {}

    def add_version(
        self,
        template_name: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PromptVersion:
        """
        Add a new version of a prompt template.

        Args:
            template_name: Name of the template
            content: Template content
            metadata: Optional metadata

        Returns:
            New PromptVersion instance
        """
        # Generate content hash
        content_hash = hashlib.md5(content.encode()).hexdigest()

        # Check if this content already exists
        for version in self.versions.values():
            if version.content_hash == content_hash and version.template_name == template_name:
                return version

        # Generate new version number
        if template_name not in self.version_counter:
            self.version_counter[template_name] = 0

        self.version_counter[template_name] += 1
        version_number = f"v{self.version_counter[template_name]}.0"

        # Create new version
        new_version = PromptVersion(
            template_name=template_name,
            version=version_number,
            content_hash=content_hash,
            created_at=datetime.now(),
            metadata=metadata or {}
        )

        # Store version
        version_key = f"{template_name}_{version_number}"
        self.versions[version_key] = new_version

        return new_version

    def get_version(self, template_name: str, version: str) -> Optional[PromptVersion]:
        """
        Get a specific version of a template.

        Args:
            template_name: Name of the template
            version: Version string

        Returns:
            PromptVersion instance or None if not found
        """
        version_key = f"{template_name}_{version}"
        return self.versions.get(version_key)

    def get_latest_version(self, template_name: str) -> Optional[PromptVersion]:
        """
        Get the latest version of a template.

        Args:
            template_name: Name of the template

        Returns:
            Latest PromptVersion instance or None if not found
        """
        template_versions = [
            v for v in self.versions.values()
            if v.template_name == template_name
        ]

        if not template_versions:
            return None

        return max(template_versions, key=lambda v: v.created_at)

    def list_versions(self, template_name: str) -> List[PromptVersion]:
        """
        List all versions of a template.

        Args:
            template_name: Name of the template

        Returns:
            List of PromptVersion instances
        """
        return [
            v for v in self.versions.values()
            if v.template_name == template_name
        ]

    def compare_versions(
        self,
        template_name: str,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """
        Compare two versions of a template.

        Args:
            template_name: Name of the template
            version1: First version to compare
            version2: Second version to compare

        Returns:
            Dictionary with comparison results
        """
        v1 = self.get_version(template_name, version1)
        v2 = self.get_version(template_name, version2)

        if not v1 or not v2:
            return {"error": "One or both versions not found"}

        comparison = {
            "template_name": template_name,
            "version1": v1.to_dict(),
            "version2": v2.to_dict(),
            "differences": {}
        }

        # Compare metadata
        for key in set(v1.metadata.keys()) | set(v2.metadata.keys()):
            if v1.metadata.get(key) != v2.metadata.get(key):
                comparison["differences"][key] = {
                    "version1": v1.metadata.get(key),
                    "version2": v2.metadata.get(key)
                }

        # Compare creation dates
        if v1.created_at != v2.created_at:
            comparison["differences"]["created_at"] = {
                "version1": v1.created_at.isoformat(),
                "version2": v2.created_at.isoformat()
            }

        return comparison


# Global version manager instance
_version_manager = PromptVersionManager()


def get_prompt_version(template_name: str, version: str) -> Optional[PromptVersion]:
    """
    Get a specific version of a prompt template.

    Args:
        template_name: Name of the template
        version: Version string

    Returns:
        PromptVersion instance or None if not found
    """
    return _version_manager.get_version(template_name, version)


def update_prompt_version(
    template_name: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> PromptVersion:
    """
    Update/create a version of a prompt template.

    Args:
        template_name: Name of the template
        content: Template content
        metadata: Optional metadata

    Returns:
        New PromptVersion instance
    """
    return _version_manager.add_version(template_name, content, metadata)


def get_latest_prompt_version(template_name: str) -> Optional[PromptVersion]:
    """
    Get the latest version of a prompt template.

    Args:
        template_name: Name of the template

    Returns:
        Latest PromptVersion instance or None if not found
    """
    return _version_manager.get_latest_version(template_name)


def list_prompt_versions(template_name: str) -> List[PromptVersion]:
    """
    List all versions of a prompt template.

    Args:
        template_name: Name of the template

    Returns:
        List of PromptVersion instances
    """
    return _version_manager.list_versions(template_name)


def compare_prompt_versions(
    template_name: str,
    version1: str,
    version2: str
) -> Dict[str, Any]:
    """
    Compare two versions of a prompt template.

    Args:
        template_name: Name of the template
        version1: First version to compare
        version2: Second version to compare

    Returns:
        Dictionary with comparison results
    """
    return _version_manager.compare_versions(template_name, version1, version2)
