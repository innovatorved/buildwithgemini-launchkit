"""LaunchKit FastAPI App and Web Proxy.

Serves:
  * /                  -> A2UI chat frontend builder
  * /chat              -> Proxies conversation to ADK agent (local InMemoryRunner or deployed A2A)
  * /p/{project_id}    -> Serves live generated landing pages from Cloud Storage
  * /api/signup        -> Waitlist signup endpoint that stores subscribers in Cloud Firestore
  * /api/projects      -> JSON list of all generated projects
"""

import datetime
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import google.auth
import google.auth.transport.requests
from google.cloud import firestore, storage
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ensure repo root is on sys.path for app imports
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

# Cloud config
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-415aeabf77b7")
BUCKET_NAME = os.environ.get("LAUNCHKIT_BUCKET", "bwg3-qwiklabs-gcp-04-415aeabf77b7")
RESOURCE = os.environ.get("AGENT_ENGINE_RESOURCE_NAME")
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")

# Lazy clients
_firestore_db = None
_storage_client = None


def get_db():
    global _firestore_db
    if _firestore_db is None:
        _firestore_db = firestore.Client(project=PROJECT_ID)
    return _firestore_db


def get_storage():
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client


app = FastAPI(
    title="LaunchKit Web & Proxy",
    description="Idea-to-Prototype Website Builder with Live Waitlist",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Waitlist Signup & Public Page Serving
# ---------------------------------------------------------------------------


class SignupRequest(BaseModel):
    project_id: str
    email: str
    name: Optional[str] = None
    source: Optional[str] = "landing_page"


@app.post("/api/signup")
async def waitlist_signup(req: SignupRequest):
    """Save user waitlist signup directly to Cloud Firestore."""
    if not req.email or "@" not in req.email:
        raise HTTPException(status_code=400, detail="A valid email address is required.")
    db = get_db()
    proj_ref = db.collection("projects").document(req.project_id)
    proj_doc = proj_ref.get()
    if not proj_doc.exists:
        raise HTTPException(
            status_code=404, detail=f"Project '{req.project_id}' does not exist."
        )

    signup_id = str(uuid.uuid4())
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    signup_data = {
        "signup_id": signup_id,
        "email": req.email,
        "name": req.name or "",
        "source": req.source or "landing_page",
        "created_at": now_iso,
    }

    proj_ref.collection("signups").document(signup_id).set(signup_data)
    return {
        "status": "success",
        "message": f"Thanks for joining! You are on the waitlist for {req.project_id}.",
        "signup_id": signup_id,
        "created_at": now_iso,
    }


@app.get("/p/{project_id}", response_class=HTMLResponse)
async def serve_project_page(project_id: str):
    """Serve the latest published responsive HTML landing page for project_id."""
    client = get_storage()
    bucket = client.bucket(BUCKET_NAME)

    # 1. Try reading latest HTML directly from GCS
    latest_blob = bucket.blob(f"{project_id}/site/latest/index.html")
    if latest_blob.exists():
        content = latest_blob.download_as_text()
        return HTMLResponse(content=content, status_code=200)

    # 2. Check Firestore project doc for version
    db = get_db()
    proj_doc = db.collection("projects").document(project_id).get()
    if proj_doc.exists:
        data = proj_doc.to_dict() or {}
        curr_v = data.get("current_version")
        if curr_v:
            v_blob = bucket.blob(f"{project_id}/site/v{curr_v}/index.html")
            if v_blob.exists():
                return HTMLResponse(content=v_blob.download_as_text(), status_code=200)

    # Not found placeholder
    not_found_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>LaunchKit — Project Not Found</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen flex items-center justify-center p-6">
    <div class="max-w-md w-full bg-slate-800 border border-slate-700 rounded-2xl p-8 text-center shadow-2xl">
        <div class="w-16 h-16 bg-indigo-500/10 text-indigo-400 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl font-bold">🚀</div>
        <h1 class="text-2xl font-bold mb-2">Project Not Found</h1>
        <p class="text-slate-400 mb-6">No prototype page has been generated yet for <span class="text-indigo-400 font-mono font-bold">'{project_id}'</span>.</p>
        <a href="/" class="inline-block bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-6 py-2.5 rounded-lg transition-colors">Open LaunchKit Builder</a>
    </div>
</body>
</html>"""
    return HTMLResponse(content=not_found_html, status_code=404)


@app.get("/p/{project_id}/v/{version_num}", response_class=HTMLResponse)
async def serve_project_version(project_id: str, version_num: int):
    """Serve a specific historic version of the landing page."""
    client = get_storage()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"{project_id}/site/v{version_num}/index.html")
    if not blob.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Version {version_num} for project '{project_id}' not found.",
        )
    return HTMLResponse(content=blob.download_as_text(), status_code=200)


@app.get("/api/projects")
async def list_all_projects():
    """API list of all generated projects."""
    db = get_db()
    docs = db.collection("projects").stream()
    result = []
    for doc in docs:
        d = doc.to_dict()
        d["project_id"] = doc.id
        result.append(d)
    return {"projects": result}


# ---------------------------------------------------------------------------
# Chat Proxy (A2A Deployed OR Local ADK InMemoryRunner)
# ---------------------------------------------------------------------------

_A2UI_MIME = "application/json+a2ui"
_contexts: dict[str, str] = {}
_card = None
_local_runner = None
_local_sessions: dict[str, str] = {}


def _extract_parts_from_a2a(parts: list) -> list[dict]:
    """Turn A2A response parts into structured parts for chat UI."""
    from a2a.types import FilePart, TextPart

    out: list[dict] = []
    for p in parts:
        root = getattr(p, "root", p)
        if isinstance(root, TextPart) and getattr(root, "text", None):
            out.append({"kind": "text", "text": root.text})
        elif getattr(root, "data", None) is not None:
            meta = getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if mime == _A2UI_MIME:
                out.append({"kind": "a2ui", "data": root.data})
        elif isinstance(root, FilePart):
            uri = getattr(getattr(root, "file", None), "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
    return out


async def _run_local_chat(message: str, user_id: str) -> list[dict]:
    """Fallback local chat runner using ADK InMemoryRunner and root_agent."""
    from app.agent import root_agent
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    global _local_runner
    if _local_runner is None:
        _local_runner = InMemoryRunner(agent=root_agent, app_name="launchkit")

    if user_id not in _local_sessions:
        session = await _local_runner.session_service.create_session(
            app_name=_local_runner.app_name, user_id=user_id
        )
        _local_sessions[user_id] = session.id

    session_id = _local_sessions[user_id]
    msg = types.Content(role="user", parts=[types.Part.from_text(text=message)])

    parts = []
    async for event in _local_runner.run_async(
        user_id=user_id, session_id=session_id, new_message=msg
    ):
        if event.content and event.content.parts:
            for p in event.content.parts:
                raw_text = getattr(p, "text", "") or ""
                inline_data = getattr(p, "inline_data", None)
                if inline_data and getattr(inline_data, "data", None):
                    try:
                        raw_text = inline_data.data.decode("utf-8")
                    except Exception:
                        pass

                # Parse A2UI JSON if wrapped
                a2ui_matches = re.findall(
                    r"<a2a_datapart_json>(.*?)</a2a_datapart_json>",
                    raw_text,
                    re.DOTALL,
                )
                if a2ui_matches:
                    for m in a2ui_matches:
                        try:
                            parsed = json.loads(m)
                            payload = parsed.get("data", parsed)
                            parts.append({"kind": "a2ui", "data": payload})
                        except Exception:
                            pass
                    clean_text = re.sub(
                        r"<a2a_datapart_json>.*?</a2a_datapart_json>",
                        "",
                        raw_text,
                        flags=re.DOTALL,
                    ).strip()
                    if clean_text:
                        parts.append({"kind": "text", "text": clean_text})
                elif raw_text:
                    parts.append({"kind": "text", "text": raw_text})

    return parts


@app.post("/chat")
async def chat(req: Request):
    """Handle chat requests from the browser UI."""
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"

    if not message:
        return JSONResponse({"parts": [{"kind": "text", "text": "Please provide an idea or message."}]})

    # If deployed with AGENT_ENGINE_RESOURCE_NAME, use A2A client proxy
    if RESOURCE:
        import httpx
        from a2a.client import ClientConfig, ClientFactory
        from a2a.types import (
            AgentCard,
            Message,
            Part,
            Role,
            TaskArtifactUpdateEvent,
            TextPart,
            TransportProtocol,
        )

        location = RESOURCE.split("/locations/")[1].split("/")[0]
        a2a_base = (
            f"https://{location}-aiplatform.googleapis.com/reasoningEngines/v1/"
            f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
        )
        a2a_card_url = f"{a2a_base}/.well-known/agent-card.json"

        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        creds.refresh(google.auth.transport.requests.Request())
        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(headers=headers, timeout=120) as client:
            global _card
            if _card is None:
                resp = await client.get(a2a_card_url)
                resp.raise_for_status()
                card = AgentCard(**resp.json())
                card.url = a2a_base
                _card = card

            factory = ClientFactory(
                ClientConfig(
                    supported_transports=[
                        TransportProtocol.jsonrpc,
                        TransportProtocol.http_json,
                    ],
                    httpx_client=client,
                )
            )
            a2a_client = factory.create(_card)

            msg = Message(
                message_id=str(uuid.uuid4()),
                role=Role.user,
                parts=[Part(root=TextPart(text=message))],
                context_id=_contexts.get(user_id),
            )

            parts = []
            last_task = None
            got_artifact_update = False
            async for event in a2a_client.send_message(msg):
                if not isinstance(event, tuple):
                    continue
                task, update = event
                if task is not None:
                    last_task = task
                    if getattr(task, "context_id", None):
                        _contexts[user_id] = task.context_id
                if isinstance(update, TaskArtifactUpdateEvent):
                    got_artifact_update = True
                    parts.extend(_extract_parts_from_a2a(update.artifact.parts))

            if not got_artifact_update and last_task is not None:
                for artifact in getattr(last_task, "artifacts", None) or []:
                    parts.extend(_extract_parts_from_a2a(artifact.parts))
    else:
        # Local direct mode
        parts = await _run_local_chat(message, user_id)

    if not parts:
        parts = [{"kind": "text", "text": "LaunchKit completed your request."}]

    return JSONResponse({"parts": parts})


# Mount static assets last
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
