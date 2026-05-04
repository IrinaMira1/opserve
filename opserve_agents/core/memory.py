import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List


class CompanyMemory:
    """Shared context layer for all agents. NOT an agent itself.

    Stores operational context across projects:
    - decisions: past decisions with owner, date, outcome
    - risks: historical risks with severity, resolution, recurrence
    - action_items: open and closed action items
    - blockers: recurring blockers by project, owner, type
    - feedback: user feedback on recommendations
    - project_history: project snapshots and status changes
    """

    CATEGORIES = ["decisions", "risks", "action_items", "blockers", "feedback", "project_history"]

    def __init__(self):
        self.base_path = Path.home() / ".opserve" / "memory"
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _project_dir(self, project_id: str) -> Path:
        d = self.base_path / project_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _global_dir(self) -> Path:
        d = self.base_path / "_global"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def read(self, project_id: str, category: str) -> list:
        """Read category entries for a project."""
        if category not in self.CATEGORIES:
            return []
        f = self._project_dir(project_id) / f"{category}.json"
        if f.exists():
            return json.loads(f.read_text())
        return []

    def write(self, project_id: str, category: str, entries: list):
        """Write category entries for a project (replaces entire category)."""
        if category not in self.CATEGORIES:
            return
        f = self._project_dir(project_id) / f"{category}.json"
        f.write_text(json.dumps(entries, indent=2))

    def append(self, project_id: str, category: str, entry: dict):
        """Append a single entry to a category."""
        if category not in self.CATEGORIES:
            return
        entries = self.read(project_id, category)
        entries.append({**entry, "timestamp": datetime.utcnow().isoformat()})
        self.write(project_id, category, entries)

    def read_global(self, category: str) -> list:
        """Read category entries across all projects (cross-project view)."""
        if category not in self.CATEGORIES:
            return []
        f = self._global_dir() / f"{category}.json"
        if f.exists():
            return json.loads(f.read_text())
        return []

    def write_global(self, category: str, entries: list):
        """Write global category entries."""
        if category not in self.CATEGORIES:
            return
        f = self._global_dir() / f"{category}.json"
        f.write_text(json.dumps(entries, indent=2))

    def append_global(self, category: str, entry: dict):
        """Append a single entry to global category."""
        if category not in self.CATEGORIES:
            return
        entries = self.read_global(category)
        entries.append({**entry, "timestamp": datetime.utcnow().isoformat()})
        self.write_global(category, entries)

    def get_all_projects(self) -> list[str]:
        """Get list of all project IDs in memory."""
        if not self.base_path.exists():
            return []
        return [d.name for d in self.base_path.iterdir() if d.is_dir() and d.name != "_global"]

    def summary(self, project_id: str) -> dict:
        """Return recent entries per category for a project (last 3 per category)."""
        return {
            category: self.read(project_id, category)[-3:]
            for category in self.CATEGORIES
        }

    def search(self, keyword: str, project_id: str | None = None) -> list[dict]:
        """Search for keyword across all categories (simple substring match)."""
        results = []
        projects = [project_id] if project_id else self.get_all_projects()

        for proj in projects:
            for category in self.CATEGORIES:
                entries = self.read(proj, category)
                for entry in entries:
                    entry_str = json.dumps(entry).lower()
                    if keyword.lower() in entry_str:
                        results.append({
                            "project": proj,
                            "category": category,
                            "entry": entry
                        })
        return results


# Singleton shared across all agents
memory = CompanyMemory()
