"""Media and visual generation tools for LaunchKit."""

import os
from typing import Any
from google import genai
from .storage_tools import BUCKET_NAME, PROJECT_ID, get_db, get_project, get_storage_client

_genai_client = None


def get_genai_client(location: str = "global") -> genai.Client:
    """Initialize Vertex AI GenAI client in global region for Nano Banana 2 Lite."""
    return genai.Client(vertexai=True, project=PROJECT_ID, location=location)


def generate_image(
    prompt: str,
    project_id: str = "default",
    asset_name: str = "hero",
    tool_context: Any = None,
) -> dict[str, Any]:
    """Generate an image using gemini-3.1-flash-lite-image (Nano Banana 2 Lite).

    Saves the image to the local Playground artifacts panel and uploads it to public Cloud Storage.

    Args:
        prompt: Text prompt describing the image to generate.
        project_id: Project slug identifier for Cloud Storage destination.
        asset_name: Name of the asset (e.g. 'hero', 'preview', 'feature').
        tool_context: Optional ADK ToolContext for artifact saving.

    Returns:
        Dictionary containing the public Cloud Storage URL and status.
    """
    client = get_genai_client(location="global")
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
        )
        img_bytes = None
        mime_type = "image/jpeg"
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    img_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not img_bytes:
            raise ValueError("No image bytes returned by gemini-3.1-flash-lite-image")

        # 1. Save artifact if tool_context is provided
        if tool_context and hasattr(tool_context, "save_artifact"):
            try:
                from google.genai import types
                part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
                tool_context.save_artifact(f"{asset_name}.jpg", part)
            except Exception as e:
                print(f"[media_tools] save_artifact warning: {e}")

        # 2. Upload to public Cloud Storage bucket
        storage_client = get_storage_client()
        bucket = storage_client.bucket(BUCKET_NAME)
        object_path = f"{project_id}/images/{asset_name}.jpg"
        blob = bucket.blob(object_path)
        blob.upload_from_string(img_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{object_path}"

        # Update Firestore if project exists
        try:
            db = get_db()
            proj_ref = db.collection("projects").document(project_id)
            doc = proj_ref.get()
            if doc.exists:
                proj_ref.update({f"assets.{asset_name}": public_url})
        except Exception:
            pass

        return {
            "status": "success",
            "model": "gemini-3.1-flash-lite-image",
            "url": public_url,
            "asset_name": asset_name,
            "project_id": project_id,
        }
    except Exception as e:
        print(f"[media_tools] Image generation error: {e}")
        # Clean fallback to SVG banner if model request fails
        return {
            "status": "fallback",
            "error": str(e),
            "asset_name": asset_name,
            "project_id": project_id,
        }


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


def generate_assets(project_id: str, tool_context: Any = None) -> dict[str, Any]:
    """Generate visual brand assets (Nano Banana hero image, logo, and 3 feature icons) for a project.

    Uploads the created assets to Cloud Storage under <project_id>/images/ and updates Firestore.

    Args:
        project_id: The slug identifier of the project.
        tool_context: Optional ADK ToolContext for artifact saving.

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

    client = get_storage_client()
    bucket = client.bucket(BUCKET_NAME)

    assets = {}

    # 1. Generate Hero Image with Nano Banana 2 Lite (gemini-3.1-flash-lite-image)
    image_prompt = (
        f"A modern, high-tech, aesthetically stunning hero banner visual for '{name}', "
        f"a tech product with tagline '{tagline}'. Sleek futuristic product interface, "
        f"soft atmospheric lighting in {primary}, clean dark background, 8k render."
    )
    img_result = generate_image(
        prompt=image_prompt,
        project_id=project_id,
        asset_name="hero",
        tool_context=tool_context,
    )
    if img_result.get("status") == "success":
        assets["hero"] = img_result["url"]
    else:
        # Fallback to SVG banner
        hero_svg = _generate_svg_banner(name, tagline, primary, bg)
        hero_path = f"{project_id}/images/hero.svg"
        hero_blob = bucket.blob(hero_path)
        hero_blob.upload_from_string(hero_svg, content_type="image/svg+xml")
        assets["hero"] = f"https://storage.googleapis.com/{BUCKET_NAME}/{hero_path}"

    # 2. Upload Logo
    logo_svg = _generate_svg_logo(name, primary)
    logo_path = f"{project_id}/images/logo.svg"
    logo_blob = bucket.blob(logo_path)
    logo_blob.upload_from_string(logo_svg, content_type="image/svg+xml")
    assets["logo"] = f"https://storage.googleapis.com/{BUCKET_NAME}/{logo_path}"

    # 3. Upload 3 Feature Icons
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

