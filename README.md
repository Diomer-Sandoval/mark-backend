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

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/content/generate-image/` | Run the full post + image generation pipeline |
| `POST` | `/api/content/edit-copy/` | Regenerate copy with optional feedback |
| `POST` | `/api/content/edit-image/` | Edit an existing image with a natural language prompt |
| `POST` | `/api/content/generate-carousel/` | Generate a branded carousel |
| `POST` | `/api/content/edit-carousel-slide/` | Regenerate a single carousel slide image |
| `POST` | `/api/content/generate-video/` | Generate a video with Veo |
| `POST` | `/api/brand-dna/extract/` | Extract brand DNA from text or URL |

### Shared Objects

These objects appear in multiple request bodies:

```json
// brand_dna
{
  "color_palette": {
    "primary": "#FF0000",
    "secondary": "#0D0D0D",
    "accent": "#000000",
    "complementary": ["#FF0000", "#000000", "#FFFFFF"]
  },
  "typography": {
    "body": "Playfair Display",
    "heading": "Montserrat"
  },
  "tone": {
    "description": "Brand description...",
    "keywords": ["sensorial", "artesanal", "educativo"],
    "voice": "inspirational"
  }
}

// identity — logo_url is used automatically to fetch the logo
{
  "logo_url": "https://example.com/logo.png",
  "name": "Brand Name",
  "slug": "brand-name",
  "site_url": "https://example.com/"
}
```

> **Logo resolution priority:** `logo_base64` → `logo_url` (top-level) → `identity.logo_url` → none.

### Request / Response Shapes

#### `POST /api/content/generate-image/`
```json
// Request
{
  "prompt": "Product launch for eco-friendly water bottle",
  "platforms": ["instagram", "facebook"],
  "post_type": "post",
  "post_tone": "promotional",
  "brand_dna": { ... },
  "identity": { ... }
}

// Response
{
  "uuid": "<creation_uuid>",
  "copy": "Generated copy text...",
  "image_url": "https://res.cloudinary.com/..."
}
```

#### `POST /api/content/edit-copy/`
```json
// Request
{
  "creation_uuid": "...",
  "prompt": "...",
  "current_copy": "...",
  "copy_feedback": "make it funnier",
  "platforms": ["instagram"],
  "post_type": "post",
  "post_tone": "casual",
  "brand_dna": { ... },  // typography is stripped server-side (not needed for copy)
  "identity": { ... }
}

// Response
{
  "uuid": "<creation_uuid>",
  "copy": "Updated copy text..."
}
```

#### `POST /api/content/edit-image/`
```json
// Request
{
  "creation_uuid": "...",
  "uuid": "<parent_generation_uuid>",
  "prompt": "Change the background to a sunset",
  "img_url": "https://res.cloudinary.com/..."
}

// Response
{
  "status": "ok",
  "message": "Image edited successfully",
  "img_url": "https://res.cloudinary.com/..."
}
```

#### `POST /api/content/generate-carousel/`
```json
// Request
{
  "topic": "5 tips for healthy sleep",
  "platform": "instagram",
  "post_tone": "educational",
  "num_slides": 6,
  "brand_dna": { ... },
  "identity": { ... }
}

// Response
{
  "uuid": "<creation_uuid>",
  "slides": [
    {
      "index": 0,
      "headline": "Sleep better tonight",
      "image_url": "https://res.cloudinary.com/...",
      "qc_passed": true,
      "qc_attempts": 1
    }
  ],
  "caption": "...",
  "hashtags": ["#sleep", "#wellness"]
}
```

#### `POST /api/content/edit-carousel-slide/`
Regenerates a single slide image without re-running the full pipeline.

```json
// Request
{
  "creation_uuid": "...",
  "slide": {
    "index": 2,
    "headline": "Sleep 8 Hours Tonight",
    "body": "Consistent sleep improves focus and mood.",
    "visual_description": "Calm bedroom scene, soft blue tones"
  },
  "visual_theme": "<overall art direction from original carousel>",
  "platform": "instagram",
  "feedback": "Make the background darker",  // optional
  "brand_dna": { ... },
  "identity": { ... }
}

// Response
{
  "uuid": "<creation_uuid>",
  "slide": {
    "index": 2,
    "headline": "Sleep 8 Hours Tonight",
    "image_url": "https://res.cloudinary.com/...",
    "qc_passed": true,
    "qc_attempts": 1
  }
}
```

#### `POST /api/content/generate-video/`
```json
// Request
{
  "topic": "Summer sale announcement",
  "platform": "Instagram Reels",
  "video_tone": "Energetic",
  "num_scenes": 4,
  "scene_duration": 6,
  "brand_dna": {
    "color_palette": {
      "primary": "#FF0000",
      "secondary": "#0D0D0D",
      "accent": "#000000",
      "complementary": ["#FF0000", "#000000", "#FFFFFF"]
    },
    "typography": {
      "body": "Playfair Display",
      "heading": "Montserrat"
    },
    "tone": {
      "description": "Chocolate colombiano de origen único, elaborado artesanalmente para explorar los sabores de cada territorio y preservar tradiciones con un enfoque sostenible.",
      "keywords": ["sensorial", "artesanal", "educativo"],
      "voice": "inspirational"
    }
  },
  "identity": {
    "logo_url": "https://tapita.io/pb/pub/media/spb/usr/8739/wysiwyg/77362987294/Tibito-logo.png.webp",
    "name": "Tibitó",
    "slug": "tibitó",
    "site_url": "https://tibito.co/"
  }
}

// Response
{
  "uuid": "<creation_uuid>",
  "scenes": [
    {
      "scene_number": 1,
      "type": "hook",
      "scene_description": "...",
      "video_url": "https://res.cloudinary.com/...",
      "filtered": false,
      "filter_reason": null,
      "error": null
    }
  ],
  "caption": "...",
  "hashtags": ["#summer", "#sale"]
}
```

#### `POST /api/brand-dna/extract/`
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
