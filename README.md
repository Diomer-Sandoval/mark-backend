# Mark Backend

## Overview
Mark Backend is the core API and service layer for an AI-driven marketing agent. This system is designed to automate and enhance digital marketing workflows by generating creative assets such as images and video carousels. Additionally, it provides robust features for managing social media publications, tracking performance insights, and automating various other marketing tasks.

## Features
- **Asset Generation:** Automatically create high-quality images and video carousels for marketing campaigns.
- **Post Management:** Schedule, publish, and seamlessly manage social media posts.
- **Insights & Analytics:** Track performance metrics and gather actionable insights from your marketing efforts.
- **Automated Marketing:** Streamline workflows with AI-driven marketing capabilities.

## Project Structure

```
mark-backend/
├── config/                         # Django project configuration
│   ├── settings.py                 # Project settings
│   ├── urls.py                     # Root URL routing
│   ├── asgi.py
│   └── wsgi.py
│
├── creation_studio/                # App: AI-powered asset creation
│   ├── views.py                    # POST /api/chat/
│   ├── graphs/
│   │   ├── state.py                # AgentState (messages)
│   │   ├── agent.py                # Graph: chat → tools → chat
│   │   └── nodes/
│   │       └── chat/
│   │           ├── node.py         # LLM chat node
│   │           ├── prompt.py       # System prompt
│   │           └── tools.py        # Tool definitions
│   └── migrations/
│
├── brand_dna_extractor/            # App: Extract brand DNA from brand input
│   ├── views.py                    # POST /api/brand-dna/extract/
│   ├── urls.py
│   ├── graphs/
│   │   ├── state.py                # BrandDNAState (messages, brand_input, brand_dna)
│   │   ├── agent.py                # Graph: extractor → (tools →) extractor → formatter
│   │   └── nodes/
│   │       ├── extractor/
│   │       │   ├── node.py         # LLM node: extracts raw brand attributes
│   │       │   ├── prompt.py       # System prompt
│   │       │   └── tools.py        # fetch_brand_website tool
│   │       └── formatter/
│   │           ├── node.py         # LLM node: structures output as JSON
│   │           └── prompt.py       # System prompt
│   └── migrations/
│
├── manage.py
├── pyproject.toml
└── poetry.lock
```

## Requirements
To run this project, you will need the following installed on your system:
- **Python:** version `>= 3.12`
- **Poetry:** Used for dependency management. You can install it following the instructions [here](https://python-poetry.org/docs/).

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd mark-backend
   ```

2. **Install dependencies:**
   Using Poetry, install the required packages (including Django):
   ```bash
   poetry install
   ```

## Running the Project

1. **Apply database migrations:**
   Before running the application for the first time, make sure your database is set up:
   ```bash
   poetry run python manage.py migrate
   ```

2. **Start the development server:**
   ```bash
   poetry run python manage.py runserver
   ```
   
   The backend API will now be accessible at `http://127.0.0.1:8000/`.