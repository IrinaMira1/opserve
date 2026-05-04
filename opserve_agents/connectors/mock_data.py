from datetime import datetime, timedelta
from .base_connector import BaseConnector


class MockDataConnector(BaseConnector):
    """Demo connector for Project Atlas scenario.

    Returns realistic hardcoded data representing:
    - Trello cards
    - Google Calendar events
    - Gmail messages
    - Google Sheets row
    - AI meeting notes
    """

    source_name = "mock_data"

    async def fetch(self, project_id: str, since: datetime | None = None) -> dict:
        """Return Project Atlas demo scenario data."""

        if project_id != "Project Atlas":
            return {
                "tasks": [],
                "events": [],
                "messages": [],
                "notes": [],
                "documents": [],
                "errors": [f"Mock data only has 'Project Atlas'. Got '{project_id}'"]
            }

        now = datetime.utcnow()
        friday = now + timedelta(days=(4 - now.weekday()))  # Next Friday

        return {
            "tasks": [
                {
                    "id": "T-45",
                    "title": "Design review",
                    "owner": "Alice Johnson",
                    "due": friday.isoformat(),
                    "status": "In Progress",
                    "source": "trello",
                    "description": "Design review for milestone"
                },
                {
                    "id": "T-46",
                    "title": "Implementation complete",
                    "owner": "Bob Smith",
                    "due": friday.isoformat(),
                    "status": "In Progress",
                    "source": "trello",
                    "description": "Complete implementation of core feature"
                },
                {
                    "id": "T-47",
                    "title": "Validate supplier datasheet",
                    "owner": None,
                    "due": friday.isoformat(),
                    "status": "Blocked",
                    "source": "trello",
                    "description": "Critical dependency: requires supplier input file",
                    "dependency": "Waiting for supplier to send datasheet"
                }
            ],
            "events": [
                {
                    "id": "cal-1",
                    "title": "Project standup",
                    "owner": "Sarah Chen",
                    "time": friday.replace(hour=9, minute=0).isoformat(),
                    "duration_minutes": 30,
                    "source": "google_calendar"
                },
                {
                    "id": "cal-2",
                    "title": "Architecture review",
                    "owner": "Sarah Chen",
                    "time": friday.replace(hour=10, minute=30).isoformat(),
                    "duration_minutes": 60,
                    "source": "google_calendar"
                },
                {
                    "id": "cal-3",
                    "title": "1:1 with CEO",
                    "owner": "Sarah Chen",
                    "time": friday.replace(hour=14, minute=0).isoformat(),
                    "duration_minutes": 30,
                    "source": "google_calendar"
                },
                {
                    "id": "cal-4",
                    "title": "Budget review",
                    "owner": "Sarah Chen",
                    "time": friday.replace(hour=15, minute=0).isoformat(),
                    "duration_minutes": 60,
                    "source": "google_calendar"
                },
                {
                    "id": "cal-5",
                    "title": "Team retrospective",
                    "owner": "Sarah Chen",
                    "time": friday.replace(hour=16, minute=30).isoformat(),
                    "duration_minutes": 45,
                    "source": "google_calendar"
                },
                {
                    "id": "cal-6",
                    "title": "Free slot",
                    "owner": "Sarah Chen",
                    "time": friday.replace(hour=10, minute=0).isoformat(),
                    "duration_minutes": 30,
                    "available": True,
                    "source": "google_calendar"
                }
            ],
            "messages": [
                {
                    "id": "email-1",
                    "from": "supplier@vendor.com",
                    "to": "alice@company.com",
                    "subject": "RE: Datasheet request",
                    "timestamp": (now - timedelta(days=3)).isoformat(),
                    "body": "We have not yet sent the required input file. Will confirm by EOD Thursday.",
                    "source": "gmail",
                    "priority": "high",
                    "status": "unresolved"
                }
            ],
            "notes": [
                {
                    "id": "sheet-row-1",
                    "project": "Project Atlas",
                    "status": "In Progress",
                    "completion_percent": 40,
                    "milestone": "Friday Release",
                    "last_updated": (now - timedelta(days=2)).isoformat(),
                    "source": "google_sheets"
                }
            ],
            "documents": [
                {
                    "id": "meeting-1",
                    "title": "Wednesday Standup Notes",
                    "timestamp": (now - timedelta(days=2)).isoformat(),
                    "content": "Discussion: Supplier dependency for Project Atlas. Required datasheet from vendor. Action item: 'Confirm supplier status' — assigned to 'team' (no specific owner). Blocker: No confirmed owner for critical task #47.",
                    "source": "meeting_notes"
                }
            ],
            "errors": []
        }

    def is_configured(self) -> bool:
        return True

    def get_status(self) -> str:
        return "Mock data (demo only)"
