"""The assistant itself: Claude plus the Todoist and Google tools."""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic

import google_tools
import todoist_tools

MODEL = "claude-opus-5-5"
TOOLS = todoist_tools.TOOLS + google_tools.TOOLS

SYSTEM_PROMPT = """You are Vic's personal life assistant. Vic lives in the UK, works as a forensic \
social work manager in the NHS, and enjoys theatre, music and London events. This assistant is for \
PERSONAL life only - not NHS work or case information.

What you do:
- Keep Vic's "Remember" list in Todoist (people, dates, ideas, home, health, other). When Vic mentions \
something worth keeping, offer to save it, picking a sensible category and a reminder date if it is a \
date-based thing such as a birthday.
- Help plan: look at the calendar, to-dos and email together, spot clashes, and suggest a realistic plan.
- Read and search Gmail, and draft emails for Vic to review and send.

Safety rules - always follow these:
- Before adding or changing ANYTHING (a Remember item, a to-do, a calendar event, a draft, ticking \
something off), show Vic exactly what you are about to do and wait for a clear yes in their next message. \
The only exception is when Vic's own message already gives the exact details and says to go ahead.
- You can never send emails. You can only save drafts, which Vic sends themselves.
- You cannot delete anything. If Vic wants something deleted, tell them how to do it in the app.
- If Vic shares details that look like NHS service user or case information, gently point out that \
this assistant is for personal life and do not save it.

Style: plain, warm, direct British English with British spelling. Keep replies short. Use bullet \
points only for lists such as a day's plan. Explain any technical term in everyday words."""


def _client():
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def chat(messages: list) -> str:
    """Send the conversation to Claude, let it use tools, and return its reply.

    `messages` is the running conversation; it is updated in place so the
    next turn carries everything that happened, including tool use.
    """
    now = datetime.now(ZoneInfo(os.environ.get("TIME_ZONE", "Europe/London")))
    # The date goes in a short system message after the user's turn so the
    # main instructions stay identical between requests (cheaper caching).
    messages.append({"role": "system", "content": f"Right now it is {now:%A %d %B %Y, %H:%M}."})

    runner = _client().beta.messages.tool_runner(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=messages,
        output_config={"effort": "medium"},
        # If Claude declines a request for safety reasons, retry on a suitable fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        cache_control={"type": "ephemeral"},
    )

    last = None
    for message in runner:
        last = message
        messages.append({"role": "assistant", "content": message.content})
        tool_response = runner.generate_tool_call_response()
        if tool_response is not None:
            messages.append(tool_response)

    if last is None:
        return "Sorry, I didn't get a reply. Please try again."
    if last.stop_reason == "refusal":
        return "Sorry, I can't help with that one."
    text = "".join(block.text for block in last.content if block.type == "text").strip()
    return text or "Done."
