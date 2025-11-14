"""Link service module with validation and reporting components."""

# Re-export submodules for direct access if needed
from docomatic.services.link.reporting import LinkReporter
from docomatic.services.link.validation import LinkValidator

__all__ = ["LinkValidator", "LinkReporter"]
