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
def _resolve_project_id() -> str:
    proj = os.environ.get("LAUNCHKIT_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT") or "qwiklabs-gcp-04-415aeabf77b7"
    if proj.isdigit():
        return "qwiklabs-gcp-04-415aeabf77b7"
    return proj

PROJECT_ID = _resolve_project_id()
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
    project_id: Optional[str] = None
    email: str
    name: Optional[str] = None
    source: Optional[str] = "landing_page"


@app.post("/api/signup")
async def waitlist_signup(req: SignupRequest, request: Request, project: Optional[str] = None):
    """Save user waitlist signup directly to Cloud Firestore."""
    target_project = req.project_id or project or request.query_params.get("project")
    if not target_project:
        raise HTTPException(status_code=400, detail="A valid project ID is required.")
    if not req.email or "@" not in req.email:
        raise HTTPException(status_code=400, detail="A valid email address is required.")
    db = get_db()
    proj_ref = db.collection("projects").document(target_project)
    proj_doc = proj_ref.get()
    if not proj_doc.exists:
        raise HTTPException(
            status_code=404, detail=f"Project '{target_project}' does not exist."
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
        "message": f"Thanks for joining! You are on the waitlist for {target_project}.",
        "signup_id": signup_id,
        "created_at": now_iso,
    }


@app.get("/p/{project_id}", response_class=HTMLResponse)
async def serve_project_page(project_id: str):
    """Serve the latest published responsive HTML landing page for project_id."""
    client = get_storage()
    bucket = client.bucket(BUCKET_NAME)

    # 1. Prefer Firestore project doc current_version to guarantee latest content
    db = get_db()
    proj_doc = db.collection("projects").document(project_id).get()
    if proj_doc.exists:
        data = proj_doc.to_dict() or {}
        curr_v = data.get("current_version")
        if curr_v:
            v_blob = bucket.blob(f"{project_id}/site/v{curr_v}/index.html")
            if v_blob.exists():
                return HTMLResponse(
                    content=v_blob.download_as_text(),
                    status_code=200,
                    headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
                )

    # 2. Fallback to reading latest HTML directly from GCS
    latest_blob = bucket.blob(f"{project_id}/site/latest/index.html")
    if latest_blob.exists():
        content = latest_blob.download_as_text()
        return HTMLResponse(
            content=content,
            status_code=200,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

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
            detail=f"Version v{version_num} for project '{project_id}' not found.",
        )
    return HTMLResponse(
        content=blob.download_as_text(),
        status_code=200,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


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
    out: list[dict] = []
    if not parts:
        return out

    for p in parts:
        root = getattr(p, "root", p)

        # 1. Text extraction
        text = getattr(root, "text", None) or getattr(p, "text", None)
        if text:
            # Check if text contains wrapped A2UI JSON
            a2ui_matches = re.findall(
                r"<a2a_datapart_json>(.*?)</a2a_datapart_json>",
                text,
                re.DOTALL,
            )
            if a2ui_matches:
                for m in a2ui_matches:
                    try:
                        parsed = json.loads(m)
                        payload = parsed.get("data", parsed)
                        out.append({"kind": "a2ui", "data": payload})
                    except Exception:
                        pass
                clean_text = re.sub(
                    r"<a2a_datapart_json>.*?</a2a_datapart_json>",
                    "",
                    text,
                    flags=re.DOTALL,
                ).strip()
                if clean_text:
                    out.append({"kind": "text", "text": clean_text})
            else:
                out.append({"kind": "text", "text": text})

        # 2. Data part (A2UI)
        data = getattr(root, "data", None) or getattr(p, "data", None)
        if data is not None:
            if isinstance(data, bytes):
                try:
                    data = json.loads(data.decode("utf-8"))
                except Exception:
                    pass
            meta = getattr(root, "metadata", None) or getattr(p, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if mime == _A2UI_MIME or (
                isinstance(data, dict)
                and any(
                    k in data
                    for k in ("beginRendering", "surfaceUpdate", "dataModelUpdate")
                )
            ):
                out.append({"kind": "a2ui", "data": data})

        # 3. File part or URI
        file_obj = getattr(root, "file", None) or getattr(p, "file", None)
        if file_obj:
            uri = getattr(file_obj, "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
        url = getattr(root, "url", None) or getattr(p, "url", None)
        if url and not text:
            out.append({"kind": "text", "text": url})

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
        return JSONResponse(
            {"parts": [{"kind": "text", "text": "Please provide an idea or message."}]}
        )

    parts: list[dict] = []

    # If deployed with AGENT_ENGINE_RESOURCE_NAME, use A2A client proxy
    if RESOURCE:
        try:
            import httpx
            from a2a.client import ClientConfig, ClientFactory
            import a2a.types as a2a_types

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
                    card = a2a_types.AgentCard(**resp.json())
                    card.url = a2a_base
                    _card = card

                # Build supported transports
                transports = []
                for t_name in ("jsonrpc", "http_json", "TRANSPORT_PROTOCOL_JSONRPC", "TRANSPORT_PROTOCOL_HTTP_JSON"):
                    if hasattr(a2a_types.TransportProtocol, t_name):
                        transports.append(getattr(a2a_types.TransportProtocol, t_name))

                factory = ClientFactory(
                    ClientConfig(
                        supported_transports=transports or [a2a_types.TransportProtocol.jsonrpc],
                        httpx_client=client,
                    )
                )
                a2a_client = factory.create(_card)

                # Determine part construction
                if hasattr(a2a_types, "TextPart"):
                    part_item = a2a_types.Part(root=a2a_types.TextPart(text=message))
                else:
                    part_item = a2a_types.Part(text=message)

                role_user = getattr(a2a_types.Role, "user", getattr(a2a_types.Role, "ROLE_USER", "user"))

                msg = a2a_types.Message(
                    message_id=str(uuid.uuid4()),
                    role=role_user,
                    parts=[part_item],
                    context_id=_contexts.get(user_id),
                )

                last_task = None
                async for event in a2a_client.send_message(msg):
                    if not isinstance(event, tuple):
                        continue
                    task, update = event
                    if task is not None:
                        last_task = task
                        if getattr(task, "context_id", None):
                            _contexts[user_id] = task.context_id

                    # 1. Handle TaskArtifactUpdateEvent
                    if isinstance(update, getattr(a2a_types, "TaskArtifactUpdateEvent", object)):
                        if hasattr(update, "artifact") and hasattr(update.artifact, "parts"):
                            parts.extend(_extract_parts_from_a2a(update.artifact.parts))

                    # 2. Handle TaskStatusUpdateEvent with status.message
                    if hasattr(update, "status") and hasattr(update.status, "message"):
                        msg_obj = update.status.message
                        if hasattr(msg_obj, "parts") and msg_obj.parts:
                            parts.extend(_extract_parts_from_a2a(msg_obj.parts))

                # Non-streaming fallback: inspect last_task
                if not parts and last_task is not None:
                    # Check task status message
                    if hasattr(last_task, "status") and hasattr(last_task.status, "message"):
                        msg_obj = last_task.status.message
                        if hasattr(msg_obj, "parts") and msg_obj.parts:
                            parts.extend(_extract_parts_from_a2a(msg_obj.parts))

                    # Check task artifacts
                    for artifact in getattr(last_task, "artifacts", None) or []:
                        parts.extend(_extract_parts_from_a2a(getattr(artifact, "parts", [])))

                    # Check task history
                    if not parts and hasattr(last_task, "history"):
                        for h_msg in getattr(last_task, "history", []):
                            h_role = str(getattr(h_msg, "role", "")).lower()
                            if "agent" in h_role:
                                parts.extend(_extract_parts_from_a2a(getattr(h_msg, "parts", [])))

        except Exception as exc:
            print(f"[A2A Chat Error] {type(exc).__name__}: {exc}", flush=True)
            parts = [{"kind": "text", "text": f"⚠️ Agent Runtime Error: {str(exc)}"}]
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
