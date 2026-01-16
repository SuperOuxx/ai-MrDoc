# Repository Guidelines

## Project Structure & Module Organization
- `MrDoc/` holds the Django project (`settings.py`, `urls.py`, `wsgi.py`).
- `app_admin/`, `app_ai/`, `app_api/`, `app_doc/` are the main Django apps.
- `template/` contains HTML templates; `static/` contains frontend assets.
- `media/` stores user uploads; `locale/` is for translations.
- `whoosh_index/` is the search index; `log/` contains runtime logs.
- Config and deployment helpers live in `config/`, `Dockerfile`, `docker-compose.yml`, and scripts like `docker_mrdoc.sh`.

## Build, Test, and Development Commands
- `pip install -r requirements.txt` installs Python dependencies.
- `python manage.py makemigrations` and `python manage.py migrate` set up the database schema.
- `python manage.py createsuperuser` creates an admin account.
- `python manage.py runserver` starts the Django dev server.
- `python manage.py test` runs the test suite.

## Coding Style & Naming Conventions
- Follow Django/Python conventions (4-space indentation, snake_case for modules/functions).
- Keep app-specific code inside the matching `app_*` directory.
- Template names should reflect the app and view (e.g., `template/app_doc/document_detail.html`).
- If you add formatting or linting, keep it consistent with existing style (no enforced tool in repo).

## Testing Guidelines
- Tests use Django’s `TestCase` in app `tests.py` files.
- Name tests by behavior, not implementation (e.g., `test_public_project_read_permission`).
- Run targeted tests with `python manage.py test app_doc` or module paths.

## Commit & Pull Request Guidelines
- Recent commits use concise, single-line summaries; some use prefixes like `feat:`.
- Keep commit subjects short and descriptive; use English or Chinese consistently within a PR.
- PRs should include a brief description, testing notes, and screenshots for UI changes.
- Link related issues when applicable.

## Security & Configuration Tips
- Store secrets in environment-specific settings, not in source control.
- Keep `whoosh_index/` and `media/` out of PRs unless the change is intentional.
