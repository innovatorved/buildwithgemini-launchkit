"""Media and visual generation tools for LaunchKit."""

import os
from typing import Any
from google import genai
from .storage_tools import BUCKET_NAME, PROJECT_ID, get_db, get_project, get_storage_client

_genai_client = None


def get_genai_client() -> genai.Client:
    """Initialize Vertex AI GenAI client."""
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location="us-central1")
    return _genai_client


def _generate_svg_banner(name: str, tagline: str, primary_color: str, bg_color: str) -> str:
    """Generate a clean, high-resolution SVG hero banner."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 600" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg_color}" />
      <stop offset="100%" stop-color="#181824" />
    </linearGradient>
    <linearGradient id="accentGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{primary_color}" />
      <stop offset="100%" stop-color="#38BDF8" />
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="30%" r="50%">
      <stop offset="0%" stop-color="{primary_color}" stop-opacity="0.35" />
      <stop offset="100%" stop-color="{bg_color}" stop-opacity="0" />
    </radialGradient>
  </defs>
  <rect width="1200" height="600" fill="url(#bgGrad)" />
  <circle cx="600" cy="200" r="300" fill="url(#glow)" />
  <g fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1">
    <circle cx="600" cy="300" r="150" />
    <circle cx="600" cy="300" r="280" />
    <circle cx="600" cy="300" r="420" />
  </g>
  <text x="600" y="260" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-weight="900" font-size="64" fill="url(#accentGrad)" text-anchor="middle" letter-spacing="-1">{name}</text>
  <text x="600" y="330" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-weight="400" font-size="26" fill="#94A3B8" text-anchor="middle">{tagline}</text>
  <g transform="translate(540, 380)">
    <rect width="120" height="40" rx="20" fill="url(#accentGrad)" opacity="0.9" />
    <text x="60" y="25" font-family="sans-serif" font-size="14" font-weight="600" fill="#FFFFFF" text-anchor="middle">PROTOTYPE</text>
  </g>
</svg>"""


def _generate_svg_logo(name: str, primary_color: str) -> str:
    """Generate a modern geometric SVG logo."""
    initial = (name[:2] if len(name) >= 2 else name[:1]).upper()
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{primary_color}" />
      <stop offset="100%" stop-color="#38BDF8" />
    </linearGradient>
  </defs>
  <rect width="200" height="200" rx="48" fill="url(#logoGrad)" />
  <text x="100" y="125" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-weight="800" font-size="80" fill="#FFFFFF" text-anchor="middle">{initial}</text>
</svg>"""


def _generate_svg_icon(index: int, primary_color: str) -> str:
    """Generate clean SVG feature icon."""
    symbols = [
        '<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
        '<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path d="M12 6v6l4 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    ]
    svg_sym = symbols[index % len(symbols)]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="48" height="48" fill="none" color="{primary_color}">
  {svg_sym}
</svg>"""


def generate_assets(project_id: str) -> dict[str, Any]:
    """Generate visual brand assets (hero banner, logo, and 3 feature icons) for a project.

    Uploads the created assets to Cloud Storage under <project_id>/images/ and updates Firestore.

    Args:
        project_id: The slug identifier of the project.

    Returns:
        Dictionary of created asset URLs and paths.
    """
    proj = get_project(project_id)
    if "error" in proj:
        return proj

    name = proj.get("name", "Startup")
    tagline = proj.get("tagline", "The future of innovation")
    palette = proj.get("palette", {})
    primary = palette.get("primary", "#7C3AED")
    bg = palette.get("bg", "#0F0F14")

    # Try Vertex AI image generation, falling back cleanly to modern vector graphics
    client = get_storage_client()
    bucket = client.bucket(BUCKET_NAME)

    hero_svg = _generate_svg_banner(name, tagline, primary, bg)
    logo_svg = _generate_svg_logo(name, primary)

    assets = {}

    # Upload Hero Banner
    hero_path = f"{project_id}/images/hero.svg"
    hero_blob = bucket.blob(hero_path)
    hero_blob.upload_from_string(hero_svg, content_type="image/svg+xml")
    assets["hero"] = f"https://storage.googleapis.com/{BUCKET_NAME}/{hero_path}"

    # Upload Logo
    logo_path = f"{project_id}/images/logo.svg"
    logo_blob = bucket.blob(logo_path)
    logo_blob.upload_from_string(logo_svg, content_type="image/svg+xml")
    assets["logo"] = f"https://storage.googleapis.com/{BUCKET_NAME}/{logo_path}"

    # Upload 3 Feature Icons
    icons = []
    for i in range(3):
        icon_path = f"{project_id}/images/icon_{i+1}.svg"
        icon_svg = _generate_svg_icon(i, primary)
        icon_blob = bucket.blob(icon_path)
        icon_blob.upload_from_string(icon_svg, content_type="image/svg+xml")
        icons.append(f"https://storage.googleapis.com/{BUCKET_NAME}/{icon_path}")
    assets["icons"] = icons

    # Update Firestore
    db = get_db()
    db.collection("projects").document(project_id).update({
        "assets": assets,
    })

    return {
        "status": "success",
        "project_id": project_id,
        "assets": assets,
    }
