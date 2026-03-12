# Mark Backend

## Overview
Mark Backend is the core API and service layer for an AI-driven marketing agent. It automates digital marketing workflows by generating creative assets (images, carousels, videos), managing brand identity, and orchestrating multi-step AI pipelines via LangGraph.

## Features
- **Post Generation:** Research-driven content pipeline that crafts strategy, copy, and images for social media posts.
- **Carousel Generation:** Slide-by-slide carousel creation with per-slide QC validation and brand-aware image generation.
- **Video Generation:** Scene-by-scene video creation via the Veo API with platform-specific aspect ratio selection.
- **Image Editing:** Edit existing images with natural language prompts using Gemini (with OpenAI fallback).
- **Copy Regeneration:** Refine existing copy with feedback without re-generating images.
- **Brand DNA Extraction:** Extract and structure brand identity attributes from any brand input using LLM-powered analysis.

## Project Structure

```
mark-backend/
├── config/                              # Django project configuration
│   ├── settings.py
│   ├── urls.py                          # Root URL routing
│   ├── asgi.py
│   └── wsgi.py
│
├── creation_studio/                     # App: AI content creation pipelines
│   ├── views.py                         # API endpoint handlers
│   ├── graphs/
│   │   ├── create_post/                 # Post + image generation pipeline
│   │   │   ├── state.py                 # ContentPipelineState
│   │   │   └── agent.py                 # build_agent() / build_copy_agent()
│   │   ├── create_carousel/             # Carousel generation pipeline
│   │   │   ├── state.py                 # CarouselPipelineState
│   │   │   └── agent.py                 # build_carousel_agent()
│   │   ├── create_video/                # Video generation pipeline
│   │   │   ├── state.py                 # VideoPipelineState
│   │   │   └── agent.py                 # build_video_agent()
│   │   ├── edit_image/                  # Image editing pipeline
│   │   │   ├── state.py                 # EditImageState
│   │   │   └── agent.py                 # build_edit_image_agent()
│   │   ├── shared/
│   │   │   └── nodes/
│   │   │       ├── research_trends/     # Gemini: trending topics research
│   │   │       ├── research_competitors/# Gemini: competitor analysis
│   │   │       └── research_platform/   # Gemini: platform best practices
│   │   └── utils/
│   │       ├── gemini_utils.py          # Gemini API client (text, vision, image gen)
│   │       ├── openai_utils.py          # OpenAI image editing fallback
│   │       ├── veo_utils.py             # Veo video generation client
│   │       ├── cloudinary_utils.py      # Cloudinary upload helpers
│   │       └── firebase_utils.py        # Firestore CRUD helpers
│   └── migrations/
│
├── brand_dna_extractor/                 # App: Extract brand DNA
│   ├── views.py                         # POST /api/brand-dna/extract/
│   ├── urls.py
│   ├── graphs/
│   │   ├── state.py                     # BrandDNAState
│   │   ├── agent.py                     # Graph: extractor → (tools) → formatter
│   │   └── nodes/
│   │       ├── extractor/               # GPT-4.1 mini: extract brand attributes
│   │       └── formatter/               # GPT-4.1 mini: structure as JSON
│   └── migrations/
│
├── langgraph.json                       # LangGraph deployment config
├── manage.py
├── pyproject.toml
└── poetry.lock
```

## Pipeline Architectures

### Post Generation (`content_pipeline`)

Two graph variants are available:

**Full pipeline** — used by `/api/content/generate-image/`:
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

**Copy-only pipeline** — used by `/api/content/edit-copy/`:
```
START
  ├── research_trends ──────┐
  ├── research_competitors ─┤  (parallel)
  └── research_platform ────┘
              │
     strategist_copywriter
              │
             END
```

### Carousel Generation (`carousel_pipeline`)
```
START
  ├── research_trends ──────┐
  ├── research_competitors ─┤  (parallel)
  └── research_platform ────┘
              │
   carousel_strategist
              │
   template_retriever
              │
    generate_slides   ← per-slide QC (up to 3 retries)
              │
             END
```

Each slide is validated by Gemini Vision: headline transcription similarity (≥0.85 Levenshtein), hex color presence, logo placement, and readability score (≥3/5).

### Video Generation (`video_pipeline`)
```
START
  ├── research_trends ──────┐
  ├── research_competitors ─┤  (parallel)
  └── research_platform ────┘
              │
    video_strategist
              │
   template_retriever
              │
    generate_scenes   ← Veo API, safety-filter aware
              │
             END
```

Platform → aspect ratio mapping: Instagram Reels / TikTok / YouTube Shorts → `9:16`, LinkedIn / YouTube → `16:9`, Facebook → `1:1`.

### Image Editing (`edit_image`)
```
START → download_image → edit_with_gemini ──(success)──→ upload_and_save → END
                                 │
                           (gemini failed)
                                 ↓
                        edit_with_openai ──────────────→ upload_and_save → END
```

### Brand DNA Extraction
```
START → extractor ──(tool call)──→ tools → extractor (loop) → formatter → END
                └──(no tool call)──────────────────────────→ formatter → END
```

The extractor can call `fetch_brand_website(url)` to scrape a brand's site before formatting.

## API Endpoints

The API is fully RESTful and manages entities like Brands, Creations, Generations, and Posts.

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/brands/` | List or create brands |
| `POST` | `/api/creations/` | Create a new content project (post, carousel, video) |
| `POST` | `/api/creations/<uuid>/generations/` | Trigger AI generation for a creation |
| `GET`  | `/api/generations/<uuid>/` | Fetch details of a specific generation (and its slices if video/carousel) |
| `POST` | `/api/brand-dna/extract/` | Extract brand DNA from text or URL |

> **Note:** The old `/api/content/...` endpoints have been superseded by the RESTful `/api/creations/...` pattern.

### Pipeline Architectures

#### Post Generation (`content_pipeline`)
Used for `post_type="post"` (or story/infographic):
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

#### Carousel Generation (`carousel_pipeline`)
Used for `post_type="carousel"`.
```
START
  ├── research_trends ──────┐
  ├── research_competitors ─┤  (parallel)
  └── research_platform ────┘
              │
   carousel_strategist
              │
   template_retriever
              │
    generate_slides   ← Parallel processing (5-10 slides simultaneously)
              │
             END
```

Each slide is processed in parallel using a ThreadPoolExecutor.

#### Video Generation (`video_pipeline`)
Used for `post_type="video"` or `reel`.
```
START
  ├── research_trends ──────┐
  ├── research_competitors ─┤  (parallel)
  └── research_platform ────┘
              │
    video_strategist
              │
   template_retriever
              │
    generate_scenes   ← Parallel processing (3-6 scenes simultaneously via Veo API)
              │
             END
```

### Request / Response Shapes

#### `POST /api/creations/<uuid>/generations/` (Image)
```json
// Request
{
  "prompt": "Product launch for eco-friendly water bottle"
}

// Response
{
  "generation": {
    "uuid": "...",
    "type": "image",
    "prompt": "Product launch for eco-friendly water bottle",
    "content": "https://res.cloudinary.com/...",
    "status": "done"
  }
}
```

#### `POST /api/creations/<uuid>/generations/` (Carousel or Video)
```json
// Request
{
  "prompt": "5 tips for healthy sleep",
  "num_slides": 6  // or "num_scenes": 4 for video
}

// Response
{
  "generation": {
    "uuid": "...",
    "type": "carousel",  // or "video"
    "prompt": "5 tips for healthy sleep",
    "content": "uuid1,uuid2,uuid3,uuid4,uuid5,uuid6", // Comma-separated slice UUIDs
    "status": "done"
  }
}
```

#### `GET /api/generations/<uuid>/` (Master Carousel/Video)
Automatically fetches and serializes the child slices/scenes when a master generation is queried.
```json
{
  "uuid": "...",
  "type": "carousel",
  "content": "uuid1,uuid2...",
  "slices": [
    {
      "uuid": "uuid1",
      "type": "image",
      "content": "https://res.cloudinary.com/..."
    }
  ]
}
```
```json
// Request
{
  "brand_input": "https://example.com or a brand description"
}

// Response
{
  "brand_dna": { ... }
}
```

## Models Used

| Provider | Model | Usage |
|----------|-------|-------|
| Google | `gemini-2.5-flash` | Research nodes, QC validation |
| Google | `gemini-2.5-flash` (image) | Image generation & editing |
| Google | `veo-3.0-generate-preview` | Video scene generation |
| OpenAI | `gpt-4.1-mini` | Strategist, copywriter, prompt engineer, brand extractor |
| OpenAI | `gpt-image-1` | Image editing fallback |

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
   Fill in the required keys:
   - `DJANGO_SECRET_KEY`
   - `OPENAI_API_KEY`
   - `GEMINI_API_KEY` / `GEMINI_IMAGE_API_KEY`
   - `CLOUDINARY_CLOUD_NAME` / `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET`
   - `FIREBASE_SERVICE_ACCOUNT_JSON`
   - `LANGCHAIN_API_KEY` (optional, for LangSmith tracing)

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
