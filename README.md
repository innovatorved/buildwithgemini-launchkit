<div align="center">

<img src="assets/build-with-gemini-banner.png" alt="Build with Gemini" width="100%" />

# 🚀 LaunchKit — Idea-to-Prototype Website Agent
### Build with Gemini · Track 3 Project

> **One-liner:** Describe your startup or side-project idea in one sentence → LaunchKit builds a live prototype website with AI-generated visual assets, a working **waitlist**, and subscriber analytics, all hosted on Google Cloud.

<br/>

[![GitHub Repo](https://img.shields.io/badge/GitHub-innovatorved%2Fbuildwithgemini--launchkit-blue?logo=github)](https://github.com/innovatorved/buildwithgemini-launchkit)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Vertex%20AI%20%7C%20Firestore%20%7C%20GCS%20%7C%20Cloud%20Run-4285F4?logo=googlecloud&logoColor=white)](https://cloud.google.com/)
[![Built with ADK](https://img.shields.io/badge/Built%20with-ADK%20%2B%20agents--cli-34A853)](https://github.com/google/adk)

</div>

---

## 1. Overview & Architecture

LaunchKit is an autonomous product builder agent that transforms ideas into published, interactive web prototypes:

1. **Idea to Brand Identity:** Given a one-line idea, LaunchKit proposes a brand name, tagline, 3 key features, target audience persona, and a tailored hex color palette.
2. **Visual Generation with Nano Banana:** Generates high-resolution hero imagery using **Nano Banana 2 Lite** (`gemini-3.1-flash-lite-image`), alongside branded vector logos and icons, uploaded directly to Google Cloud Storage.
3. **Responsive Web Prototyping:** Automatically composes single-file responsive Tailwind CSS landing pages with an integrated waitlist form.
4. **Live Publishing & Versioning:** Saves each page version to Cloud Storage and Firestore, serving them at `/p/<project-id>` without overwriting history.
5. **Real-Time Waitlist Subscriptions:** Visitors submit their email into the prototype page; submissions are stored instantly in Cloud Firestore via `/api/signup`.
6. **Analytics & Growth Insights:** Queries Firestore subscribers, computes signup metrics, and renders dark-mode growth trend visualizations.
7. **Long-Term Memory:** Retains brand preferences, aesthetic choices, and past project details across sessions via Vertex AI Memory Bank.

```
            Developer / Creator                     Public Visitors
                    │                                      │
                    ▼                                      ▼
  ┌──────────────────────────────────────────────────────────────┐
  │ Cloud Run — FastAPI Proxy & Web Server                       │
  │  • /                 → A2UI Builder Chat Interface           │
  │  • /p/<project-id>   → Serves published prototype HTML       │
  │  • /api/signup       → Records waitlist subscribers          │
  │  • /api/projects     → Lists generated projects              │
  └──────────────────────────────┬───────────────────────────────┘
                                 │ A2A Protocol
                                 ▼
  ┌──────────────────────────────────────────────────────────────┐
  │ Agent Platform: "launchkit" (Agent Runtime / Reasoning Eng)  │
  │  ├─ Model: Vertex AI Gemini 2.5 Flash                        │
  │  ├─ Media: Nano Banana 2 Lite (gemini-3.1-flash-lite-image)  │
  │  ├─ Memory: Vertex AI Memory Bank (Long-Term Memory)         │
  │  ├─ Surface: A2UI v0.8 Basic Catalog Card Callback           │
  │  └─ 11 Function Tools                                        │
  └──────────────┬──────────────────────┬────────────────────────┘
                 ▼                      ▼
  ┌──────────────────────────┐   ┌───────────────────────────────┐
  │ Cloud Firestore (Native) │   │ Cloud Storage (GCS)           │
  │  • projects/{id}         │   │  • <id>/images/hero.jpg, logo │
  │  • projects/{id}/versions│   │  • <id>/site/v*/index.html    │
  │  • projects/{id}/signups │   │  • <id>/analytics/growth.png  │
  └──────────────────────────┘   └───────────────────────────────┘
```

---

## 2. Lab Services & Tech Stack

| Lab Layer | Technology | Role in LaunchKit |
|---|---|---|
| 🤖 **Agent Framework** | Google Agent Development Kit (ADK) & `agents-cli` | Core agent runtime, tool routing, and orchestration |
| 🧠 **LLM (Reasoning)** | Vertex AI **Gemini 2.5 Flash** (`gemini-2.5-flash`) | Fast reasoning, product planning, code generation, and adaptation |
| 🎨 **Media Generation** | **Nano Banana 2 Lite** (`gemini-3.1-flash-lite-image`) | High-res hero imagery and visual brand assets |
| 💬 **Sessions & Memory** | ADK Session Service + Vertex AI Memory Bank | Cross-turn memory for design preferences, brand styles, and projects |
| 🗄️ **Structured Data** | Cloud Firestore Native | Multi-tenant projects, page versions, and waitlist signups |
| 🖼️ **Blob Storage** | Google Cloud Storage (GCS) | Hosted Nano Banana imagery, logos, versioned HTML pages, and charts |
| 📊 **Analytics** | Matplotlib & Code Execution | Automated waitlist subscriber growth velocity analysis |
| 🪟 **Agent-first UI** | A2UI (v0.8 Basic Catalog) | Project overview cards, previews, and interactive widgets |
| 🌐 **Frontend & Proxy** | FastAPI & Uvicorn on Cloud Run | Chat interface, `/p/<id>` page serving, and `/api/signup` endpoint |

---

## 3. Function Tools

LaunchKit equips 11 production-grade ADK function tools:

| Tool | Module | Description |
|---|---|---|
| `create_project` | `storage_tools.py` | Creates a new startup record in Firestore with name, tagline, features, palette, and audience. |
| `get_project` | `storage_tools.py` | Retrieves project metadata and version history from Firestore. |
| `list_projects` | `storage_tools.py` | Lists all active startup projects. |
| `save_page_version` | `storage_tools.py` | Persists a new HTML version to Cloud Storage and updates Firestore. |
| `add_waitlist_signup` | `storage_tools.py` | Adds a subscriber to the project's waitlist collection. |
| `get_signups` | `storage_tools.py` | Retrieves all registered waitlist subscribers for a project. |
| `generate_image` | `media_tools.py` | Generates images via **Nano Banana 2 Lite** (`gemini-3.1-flash-lite-image`), uploads to GCS, and saves ADK artifacts. |
| `generate_assets` | `media_tools.py` | Generates a complete brand pack (Nano Banana hero image, SVG logo, and 3 feature icons). |
| `generate_page` | `builder_tools.py` | Generates and publishes responsive Tailwind CSS landing pages with live waitlist forms. |
| `analyze_waitlist` | `analytics_tools.py` | Analyzes subscriber velocity and generates Matplotlib growth trend plots. |
| `preload_memory` | ADK Built-in | Recalls user brand style, theme choices, and past feedback from Vertex AI Memory Bank. |

---

## 4. Directory Layout

```
launchkit/
├── app/
│   ├── agent.py                 # Root ADK agent with Gemini 2.5 Flash, tools & callbacks
│   ├── a2ui_utils.py            # A2UI v0.8 response callback
│   ├── fast_api_app.py          # Standard ADK A2A FastAPI server
│   └── tools/
│       ├── storage_tools.py     # Firestore projects, versions, & waitlist signups
│       ├── media_tools.py       # Nano Banana 2 Lite image generation & asset builder
│       ├── builder_tools.py     # Tailwind CSS landing page builder
│       └── analytics_tools.py   # Waitlist analytics & Matplotlib growth chart
├── frontend/
│   ├── main.py                  # FastAPI proxy (A2A client, /p/<id> serving, /api/signup)
│   ├── static/
│   │   └── index.html           # A2UI chat builder with native card renderer
│   ├── requirements.txt         # Lightweight frontend dependencies
│   └── Dockerfile               # Production container for Cloud Run
├── tests/                       # Unit & integration verification tests
├── pyproject.toml               # Python dependencies managed with uv
├── agents-cli-manifest.yaml     # Agent deployment manifest
└── README.md                    # Project documentation
```

---

## 5. Setup & Local Development

### Prerequisites
- Python 3.11+
- [uv](https://astral.sh/uv/) package manager
- Google Cloud SDK authenticated (`gcloud auth application-default login`)

### Installation

```bash
# Clone the repository
git clone https://github.com/innovatorved/buildwithgemini-launchkit.git
cd buildwithgemini-launchkit

# Install dependencies
uv sync
```

### Environment Configuration

Configure `.env` in the repository root:

```env
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_GENAI_USE_ENTERPRISE=true
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_CLOUD_LOCATION=us-central1
LAUNCHKIT_MODEL=gemini-2.5-flash
LAUNCHKIT_BUCKET=YOUR_GCS_BUCKET_NAME
```

### Running Locally

Start the local development server:

```bash
uv run python frontend/main.py
```

Access the application in your browser:
- **Builder Interface:** Navigate to root `/`
- **Projects Directory:** Navigate to `/api/projects`
- **Sample Prototype:** Navigate to `/p/studybuddy` (or any generated project slug)

---

## 6. Cloud Deployment

### 1. Deploy Agent to Agent Runtime (Reasoning Engine)

Deploy the ADK agent to Vertex AI Agent Platform:

```bash
agents-cli deploy \
  --deployment-target agent_runtime \
  --project=YOUR_PROJECT_ID \
  --region=us-central1 \
  --update-env-vars="GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,LAUNCHKIT_BUCKET=YOUR_BUCKET,LAUNCHKIT_MODEL=gemini-2.5-flash" \
  --no-confirm-project
```

Note the output `Agent Runtime ID` (e.g. `projects/<project-num>/locations/us-central1/reasoningEngines/<id>`).

### 2. Deploy Frontend Proxy to Cloud Run

Deploy the FastAPI container to Cloud Run pointing to the deployed Agent Runtime resource:

```bash
gcloud run deploy launchkit-frontend \
  --source frontend \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="AGENT_ENGINE_RESOURCE_NAME=projects/<project-num>/locations/us-central1/reasoningEngines/<id>,AGENT_DIRECTORY=app,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,LAUNCHKIT_BUCKET=YOUR_BUCKET"
```

Ensure the Cloud Run compute service account is granted `roles/aiplatform.user` on the project:

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:<project-num>-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

---

## 7. User Journey & Example Flow

1. **Describe an Idea:**  
   *"Build a prototype site for StudyBuddy — an app that helps students find study partners nearby."*
2. **Review Plan:**  
   LaunchKit creates the project in Firestore and responds with an A2UI card detailing the name (*StudyBuddy*), tagline, 3 features, target audience, and hex palette.
3. **Generate Assets:**  
   Calls `generate_image` using **Nano Banana 2 Lite** (`gemini-3.1-flash-lite-image`) for a high-tech hero banner, plus creates vector logos and feature icons uploaded to Cloud Storage.
4. **Build & Publish:**  
   LaunchKit synthesizes a responsive Tailwind landing page with the assets and waitlist form embedded, saving version 1 to GCS and Firestore, and returns `/p/studybuddy`.
5. **Collect Live Signups:**  
   Visitors browse `/p/studybuddy`, enter their email into the waitlist form, and submit. The form posts to `/api/signup`, storing the subscriber record in Firestore.
6. **Analyze Growth:**  
   Creator asks: *"How is my waitlist doing for studybuddy?"*  
   LaunchKit queries Firestore, calculates signup velocity, plots a dark-mode growth chart, saves it to GCS, and presents the metrics and chart in chat.
7. **Iterate & Adapt:**  
   Creator asks: *"Make it dark mode with neon purple glow and add a pricing tier."*  
   LaunchKit generates version 2 with updated styling while preserving version 1 in GCS history.

---

## 8. API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/` | `GET` | Interactive A2UI Chat interface |
| `/chat` | `POST` | Proxy conversation to agent (`{"message": "...", "user_id": "..."}`) |
| `/p/{project_id}` | `GET` | Live published landing page HTML from Cloud Storage |
| `/p/{project_id}/v/{v}` | `GET` | Specific historic version of the landing page |
| `/api/signup` | `POST` | Waitlist signup (`{"project_id": "...", "email": "..."}`) |
| `/api/projects` | `GET` | List of all generated projects and versions |

---

## License & Attribution

Built for the **Build with Gemini** workshop (Track 3: Prototype Website Agent).  
Maintained by [@innovatorved](https://github.com/innovatorved).

