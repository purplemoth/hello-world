"""Todoist connection: your to-do list and your 'Remember' list.

Things to remember are stored as tasks in a Todoist project called "Remember",
split into sections (People, Dates, Ideas, Home, Health, Other).
"""

import os

import requests
from anthropic import beta_tool

API = "https://api.todoist.com/api/v1"
MEMORY_PROJECT = "Remember"
MEMORY_SECTIONS = ["People", "Dates", "Ideas", "Home", "Health", "Other"]


def _headers():
    return {"Authorization": f"Bearer {os.environ['TODOIST_API_TOKEN']}"}


def _get_all(path, params=None):
    """Fetch every page of a Todoist list."""
    params = dict(params or {})
    items = []
    while True:
        r = requests.get(f"{API}{path}", headers=_headers(), params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return items + data
        items += data.get("results", [])
        cursor = data.get("next_cursor")
        if not cursor:
            return items
        params["cursor"] = cursor


def _post(path, body=None):
    r = requests.post(f"{API}{path}", headers=_headers(), json=body or {}, timeout=30)
    r.raise_for_status()
    return r.json() if r.content else {}


def _memory_ids():
    """Find (or create) the Remember project and its sections."""
    project = next((p for p in _get_all("/projects") if p["name"] == MEMORY_PROJECT), None)
    if project is None:
        project = _post("/projects", {"name": MEMORY_PROJECT})
    sections = {s["name"]: s["id"] for s in _get_all("/sections", {"project_id": project["id"]})}
    for name in MEMORY_SECTIONS:
        if name not in sections:
            sections[name] = _post("/sections", {"name": name, "project_id": project["id"]})["id"]
    return project["id"], sections


def _describe(task, section_names=None):
    line = f"- {task['content']} (id {task['id']})"
    if section_names and task.get("section_id") in section_names:
        line += f" [{section_names[task['section_id']]}]"
    if task.get("due"):
        line += f" - due {task['due'].get('string') or task['due'].get('date')}"
    if task.get("description"):
        line += f"\n    {task['description']}"
    return line


@beta_tool
def remember(item: str, category: str = "Other", details: str = "", remind_on: str = "") -> str:
    """Save something to the user's 'Remember' list in Todoist.

    Args:
        item: The thing to remember, short and clear, e.g. "Sarah's birthday - 3 March".
        category: One of People, Dates, Ideas, Home, Health, Other.
        details: Optional longer notes.
        remind_on: Optional date in plain English for a reminder, e.g. "every 3 March" or "next Friday".
    """
    project_id, sections = _memory_ids()
    body = {
        "content": item,
        "project_id": project_id,
        "section_id": sections.get(category, sections["Other"]),
    }
    if details:
        body["description"] = details
    if remind_on:
        body["due_string"] = remind_on
        body["due_lang"] = "en"
    _post("/tasks", body)
    return f"Saved to Remember > {category}: {item}"


@beta_tool
def recall(search: str = "") -> str:
    """Look through the user's 'Remember' list. Leave search empty to list everything.

    Args:
        search: Optional word or phrase to look for, e.g. "birthday" or "Sarah".
    """
    project_id, sections = _memory_ids()
    names = {v: k for k, v in sections.items()}
    tasks = _get_all("/tasks", {"project_id": project_id})
    if search:
        s = search.lower()
        tasks = [t for t in tasks if s in t["content"].lower() or s in (t.get("description") or "").lower()]
    if not tasks:
        return "Nothing found in the Remember list."
    return "\n".join(_describe(t, names) for t in tasks)


@beta_tool
def list_tasks(filter: str = "today | overdue") -> str:
    """List the user's Todoist to-dos using a Todoist filter.

    Args:
        filter: A Todoist filter, e.g. "today | overdue", "7 days", "#Shopping", "p1", "all".
    """
    if filter.strip().lower() == "all":
        tasks = _get_all("/tasks")
    else:
        tasks = _get_all("/tasks/filter", {"query": filter})
    if not tasks:
        return f"No tasks match '{filter}'."
    return "\n".join(_describe(t) for t in tasks[:100])


@beta_tool
def add_task(content: str, due: str = "", project: str = "", priority: int = 1, notes: str = "") -> str:
    """Add a to-do to Todoist. Only call this after the user has said yes to the exact wording.

    Args:
        content: What needs doing, e.g. "Book theatre tickets".
        due: Optional due date in plain English, e.g. "tomorrow 9am", "every Monday".
        project: Optional Todoist project name. Leave empty for the Inbox.
        priority: 1 (normal) to 4 (most urgent).
        notes: Optional extra detail.
    """
    body = {"content": content, "priority": max(1, min(priority, 4))}
    if due:
        body["due_string"] = due
        body["due_lang"] = "en"
    if notes:
        body["description"] = notes
    if project:
        match = next((p for p in _get_all("/projects") if p["name"].lower() == project.lower()), None)
        if match is None:
            return f"There is no Todoist project called '{project}'. Ask the user which project to use."
        body["project_id"] = match["id"]
    task = _post("/tasks", body)
    return f"Added to Todoist: {content}" + (f" (due {task['due']['string']})" if task.get("due") else "")


@beta_tool
def complete_task(task_id: str) -> str:
    """Tick off a Todoist task (or Remember item) as done. Only after the user confirms.

    Args:
        task_id: The task id shown in list_tasks or recall results.
    """
    _post(f"/tasks/{task_id}/close")
    return "Marked as done. (It can be restored from Todoist's 'Completed' view if needed.)"


TOOLS = [remember, recall, list_tasks, add_task, complete_task]
