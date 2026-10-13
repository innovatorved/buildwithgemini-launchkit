# 🚀 LaunchKit — Idea-to-Prototype Website Agent
### Build with Gemini · Track 3 Project

> **One-liner:** Describe your startup or side-project idea in one sentence → LaunchKit builds a live prototype website with branded assets, a working **waitlist**, and subscriber analytics, all hosted on Google Cloud.

[![GitHub Repo](https://img.shields.io/badge/GitHub-innovatorved%2Fbuildwithgemini--launchkit-blue?logo=github)](https://github.com/innovatorved/buildwithgemini-launchkit)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Vertex%20AI%20%7C%20Firestore%20%7C%20GCS-orange?logo=googlecloud)](https://cloud.google.com/)
[![ADK 2.11](https://img.shields.io/badge/ADK-2.11-green)](https://github.com/google/adk)

---

## 1. Overview & Architecture

LaunchKit transforms ideas into interactive, published web prototypes in seconds:
1. Proposes brand identity, name, tagline, color palette, and 3 key features.
2. Generates visual assets (hero banner, logo, feature icons) stored in Cloud Storage.
3. Builds responsive, single-file Tailwind CSS landing pages with embedded waitlist forms.
4. Serves published pages publicly at `/p/<project-id>`.
5. Records waitlist signups directly into Cloud Firestore (`/api/signup`).
6. Analyzes subscriber velocity and generates dark-mode growth charts on demand.
7. Remembers user brand preferences (colors, themes) across sessions using Memory Bank.

```
            Developer / Creator                     Public Visitors
                    │                                      │
                    ▼                                      ▼
  ┌──────────────────────────────────────────────────────────────┐
  │ Cloud Run — FastAPI Web Proxy                                │
  │  /                  → A2UI Builder Chat Interface            │
  │  /p/<id>            → Serves published prototype HTML        │
  │  /api/signup        → Records waitlist subscriber            │
  │  /api/projects      → Lists active projects                  │
  └──────────────────────────────┬───────────────────────────────┘
                                 ▼
  ┌──────────────────────────────────────────────────────────────┐
  │ Google ADK Agent: "launchkit" (Gemini 2.5 Flash)             │
  │  ├─ A2UI v0.8 Rich Surface Callback                          │
  │  ├─ Memory Bank Callback (session persistence)               │
  │  └─ Function Tools                                           │
  └──────────────┬──────────────────────┬────────────────────────┘
                 ▼                      ▼
  ┌──────────────────────────┐   ┌───────────────────────────────┐
  │ Cloud Firestore (Native) │   │ Cloud Storage (GCS)           │
  │  • projects/{id}         │   │  • <id>/images/hero.svg, logo │
  │  • projects/{id}/versions│   │  • <id>/site/v*/index.html    │
  │  • projects/{id}/signups │   │  • <id>/analytics/growth.png  │
  └──────────────────────────┘   └───────────────────────────────┘
```

---

## 2. Lab Services & Tech Stack

| Lab Layer | Technology | Role in LaunchKit |
|---|---|---|
| 🤖 **Agent Framework** | Google Agent Development Kit (ADK) & `agents-cli` | Root `launchkit` product builder agent |
| 🧠 **LLM** | Vertex AI Gemini 2.5 Flash | Idea reasoning, site generation, tone adaptation |
| 💬 **Sessions & Memory** | ADK Session Service + Vertex AI Memory Bank | Cross-turn memory for design preferences |
| 🗄️ **Database** | Cloud Firestore Native (`us-central1`) | Multi-tenant projects, page versions, waitlist signups |
| 🖼️ **Storage** | Google Cloud Storage (GCS) | Hosted SVG assets, versioned HTML pages, analytics charts |
| 📊 **Analytics** | Matplotlib & Code Sandbox | Automated waitlist subscriber growth plots |
| 🪟 **Agent-first UI** | A2UI (v0.8 Basic Catalog) | Project overview cards, previews, and quick actions |
| 🌐 **Frontend & Proxy** | FastAPI & Uvicorn on Cloud Run | Chat interface + `/p/<id>` page serving + `/api/signup` |

---

## 3. Directory Layout

```
launchkit/
├── app/
│   ├── agent.py                 # Root ADK agent with 10 tools & callbacks
│   ├── a2ui_utils.py            # A2UI v0.8 response callback
│   ├── fast_api_app.py          # Standard ADK A2A FastAPI server
│   └── tools/
│       ├── storage_tools.py     # Firestore projects, versions, & waitlist signups
│       ├── media_tools.py       # SVG hero banners, logos, and icon assets
│       ├── builder_tools.py     # Tailwind CSS landing page builder
│       └── analytics_tools.py   # Waitlist analytics & Matplotlib growth chart
├── frontend/
│   ├── main.py                  # FastAPI proxy (chat, /p/<id> serving, /api/signup)
│   ├── static/
│   │   └── index.html           # A2UI chat builder with clickable suggestions
│   ├── requirements.txt         # Lightweight frontend dependencies
│   └── Dockerfile               # Production container for Cloud Run
├── tests/                       # Unit & integration verification tests
├── pyproject.toml               # Python dependencies managed with uv
└── README.md                    # Project documentation
```

---

## 4. Setup & Local Development

### Prerequisites
- Python 3.11+
- `uv` package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Google Cloud SDK authenticated (`gcloud auth application-default login`)

### Installation

```bash
# Clone the repository
git clone https://github.com/innovatorved/buildwithgemini-launchkit.git
cd buildwithgemini-launchkit

# Install dependencies with uv
uv sync
```

### Environment Configuration

Create or verify `.env`:

```env
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_GENAI_USE_ENTERPRISE=true
GOOGLE_CLOUD_PROJECT=qwiklabs-gcp-04-415aeabf77b7
GOOGLE_CLOUD_LOCATION=us-central1
LAUNCHKIT_MODEL=gemini-2.5-flash
LAUNCHKIT_BUCKET=bwg3-qwiklabs-gcp-04-415aeabf77b7
```

### Running the App

Start the unified LaunchKit web builder and proxy:

```bash
uv run python frontend/main.py
```

Open your browser to:
- **Builder Chat:** `http://localhost:8080`
- **Projects API:** `http://localhost:8080/api/projects`
- **Published Prototype:** `http://localhost:8080/p/studybuddy`

---

## 5. User Journey & Example Flow

1. **Describe an idea:**  
   *"An app that helps students find study partners nearby."*
2. **Review Plan:**  
   LaunchKit returns an A2UI card with name (*StudyBuddy*), tagline, 3 features, and hex palette (`#6366F1`, `#0F172A`).
3. **Build & Publish:**  
   LaunchKit creates branded SVG assets, writes a responsive landing page, uploads to Cloud Storage, and returns `/p/studybuddy`.
4. **Collect Signups:**  
   Visitors visit `http://localhost:8080/p/studybuddy`, enter their email in the waitlist form, and submit. The form sends `POST /api/signup`, saving the record in Firestore.
5. **Analyze Growth:**  
   Ask: *"How is my waitlist doing for studybuddy?"*  
   LaunchKit queries Firestore, calculates signup velocity, plots a dark-mode growth chart with Matplotlib, saves it to Cloud Storage, and presents the link and subscriber metrics.

---

## 6. API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/` | `GET` | Interactive A2UI Chat interface |
| `/chat` | `POST` | Proxy conversation to agent (`{"message": "..."}`) |
| `/p/{project_id}` | `GET` | Live published landing page HTML |
| `/p/{project_id}/v/{v}` | `GET` | Specific historic version of the landing page |
| `/api/signup` | `POST` | Waitlist signup (`{"project_id": "...", "email": "..."}`) |
| `/api/projects` | `GET` | List of all generated projects and versions |

---

## 7. Cloud Run Deployment

To deploy the frontend to Cloud Run:

```bash
# Build and deploy frontend
gcloud run deploy launchkit-frontend \
  --source frontend \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=qwiklabs-gcp-04-415aeabf77b7,LAUNCHKIT_BUCKET=bwg3-qwiklabs-gcp-04-415aeabf77b7
```

---

## 8. License & Attribution

Built for the **Build with Gemini** workshop (Track 3: Prototype Website Agent).  
Maintained by [@innovatorved](https://github.com/innovatorved).
