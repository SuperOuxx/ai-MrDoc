# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup & Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python manage.py makemigrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser
```

### Running the Application
```bash
# Start development server
python manage.py runserver
```

### Testing
```bash
# Run all tests
python manage.py test

# Run specific test module
python manage.py test app.tests.module_name
```

## Architecture Overview

### Core Components
1. **Django Project Structure**
   - Main settings: `MrDoc/settings.py`
   - URL routing: `MrDoc/urls.py`
   - WSGI configuration: `MrDoc/wsgi.py`

2. **Document Management System**
   - Editor based on Editor.md and Vditor
   - Supports Markdown with extensions for:
     - Images and attachments
     - Flowcharts and sequence diagrams
     - Mind mapping

3. **API System**
   - REST API using Django REST Framework
   - Token-based authentication
   - Endpoints for content retrieval and creation

4. **Search Functionality**
   - Powered by Whoosh search engine
   - Integrated through Django Haystack

5. **Export Capabilities**
   - PDF generation
   - ePub file export

6. **AI LLM Capabilities**
   - Dify: ```ai_text_genarate```
   - openai compatible API: ```openai_text_generate```

### Key Directories
- `static/`: Frontend assets and editor components
- `templates/`: HTML templates
- `media/`: User-uploaded files

### Dependencies Highlights
- Core: Django 4.2
- Search: Whoosh + Django Haystack
- Document Processing: Mammoth, Markdownify
- Editors: Editor.md, Vditor
- Utilities: Pillow, Requests, BeautifulSoup

### Deployment Notes
- Docker deployment supported via `docker-install.sh`
- Production settings should be configured separately