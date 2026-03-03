# Mark Backend

## Overview
Mark Backend is the core API and service layer for an AI-driven marketing agent. This system is designed to automate and enhance digital marketing workflows by generating creative assets such as images and video carousels. Additionally, it provides robust features for managing social media publications, tracking performance insights, and automating various other marketing tasks.

## Features
- **Asset Generation:** Automatically create high-quality images and video carousels for marketing campaigns.
- **Post Management:** Schedule, publish, and seamlessly manage social media posts.
- **Insights & Analytics:** Track performance metrics and gather actionable insights from your marketing efforts.
- **Automated Marketing:** Streamline workflows with AI-driven marketing capabilities.

## Project Structure
- **`config/`**: Contains the core Django project settings, URL configurations, and WSGI/ASGI specifications.
- **`creation_studio/`**: The main application responsible for asset creation. It handles the generation of images, videos, and carousels using AI.
- **`manage.py`**: Django's command-line utility for administrative tasks.
- **`pyproject.toml` & `poetry.lock`**: Configuration files for Poetry dependency management.

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