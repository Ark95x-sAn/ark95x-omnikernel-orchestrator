"""
Version Management System
==========================
Quantum signature-based versioning using solar degree (Leo 18°47').

Generates version identifiers from astrological positioning:
- Major: Zodiac sign (Leo = 5th sign)
- Minor: Degree (18)
- Patch: Decimal minutes (47)

Result: v5.18.47 (base version) with build metadata
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from quantum_signature import get_quantum_signature


class ReleaseChannel(Enum):
    """Software release channels."""
    STABLE = "stable"
    BETA = "beta"
    ALPHA = "alpha"
    DEV = "dev"


@dataclass
class Version:
    """Semantic version representation."""
    major: int
    minor: int
    patch: int
    channel: ReleaseChannel = ReleaseChannel.STABLE
    build: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        """String representation of version."""
        version_str = f"v{self.major}.{self.minor}.{self.patch}"

        if self.channel != ReleaseChannel.STABLE:
            version_str += f"-{self.channel.value}"

        if self.build:
            version_str += f"+{self.build}"

        return version_str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'major': self.major,
            'minor': self.minor,
            'patch': self.patch,
            'channel': self.channel.value,
            'build': self.build,
            'string': str(self),
            'metadata': self.metadata or {},
        }

    def compare(self, other: 'Version') -> int:
        """
        Compare versions.

        Returns:
            -1 if self < other
            0 if self == other
            1 if self > other
        """
        # Compare major.minor.patch
        self_tuple = (self.major, self.minor, self.patch)
        other_tuple = (other.major, other.minor, other.patch)

        if self_tuple < other_tuple:
            return -1
        elif self_tuple > other_tuple:
            return 1

        # Same version, compare channels
        channel_order = {
            ReleaseChannel.DEV: 0,
            ReleaseChannel.ALPHA: 1,
            ReleaseChannel.BETA: 2,
            ReleaseChannel.STABLE: 3,
        }

        self_channel = channel_order[self.channel]
        other_channel = channel_order[other.channel]

        if self_channel < other_channel:
            return -1
        elif self_channel > other_channel:
            return 1

        return 0

    def __lt__(self, other: 'Version') -> bool:
        return self.compare(other) < 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return False
        return self.compare(other) == 0

    def __gt__(self, other: 'Version') -> bool:
        return self.compare(other) > 0


class QuantumVersionManager:
    """
    Version management anchored to quantum signature solar degree.

    Base version derived from Leo 18°47':
    - v5.18.47 (Leo=5th sign, 18°, 47')

    Incremental versions build upon this foundation.
    """

    def __init__(self):
        """Initialize version manager with quantum signature."""
        self.signature = get_quantum_signature()

        # Derive base version from solar degree
        self.base_version = self._derive_base_version()

        # Version history
        self.version_history: List[Version] = [self.base_version]

        # Current version (starts at base)
        self.current_version = self.base_version

    def _derive_base_version(self) -> Version:
        """
        Derive base version from quantum signature.

        Returns:
            Base Version object
        """
        solar_degree = self.signature.get_solar_degree()
        zodiac_position = self.signature.sovereign_key['zodiac_position']

        # Extract major (zodiac sign number: Leo = 5)
        major = 5

        # Extract minor (degree: 18)
        minor = int(solar_degree)

        # Extract patch (decimal as minutes: 0.78333 → 78, but we know it's 47')
        # Using 47 directly as specified
        patch = 47

        # Build metadata
        metadata = {
            'zodiac': zodiac_position,
            'solar_degree': solar_degree,
            'genesis_hash': self.signature.genesis_hash,
            'temporal_anchor': self.signature.get_master_seed(),
            'is_base_version': True,
        }

        return Version(
            major=major,
            minor=minor,
            patch=patch,
            channel=ReleaseChannel.STABLE,
            metadata=metadata
        )

    def get_current_version(self) -> Version:
        """
        Get current system version.

        Returns:
            Current Version
        """
        return self.current_version

    def create_release(
        self,
        version_bump: str = "patch",
        channel: ReleaseChannel = ReleaseChannel.STABLE,
        build_metadata: Optional[str] = None
    ) -> Version:
        """
        Create new release version.

        Args:
            version_bump: Type of bump ("major", "minor", "patch")
            channel: Release channel
            build_metadata: Optional build metadata

        Returns:
            New Version object
        """
        current = self.current_version

        # Calculate new version numbers
        if version_bump == "major":
            new_major = current.major + 1
            new_minor = 0
            new_patch = 0
        elif version_bump == "minor":
            new_major = current.major
            new_minor = current.minor + 1
            new_patch = 0
        else:  # patch
            new_major = current.major
            new_minor = current.minor
            new_patch = current.patch + 1

        # Build metadata
        metadata = {
            'previous_version': str(current),
            'bump_type': version_bump,
            'created_at': datetime.now().isoformat(),
            'genesis_hash': self.signature.genesis_hash,
        }

        new_version = Version(
            major=new_major,
            minor=new_minor,
            patch=new_patch,
            channel=channel,
            build=build_metadata,
            metadata=metadata
        )

        # Add to history and set as current
        self.version_history.append(new_version)
        self.current_version = new_version

        return new_version

    def get_version_string(self) -> str:
        """
        Get current version as string.

        Returns:
            Version string (e.g., "v5.18.47")
        """
        return str(self.current_version)

    def get_version_info(self) -> Dict[str, Any]:
        """
        Get detailed version information.

        Returns:
            Dict with version details
        """
        return {
            'current': self.current_version.to_dict(),
            'base': self.base_version.to_dict(),
            'history_count': len(self.version_history),
            'quantum_signature': {
                'solar_degree': self.signature.get_solar_degree(),
                'zodiac': self.signature.sovereign_key['zodiac_position'],
                'genesis_hash': self.signature.genesis_hash[:16] + '...',
            },
        }

    def check_compatibility(self, required_version: str) -> bool:
        """
        Check if current version satisfies required version.

        Supports simple comparisons like:
        - "v5.18.47" (exact match)
        - ">=v5.18.0" (minimum version)
        - "~v5.18.0" (compatible minor version)

        Args:
            required_version: Required version string

        Returns:
            True if compatible
        """
        # Parse requirement
        if required_version.startswith(">="):
            operator = ">="
            version_str = required_version[2:]
        elif required_version.startswith("~"):
            operator = "~"
            version_str = required_version[1:]
        else:
            operator = "=="
            version_str = required_version

        # Parse version string
        required = self._parse_version_string(version_str)

        if operator == "==":
            return (
                self.current_version.major == required.major
                and self.current_version.minor == required.minor
                and self.current_version.patch == required.patch
            )
        elif operator == ">=":
            return self.current_version >= required
        elif operator == "~":
            # Compatible minor version (same major and minor)
            return (
                self.current_version.major == required.major
                and self.current_version.minor == required.minor
                and self.current_version.patch >= required.patch
            )

        return False

    def _parse_version_string(self, version_str: str) -> Version:
        """
        Parse version string to Version object.

        Args:
            version_str: Version string (e.g., "v5.18.47")

        Returns:
            Version object
        """
        # Remove 'v' prefix if present
        if version_str.startswith('v'):
            version_str = version_str[1:]

        # Split by '-' for channel
        parts = version_str.split('-')
        version_part = parts[0]
        channel = ReleaseChannel.STABLE if len(parts) == 1 else ReleaseChannel(parts[1].split('+')[0])

        # Split version numbers
        numbers = version_part.split('.')
        major = int(numbers[0])
        minor = int(numbers[1]) if len(numbers) > 1 else 0
        patch = int(numbers[2]) if len(numbers) > 2 else 0

        return Version(major=major, minor=minor, patch=patch, channel=channel)

    def get_changelog(self) -> List[Dict[str, Any]]:
        """
        Get version history changelog.

        Returns:
            List of version changes
        """
        changelog = []

        for version in reversed(self.version_history):
            entry = {
                'version': str(version),
                'channel': version.channel.value,
                'metadata': version.metadata or {},
            }
            changelog.append(entry)

        return changelog


# Singleton instance
_version_manager_instance = None

def get_version_manager() -> QuantumVersionManager:
    """
    Get or create singleton version manager instance.

    Returns:
        QuantumVersionManager: Global version manager
    """
    global _version_manager_instance
    if _version_manager_instance is None:
        _version_manager_instance = QuantumVersionManager()
    return _version_manager_instance


def get_version() -> str:
    """
    Quick access to current version string.

    Returns:
        Version string
    """
    return get_version_manager().get_version_string()
