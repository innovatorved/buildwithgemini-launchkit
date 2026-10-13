"""Website builder tools for LaunchKit."""

from typing import Any
from .storage_tools import get_project, save_page_version
from .media_tools import generate_assets


def _build_html_template(
    project_id: str,
    name: str,
    tagline: str,
    features: list[str],
    palette: dict[str, str],
    assets: dict[str, Any],
    extra_instructions: str = "",
) -> str:
    """Build a complete, responsive HTML landing page with Tailwind CSS."""
    primary = palette.get("primary", "#7C3AED")
    bg = palette.get("bg", "#0F0F14")
    accent = palette.get("accent", "#38BDF8")

    hero_img = assets.get("hero", "")
    logo_img = assets.get("logo", "")
    icons = assets.get("icons", ["", "", ""])

    feature_cards = ""
    for idx, feat in enumerate(features[:3]):
        icon_url = icons[idx] if idx < len(icons) else ""
        icon_html = (
            f'<img src="{icon_url}" class="w-10 h-10 mb-4" alt="Feature {idx+1}">'
            if icon_url
            else '<div class="w-10 h-10 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold mb-4">★</div>'
        )
        feature_cards += f"""
        <div class="bg-white/5 border border-white/10 backdrop-blur-md p-8 rounded-2xl hover:border-white/20 transition-all">
          {icon_html}
          <h3 class="text-xl font-bold text-white mb-2">{feat}</h3>
          <p class="text-slate-400 text-sm leading-relaxed">Built from the ground up to give you instant speed, reliable workflows, and seamless collaboration.</p>
        </div>
        """

    # Extra sections if requested
    extra_section = ""
    if "pricing" in extra_instructions.lower():
        extra_section = f"""
        <section id="pricing" class="py-16 max-w-5xl mx-auto px-6">
          <div class="text-center mb-12">
            <h2 class="text-3xl font-bold text-white">Simple, Transparent Pricing</h2>
            <p class="text-slate-400 mt-2">Get early access at launch pricing.</p>
          </div>
          <div class="grid md:grid-cols-2 gap-8 max-w-3xl mx-auto">
            <div class="bg-white/5 border border-white/10 p-8 rounded-2xl">
              <h3 class="text-xl font-bold text-white">Starter (Free)</h3>
              <p class="text-3xl font-extrabold text-white mt-4">$0 <span class="text-sm font-normal text-slate-400">/ forever</span></p>
              <ul class="text-slate-300 text-sm mt-6 space-y-3">
                <li>✓ Full core access</li>
                <li>✓ Community support</li>
              </ul>
            </div>
            <div class="bg-gradient-to-b from-indigo-900/40 to-white/5 border border-indigo-500/30 p-8 rounded-2xl relative">
              <span class="absolute top-4 right-4 text-xs font-bold uppercase tracking-wider bg-indigo-500 text-white px-2.5 py-1 rounded-full">Early Bird</span>
              <h3 class="text-xl font-bold text-white">Pro</h3>
              <p class="text-3xl font-extrabold text-white mt-4">$19 <span class="text-sm font-normal text-slate-400">/ mo</span></p>
              <ul class="text-slate-300 text-sm mt-6 space-y-3">
                <li>✓ Everything in Starter</li>
                <li>✓ Priority matching & AI assistance</li>
                <li>✓ Dedicated 24/7 support</li>
              </ul>
            </div>
          </div>
        </section>
        """

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name} — {tagline}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          colors: {{
            brand: '{primary}',
            brandBg: '{bg}',
            brandAccent: '{accent}',
          }}
        }}
      }}
    }}
  </script>
  <style>
    body {{ background-color: {bg}; color: #F8FAFC; }}
  </style>
</head>
<body class="font-sans antialiased min-h-screen flex flex-col justify-between selection:bg-brand selection:text-white">

  <!-- Navigation -->
  <header class="sticky top-0 z-50 backdrop-blur-md bg-opacity-70 border-b border-white/10" style="background-color: {bg}CC;">
    <div class="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
      <div class="flex items-center gap-3">
        {f'<img src="{logo_img}" class="w-8 h-8 rounded-lg" alt="{name} Logo">' if logo_img else ''}
        <span class="font-bold text-lg tracking-tight text-white">{name}</span>
      </div>
      <a href="#waitlist" class="text-sm font-semibold px-4 py-2 rounded-xl text-white transition-opacity hover:opacity-90" style="background-color: {primary};">
        Join Waitlist
      </a>
    </div>
  </header>

  <!-- Hero Section -->
  <main>
    <section class="pt-20 pb-16 max-w-5xl mx-auto px-6 text-center">
      <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold mb-6 border border-white/10 bg-white/5 text-slate-300">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Now accepting early access signups
      </div>
      <h1 class="text-5xl md:text-7xl font-extrabold tracking-tight text-white leading-tight mb-6">
        {name}
      </h1>
      <p class="text-xl md:text-2xl text-slate-300 font-light max-w-2xl mx-auto mb-10 leading-relaxed">
        {tagline}
      </p>

      <!-- Hero Visual Banner -->
      {f'''<div class="max-w-3xl mx-auto mb-12 rounded-2xl overflow-hidden border border-white/15 shadow-2xl">
        <img src="{hero_img}" alt="{name} Preview" class="w-full h-auto object-cover">
      </div>''' if hero_img else ''}

      <!-- Waitlist Form (Hero CTA) -->
      <div id="waitlist" class="max-w-md mx-auto bg-white/5 border border-white/10 backdrop-blur-xl p-6 rounded-2xl shadow-xl">
        <h2 class="text-lg font-bold text-white mb-2">Be the first to get access</h2>
        <p class="text-xs text-slate-400 mb-4">Join our waitlist for product updates and early access perks.</p>
        <form id="signup-form" onsubmit="handleSignup(event)" class="flex flex-col gap-3">
          <input type="text" id="signup-name" placeholder="Your name (optional)" class="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-brand">
          <input type="email" id="signup-email" required placeholder="name@example.com" class="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-brand">
          <button type="submit" id="signup-btn" class="w-full py-2.5 rounded-xl font-semibold text-sm text-white transition-all hover:opacity-90 active:scale-95 flex items-center justify-center gap-2" style="background-color: {primary};">
            <span>Join Waitlist</span>
          </button>
        </form>
        <div id="signup-message" class="hidden mt-4 p-3 rounded-xl text-xs font-medium text-center"></div>
      </div>
    </section>

    <!-- Features Section -->
    <section class="py-20 border-t border-white/10">
      <div class="max-w-6xl mx-auto px-6">
        <div class="text-center mb-16">
          <h2 class="text-3xl font-extrabold text-white">Why {name}?</h2>
          <p class="text-slate-400 text-sm mt-2">Everything you need to get moving faster.</p>
        </div>
        <div class="grid md:grid-cols-3 gap-6">
          {feature_cards}
        </div>
      </div>
    </section>

    <!-- Optional Extra Section -->
    {extra_section}
  </main>

  <!-- Footer -->
  <footer class="border-t border-white/10 py-10 mt-16 text-center text-xs text-slate-500">
    <div class="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
      <p>© 2026 {name}. All rights reserved.</p>
      <p>Built with <span class="text-white font-medium">LaunchKit</span> on Google Cloud</p>
    </div>
  </footer>

  <script>
    async function handleSignup(e) {{
      e.preventDefault();
      const email = document.getElementById('signup-email').value;
      const name = document.getElementById('signup-name').value;
      const btn = document.getElementById('signup-btn');
      const msg = document.getElementById('signup-message');

      btn.disabled = true;
      btn.innerText = 'Joining...';

      try {{
        const res = await fetch('/api/signup?project={project_id}', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ email: email, name: name, project_id: '{project_id}' }})
        }});
        const data = await res.json();
        msg.classList.remove('hidden', 'bg-red-500/20', 'text-red-300', 'bg-emerald-500/20', 'text-emerald-300');
        if (res.ok && data.status !== 'error') {{
          msg.classList.add('bg-emerald-500/20', 'text-emerald-300');
          msg.innerText = data.message || '🎉 You have been added to the waitlist!';
          document.getElementById('signup-form').reset();
        }} else {{
          msg.classList.add('bg-red-500/20', 'text-red-300');
          msg.innerText = data.message || data.error || 'Failed to submit. Please try again.';
        }}
      }} catch (err) {{
        msg.classList.remove('hidden');
        msg.classList.add('bg-red-500/20', 'text-red-300');
        msg.innerText = 'Network error. Please try again later.';
      }} finally {{
        btn.disabled = false;
        btn.innerText = 'Join Waitlist';
      }}
    }}
  </script>
</body>
</html>
"""


def generate_page(project_id: str, instructions: str = "") -> dict[str, Any]:
    """Generate and publish a responsive HTML landing page for a startup/project.

    Args:
        project_id: The slug identifier of the project.
        instructions: Optional design modifications (e.g. 'dark mode', 'add pricing section', 'clean light theme').

    Returns:
        Dictionary with project_id, version number, public URL, and change summary.
    """
    proj = get_project(project_id)
    if "error" in proj:
        return proj

    # Check if assets exist; generate them if missing
    assets = proj.get("assets", {})
    if not assets or not assets.get("hero"):
        asset_res = generate_assets(project_id)
        if "assets" in asset_res:
            assets = asset_res["assets"]

    name = proj.get("name", "Project")
    tagline = proj.get("tagline", "Next-generation platform")
    features = proj.get("features", ["Fast", "Modern", "Intelligent"])
    palette = proj.get("palette", {"primary": "#7C3AED", "bg": "#0F0F14", "accent": "#38BDF8"})

    # Update palette if dark/light mode requested in instructions
    if "light" in instructions.lower():
        palette["bg"] = "#F8FAFC"
        palette["text"] = "#0F172A"
    elif "dark" in instructions.lower():
        palette["bg"] = "#09090B"

    html = _build_html_template(
        project_id=project_id,
        name=name,
        tagline=tagline,
        features=features,
        palette=palette,
        assets=assets,
        extra_instructions=instructions,
    )

    change_note = instructions if instructions else "Generated initial responsive landing page"
    result = save_page_version(project_id=project_id, html_content=html, change_note=change_note)
    return result
