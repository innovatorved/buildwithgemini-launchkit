"""Waitlist growth analytics and chart generation tools for LaunchKit."""

from collections import Counter
import datetime
import io
from typing import Any
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .storage_tools import BUCKET_NAME, get_signups, get_storage_client


def analyze_waitlist(project_id: str) -> dict[str, Any]:
    """Analyze waitlist subscribers and generate a growth trend chart.

    Args:
        project_id: The slug identifier of the project.

    Returns:
        Dictionary containing total signups, growth metrics, and public chart URL.
    """
    signup_data = get_signups(project_id)
    signups = signup_data.get("signups", [])
    total = len(signups)

    if total == 0:
        return {
            "status": "success",
            "project_id": project_id,
            "total_signups": 0,
            "summary": f"Project '{project_id}' currently has 0 waitlist signups. Share your public link /p/{project_id} to start gathering users!",
            "chart_url": None,
        }

    # Group by date
    dates = []
    for s in signups:
        created_str = s.get("created_at")
        if created_str:
            try:
                d = created_str.split("T")[0]
            except Exception:
                d = datetime.date.today().isoformat()
        else:
            d = datetime.date.today().isoformat()
        dates.append(d)

    date_counts = Counter(dates)
    sorted_dates = sorted(date_counts.keys())
    daily_values = [date_counts[d] for d in sorted_dates]

    # Cumulative growth
    cumulative = []
    curr = 0
    for count in daily_values:
        curr += count
        cumulative.append(curr)

    # Plot dark-mode growth chart
    fig, ax = plt.subplots(figsize=(8, 4), facecolor="#0F0F14")
    ax.set_facecolor("#0F0F14")

    ax.plot(sorted_dates, cumulative, marker="o", color="#7C3AED", linewidth=2.5, markersize=6, label="Total Signups")
    ax.fill_between(sorted_dates, cumulative, color="#7C3AED", alpha=0.25)

    ax.set_title(f"Waitlist Growth — {project_id}", color="#FFFFFF", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Date", color="#94A3B8", fontsize=10)
    ax.set_ylabel("Total Subscribers", color="#94A3B8", fontsize=10)

    ax.tick_params(colors="#94A3B8", which="both")
    ax.grid(True, linestyle="--", alpha=0.15, color="#FFFFFF")
    for spine in ax.spines.values():
        spine.set_color("#27272A")

    plt.xticks(rotation=45 if len(sorted_dates) > 4 else 0)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    buf.seek(0)

    # Upload to Cloud Storage
    client = get_storage_client()
    bucket = client.bucket(BUCKET_NAME)
    chart_path = f"{project_id}/analytics/growth.png"
    blob = bucket.blob(chart_path)
    blob.upload_from_file(buf, content_type="image/png")

    chart_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{chart_path}"

    summary = (
        f"Project '{project_id}' has {total} subscriber{'s' if total != 1 else ''}. "
        f"Growth trend generated and updated in Cloud Storage."
    )

    return {
        "status": "success",
        "project_id": project_id,
        "total_signups": total,
        "summary": summary,
        "chart_url": chart_url,
        "daily_breakdown": dict(date_counts),
    }
