"""Storage and Firestore database tools for LaunchKit."""

import datetime
import os
import re
from typing import Any
from google.cloud import firestore
from google.cloud import storage

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-415aeabf77b7")
BUCKET_NAME = os.getenv("LAUNCHKIT_BUCKET", "bwg3-qwiklabs-gcp-04-415aeabf77b7")

_db = None
_storage_client = None


def get_db() -> firestore.Client:
    """Lazy initialization of Firestore client."""
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def get_storage_client() -> storage.Client:
    """Lazy initialization of Cloud Storage client."""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client


def _slugify(text: str) -> str:
    """Convert text to a clean URL/ID slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "project"


def create_project(
    name: str,
    tagline: str,
    features: list[str],
    palette: dict[str, str],
) -> dict[str, Any]:
    """Create a new startup/project record in Firestore.

    Args:
        name: Name of the startup or app (e.g. 'StudyBuddy').
        tagline: Catchy one-line slogan.
        features: List of 3 key product features.
        palette: Dictionary of hex colors e.g. {"primary": "#7C3AED", "bg": "#0F0F14", "accent": "#38BDF8"}.

    Returns:
        Dictionary with project_id and confirmation details.
    """
    db = get_db()
    project_id = _slugify(name)
    doc_ref = db.collection("projects").document(project_id)

    data = {
        "name": name,
        "tagline": tagline,
        "features": features,
        "palette": palette,
        "current_version": 0,
        "public_url": f"/p/{project_id}",
        "assets": {},
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    doc_ref.set(data, merge=True)
    return {
        "status": "success",
        "project_id": project_id,
        "name": name,
        "tagline": tagline,
        "features": features,
        "palette": palette,
        "public_url": f"/p/{project_id}",
    }


def get_project(project_id: str) -> dict[str, Any]:
    """Retrieve details and metadata for an existing project.

    Args:
        project_id: The slug identifier of the project.

    Returns:
        Dictionary containing project data or an error message.
    """
    db = get_db()
    doc = db.collection("projects").document(project_id).get()
    if not doc.exists:
        return {"error": f"Project '{project_id}' not found."}
    return doc.to_dict() or {}


def list_projects() -> list[dict[str, Any]]:
    """List all created projects in LaunchKit."""
    db = get_db()
    docs = db.collection("projects").stream()
    projects = []
    for doc in docs:
        d = doc.to_dict()
        d["project_id"] = doc.id
        projects.append(d)
    return projects


def save_page_version(
    project_id: str,
    html_content: str,
    change_note: str = "Initial generation",
) -> dict[str, Any]:
    """Save a new version of the project's landing page HTML to GCS and Firestore.

    Args:
        project_id: The slug identifier of the project.
        html_content: The full valid HTML string for the landing page.
        change_note: Short description of changes made (e.g. 'Added pricing & dark mode').

    Returns:
        Version number, GCS path, and public URL.
    """
    db = get_db()
    proj_ref = db.collection("projects").document(project_id)
    proj_doc = proj_ref.get()
    if not proj_doc.exists:
        return {"error": f"Project '{project_id}' does not exist. Call create_project first."}

    proj_data = proj_doc.to_dict() or {}
    new_version = int(proj_data.get("current_version", 0)) + 1

    # Upload versioned HTML and latest HTML to Cloud Storage
    client = get_storage_client()
    bucket = client.bucket(BUCKET_NAME)

    version_path = f"{project_id}/site/v{new_version}/index.html"
    latest_path = f"{project_id}/site/latest/index.html"

    v_blob = bucket.blob(version_path)
    v_blob.upload_from_string(html_content, content_type="text/html")

    latest_blob = bucket.blob(latest_path)
    latest_blob.upload_from_string(html_content, content_type="text/html")

    # Record version in Firestore subcollection
    version_doc = {
        "version": new_version,
        "change_note": change_note,
        "gcs_path": f"gs://{BUCKET_NAME}/{version_path}",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    proj_ref.collection("versions").document(f"v{new_version}").set(version_doc)

    # Update project current version
    proj_ref.update({
        "current_version": new_version,
        "latest_html_path": f"gs://{BUCKET_NAME}/{latest_path}",
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

    return {
        "status": "success",
        "project_id": project_id,
        "version": new_version,
        "public_url": f"/p/{project_id}",
        "change_note": change_note,
    }


def add_waitlist_signup(
    project_id: str,
    email: str,
    name: str = "",
) -> dict[str, Any]:
    """Add a verified subscriber to the project's waitlist.

    Args:
        project_id: The slug identifier of the project.
        email: Email address of the subscriber.
        name: Optional subscriber name.

    Returns:
        Confirmation dictionary or error if invalid/duplicate.
    """
    email_clean = email.strip().lower()
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email_clean):
        return {"error": f"Invalid email format: '{email}'."}

    db = get_db()
    signups_ref = db.collection("projects").document(project_id).collection("signups")

    # Prevent duplicate emails
    existing = signups_ref.where("email", "==", email_clean).limit(1).get()
    if len(existing) > 0:
        return {"status": "already_registered", "message": f"{email_clean} is already on the waitlist!"}

    doc_ref = signups_ref.document()
    doc_ref.set({
        "email": email_clean,
        "name": name.strip(),
        "source": "web",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

    return {
        "status": "success",
        "project_id": project_id,
        "email": email_clean,
        "message": f"Successfully joined waitlist for {project_id}!",
    }


def get_signups(project_id: str) -> dict[str, Any]:
    """Retrieve all waitlist signups for a given project.

    Args:
        project_id: The slug identifier of the project.

    Returns:
        Total count and list of signups with emails and timestamps.
    """
    db = get_db()
    docs = (
        db.collection("projects")
        .document(project_id)
        .collection("signups")
        .order_by("created_at")
        .stream()
    )
    signups = []
    for doc in docs:
        data = doc.to_dict()
        signups.append({
            "id": doc.id,
            "email": data.get("email"),
            "name": data.get("name", ""),
            "created_at": data.get("created_at"),
        })
    return {
        "project_id": project_id,
        "total_signups": len(signups),
        "signups": signups,
    }
