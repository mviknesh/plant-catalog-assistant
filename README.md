# Plant Catalog Assistant (simple-agent)

An intelligent botanical assistant built with Google Agent Development Kit (ADK), Vertex AI Agent Runtime, and Gemini models. The assistant helps plant enthusiasts search catalog items, retrieve botanical taxonomy, generate realistic plant imagery and videos, find local florists using Google Maps, and view ambient weather conditions.

![Plant Catalog Assistant Demo](demo.gif)

---

## 🌟 Implemented Features & Capabilities

The agent is powered by a multi-tool Gemini architecture with rich UI surface rendering (A2UI) and seamless Google Cloud service integrations:

* **🌱 Firestore Plant Catalog**: Retrieves catalog items and detailed plant descriptions directly from a Google Cloud Firestore NoSQL database (`items` collection).
* **🔬 Botanical Taxonomy Lookup**: Queries the Global Biodiversity Information Facility (GBIF) REST API to provide scientific classification (Kingdom, Phylum, Class, Order, Family, Genus, Species).
* **🎨 AI Image Generation (Imagen 3)**: Synthesizes high-resolution plant imagery using `imagen-3.0-generate-002`, uploads the generated image bytes directly to Google Cloud Storage (GCS), and updates the Firestore item record.
* **🎥 AI Video Generation (Gemini Omni Flash)**: Generates short plant videos using `gemini-omni-flash-preview` in the `global` region, registers video parts into the Playground Artifacts panel via ADK `ToolContext`, uploads video bytes to Cloud Storage, and returns public GCS video URLs.
* **📍 Local Nurseries & Florists Lookup**: Connects to the Google Maps Places API (`places:searchText`) to discover nearby florists and garden centers.
* **🌤️ Ambient Weather Check**: Queries the Open-Meteo API for real-time temperature, humidity, and weather conditions relevant to plant care.
* **🧠 Long-Term Session Memory**: Integrates with Vertex AI Memory Bank to retain user context and plant preferences across conversation sessions.
* **🖼️ Rich A2UI Surface Rendering**: Outputs structured JSON surface updates rendered as interactive cards, image grids, copy buttons, and lightbox overlays.

---

## 🛠️ Google Cloud Services & Technologies Wired Up

| Service / Technology | Implementation Usage |
| :--- | :--- |
| **Vertex AI Agent Runtime** | Deployed backend Reasoning Engine (`us-east1`) hosting the ADK agent. |
| **Gemini 2.5 Flash** | Primary reasoning & tool orchestration model (`gemini-2.5-flash`). |
| **Gemini Omni Flash** | Multimodal video synthesis (`gemini-omni-flash-preview`) in the `global` region. |
| **Imagen 3** | High-fidelity image generation model (`imagen-3.0-generate-002`). |
| **Google Cloud Firestore** | NoSQL database storing plant catalog documents and media metadata. |
| **Google Cloud Storage** | Asset storage bucket for generated images and video MP4 files. |
| **Vertex AI Memory Bank** | Session memory service for long-term user context retention. |
| **Google Maps Places API** | Places text search integration for local florist discovery. |
| **FastAPI Proxy Frontend** | Custom web application with dark mode, prompt chips, and lightbox preview. |

> **Note on Planned Features**: E-commerce shopping cart, inventory ordering, and payment processing mentioned in design drafts are *planned, not yet implemented*.

---

## 🚀 Local Setup & Running Instructions

### Prerequisites

* Python 3.10+ and `uv` package manager
* Google Cloud SDK (`gcloud`) authenticated to your GCP project
* Environment variable set with a valid Google Maps API Key (`GOOGLE_MAPS_API_KEY`)

### 1. Install Dependencies

Clone the repository and install dependencies in a virtual environment:

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
```

### 3. Run Local Agent & Web UI

Start the local FastAPI proxy frontend server:

```bash
cd frontend
uv run python main.py
```

Access the web interface in your web browser by navigating to the locally hosted port specified in terminal logs (e.g. port `8080`).

---

## ☁️ Deploying to Vertex AI Agent Runtime

Deploy the agent code to Vertex AI Agent Runtime using `agents-cli`:

```bash
agents-cli deploy --project your-gcp-project-id --region us-east1
```

To update the frontend proxy on Cloud Run:

```bash
gcloud run deploy plant-catalog-frontend \
  --source ./frontend \
  --region us-central1 \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME=projects/your-project-id/locations/us-east1/reasoningEngines/your-engine-id,AGENT_DIRECTORY=app
```
