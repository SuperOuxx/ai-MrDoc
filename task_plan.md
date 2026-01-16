# Task Plan: Front/back separation roadmap (Vue3 + DRF)
<!-- 
  WHAT: This is your roadmap for the entire task. Think of it as your "working memory on disk."
  WHY: After 50+ tool calls, your original goals can get forgotten. This file keeps them fresh.
  WHEN: Create this FIRST, before starting any work. Update after each phase completes.
-->

## Goal
- Deliver a phased migration with DRF `/api/v1` backend and a Vue 3 SPA frontend (with Pinia/Router/Axios) following MIGRATION_PLAN.md, PERMISSION_DESIGN.md, and PERMISSION_REVIEW.md.

## Current Phase
Phase 9

## Phases
<!-- 
  WHAT: Break your task into 3-7 logical phases. Each phase should be completable.
  WHY: Breaking work into phases prevents overwhelm and makes progress visible.
  WHEN: Update status after completing each phase: pending → in_progress → complete
-->

### Phase 1: Requirements & Discovery
- [x] Capture user intent and scope
- [x] Extract constraints from MIGRATION_PLAN.md, PERMISSION_DESIGN.md, PERMISSION_REVIEW.md
- [x] Log findings in findings.md
- **Status:** complete
<!-- 
  STATUS VALUES:
  - pending: Not started yet
  - in_progress: Currently working on this
  - complete: Finished this phase
-->

### Phase 2: Planning & Structure
- [x] Define target architecture (Vue3 SPA + DRF `/api/v1` + JWT + versioning + docs)
- [x] Outline migration milestones (Phase1/1.5/2/3/4/4.5/5) and sequencing
- [x] Record technical decisions and risks in findings.md
- **Status:** complete

### Phase 3: API v1 Foundation (DRF + JWT + Docs)
- [x] Add dependencies (SimpleJWT, drf-spectacular) and settings (REST_FRAMEWORK, SIMPLE_JWT, SPECTACULAR_SETTINGS)
- [x] Create `app_api_v1` scaffold and include in INSTALLED_APPS/urls
- [x] Implement auth endpoints `/auth/login`, `/auth/refresh`, `/users/me` with unified response envelope and API-Version header
- [x] Expose OpenAPI/Swagger at `/api/v1/schema/` and `/api/v1/docs/`
- **Status:** complete

### Phase 4: Permission Layer (Policy + DRF Permissions + Tests)
- [x] Implement policies and DRF permissions per design + review fixes
- [x] Add utils (project/doc readable/writable/manageable helpers)
- [x] Cover with unit tests (>90% coverage) and fix doc/test matrix
- **Status:** complete

### Phase 5: Core Resource APIs
- [x] Implement project/doc read APIs (Phase 2a) using permission layer
- [x] Implement project/doc write APIs (Phase 2b) + history/sort/soft delete)
- [x] Ensure response envelope, version header, and OpenAPI coverage
- **Status:** complete

### Phase 6: Frontend Scaffold & Infra
- [x] Create Vue 3 + TS + Vite app with Router + Pinia + Axios service layer
- [x] Implement base layout, theme variables, typography, and global styles
- [x] Wire Axios interceptors for JWT + refresh + API-Version header
- **Status:** complete

### Phase 7: Frontend Auth & Shell
- [x] Build login page hitting `/api/v1/auth/login` + token persistence
- [x] Add protected routes and user context via Pinia
- [x] Add top-level navigation shell and API error states
- **Status:** complete

### Phase 8: Frontend Core Screens
- [x] Projects list (uses `/api/v1/projects`) with pagination
- [x] Project detail/doc list read flow; doc detail view consuming API
- [ ] Access code prompt flow (cookie) and basic upload hook placeholder
- **Status:** in_progress

### Phase 9: Delivery
- [ ] Review plan completeness vs docs
- [ ] Summarize deliverables for user
- [ ] Share follow-up recommendations
- **Status:** in_progress

### Phase 10: Legacy Parity (Frontend Feature Gap)
- [ ] Inventory legacy template features not yet in Vue (collect/favorite, downloads/export, full-text/tag search pages, prev/next nav, diff view, share token check, doc editor variants)
- [ ] Implement high-priority gaps (search page, tag docs page, favorites)
- [ ] Plan remaining lower-priority items (downloads/export, diff, advanced editors)
- **Status:** pending

### Phase 11: Editors
- [x] Add editor components for Vditor/Editormd/Luckysheet
- [ ] Wire editors to doc create/update API with mode switch
- [ ] Add upload integration hooks for images/attachments
- **Status:** in_progress

### Phase 12: Vditor Editor Refactoring
- [ ] Phase 1: Enhanced EditorVditor.vue
  - [ ] Add upload configuration with custom handler for MrDoc API
  - [ ] Expose editor methods via defineExpose (getValue, getHTML, setValue, insertValue, etc.)
  - [ ] Add mode prop (wysiwyg/ir/sv) with default 'wysiwyg'
  - [ ] Add theme prop (classic/dark) with theme switching support
  - [ ] Add height prop (configurable height)
  - [ ] Enhanced toolbar with more buttons (upload, link, emoji, fullscreen, preview)
  - [ ] Add missing callbacks (focus, blur, select, ctrlEnter)
  - [ ] Add toolbar customization prop
- [ ] Phase 2: Create VditorPreview.vue
  - [ ] New component for read-only markdown rendering
  - [ ] Use Vditor.preview() static method
  - [ ] Theme support for preview
  - [ ] Integrate into DocDetailView for read-only display
- [ ] Phase 3: Advanced Features
  - [ ] Outline view toggle
  - [ ] Character counter with limit
  - [ ] Auto-completion (emoji, @mentions)
  - [ ] Resize handle
  - [ ] Cache configuration
  - [ ] Typewriter mode option
- [ ] Phase 4: Backend Upload Integration
  - [ ] Create/update Django upload API endpoint
  - [ ] Wire Vditor upload to backend
  - [ ] Image management integration
  - [ ] File attachment handling
  - [ ] Test drag-drop and clipboard paste
- **Status:** pending

### Phase 13: Tiptap Editor Integration (Future)
- [ ] Install Tiptap dependencies (@tiptap/vue-3, @tiptap/pm, @tiptap/starter-kit)
- [ ] Create EditorTiptap.vue component with v-model pattern
- [ ] Configure Tiptap extensions (StarterKit, Image, Table, Link, etc.)
- [ ] Add custom toolbar UI for Tiptap
- [ ] Integrate markdown import/export for compatibility
- [ ] Add Tiptap option to DocEditView (editor_mode = 3 or 5)
- [ ] Test Tiptap with doc create/update API
- [ ] Add image upload integration
- [ ] Document Tiptap usage and configuration
- **Status:** pending

## Key Questions
1. Which modules/services should move first to reduce risk (e.g., auth, docs, AI features)?
2. How to preserve existing permission model and APIs during the transition?
3. What data and static assets require migration or new serving strategy?

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Use phased plan before code changes | Aligns work with existing migration and permission design documents |
| Integrate permission review correction (role=1 delete-any) | Prevents propagating known error into new APIs and tests |
| Add JWT + OpenAPI foundation first | Enables frontend dev to start and isolates new API surface |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| manage.py startapp failed (Django not installed) | 1 | Create app folder manually and proceed without running management command |

## Notes
<!-- 
  REMINDERS:
  - Update phase status as you progress: pending → in_progress → complete
  - Re-read this plan before major decisions (attention manipulation)
  - Log ALL errors - they help avoid repetition
  - Never repeat a failed action - mutate your approach instead
-->
- Update phase status as you progress: pending → in_progress → complete
- Re-read this plan before major decisions (attention manipulation)
- Log ALL errors - they help avoid repetition
