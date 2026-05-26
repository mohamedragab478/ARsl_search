---
title: ARsl Search
emoji: 🤟
colorFrom: purple
colorTo: green
sdk: docker
pinned: false
---

# 🤟 Arabic Sign Language (ArSL) Search

A powerful tool for searching and retrieving Arabic Sign Language (ArSL) GIFs based on Arabic text queries using state-of-the-art NLP models.

---

## Features

- 🔍 **Text-to-Sign Search**: Converts Arabic text to corresponding sign language sequences.
- 🎬 **Sign Language GIF Retrieval**: Automatically generates cohesive sentence-level GIFs.
- 🧠 **Smart NLP Engine**: Uses Arabic NER and E5 text embeddings to understand context.
- ⚡ **Fast Local API**: Built with FastAPI for high-performance and modular design.
- 🌐 **Modern Web Interface**: Glassmorphism UI for a beautiful interactive experience.

---

## Project Structure

```text
ARsl_search/
│
├── app/                       # FastAPI Application Module
│   ├── static/                # Single Page Web App (HTML/CSS/JS)
│   │   ├── index.html
│   │   ├── style.css
│   │   └── app.js
│   ├── config.py              # System configuration and directories
│   ├── synonyms.py            # Arabic Synonyms dictionary and alphabet maps
│   ├── utils.py               # Preprocessing and frame extraction helpers
│   ├── engine.py              # Search engine, corpus embeddings, and NLP
│   ├── schemas.py             # Pydantic schemas for requests/responses
│   └── main.py                # FastAPI endpoints, CORS, static routes
│
├── data_gifs/                 # Dataset folder containing 514 sign GIFs
├── output/                    # Cached/generated combined sentence GIFs
├── KARSL-502_Labels.xlsx      # Sign dictionary definitions sheet
├── sign_search.py             # Legacy Gradio UI (re-engineered)
├── pyproject.toml
└── README.md
```

---

## Requirements

- Python 3.11+
- uv package manager

Install uv:
```bash
pip install uv
```

---

## Installation

Clone the repository:
```bash
git clone https://github.com/mohamedragab478/ARsl_search.git
cd ARsl_search
```

Install dependencies:
```bash
uv sync
```

---

## Dataset Setup

The project requires the `data_gifs` folder containing all ArSL GIF files.
Place the folder in the project root:
```text
ARsl_search/
│
└── data_gifs/
    ├── 0001.gif
    ├── 0002.gif
    └── ...
```

> Note:
> The dataset is not included in this repository because of its large size. You can download it from ["https://github.com/mohamedragab478/ARsl_search/releases/download/ARsl_search/data_gifs.zip"] and extract it here.

---

## Running the Project

You can run either the modern FastAPI web server (which serves the single-page application and API endpoints) or the legacy Gradio interface.

### Option A: Run the FastAPI Web Server (Recommended)
This launches a modern, fast, responsive web interface at `http://127.0.0.1:8000` with visual word analysis, spelling toggles, and dictionary browser.

```bash
uv run uvicorn app.main:app --reload
```

Open your browser and navigate to `http://127.0.0.1:8000`.

### Option B: Run the Gradio Interface
This runs the legacy dashboard interface using the refactored backend engine:

```bash
uv run python sign_search.py
```

---

## API Documentation

When running the FastAPI server, you can view the interactive OpenAPI documentation at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- Redoc: `http://127.0.0.1:8000/redoc`

### Core Endpoints:
- `POST /api/analyze`: Takes a sentence and threshold to identify person names and semantic dictionary matches.
- `POST /api/generate`: Synthesizes visual sign language sequences into a single GIF.
- `GET /api/signs`: Lists all 502 available sign language labels with synonyms and metadata.

---

## Notes

- Make sure the `data_gifs` folder exists in the root directory before running the servers.
- The system automatically caches generated sentence GIFs in the `output/` folder based on the request hash to avoid redundant synthesis overhead.

