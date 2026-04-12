# ThinkMate

**An AI-Powered Socratic Tutoring Platform for Developing Critical Thinking Skills**

UAEU CETL Innovation in Teaching and Learning Student Projects | May - December 2026

---

## Overview

ThinkMate is a theory-constrained Socratic tutoring platform that develops critical thinking through structured AI dialogue. It separates pedagogical control from language generation: a rule-based move selector determines what the tutor should do next, and only then does the LLM generate the question. A safeguard layer audits every response before delivery.

Grounded in three frameworks:
- **Bloom's Revised Taxonomy** - cognitive level progression
- **Paul-Elder CT Model** - six intellectual standards
- **ICAP Framework** - engagement classification

## Project Team

| Role | Name | Focus |
|------|------|-------|
| PI | Dr. Sanan H. Khan | System architecture, AI integration |
| Co-PI | Dr. Mariana V. C. Coutinho | Pedagogical design, evaluation |
| UG Engineer | Sara Khaled Alsaedi | Back-end (FastAPI) |
| UG Engineer | Wadima Ahmed Aldhaheri | Front-end (React) |
| UG Humanities | Laiya Khorshed Jamsheer | Prompt library authoring |
| UG Humanities | Salma Alhashmi | Content development |
| Graduate RA | Madni Shifa Ullah Khan | Research coordination, analysis |

## Repository Structure

```
thinkmate-platform/
  docs/                     -- Platform specification and guides
  site/                     -- GitHub Pages landing page
  proposal/                 -- CETL application form (LaTeX + PDF)
  frontend/                 -- React + TypeScript + TailwindCSS
  backend/                  -- FastAPI + Python
  prompt_libraries/         -- Socratic prompt templates per discipline
  course_materials/         -- RAG source documents (to be populated)
  docker-compose.yml        -- Full stack deployment
```

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/thinkmate-platform.git
cd thinkmate-platform

# 2. Copy environment variables
cp .env.example .env
# Edit .env with your API keys

# 3. Start all services
docker-compose up -d

# 4. Access the platform
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
# ChromaDB: http://localhost:8001
```

## Documentation

- [Platform Specification](docs/THINKMATE_PLATFORM_SPEC.md) - Complete technical spec
- [API Reference](docs/API_REFERENCE.md) - Endpoint documentation
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) - Production setup

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Vite + TailwindCSS + shadcn/ui |
| Backend | FastAPI (Python 3.11+) |
| Database | PostgreSQL 15 |
| Vector Store | ChromaDB |
| LLM | OpenAI GPT-4o (primary) / Llama 3.1 (fallback) |
| Deployment | Docker + Docker Compose |

## Status

**Phase: Pre-Pilot Development**

- [x] CETL proposal submitted
- [x] Platform specification complete
- [x] Project landing page live
- [ ] Database schema implemented
- [ ] AI core modules built
- [ ] Frontend dialogue UI
- [ ] Instructor dashboard
- [ ] Red-team testing
- [ ] Pilot deployment (Fall 2026)

## License

This project is developed for UAE University under the CETL Innovation in Teaching and Learning programme.

---

*Contact: sanan.khan@uaeu.ac.ae*
