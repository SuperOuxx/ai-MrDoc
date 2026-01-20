# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup & Installation
```bash
# Install backend dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd -

# Initialize database
python manage.py makemigrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser
```

### Running the Application
```bash
# Start Django development server
python manage.py runserver

# Start Vue dev server (in another terminal)
cd frontend
npm run dev
cd -
```

### Testing
```bash
# Run all tests
python manage.py test

# Run specific test module
python manage.py test app.tests.module_name

# Frontend type-check + build (in frontend/)
cd frontend
npm run build
cd -
```

## Architecture Overview

### Core Components
1. **Django Project Structure**
   - Main settings: `MrDoc/settings.py`
   - URL routing: `MrDoc/urls.py`
   - WSGI configuration: `MrDoc/wsgi.py`

2. **Vue 3 Frontend (SPA)**
   - Vite + TypeScript + Vue Router + Pinia
   - Communicates with `/api/v1/` via Axios

3. **Document Management System**
   - Editor based on Editor.md and Vditor
   - Supports Markdown with extensions for:
     - Images and attachments
     - Flowcharts and sequence diagrams
     - Mind mapping

4. **API System**
   - REST API using Django REST Framework (`app_api_v1/`)
   - JWT authentication via SimpleJWT
   - OpenAPI schema via drf-spectacular

5. **Search Functionality**
   - Powered by Whoosh search engine
   - Integrated through Django Haystack

6. **Export Capabilities**
   - PDF generation
   - ePub file export

7. **AI LLM Capabilities**
   - Dify: ```ai_text_genarate```
   - openai compatible API: ```openai_text_generate```

### Key Directories
- `frontend/`: Vue 3 SPA (Vite + TypeScript)
- `app_api_v1/`: DRF `/api/v1` backend
- `static/`: Legacy frontend assets and editor components
- `template/`: HTML templates
- `media/`: User-uploaded files

### Dependencies Highlights
- Core: Django 4.2
- API: Django REST Framework, SimpleJWT, drf-spectacular
- Search: Whoosh + Django Haystack
- Document Processing: Mammoth, Markdownify
- Editors: Editor.md, Vditor
- Utilities: Pillow, Requests, BeautifulSoup
- Frontend: Vue 3, Vite, Pinia, Vue Router, Axios

### Deployment Notes
- Docker deployment supported via `docker_mrdoc.sh` and `docker-compose.yml`
- Production settings should be configured separately
- Build frontend assets with `npm run build` (outputs to `frontend/dist/`)
