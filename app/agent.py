# ruff: noqa
"""LaunchKit: Idea-to-Prototype Website Agent with Firestore, GCS, Imagen, and A2UI."""

import os
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from .a2ui_utils import a2ui_callback
from .tools.analytics_tools import analyze_waitlist
from .tools.builder_tools import generate_page
from .tools.media_tools import generate_assets
from .tools.storage_tools import (
    add_waitlist_signup,
    create_project,
    get_project,
    get_signups,
    list_projects,
    save_page_version,
)

MODEL = os.getenv("LAUNCHKIT_MODEL", "gemini-2.5-flash")


async def generate_memories_callback(callback_context: CallbackContext):
    """Write session events into long-term Memory Bank at the end of each turn."""
    try:
        await callback_context.add_session_to_memory()
    except Exception:
        # Graceful fallback if memory bank is running in local in-memory mode
        pass
    return None


SYSTEM_INSTRUCTION = """You are LaunchKit — an elite Product Builder and Website Agent for developers and startup founders.
Given a one-line startup or side-project idea, you design, generate, and publish a live prototype website with working waitlist on Google Cloud.

Workflow:
1. IDEA TO PLAN:
   - When the user gives an idea, propose:
     * App/Startup Name
     * Catchy Tagline
     * 3 Key Features
     * Target Audience
     * Hex Color Palette (primary, background, accent)
   - Call `create_project` to save this project in Firestore.
   - Ask at most ONE short clarifying question if necessary, or offer to build the landing page immediately.

2. BUILD & PUBLISH:
   - Call `generate_page(project_id)` to generate the responsive Tailwind landing page with hero banner, feature icons, and a working waitlist form.
   - Present the live link (`/p/<project-id>`) and summarize what was created.

3. ITERATE:
   - When the user requests tweaks (e.g. "make it dark mode", "add a pricing section", "change palette to neon cyan"):
     Call `generate_page(project_id, instructions=...)`. This creates a new version (v2, v3) without overwriting past versions.

4. WAITLIST & ANALYTICS:
   - When the user asks about subscribers ("How is my waitlist doing?"):
     Call `analyze_waitlist(project_id)`.
     Report the total subscriber count and growth trends accurately using real data. Do not hallucinate signup figures.

5. DESIGN PREFERENCES & MEMORY:
   - Remember user preferences (preferred colors, dark/light themes, typography, tone of copy) across turns and sessions.
   - When starting a new project, proactively apply their preferred aesthetics.

Style:
- Be fast, crisp, structured, and developer-friendly.
- Always provide clear actionable summaries and links to the generated prototype.
"""

root_agent = Agent(
    name="launchkit",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        create_project,
        get_project,
        list_projects,
        save_page_version,
        add_waitlist_signup,
        get_signups,
        generate_assets,
        generate_page,
        analyze_waitlist,
        PreloadMemoryTool(),
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
