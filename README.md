# Mark Backend

## Overview
Mark Backend is the core API and service layer for an AI-driven marketing agent. This system automates and enhances digital marketing workflows by generating creative assets such as images and video carousels, managing social media publications, tracking performance insights, and automating various marketing tasks.

## Features
- **Content Generation Pipeline:** AI-powered pipeline that researches trends, analyzes competitors, understands platform best practices, crafts strategy & copy, and generates images — all orchestrated via LangGraph.
- **Brand DNA Extraction:** Extract and structure brand identity attributes from any brand input using LLM-powered analysis.
- **Post Management:** Schedule, publish, and manage social media posts.
- **Insights & Analytics:** Track performance metrics and gather actionable insights.

## Project Structure

```
mark-backend/
├── config/                              # Django project configuration
│   ├── settings.py
│   ├── urls.py                          # Root URL routing
│   ├── asgi.py
│   └── wsgi.py
│
├── creation_studio/                     # App: AI content creation pipeline
│   ├── views.py                         # POST /api/content/generate/
│   ├── graphs/
│   │   ├── state.py                     # ContentPipelineState
│   │   ├── agent.py                     # LangGraph: research → strategy → image
│   │   ├── nodes/
│   │   │   ├── research_trends/         # Gemini: trending topics research
│   │   │   ├── research_competitors/    # Gemini: competitor analysis
│   │   │   ├── research_platform/       # Gemini: platform best practices
│   │   │   ├── strategist_copywriter/   # Strategy & copy generation
│   │   │   ├── prompt_engineer/         # Image prompt crafting
│   │   │   └── generate_image/          # Gemini image generation + Cloudinary upload
│   │   └── utils/
│   │       ├── gemini_utils.py          # Gemini API client (text + image)
│   │       └── cloudinary_utils.py      # Cloudinary upload helper
│   └── migrations/
│
├── brand_dna_extractor/                 # App: Extract brand DNA
│   ├── views.py                         # POST /api/brand-dna/extract/
│   ├── urls.py
│   ├── graphs/
│   │   ├── state.py                     # BrandDNAState
│   │   ├── agent.py                     # Graph: extractor → formatter
│   │   └── nodes/
│   │       ├── extractor/               # LLM node: extract brand attributes
│   │       └── formatter/               # LLM node: structure as JSON
│   └── migrations/
│
├── langgraph.json                       # LangGraph deployment config
├── manage.py
├── pyproject.toml
└── poetry.lock
```

## Content Pipeline Architecture

The creation studio uses a **fan-out / fan-in** LangGraph pipeline:

```
START
  ├── research_trends ──────┐
  ├── research_competitors ─┤  (parallel)
  └── research_platform ────┘
              │
     strategist_copywriter
              │
       prompt_engineer
              │
       generate_image
              │
             END
```

1. **Research phase (parallel):** Three Gemini-powered nodes run simultaneously to gather trends, competitor insights, and platform-specific best practices.
2. **Strategy & copy:** Synthesizes research into a content strategy and written copy.
3. **Image prompt:** Crafts a detailed image generation prompt.
4. **Image generation:** Generates the image via Gemini and uploads it to Cloudinary.

## Requirements
- **Python:** `>= 3.12`
- **Poetry:** [Install here](https://python-poetry.org/docs/)

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd mark-backend
   ```

2. **Install dependencies:**
   ```bash
   poetry install
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Fill in the required keys — see `.env.example` for the full list:
   - `DJANGO_SECRET_KEY`
   - `OPENAI_API_KEY`
   - `GEMINI_API_KEY` / `GEMINI_IMAGE_API_KEY`
   - `CLOUDINARY_CLOUD_NAME` / `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET`
   - `LANGCHAIN_API_KEY` (optional, for LangSmith tracing)
   - `FIREBASE_SERVICE_ACCOUNT_JSON`

## Running the Project

1. **Apply database migrations:**
   ```bash
   poetry run python manage.py migrate
   ```

2. **Start the development server:**
   ```bash
   poetry run python manage.py runserver
   ```
   The API will be available at `http://127.0.0.1:8000/`.

3. **Run with LangGraph Studio (optional):**
   ```bash
   langgraph dev
   ```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/content/generate/` | Run the content creation pipeline |
| `POST` | `/api/brand-dna/extract/` | Extract brand DNA from input |
