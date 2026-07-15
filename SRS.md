# Software Requirements Specification (SRS)
## StudyMate AI HUB

**Version:** 2.0  
**Date:** July 15, 2026  
**Project Type:** Academic Productivity Web Application  
**Target Platform:** Web (Desktop & Mobile Responsive)  
**Architecture:** FastAPI Backend + Static HTML/CSS/JS Frontend

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Functional Requirements](#4-functional-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [User Roles & Permissions](#6-user-roles--permissions)
7. [Database Design](#7-database-design)
8. [API Specifications](#8-api-specifications)
9. [UI/UX Specifications](#9-ux-specifications)
10. [Security Requirements](#10-security-requirements)
11. [Performance Requirements](#11-performance-requirements)
12. [Deployment Requirements](#12-deployment-requirements)
13. [Glossary](#13-glossary)

---

## 1. Introduction

### 1.1 Purpose
This Software Requirements Specification (SRS) document provides a comprehensive description of the **StudyMate AI HUB** application. It defines the functional and non-functional requirements, system architecture, technology stack, database design, API specifications, and all other relevant details for developers, stakeholders, and QA teams.

### 1.2 Scope
StudyMate AI HUB is a premium modern academic productivity web application that transforms raw study materials — including textbooks, PDFs, lecture slides, notes, and images — into structured, interactive learning formats. The application leverages Google Gemini AI to generate notes, flashcards, mind maps, MCQ quizzes, and revision cheat sheets. It provides user authentication, file management, history tracking, PDF export, and personalized theming.

The application follows a **decoupled architecture**: a Python/FastAPI backend serving RESTful APIs, and a static frontend built with vanilla HTML, CSS, and JavaScript that communicates with the backend via fetch/XHR.

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|---|---|
| SRS | Software Requirements Specification |
| AI | Artificial Intelligence |
| LLM | Large Language Model |
| MCQ | Multiple Choice Question |
| OCR | Optical Character Recognition |
| OAuth | Open Authorization |
| JWT | JSON Web Token |
| ORM | Object-Relational Mapping |
| API | Application Programming Interface |
| PDF | Portable Document Format |
| DOCX | Word Open XML Document |
| PPTX | PowerPoint Open XML Presentation |
| AES | Advanced Encryption Standard |
| GCM | Galois/Counter Mode |
| OTP | One-Time Password |
| SMTP | Simple Mail Transfer Protocol |
| ASGI | Asynchronous Server Gateway Interface |
| SPA | Single Page Application |
| MPA | Multi-Page Application |

### 1.4 References
- FastAPI Documentation: https://fastapi.tiangolo.com
- SQLAlchemy Documentation: https://docs.sqlalchemy.org
- Alembic Documentation: https://alembic.sqlalchemy.org
- Google Gemini API Documentation: https://ai.google.dev/docs
- Tailwind CSS v4 Documentation: https://tailwindcss.com/docs
- ReportLab Documentation: https://www.reportlab.com/docs
- Google OAuth 2.0: https://developers.google.com/identity/protocols/oauth2

---

## 2. System Architecture

### 2.1 Architecture Overview
StudyMate AI HUB follows a **decoupled client-server architecture**. The frontend is a static multi-page application (MPA) built with vanilla HTML5, CSS3, and JavaScript, served by a web server or CDN. The backend is a Python-based REST API built with FastAPI, running on an ASGI server (Uvicorn). The architecture is divided into:

- **Presentation Layer**: Static HTML pages styled with Tailwind CSS v4, enhanced with vanilla JavaScript for interactivity, AJAX calls, and DOM manipulation
- **Application Layer**: FastAPI route handlers and background task processors
- **Data Layer**: SQLAlchemy (async) ORM with Neon PostgreSQL (serverless)
- **AI Layer**: Google Gemini API via `google-generativeai` Python SDK
- **Storage Layer**: AWS S3-compatible object storage with local filesystem fallback

### 2.2 High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    Client Browser                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐   │
│  │  HTML5   │  │  CSS3    │  │  Vanilla │  │  localStorage│   │
│  │  Pages   │  │(Tailwind)│  │    JS    │  │  (Theme,     │   │
│  │          │  │          │  │ (fetch/  │  │   Session)   │   │
│  │          │  │          │  │  XHR)    │  │              │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────────┘   │
│       │              │              │                          │
└───────┼──────────────┼──────────────┼──────────────────────────┘
        │              │              │
        ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend Server                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              API Route Handlers (/api/*)                    │  │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │  │
│  │  │  Auth   │ │ Features │ │ History  │ │ Upload/Export │  │  │
│  │  │ /api/auth│ │/api/feat.│ │/api/hist.│ │ /api/upload   │  │  │
│  │  └─────────┘ └──────────┘ └──────────┘ │ /api/export   │  │  │
│  │                                        └──────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Core Python Libraries                    │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │  │
│  │  │   Auth   │ │SQLAlchemy│ │  Gemini  │ │   Parsers    │  │  │
│  │  │ JWT+OAuth│ │   ORM    │ │  Python  │ │pdf/docx/pptx │  │  │
│  │  │ passlib  │ │ Alembic  │ │   SDK    │ │ image/text   │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
 ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐
 │  PostgreSQL  │  │  Google Gemini   │  │  S3 / Local FS   │
 │  (Neon.tech) │  │  AI API          │  │  (File Storage)   │
 │  Serverless  │  │  (LLM)           │  │                   │
 └──────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 3. Technology Stack

### 3.1 Frontend (Static Web)

| Component | Technology | Version | Purpose |
|---|---|---|---|
| Markup | HTML5 | — | Semantic page structure |
| Styling | CSS3 + Tailwind CSS | ^4 | Utility-first responsive styling |
| Scripting | Vanilla JavaScript | ES2024+ | DOM manipulation, fetch/XHR, interactivity |
| Icons | Lucide (CDN) | — | SVG icon library (via CDN script) |
| Animation | CSS Animations + Transitions | — | UI animations and micro-interactions |
| Fonts | Google Fonts (Playfair Display, Inter) | — | Typography |
| Mind Map Canvas | HTML5 Canvas / SVG | — | Interactive mind map rendering |
| PDF Viewing | Native `<embed>` / `<iframe>` | — | In-browser PDF preview |

### 3.2 Backend (Python/FastAPI)

| Component | Technology | Version | Purpose |
|---|---|---|---|
| Web Framework | FastAPI | ^0.115 | High-performance async REST API framework |
| ASGI Server | Uvicorn | ^0.34 | ASGI server for running FastAPI |
| Language | Python | ^3.12 | Backend programming language |

### 3.3 Database & ORM

| Component | Technology | Version | Purpose |
|---|---|---|---|
| Database | PostgreSQL (Neon.tech) | Serverless | Primary data store |
| ORM | SQLAlchemy (async) | ^2.0 | Async ORM with type-safe queries |
| Migration Tool | Alembic | ^1.14 | Database migration management |
| DB Driver | asyncpg | ^0.30 | Async PostgreSQL driver |
| Connection Pool | asyncpg pool | — | Connection pooling for Neon |

### 3.4 Authentication

| Component | Technology | Version | Purpose |
|---|---|---|---|
| Auth Framework | FastAPI + python-jose | ^3.4 | JWT token generation & validation |
| OAuth Provider | Google OAuth 2.0 + authlib | ^1.4 | Social login |
| Password Hashing | passlib[bcrypt] | ^1.7 | Secure password hashing |
| Encryption | Python cryptography (AES-256-GCM) | ^44.0 | API key & reset token encryption |

### 3.5 AI & LLM Integration

| Component | Technology | Version | Purpose |
|---|---|---|---|
| AI Provider | google-generativeai | ^0.8 | Google Gemini API Python client |
| Model | Gemini 3.5 Flash | — | Primary LLM for content generation |
| Streaming | FastAPI StreamingResponse | — | Server-Sent Events for real-time streaming |

### 3.6 File Processing

| Component | Technology | Version | Purpose |
|---|---|---|---|
| PDF Parser | PyMuPDF (fitz) | ^1.25 | Extract text from PDF files |
| DOCX Parser | python-docx | ^1.1 | Extract text from Word documents |
| PPTX Parser | python-pptx | ^1.0 | Extract text from PowerPoint files |
| Image Processing | Pillow | ^11.1 | Image resize & base64 encoding for OCR |
| File Type Detection | python-magic | ^0.4 | MIME type detection for uploaded files |

### 3.7 Document Generation

| Component | Technology | Version | Purpose |
|---|---|---|---|
| PDF Generation | ReportLab | ^4.3 | Server-side PDF document creation |
| HTML-to-PDF | WeasyPrint | ^3.1 | Alternative HTML-based PDF generation |

### 3.8 Visualization (Client-Side)

| Component | Technology | Version | Purpose |
|---|---|---|---|
| Mind Map Canvas | HTML5 Canvas API | — | Interactive mind map rendering |
| Graph Layout | Custom JS (dagre-like) | — | Hierarchical node layout algorithm |
| SVG/Canvas Drawing | Vanilla JS | — | Node rendering, zoom, pan interactions |

### 3.9 Storage & Email

| Component | Technology | Version | Purpose |
|---|---|---|---|
| File Storage | boto3 (S3-compatible) | ^1.36 | Cloud object storage (primary) |
| Local Storage | Python pathlib / shutil | Built-in | Local file storage (fallback) |
| Email Service | fastapi-mail | ^1.4 | OTP email delivery via Gmail SMTP |

### 3.10 Development & Quality

| Component | Technology | Version | Purpose |
|---|---|---|---|
| Linting | Ruff | ^0.11 | Python code linting & formatting |
| Type Checking | mypy | ^1.15 | Static type checking for Python |
| Pre-commit Hooks | pre-commit | ^4.2 | Git hook management |
| Unit Testing | pytest | ^8.3 | Python unit & integration tests |
| Async Testing | pytest-asyncio | ^0.26 | Async test support |
| HTTP Testing | httpx | ^0.28 | Async HTTP client for API testing |
| Coverage | pytest-cov | ^6.1 | Test coverage reporting |
| E2E Testing | Playwright | ^1.60 | End-to-end browser testing |

### 3.11 Environment & Configuration

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Neon PostgreSQL connection string (async) |
| `JWT_SECRET` | JWT signing secret |
| `JWT_ALGORITHM` | JWT algorithm (HS256) |
| `JWT_EXPIRY_HOURS` | JWT token expiration in hours |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | Google OAuth redirect URI |
| `S3_ENDPOINT` | S3-compatible storage endpoint |
| `S3_ACCESS_KEY` | S3 access key |
| `S3_SECRET_KEY` | S3 secret key |
| `S3_BUCKET_NAME` | S3 bucket name |
| `ENCRYPTION_SECRET` | 64-char hex key for AES-256-GCM encryption |
| `SMTP_SERVER` | SMTP server hostname |
| `SMTP_PORT` | SMTP server port |
| `SMTP_USERNAME` | SMTP username (Gmail address) |
| `SMTP_PASSWORD` | SMTP app password |
| `FRONTEND_URL` | Frontend base URL (for CORS) |
| `CORS_ORIGINS` | Allowed CORS origins |

---

## 4. Functional Requirements

### 4.1 User Authentication & Account Management

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Users shall be able to register with name, email, and password | High |
| FR-02 | Users shall be able to sign in using email/password credentials | High |
| FR-03 | Users shall be able to sign in using Google OAuth 2.0 | High |
| FR-04 | Users shall be able to reset their password via email OTP verification | High |
| FR-05 | Users shall maintain persistent sessions via JWT tokens stored in localStorage/HttpOnly cookies | High |
| FR-06 | Users shall be able to view and edit their profile (name, image) | Medium |
| FR-07 | Users shall be able to log out, destroying their session | High |

### 4.2 File Upload & Processing

| ID | Requirement | Priority |
|---|---|---|
| FR-08 | Users shall upload files via drag-and-drop or file picker (native HTML5) | High |
| FR-09 | Supported file types: PDF, DOCX, PPTX, TXT, JPG, PNG, WebP | High |
| FR-10 | Maximum file size shall be 25 MB | High |
| FR-11 | Uploaded files shall be stored in S3-compatible object storage (with local filesystem fallback) | High |
| FR-12 | File type validation shall occur client-side (JS) and server-side (python-magic) | High |
| FR-13 | Upload progress shall be displayed to the user via XHR progress events | Medium |
| FR-14 | Text shall be extracted from uploaded files using appropriate Python parsers | High |

### 4.2 AI-Powered Feature Modules

#### 4.2.1 Notes Conversion (FR-15 to FR-18)
| ID | Requirement | Priority |
|---|---|---|
| FR-15 | System shall convert uploaded study material into structured markdown notes | High |
| FR-16 | Notes shall support compact and detailed generation modes | Medium |
| FR-17 | Notes shall be streamed in real-time to the client via Server-Sent Events | High |
| FR-18 | Generated notes shall be savable and viewable from history | High |

#### 4.2.2 Flashcards (FR-19 to FR-22)
| ID | Requirement | Priority |
|---|---|---|
| FR-19 | System shall generate interactive flashcards from study material | High |
| FR-20 | Flashcards shall display a question on front and answer on back (CSS flip animation) | High |
| FR-21 | Users shall navigate through flashcards with previous/next controls | Medium |
| FR-22 | Users shall mark cards as known/unknown for progress tracking | Medium |

#### 4.2.3 MCQ Quiz (FR-23 to FR-26)
| ID | Requirement | Priority |
|---|---|---|
| FR-23 | System shall generate multiple-choice quiz questions from study material | High |
| FR-24 | Users shall configure difficulty level and number of questions | Medium |
| FR-25 | Users shall select answers and receive immediate correctness feedback | High |
| FR-26 | Quiz results shall display score summary with answer review | High |

#### 4.2.4 Mind Maps (FR-27 to FR-30)
| ID | Requirement | Priority |
|---|---|---|
| FR-27 | System shall generate hierarchical mind maps from study material | High |
| FR-28 | Mind maps shall be rendered as interactive, zoomable HTML5 Canvas | High |
| FR-29 | Nodes shall be collapsible/expandable for focused viewing | Medium |
| FR-30 | Mind map structure shall support up to 3 levels of depth | Medium |

#### 4.2.5 Revision Cheat Sheets (FR-31 to FR-33)
| ID | Requirement | Priority |
|---|---|---|
| FR-31 | System shall generate concise revision cheat sheets (max 600 words) | High |
| FR-32 | Revision sheets shall be streamed in real-time via SSE | High |
| FR-33 | Revision sheets shall be formatted for A5/2-column layout | Medium |

### 4.3 History & Session Management

| ID | Requirement | Priority |
|---|---|---|
| FR-34 | Users shall view a chronological list of their past sessions | High |
| FR-35 | History shall be filterable by feature type (notes, flashcards, quiz, etc.) | Medium |
| FR-36 | Users shall view detailed output of any past session | High |
| FR-37 | Users shall delete individual history entries | Medium |
| FR-38 | Users shall download original uploaded files from history | Low |
| FR-39 | Users shall download generated content as PDF from history | Medium |

### 4.4 PDF Export

| ID | Requirement | Priority |
|---|---|---|
| FR-40 | Users shall export any generated content as a PDF document | High |
| FR-41 | PDF templates shall exist for each feature type (notes, flashcards, quiz, mind map, revision) | High |
| FR-42 | PDF generation shall occur server-side using ReportLab | High |

### 4.5 API Key Management

| ID | Requirement | Priority |
|---|---|---|
| FR-43 | Users shall add their own Google Gemini API keys | Medium |
| FR-44 | API keys shall be encrypted at rest using AES-256-GCM | High |
| FR-45 | Users shall view masked API keys in their profile | Medium |
| FR-46 | Users shall delete stored API keys | Medium |
| FR-47 | Feature usage shall be gated on the presence of a valid API key | High |

### 4.6 Personalization

| ID | Requirement | Priority |
|---|---|---|
| FR-48 | Users shall choose from 6 preset color themes | Medium |
| FR-49 | Users shall create custom themes via live color pickers | Low |
| FR-50 | Theme preferences shall persist across sessions via localStorage | Medium |
| FR-51 | Users shall view their usage statistics (files processed, sessions count) | Low |

---

## 5. Non-Functional Requirements

### 5.1 Performance

| ID | Requirement | Priority |
|---|---|---|
| NFR-01 | Page load time shall be under 2 seconds on standard broadband | High |
| NFR-02 | AI content generation shall begin streaming within 5 seconds of request | High |
| NFR-03 | File uploads up to 25 MB shall complete within 30 seconds | Medium |
| NFR-04 | The application shall support at least 100 concurrent users | Medium |
| NFR-05 | Database queries shall execute in under 200ms for standard operations | High |

### 5.2 Security

| ID | Requirement | Priority |
|---|---|---|
| NFR-06 | All passwords shall be hashed using passlib[bcrypt] before storage | High |
| NFR-07 | API keys shall be encrypted using AES-256-GCM before storage | High |
| NFR-08 | Authentication shall use JWT tokens with secure HttpOnly cookie or Authorization header | High |
| NFR-09 | All API routes shall verify user authentication via JWT dependency injection | High |
| NFR-10 | Password reset tokens shall be encrypted and time-limited | High |
| NFR-11 | File type and size validation shall occur on both client and server | High |
| NFR-12 | Environment variables containing secrets shall never be exposed to the client | High |
| NFR-13 | CORS shall be configured to allow only the frontend origin | High |

### 5.3 Reliability & Availability

| ID | Requirement | Priority |
|---|---|---|
| NFR-14 | The system shall handle API failures gracefully with user-friendly error messages | High |
| NFR-15 | File storage shall fall back to local filesystem if S3 storage is unavailable | Medium |
| NFR-16 | AI generation failures shall be reported with clear error messages | High |
| NFR-17 | The system shall maintain data integrity through database transactions | Medium |

### 5.4 Usability

| ID | Requirement | Priority |
|---|---|---|
| NFR-18 | The UI shall be responsive across desktop, tablet, and mobile devices | High |
| NFR-19 | Loading states shall be displayed during all async operations | High |
| NFR-20 | Error states shall be communicated with clear, actionable messages | High |
| NFR-21 | Empty states shall provide guidance on how to use the feature | Medium |
| NFR-22 | The application shall support keyboard navigation where applicable | Medium |

### 5.5 Scalability

| ID | Requirement | Priority |
|---|---|---|
| NFR-23 | The database schema shall support indexing on frequently queried columns (userId, feature, createdAt) | High |
| NFR-24 | File storage shall use S3-compatible object storage for horizontal scalability | Medium |
| NFR-25 | The backend shall be deployable as a stateless service behind a reverse proxy (Nginx) | High |

### 5.6 Maintainability

| ID | Requirement | Priority |
|---|---|---|
| NFR-26 | Code shall be written in Python with type hints and mypy strict mode | High |
| NFR-27 | Database schema changes shall be managed through Alembic migrations | High |
| NFR-28 | The codebase shall follow consistent linting and formatting rules (Ruff) | Medium |
| NFR-29 | Pre-commit hooks shall enforce code quality standards via pre-commit framework | Medium |

---

## 6. User Roles & Permissions

### 6.1 Anonymous User
- Can view landing page, features page, and about page
- Cannot access any feature tools
- Cannot upload files
- Cannot view history
- Redirected to login page when attempting protected routes

### 6.2 Authenticated User
- Can access all feature tools (notes, flashcards, quiz, mind map, revision)
- Can upload and process files
- Can view and manage personal history
- Can manage profile settings and theme preferences
- Can add/delete personal Gemini API keys
- Can export content as PDF
- Can view personal usage statistics

---

## 7. Database Design

### 7.1 Entity-Relationship Overview

```
users (1) ─────< accounts (N)
users (1) ─────< sessions (N)
users (1) ─────< api_keys (N)
users (1) ─────< file_records (N)
users (1) ─────< sessions_output (N)
file_records (1) ─────< sessions_output (N)
```

### 7.2 Table Specifications

#### 7.2.1 `users`
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | uuid | PK, DEFAULT gen_random_uuid() | Unique user identifier |
| name | text | NULLABLE | User's display name |
| email | text | NOT NULL, UNIQUE | User's email address |
| emailVerified | timestamp | NULLABLE | Email verification timestamp |
| image | text | NULLABLE | Avatar image URL |
| passwordHash | text | NULLABLE | bcrypt-hashed password (null for OAuth users) |
| createdAt | timestamp | NOT NULL, DEFAULT now() | Account creation timestamp |
| updatedAt | timestamp | NOT NULL, DEFAULT now() | Last update timestamp |

#### 7.2.2 `accounts`
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | uuid | PK | Account identifier |
| userId | uuid | FK -> users.id, ON DELETE CASCADE | Associated user |
| type | text | NOT NULL | Account type (oauth, credentials) |
| provider | text | NOT NULL | Provider name (google, credentials) |
| providerAccountId | text | NOT NULL | Provider-specific account ID |
| refresh_token | text | NULLABLE | OAuth refresh token |
| access_token | text | NULLABLE | OAuth access token |
| expires_at | integer | NULLABLE | Token expiration timestamp |
| token_type | text | NULLABLE | OAuth token type |
| scope | text | NULLABLE | OAuth scope |
| id_token | text | NULLABLE | OAuth ID token |
| session_state | text | NULLABLE | OAuth session state |

**Indexes:** UNIQUE on (provider, providerAccountId)

#### 7.2.3 `sessions`
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | uuid | PK | Session identifier |
| sessionToken | text | NOT NULL, UNIQUE | Session token string |
| userId | uuid | FK -> users.id, ON DELETE CASCADE | Associated user |
| expires | timestamp | NOT NULL | Session expiration |

#### 7.2.4 `verificationTokens`
| Column | Type | Constraints | Description |
|---|---|---|---|
| identifier | text | NOT NULL | Token identifier (email) |
| token | text | NOT NULL | Verification token |
| expires | timestamp | NOT NULL | Token expiration |

**Primary Key:** COMPOSITE (identifier, token)

#### 7.2.5 `api_keys`
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | uuid | PK | Key identifier |
| userId | uuid | FK -> users.id, ON DELETE CASCADE | Key owner |
| provider | text | NOT NULL | API provider (e.g., "gemini") |
| encryptedKey | text | NOT NULL | AES-256-GCM encrypted key |
| label | text | NULLABLE | User-friendly label |
| isActive | boolean | NOT NULL, DEFAULT true | Whether key is active |
| createdAt | timestamp | NOT NULL, DEFAULT now() | Creation timestamp |
| updatedAt | timestamp | NOT NULL, DEFAULT now() | Last update timestamp |

**Indexes:** ON (userId)

#### 7.2.6 `file_records`
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | uuid | PK | File record identifier |
| userId | uuid | FK -> users.id, ON DELETE CASCADE | Uploading user |
| originalName | text | NOT NULL | Original filename |
| fileUrl | text | NOT NULL | Storage URL/path |
| fileType | text | NOT NULL | File extension (pdf, docx, pptx, txt, image) |
| fileSize | integer | NULLABLE | File size in bytes |
| feature | text | NOT NULL | Target feature (notes, flashcards, quiz, mindmap, revision) |
| status | text | NOT NULL, DEFAULT 'pending' | Processing status (pending, processing, done, failed) |
| errorMessage | text | NULLABLE | Error details if failed |
| createdAt | timestamp | NOT NULL, DEFAULT now() | Upload timestamp |

**Indexes:** ON (userId), ON (feature)

#### 7.2.7 `sessions_output`
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | uuid | PK | Output identifier |
| fileRecordId | uuid | FK -> file_records.id, ON DELETE CASCADE, NULLABLE | Source file record |
| userId | uuid | FK -> users.id, ON DELETE CASCADE | Owning user |
| feature | text | NOT NULL | Feature type |
| outputJson | jsonb | NULLABLE | Structured JSON output (flashcards, quiz, mindmap) |
| outputText | text | NULLABLE | Text output (notes, revision) |
| pdfUrl | text | NULLABLE | Generated PDF URL |
| createdAt | timestamp | NOT NULL, DEFAULT now() | Creation timestamp |

**Indexes:** ON (userId), ON (fileRecordId)

---

## 8. API Specifications

All API endpoints are served from the FastAPI backend at `/api/*`. Authentication is via JWT Bearer token in the `Authorization` header (or HttpOnly cookie for browser-based flows). All endpoints return JSON responses unless otherwise specified.

### 8.1 Authentication APIs

#### `POST /api/auth/register`
- **Description:** Register a new user with email and password
- **Request Body:** `{ name: string, email: string, password: string }`
- **Response:** `201 { user: { id, name, email }, access_token: string }` or `400 { detail: string }`
- **Validation:** Email format, password length (min 8 chars), unique email

#### `POST /api/auth/login`
- **Description:** Authenticate user with email and password
- **Request Body:** `{ email: string, password: string }`
- **Response:** `200 { user: { id, name, email, image }, access_token: string, token_type: "bearer" }` or `401 { detail: string }`

#### `GET /api/auth/google/login`
- **Description:** Initiate Google OAuth flow
- **Response:** `302` Redirect to Google consent screen

#### `GET /api/auth/google/callback`
- **Description:** Handle Google OAuth callback
- **Query Params:** `code`, `state`
- **Response:** `302` Redirect to frontend with JWT token in URL fragment or set as cookie

#### `POST /api/auth/forgot-password`
- **Description:** Send OTP to user's email for password reset
- **Request Body:** `{ email: string }`
- **Response:** `200 { message: string }` or `404 { detail: string }`

#### `POST /api/auth/verify-otp`
- **Description:** Verify OTP and return a reset token
- **Request Body:** `{ email: string, otp: string }`
- **Response:** `200 { resetToken: string }` or `400 { detail: string }`

#### `POST /api/auth/reset-password`
- **Description:** Reset password using verified reset token
- **Request Body:** `{ resetToken: string, newPassword: string }`
- **Response:** `200 { message: string }` or `400 { detail: string }`

### 8.2 Feature APIs

#### `POST /api/features/notes`
- **Description:** Generate structured notes from uploaded file
- **Authentication:** Required (JWT Bearer)
- **Request Body:** `{ fileRecordId: string, mode?: "compact" | "detailed" }`
- **Response:** Streaming text via `text/event-stream` (Server-Sent Events)
- **Flow:** Extract text from file → Build prompt → Gemini streaming generation → Save to sessions_output

#### `POST /api/features/flashcards`
- **Description:** Generate interactive flashcards from uploaded file
- **Authentication:** Required (JWT Bearer)
- **Request Body:** `{ fileRecordId: string }`
- **Response:** `200 { flashcards: Flashcard[] }` where Flashcard = `{ id, question, answer }`
- **Flow:** Extract text → Build prompt → Gemini JSON generation → Save to sessions_output

#### `POST /api/features/quiz`
- **Description:** Generate MCQ quiz questions from uploaded file
- **Authentication:** Required (JWT Bearer)
- **Request Body:** `{ fileRecordId: string, difficulty?: "easy" | "medium" | "hard", count?: number }`
- **Response:** `200 { questions: QuizQuestion[] }` where QuizQuestion = `{ id, question, options: string[], correctAnswer: number }`
- **Flow:** Extract text → Build prompt → Gemini JSON generation → Save to sessions_output

#### `POST /api/features/mindmap`
- **Description:** Generate hierarchical mind map from uploaded file
- **Authentication:** Required (JWT Bearer)
- **Request Body:** `{ fileRecordId: string }`
- **Response:** `200 { mindmap: MindMapNode }` where MindMapNode = `{ id, label, children: MindMapNode[] }`
- **Flow:** Extract text → Build prompt → Gemini JSON generation → Save to sessions_output

#### `POST /api/features/revision`
- **Description:** Generate concise revision cheat sheet from uploaded file
- **Authentication:** Required (JWT Bearer)
- **Request Body:** `{ fileRecordId: string }`
- **Response:** Streaming text via `text/event-stream` (Server-Sent Events)
- **Flow:** Extract text → Build prompt (max 600 words) → Gemini streaming → Save to sessions_output

### 8.3 Upload API

#### `POST /api/upload`
- **Description:** Upload a file to storage
- **Authentication:** Required (JWT Bearer)
- **Request Body:** multipart/form-data with file field (via `python-multipart`)
- **Response:** `200 { fileRecordId: string, fileUrl: string, fileType: string, originalName: string, fileSize: int }`
- **Validation:** File type whitelist (via python-magic), max 25MB size
- **Storage:** S3-compatible object storage (primary) → local `uploads/` directory (fallback)

### 8.4 History APIs

#### `GET /api/history`
- **Description:** List user's file records
- **Authentication:** Required (JWT Bearer)
- **Query Parameters:** `?feature=notes|flashcards|quiz|mindmap|revision` (optional filter)
- **Response:** `200 { history: HistoryItem[] }`

#### `GET /api/history/{id}`
- **Description:** Get detailed session information including output
- **Authentication:** Required (JWT Bearer)
- **Response:** `200 { fileRecord: FileRecord, output: SessionsOutput }`

#### `DELETE /api/history/{id}`
- **Description:** Delete a session and associated file record (cascade)
- **Authentication:** Required (JWT Bearer)
- **Response:** `200 { message: string }`

#### `GET /api/history/{id}/file`
- **Description:** Stream the original uploaded file
- **Authentication:** Required (JWT Bearer)
- **Response:** Binary file stream with appropriate Content-Type and Content-Disposition headers (via `FileResponse`)

#### `GET /api/history/{id}/pdf`
- **Description:** Generate and stream a PDF of the session output
- **Authentication:** Required (JWT Bearer)
- **Response:** PDF binary stream (via `StreamingResponse` with `application/pdf`)

### 8.5 Profile APIs

#### `GET /api/profile`
- **Description:** Fetch user profile and usage statistics
- **Authentication:** Required (JWT Bearer)
- **Response:** `200 { user: User, stats: { totalFiles, totalSessions, ... } }`

#### `PATCH /api/profile`
- **Description:** Update user profile (name, image)
- **Authentication:** Required (JWT Bearer)
- **Request Body:** `{ name?: string, image?: string }`
- **Response:** `200 { user: User }`

#### `GET /api/profile/api-keys`
- **Description:** List user's API keys (masked)
- **Authentication:** Required (JWT Bearer)
- **Response:** `200 { apiKeys: ApiKey[] }` (keys masked as `sk-****...****`)

#### `POST /api/profile/api-keys`
- **Description:** Add a new encrypted API key
- **Authentication:** Required (JWT Bearer)
- **Request Body:** `{ provider: string, key: string, label?: string }`
- **Response:** `201 { apiKey: ApiKey }`

#### `DELETE /api/profile/api-keys/{id}`
- **Description:** Delete an API key
- **Authentication:** Required (JWT Bearer)
- **Response:** `200 { message: string }`

### 8.6 Export API

#### `POST /api/export/pdf`
- **Description:** Generate a PDF export of any feature output
- **Authentication:** Required (JWT Bearer)
- **Request Body:** `{ feature: string, outputText?: string, outputJson?: object }`
- **Response:** PDF binary stream (application/pdf)
- **Templates:** NotesPDF, FlashcardsPDF, QuizPDF, MindMapPDF, RevisionPDF (ReportLab)

---

## 9. UI/UX Specifications

### 9.1 Page Structure

| Route | Page | Type | Description |
|---|---|---|---|
| `/` | Home (Landing) | Static HTML | Hero section, feature cards, call-to-action |
| `/login` | Login | Static HTML | Email/password + Google OAuth sign-in form |
| `/register` | Register | Static HTML | New user registration form |
| `/forgot-password` | Forgot Password | Static HTML | Email input for OTP |
| `/reset-password` | Reset Password | Static HTML | Token-based password reset form |
| `/features` | Features | Static HTML | Detailed feature listing page |
| `/about` | About | Static HTML | Project mission, team, and background |
| `/profile` | Profile | Static HTML | Profile editing, theme settings, API keys, usage stats |
| `/feature/notes` | Notes | Static HTML | Notes conversion tool |
| `/feature/flashcards` | Flashcards | Static HTML | Flashcard generation and review |
| `/feature/quiz` | Quiz | Static HTML | MCQ quiz generation and answering |
| `/feature/mindmap` | Mind Map | Static HTML | Mind map generation and interaction |
| `/feature/revision` | Revision | Static HTML | Revision cheat sheet generation |

### 9.2 Layout Structure

**Root Template (`index.html` / shared layout):**
- Fonts: Playfair Display (headings), Inter (body/sans) via Google Fonts CDN
- Global CSS: Tailwind CSS v4 via CDN + custom `styles.css` with theme variables
- JavaScript modules loaded per-page for interactivity

**Auth Pages (login, register, forgot-password, reset-password):**
- Full-screen centered layout
- No navbar, sidebar, or footer
- Minimal distraction design

**Main Pages (all others):**
- Sticky responsive Navbar at top (semantic `<nav>`)
- Collapsible HistorySidebar on left (feature pages only)
- Main content area (`<main>`)
- Footer at bottom (`<footer>`)

### 9.3 Page Structure (HTML Semantics)

```
<body>
  <header>
    <nav>                                    // Sticky, responsive, mobile hamburger menu
      <a href="/" class="logo">StudyMate AI</a>
      <ul class="nav-links">...</ul>
      <button class="mobile-menu-toggle">☰</button>
    </nav>
  </header>

  <aside class="history-sidebar">            // Feature-filtered, collapsible
    <h2>History</h2>
    <select id="feature-filter">...</select>
    <ul id="history-list">...</ul>
  </aside>

  <main>
    <!-- Feature Guard: JS checks JWT token before rendering feature content -->
    <section class="upload-area">
      <div id="dropzone">                    // Native drag-and-drop
        <p>Drag & drop files here or click to browse</p>
        <input type="file" id="file-input" hidden />
      </div>
      <div id="upload-progress" class="progress-bar" hidden></div>
    </section>

    <section id="feature-output">            // Feature-specific output container
      <!-- Populated dynamically by JavaScript -->
    </section>

    <button id="download-pdf" class="btn" hidden>Download PDF</button>
  </main>

  <footer>
    <p>&copy; 2026 StudyMate AI HUB</p>
  </footer>

  <script src="/js/auth.js" type="module"></script>
  <script src="/js/upload.js" type="module"></script>
  <script src="/js/features/notes.js" type="module"></script>
  <!-- Feature-specific scripts loaded as needed -->
</body>
```

### 9.3 JavaScript Architecture (Vanilla JS Modules)

```
/js/
├── main.js                  // App initialization, theme loading, nav toggle
├── auth.js                  // JWT token management, login/register/logout
├── api.js                   // Centralized fetch wrapper with JWT injection
├── upload.js                // File upload with XHR progress tracking
├── theme.js                 // Theme preset & custom theme management (localStorage)
├── utils.js                 // DOM helpers, markdown-to-HTML converter
├── features/
│   ├── notes.js             // Notes SSE streaming, markdown rendering
│   ├── flashcards.js        // Flashcard deck logic, flip animation, navigation
│   ├── quiz.js              // Quiz rendering, answer selection, scoring
│   ├── mindmap.js           // Canvas-based mind map rendering, zoom, pan
│   └── revision.js          // Revision SSE streaming, A5 layout rendering
└── pages/
    ├── profile.js           // Profile editing, API key management, usage stats
    └── history.js           // History listing, filtering, detail view
```

### 9.4 Theme System

**6 Preset Themes:**
1. **Warm Light** (Default) — Warm neutrals with amber accents
2. **Pure Light (Sky Blue)** — Cool whites with sky blue accents
3. **Warm Dark** — Dark warm tones with amber accents
4. **Slate Dark** — Dark cool tones with slate accents
5. **Midnight Ambient** — Deep blue-black with indigo accents
6. **Forest Ambient** — Dark green with emerald accents

**Custom Theme Variables (CSS custom properties on `:root`):**
- `--color-primary`
- `--color-background`
- `--color-card`
- `--color-text`
- `--color-muted-text`
- `--color-border`

**Persistence:** localStorage keys `studymate-theme` and `studymate-custom-theme-colors`

**Application:** JavaScript sets `data-theme` attribute on `<html>` element; CSS rules in `styles.css` apply corresponding custom property values.

---

## 10. Security Requirements

### 10.1 Authentication & Authorization
- All protected API routes verify JWT via FastAPI dependency injection (`Depends(get_current_user)`)
- JWT strategy with access tokens (short-lived, 15-60 min) and refresh tokens (long-lived, 7 days)
- Passwords hashed with passlib[bcrypt] (salt rounds: 12)
- Google OAuth tokens managed via authlib integration
- CORS restricted to `FRONTEND_URL` origin only

### 10.2 Data Encryption
- API keys encrypted with AES-256-GCM before database storage (Python `cryptography` library)
- Encryption key sourced from `ENCRYPTION_SECRET` environment variable (64 hex characters)
- Password reset tokens encrypted with AES-256-GCM, time-limited (15 minutes)

### 10.3 Input Validation
- File type validation against whitelist using python-magic (MIME type detection)
- File size capped at 25 MB
- Email format validation (Pydantic)
- Password strength validation (minimum 8 characters)
- Pydantic models for all API request validation

### 10.4 Data Protection
- No plaintext secrets in client-side code
- Environment variables for all sensitive configuration
- CORS configured to allow only the frontend origin
- SQL injection prevention via SQLAlchemy parameterized queries
- CSRF protection via token-based auth (JWT in header, not cookies)

---

## 11. Performance Requirements

| Metric | Target | Measurement Method |
|---|---|---|
| Initial Page Load (LCP) | < 2.5s | Lighthouse / Web Vitals |
| Time to Interactive (TTI) | < 3.0s | Lighthouse |
| AI Generation First Token | < 5s | Server-side monitoring |
| File Upload (25MB) | < 30s | Client-side timing |
| API Response (non-streaming) | < 200ms | Server-side logging (FastAPI middleware) |
| Database Query | < 200ms | SQLAlchemy query logging |
| Concurrent Users | 100+ | Load testing (locust) |

---

## 12. Deployment Requirements

### 12.1 Frontend Deployment
- **Platform:** Any static web host (Vercel, Netlify, GitHub Pages, Nginx, S3 static hosting)
- **Build Step:** Tailwind CSS compilation (if using CLI) or CDN-based Tailwind
- **Output:** Static HTML, CSS, JS files served directly

### 12.2 Backend Deployment
- **Platform:** Any Python host (VPS, Railway, Render, Fly.io, AWS EC2, Docker container)
- **ASGI Server:** Uvicorn (with Gunicorn for process management)
- **Reverse Proxy:** Nginx (for production, handles SSL, static file serving, rate limiting)
- **Process Manager:** Supervisor or systemd
- **Containerization:** Docker with multi-stage build (optional)

### 12.3 Infrastructure Dependencies
- **Database:** Neon.tech PostgreSQL (serverless, auto-scaling)
- **File Storage:** S3-compatible object storage (AWS S3, MinIO, DigitalOcean Spaces)
- **AI API:** Google Gemini API
- **Email:** Gmail SMTP (via fastapi-mail)
- **OAuth:** Google Cloud Console (OAuth 2.0 credentials)

### 12.4 CI/CD
- GitHub repository with branch protection
- pre-commit hooks for linting (Ruff, mypy)
- GitHub Actions for automated testing (pytest) on PR
- Automated deployment via GitHub Actions to target platform

---

## 13. Glossary

| Term | Definition |
|---|---|
| **FastAPI** | Modern, high-performance Python web framework for building APIs with automatic OpenAPI documentation |
| **Uvicorn** | ASGI server for running Python async web applications |
| **SQLAlchemy** | Python SQL toolkit and Object-Relational Mapper |
| **Alembic** | Lightweight database migration tool for SQLAlchemy |
| **Neon.tech** | Serverless PostgreSQL platform with automatic scaling |
| **Gemini AI** | Google's large language model API for text generation |
| **google-generativeai** | Official Python SDK for Google Gemini API |
| **ReportLab** | Python library for programmatic PDF document creation |
| **WeasyPrint** | Python library for HTML/CSS to PDF conversion |
| **PyMuPDF (fitz)** | Python library for PDF text extraction and manipulation |
| **python-docx** | Python library for reading and writing Word .docx files |
| **python-pptx** | Python library for reading and writing PowerPoint .pptx files |
| **Pillow** | Python Imaging Library fork for image processing |
| **python-magic** | Python interface to libmagic for file type detection |
| **AES-256-GCM** | Advanced Encryption Standard with 256-bit key in Galois/Counter Mode |
| **python-jose** | JavaScript Object Signing and Encryption implementation in Python |
| **passlib** | Comprehensive password hashing framework for Python |
| **authlib** | Python library for OAuth and OpenID Connect |
| **fastapi-mail** | FastAPI email sending library with SMTP support |
| **boto3** | AWS SDK for Python (S3-compatible storage) |
| **Ruff** | Extremely fast Python linter and formatter written in Rust |
| **mypy** | Static type checker for Python |
| **pytest** | Python testing framework |
| **Server-Sent Events (SSE)** | Standard for server-to-client streaming over HTTP |
| **JWT** | JSON Web Token for stateless authentication |
| **OTP** | One-Time Password for email verification |
| **OCR** | Optical Character Recognition for image text extraction |
| **MCQ** | Multiple Choice Question |
| **LLM** | Large Language Model |

---

## Document Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | July 15, 2026 | System Analysis | Initial SRS document creation (Next.js architecture) |
| 2.0 | July 15, 2026 | System Analysis | Restructured for FastAPI backend + static HTML/CSS/JS frontend. Removed Next.js, React, Drizzle ORM, NextAuth.js, Vercel Blob. Added FastAPI, SQLAlchemy, Alembic, python-jose, passlib, google-generativeai, PyMuPDF, ReportLab, S3 storage, Ruff, pytest. Frontend migrated to vanilla HTML5/CSS3/JS with Tailwind CSS. |
