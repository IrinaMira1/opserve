from datetime import datetime
from typing import Any, Dict


class BaseConnector:
    """Abstract interface all connectors must implement.

    A connector fetches structured operational data from a source
    (Trello, Google Calendar, Gmail, Sheets, meeting notes, etc.)
    and returns it in a standard format for the Context Collector agent.
    """

    source_name: str = "unknown"

    async def fetch(self, project_id: str, since: datetime | None = None) -> dict:
        """Fetch structured data from the source.

        Args:
            project_id: Which project to fetch data for
            since: Only return items changed since this time (optional)

        Returns:
            dict with standardized structure:
            {
                "tasks": [...],
                "events": [...],
                "messages": [...],
                "notes": [...],
                "documents": [...],
                "errors": [...]
            }
        """
        raise NotImplementedError

    def is_configured(self) -> bool:
        """Check if connector has credentials/config available."""
        raise NotImplementedError

    def get_status(self) -> str:
        """Return human-readable status (e.g., 'Connected', 'Not configured', 'Error')."""
        return "Not implemented"
