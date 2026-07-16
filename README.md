<div align="center">
  <h1>🎓 StudyMate AI HUB</h1>
  <p><strong>Transforming Raw Academic Study Materials into Interactive, AI-Powered Learning Hubs</strong></p>

  <!-- Badges -->
  <p>
    <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" alt="FastAPI" />
    <img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12+" />
    <img src="https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white" alt="Google Gemini AI" />
    <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL Neon" />
    <img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="Tailwind CSS" />
    <img src="https://img.shields.io/badge/AsyncIO-Full%20Async-009688?style=for-the-badge" alt="AsyncIO" />
  </p>
</div>

---

## 🌟 Executive Summary

**StudyMate AI HUB** is an enterprise-grade academic productivity platform built with **FastAPI (Async)** and **Google Gemini AI**. It addresses the friction of digesting complex academic textbooks, lecture slides (`.pptx`), research papers (`.pdf`), and handwritten notes (`.docx` / images) by instantly converting raw documents into **interactive, multi-modal learning experiences**.

Designed with **decoupled client-server architecture**, real-time **Server-Sent Events (SSE)** streaming, **AES-256-GCM encryption** for user credentials, and serverless **PostgreSQL (Neon)** storage, StudyMate AI HUB represents modern, type-safe full-stack engineering best practices.

---

## 🏗️ System Architecture

StudyMate AI HUB enforces strict separation of concerns between its static frontend presentation layer and asynchronous backend services:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Client Presentation Layer                     │
│   Vanilla HTML5 + CSS3 (Tailwind CSS v4) + ES2024 Modules + Lucide     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │  REST / Server-Sent Events (SSE)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Asynchronous Gateway                    │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                         API Routers                            │   │
│   │   • /api/v1/auth   • /api/v1/features   • /api/v1/upload       │   │
│   │   • /api/v1/history  • /api/v1/export                          │   │
│   └────────────────────────────────────────────────────────────────┘   │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                        Core Services                           │   │
│   │   • JWT Auth & Google OAuth 2.0  • AES-256-GCM Key Encryption  │   │
│   │   • Document Parser (PyMuPDF, docx, pptx, Pillow OCR)          │   │
│   │   • ReportLab PDF Generator & S3 Object Storage Service        │   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────┬──────────────────────────┬───────────────────────────┬────────┘
         │                          │                           │
         ▼                          ▼                           ▼
┌──────────────────┐      ┌──────────────────┐       ┌───────────────────┐
│ Neon PostgreSQL  │      │  Google Gemini   │       │  AWS S3 / S3-Compat│
│  (SQLAlchemy 2.0 │      │  3.5 Flash LLM   │       │  Object & File    │
│    Async ORM)    │      │  (Streaming SSE) │       │  Storage Service  │
└──────────────────┘      └──────────────────┘       └───────────────────┘
```

---

## ✨ Key Features & Capabilities

### 📄 1. Multi-Modal Document Engine
- **Universal Ingestion**: Extracts structured text and metadata from **PDFs** (`PyMuPDF`), **Word Documents** (`python-docx`), **PowerPoint Slides** (`python-pptx`), and **High-Res Images** (`Pillow` OCR / Base64).
- **Intelligent Caching & Deduplication**: SHA-256 file hashing prevents redundant LLM processing across user sessions.

### 📝 2. Academic Study Notes Generator (`SSE Streaming`)
- Produces university-grade, hierarchical study notes formatted with clear section headings, concept definitions, bulleted summaries, and key takeaways.
- **Real-Time Streaming**: Uses **FastAPI `StreamingResponse` (SSE)** to stream chunks smoothly to the browser, accompanied by live step-by-step progress indicators (`Analyzing document...` ➔ `Extracting text...` ➔ `Generating notes...`).

### 🎯 3. Interactive MCQ Quiz Engine
- Dynamically generates custom multiple-choice quizzes tailored by **difficulty** (`Easy`, `Medium`, `Hard`) and **question count**.
- **Instant Grading & Explanations**: Features interactive client-side grading with detailed conceptual explanations (`💡`) for both correct and incorrect answers.

### 🧠 4. Dynamic Mind Map Visualization
- Automatically extracts conceptual hierarchies (`root` ➔ `branches` ➔ `leaf nodes`) and renders them using **HTML5 Canvas**.
- **Custom Hierarchical Layout**: Implements a custom tree-layout algorithm with radial color gradients (`rgba`), smooth click-and-drag panning, scroll-to-zoom, and touch-screen support.

### 🃏 5. Flashcard Deck & Revision Cheat Sheet Builders
- **Flashcard Study Mode**: Creates flip-cards designed for active recall and spaced repetition.
- **Exam Cheat Sheets**: Synthesizes massive documents into ultra-dense, bulleted review sheets tailored for high-speed pre-exam study.

### 🛡️ 6. Enterprise-Grade Security & Authentication
- **Dual Authentication**: Supports both secure local JWT bearer authentication (`python-jose` + `passlib[bcrypt]`) and **Google OAuth 2.0** (`authlib`).
- **Encrypted API Key Vault**: Users can bring their own Google Gemini API keys, which are securely encrypted at rest using **AES-256-GCM** (`cryptography`).

### 📦 7. ReportLab PDF Export Service
- Allows instant one-click export of generated notes, quiz results, and revision sheets into polished, professional PDF documents (`ReportLab` / `WeasyPrint`).

---

## 💻 Technology Stack

| Layer | Technologies & Tools | Key Responsibilities |
| :--- | :--- | :--- |
| **Backend API** | **FastAPI (`^0.115`)**, Python 3.12+, Uvicorn (`^0.34`) | High-performance asynchronous REST API & SSE streaming gateway |
| **Database & ORM** | **PostgreSQL (Neon.tech)**, **SQLAlchemy 2.0 Async (`asyncpg`)**, Alembic | Type-safe asynchronous data persistence and migration tracking |
| **AI / LLM Layer** | **Google Gemini (`google-generativeai ^0.8`)**, Gemini 3.5 Flash | Advanced natural language synthesis and structured JSON/Markdown extraction |
| **Frontend UI** | HTML5, **Tailwind CSS v4**, ES2024 Modules, Lucide Icons | Responsive, state-driven user interface with zero heavy bundle overhead |
| **Document Processing** | PyMuPDF (`fitz`), `python-docx`, `python-pptx`, `Pillow`, `python-magic` | High-fidelity parsing across all major academic file formats |
| **PDF Generation** | **ReportLab (`^4.3`)**, WeasyPrint | Server-side programmatic PDF generation |
| **Testing & Quality** | `pytest`, `pytest-asyncio`, `httpx`, **Playwright (`E2E`)**, `mypy`, `ruff` | Complete unit, integration, type, lint, and browser E2E coverage |

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
- **Python 3.12+** installed on your system.
- **PostgreSQL database instance** (e.g., free serverless database at [Neon.tech](https://neon.tech/)).
- **Google Gemini API Key** (obtainable from [Google AI Studio](https://aistudio.google.com/)).

### 2. Repository Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/StudyMate.git
cd StudyMate

# Create and activate a virtual environment
python -m venv .venv
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -e .
# Or via requirements:
pip install -r pyproject.toml
```

### 3. Environment Configuration
Copy the `.env.example` template and configure your connection strings:
```bash
cp .env.example .env
```
Ensure your `.env` contains the following critical keys:
```ini
DATABASE_URL="postgresql+asyncpg://user:password@ep-xxxx.us-east-1.aws.neon.tech/studymate?sslmode=require"
JWT_SECRET="your-256-bit-secure-random-jwt-secret-key"
ENCRYPTION_SECRET="your-64-character-hexadecimal-secret-for-aes-256-gcm"
GOOGLE_CLIENT_ID="optional-for-oauth"
GOOGLE_CLIENT_SECRET="optional-for-oauth"
```

### 4. Database Migrations
Run Alembic migrations to build the database tables (`users`, `api_keys`, `file_records`, `document_cache`, `session_outputs`):
```bash
alembic upgrade head
```

### 5. Launch the Application Server
Start the Uvicorn asynchronous development server:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Open your browser and navigate to **[http://127.0.0.1:8000](http://127.0.0.1:8000)** to experience StudyMate AI HUB!

---

## 🧪 Testing & Verification

StudyMate AI HUB includes a rigorous test suite covering API endpoints, database transactions, and browser automation:

```bash
# Run all unit and integration tests with pytest & asyncio
pytest tests/ -v --asyncio-mode=auto

# Check code type safety with mypy
mypy app/

# Run code linter & formatter checks
ruff check app/ static/js/
```

---

## 📁 Project Structure

```
StudyMate/
├── alembic/                  # Alembic asynchronous database migrations
├── app/
│   ├── api/v1/               # REST API Endpoints (Auth, Features, Upload, History, Export)
│   ├── core/                 # App config, database session pool, AES & JWT security utilities
│   ├── models/               # SQLAlchemy 2.0 Async ORM Models
│   ├── schemas/              # Pydantic v2 Request/Response Data Validation Schemas
│   └── services/             # Core Business Logic (Gemini AI Service, File Parser, Storage)
├── static/
│   ├── css/                  # Vanilla CSS + Tailwind v4 Styling System
│   ├── feature/              # Feature Pages (Notes, Quiz, Mindmap, Flashcards, Revision)
│   └── js/                   # Modular ES2024 Frontend JavaScript (API, Auth, Upload, Utils)
├── tests/                    # Pytest Async Integration & API Tests
├── alembic.ini               # Alembic configuration
├── pyproject.toml            # Project dependencies and tool configurations
├── SRS.md                    # Detailed Software Requirements Specification (v2.0)
└── README.md                 # Project Documentation
```

---

## 🤝 Contributing & License

Contributions, bug reports, and feature requests are welcome!  
Distributed under the **MIT License**. See `LICENSE` for more information.

<div align="center">
  <p>Built with ❤️ using <strong>FastAPI</strong>, <strong>PostgreSQL Neon</strong>, and <strong>Google Gemini</strong>.</p>
</div>
