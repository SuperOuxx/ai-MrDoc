# Findings & Decisions
<!-- 
  WHAT: Your knowledge base for the task. Stores everything you discover and decide.
  WHY: Context windows are limited. This file is your "external memory" - persistent and unlimited.
  WHEN: Update after ANY discovery, especially after 2 view/browser/search operations (2-Action Rule).
-->

## Requirements
<!-- 
  WHAT: What the user asked for, broken down into specific requirements.
  WHY: Keeps requirements visible so you don't forget what you're building.
  WHEN: Fill this in during Phase 1 (Requirements & Discovery).
  EXAMPLE:
    - Command-line interface
    - Add tasks
    - List all tasks
    - Delete tasks
    - Python implementation
-->
- Generate a phased migration plan to refactor the project to a Vue 3 frontend and Django REST Framework backend.
- Base the plan on MIGRATION_PLAN.md, PERMISSION_DESIGN.md, and PERMISSION_REVIEW.md.
- Produce actionable, stage-by-stage guidance (architecture, sequencing, tooling, testing).

## Research Findings
<!-- 
  WHAT: Key discoveries from web searches, documentation reading, or exploration.
  WHY: Multimodal content (images, browser results) doesn't persist. Write it down immediately.
  WHEN: After EVERY 2 view/browser/search operations, update this section (2-Action Rule).
  EXAMPLE:
    - Python's argparse module supports subcommands for clean CLI design
    - JSON module handles file persistence easily
    - Standard pattern: python script.py <command> [args]
-->
<!-- Key discoveries during exploration -->
- Repo is a Django project with apps: app_admin, app_ai, app_api, app_doc; core config in MrDoc/.
- Existing setup commands: pip install -r requirements.txt; manage.py makemigrations/migrate; runserver; createsuperuser; manage.py test.
- MIGRATION_PLAN outlines phased split: Phase 0 inventory; Phase 1 add `/api/v1` with DRF + JWT + OpenAPI via drf-spectacular; Phase 1.5 introduce policy/permission layer (`app_api_v1/policies`, DRF permissions) with high test coverage; Phase 2a/2b implement read/write project/doc APIs using new permissions.
- Target architecture: Vue 3 SPA frontend; backend DRF with `/api/v1/` while keeping existing `/api/` & `/api_app/` during migration; permission model must preserve role0/1/2/3 + viewcode + collaborator/owner/superuser.
- Phase 3 adds collaborator, template, tag, search, share, upload, and user-center APIs; Phase 4 builds Vue SPA with Pinia/Vue Router/Axios, route mapping, editor integration (Vditor, Tiptap, x-spreadsheet), access-code handling, and upload strategy.
- Phase 4.5 covers monitoring, gray release, and downgrade; Phase 5 switches entry to Vue with old templates retained for rollback.
- Deployment notes: Nginx serves Vue dist at `/`, proxies `/api/` to Django, serves `/media/`; gray release via cookie/IP; WebSocket block for real-time if needed.
- Risk/mitigation: run permission abstraction first with full tests; editor compatibility needs PoC and fallback; handle concurrency with optimistic locking; performance mitigated via indexes/caching/pagination; estimated timeline ~57 days (+20% buffer).
- Permission design consolidates policies under `app_api_v1/policies` (BasePolicy, ProjectAccessPolicy, DocAccessPolicy) and DRF permissions under `app_api_v1/permissions` with utils + tests; uses action enums VIEW/CREATE/UPDATE/DELETE/MANAGE.
- Current rules: project role 0 public, 1 private, 2 allowed users (role_value usernames), 3 access code; collaborator roles 0/1; doc status 0 draft creator-only, 1 published; superuser bypass.
- Policies expose `has_read/write/manage` and `can_perform_action` for projects; doc policy includes draft-only creator access, collaborator role differences for update/delete, and uses project permissions for read.
- DRF integration via ProjectPermission/DocPermission handling viewcode from cookies, distinguishing manage vs write on role updates, and ensuring project permissions for doc creation; utils provide readable/writable/manageable project ID helpers for query filtering.
- Permission test commands: `python manage.py test app_api_v1.tests.test_permissions` (with class/method selectors); test matrix covers project roles vs roles, collaborator capabilities, draft vs published.
- Phase 1.5 steps: create directories, implement policies/utils (days 2-3), write tests (days 4-5), add DRF permissions (day 6), run integration tests (day 7); acceptance requires >90% coverage and full matrix pass.
- Best practices: least-privilege, early permission checks, caching collaborator lookups, clear naming (`*Policy`, `*Permission`), docstrings, and comprehensive tests including negative cases.
- Permission review flags a correction: role=1 collaborators can delete any document (design doc mistakenly limited to own); delete permission docstrings/logic and matrices need update to reflect this.
- Review notes: update design doc sections 1.2, 3.3.1, and test matrix to reflect role=1 delete-any; ensure new API implements full delete rights (old API only allows doc creator); add integration tests and frontend prompts clarifying collaborator delete scope.
- Implemented Phase 3 scaffold: new `app_api_v1` with auth endpoints (`/auth/login`, `/auth/refresh`, `/users/me`), unified `{code,data,msg}` envelope, API-Version header, JWT auth via SimpleJWT, OpenAPI at `/api/v1/schema` and Swagger at `/api/v1/docs`.
- Settings updated: REST framework defaults (JWT + Session auth, schema class), SIMPLE_JWT lifetimes, SPECTACULAR_SETTINGS, API_V1_VERSION; installed `drf-spectacular` and `djangorestframework-simplejwt` in `.venv`.
- Implemented permission layer: `policies/base.py`, `project_policy.py`, `doc_policy.py` with role=1 delete-any fix; DRF permissions in `permissions/project.py` & `permissions/doc.py`; helpers in `permissions/utils.py`; added smoke tests in `tests/test_permissions.py` covering collaborator delete semantics.
- Implemented core resource viewsets: Project/Doc serializers, viewsets with permission filtering and unified response envelope + pagination, routes via DefaultRouter under `/api/v1/projects` and `/api/v1/docs`; collaborator listing action added.
- Soft-delete and history: DocViewSet update stores DocHistory; delete sets status=3 and cascades children; tests cover collaborator delete semantics and CRUD behaviors.
- Frontend scaffold: Vite + Vue3 + TS + Pinia + Router + Axios; global theme in `style.css`; Axios interceptors add JWT + refresh + API-Version; auth store persists tokens and exposes restore/logout; login page, projects list, doc detail consume `/api/v1` APIs; protected routing with redirect handling; `npm run build` succeeds.
- Frontend core additions: project detail view (docs + collaborators), access-code modal writes `viewcode-{projectId}` cookie on 403 and retries; upload placeholders for future `/api/v1/uploads` or OSS signed uploads; backend doc list supports top_doc/parent_doc filters and project docs action to feed UI.
- Extended features: project tree endpoint (uses ProjectToc or fallback build) with UI tree; tag endpoints (list, doc tags read/write with permission) and front-end tag add/remove; router includes project detail; doc view uses access-code modal.
- Search/share/ordering enhancements: doc list supports q filter; project docs action includes search; project tree PUT updates parent/sort + saves toc; doc share endpoints (public/private with code, enable flag) and UI; tag autocomplete via tags endpoint.
- Legacy feature gaps (from Django templates) still missing in Vue:
  - Favorites/collect (project/doc), and favorites management UI.
  - Downloads/export (doc md/pdf, doc xls for sheet, project export epub/pdf, report md zip).
  - Full search pages (global search, project search) with result UI; tag docs listing pages.
  - Doc navigation (prev/next), doc diff view, share-check page for token/password, doc download for sheet.
  - Rich editor modes (luckysheet replacement, WYSIWYG), comments? (not visible), user center/manage pages (collect/share management, project options).
- Editors added: Vditor (wysiwyg markdown), Editormd (markdown via CDN assets), Luckysheet (table) components with demo route `/editor-demo`; not yet wired to doc create/update or uploads.

## Tiptap Research (2026-01-16)

### Tiptap Overview
- **What is Tiptap**: Headless rich-text editor framework built on top of ProseMirror
- **Architecture**: Event-driven with Commands, Events, and Extensions API
- **Key Features**:
  - Modular by default: add only needed extensions (bold, links, tables, slash-menus, etc.)
  - Headless first: works with React, Vue, Svelte, plain JS, or any framework
  - Has open source (MIT license) and Pro extensions (comments, AI commands, collaboration)
  - UI Components and templates available for React
  - Built on battle-tested ProseMirror library

### Vue 3 Integration Details
- **Required packages**:
  - `@tiptap/vue-3`: Vue 3 integration layer
  - `@tiptap/pm`: ProseMirror library dependency
  - `@tiptap/starter-kit`: Common extensions bundle (recommended starting point)

- **Installation command**:
  ```bash
  npm install @tiptap/vue-3 @tiptap/pm @tiptap/starter-kit
  ```

- **Basic usage patterns**:
  1. **Options API**: Create editor in `mounted()`, destroy in `beforeUnmount()`
  2. **Composition API**: Use `useEditor()` composable
  3. **Script Setup**: Direct `useEditor()` call (recommended for Vue 3)

- **Core components**:
  - `EditorContent`: Main component to render editor
  - `useEditor()`: Composable to create editor instance
  - `Editor`: Class for programmatic editor creation

- **Basic example** (Script Setup):
  ```vue
  <template>
    <editor-content :editor="editor" />
  </template>

  <script setup>
  import { useEditor, EditorContent } from '@tiptap/vue-3'
  import StarterKit from '@tiptap/starter-kit'

  const editor = useEditor({
    content: "<p>Initial content</p>",
    extensions: [StarterKit],
  })
  </script>
  ```

- **Features**:
  - Supports `v-model` binding for two-way data sync
  - StarterKit includes: bold, italic, heading, paragraph, bullet/ordered lists, code blocks, etc.
  - Can add more extensions for images, tables, diagrams, custom nodes
  - Headless means full control over styling and UI

### Extensions Available
- **Core marks/nodes**: Bold, Italic, Link, Strike, Underline, Code, Heading, Paragraph, Lists, Tables
- **Functionality**: Bubble menu, Character count, Drag handle, File handler, Floating menu, Placeholder, Typography, Undo/Redo
- **Advanced (Pro)**: Collaboration, Comments, AI Generation, Export, Import, Version history
- **Content**: Image, Table, Mathematics, Mention, Emoji, Youtube, Twitch
- **Markdown support**: Beta markdown extension available for bidirectional conversion

### Migration Path Considerations
- **From Vditor/Editormd to Tiptap**:
  - Both current editors are markdown-focused
  - Tiptap has markdown support (beta) but is primarily WYSIWYG
  - Need to evaluate markdown extension for compatibility
  - Can coexist: keep Vditor/Editormd for markdown, add Tiptap as WYSIWYG option

- **Integration points**:
  - Upload handling: File handler extension available
  - Image support: Image extension with upload capabilities
  - Tables: Table kit extension
  - Custom nodes: Can create custom extensions for diagrams, mind maps

- **Challenges**:
  - Flowcharts/sequence diagrams: Need custom extension or keep Editormd for these
  - Mind mapping: May need custom integration or separate tool
  - Export to PDF/ePub: Need to evaluate Tiptap export capabilities
  - Luckysheet (spreadsheet): Separate concern, keep as-is

### Current Editor Implementation Analysis

**Frontend Location**: `frontend/src/components/` and `frontend/src/views/`

**Current Editors** (all Vue 3 components with v-model):
1. **EditorVditor.vue**
   - Uses Vditor library (npm package `vditor`)
   - Mode: `wysiwyg` (WYSIWYG markdown)
   - Features: Chinese i18n, custom toolbar, auto-save disabled
   - Height: 520px
   - Props: `modelValue` (string), `placeholder`
   - Emits: `update:modelValue`, `change`
   - Lifecycle: init in `onMounted`, destroy in `onBeforeUnmount`

2. **EditorEditormd.vue**
   - Uses Editor.md library (loaded from CDN)
   - CDN fallback strategy: tries cloudflare → jsdelivr → unpkg
   - Loads: jQuery, marked, prettify, raphael, underscore, sequence-diagram, flowchart libraries
   - Features: Supports flowcharts and sequence diagrams
   - Height: 500px
   - Props: `modelValue` (string), `placeholder`
   - Emits: `update:modelValue`, `change`
   - Has error handling for CDN load failures

3. **EditorLuckysheet.vue**
   - Uses Luckysheet library (npm package `luckysheet`)
   - For spreadsheet/table editing
   - Props: `modelValue` (array of sheet data)
   - Emits: `update:modelValue`, `change`

**Integration Points** (DocEditView.vue):
- Editor mode selection: dropdown with options (1=Editormd, 2=Vditor, 4=Luckysheet)
- Content storage:
  - Markdown editors (1,2): Store in `pre_content` field as string
  - Luckysheet (4): Store in `pre_content` field as JSON string
  - `content` field left empty (likely for rendered HTML)
- Form fields: name, top_doc, parent_doc, editor_mode, status
- Save flow: `createDoc()` or `updateDoc()` API calls
- Load flow: `fetchDoc()` → parse based on editor_mode

**API Integration**:
- Uses `/api/v1/docs` endpoints
- Doc model fields: id, name, top_doc, parent_doc, editor_mode, status, pre_content, content
- editor_mode values: 1 (Editormd), 2 (Vditor), 4 (Luckysheet)

**Migration Strategy Recommendations**:
1. **Add Tiptap as 4th editor option** (editor_mode = 5 or 3)
2. **Keep existing editors** for backwards compatibility and special features (flowcharts, spreadsheets)
3. **Tiptap advantages** to promote:
   - More modern UI/UX
   - Better performance
   - Easier to extend
   - Better TypeScript support
   - Active development
4. **Implementation approach**:
   - Create `EditorTiptap.vue` following same v-model pattern
   - Add to DocEditView dropdown
   - Store content in same `pre_content` field (HTML or JSON)
   - Consider adding markdown export/import for compatibility

## Vditor Deep Dive & Refactoring Analysis (2026-01-16)

### Vditor Official Capabilities (from GitHub README)

**Core Features**:
- **Three editing modes**: WYSIWYG, IR (instant rendering, Typora-like), SV (split view)
- Rich Markdown support: CommonMark, GFM, tables, task lists, footnotes, ToC
- **36+ toolbar operations** with customizable shortcuts, icons, tooltips
- **Diagrams**: mermaid (flowchart/sequence/gantt), ECharts, GraphViz, PlantUML, **mindmaps**
- Math formulas (MathJax/KaTeX), music notation (abc.js), code highlighting (36 themes)
- Auto-completion for emoji/@mentions/topics
- **File upload** with drag-drop and clipboard paste
- Export, lazy image loading, voice reading, outline view
- **Multi-theme support**: editor (classic/dark), content (ant-design/light/dark/wechat), code (36 styles)
- Mobile-friendly, real-time content saving

**Key Configuration Options**:
- `mode`: 'sv' | 'ir' | 'wysiwyg' (default: 'ir')
- `theme`: 'classic' | 'dark'
- `icon`: 'ant' | 'material'
- `typewriterMode`: typewriter mode
- `upload`: comprehensive upload configuration with custom handlers
- `preview`: markdown rendering settings (delay, theme, hljs, math engine)
- `cache`: localStorage caching with callbacks
- `counter`: character counter (max limit)
- `hint`: emoji/@ auto-completion with extend support
- `resize`: draggable resize
- `outline`: document outline (left/right position)
- `toolbar`: fully customizable with custom buttons support

**Important Methods**:
- `getValue()`: Get markdown
- `getHTML()`: Get rendered HTML
- `setValue(markdown)`: Set content
- `insertValue(value, render)`: Insert at cursor
- `focus()` / `blur()` / `disabled()` / `enable()`
- `getSelection()`: Get selected text
- `clearCache()`: Clear cache
- `setTheme(theme, contentTheme, codeTheme)`: Dynamic theme switching
- `getCurrentMode()`: Get current mode
- `destroy()`: Cleanup

**Static Methods** (for rendering outside editor):
- `Vditor.preview(element, markdown, options)`: Render markdown in any element
- `Vditor.md2html(mdText, options)`: Convert markdown to HTML
- `Vditor.mermaidRender()` / `mathRender()` / `codeRender()`: Specialized rendering

### Current Implementation Analysis (EditorVditor.vue)

**Current Version**: vditor@3.11.2 (latest stable)

**What's Implemented**:
- ✅ Basic WYSIWYG mode
- ✅ Chinese i18n (zh_CN)
- ✅ Basic toolbar (headings, bold, italic, lists, code, table, etc.)
- ✅ v-model binding (two-way data sync)
- ✅ Proper lifecycle management (init, destroy)
- ✅ Watch for external value changes
- ✅ Custom styling (border-radius, shadow)
- ✅ Dynamic imports for code-splitting

**What's Missing / Could Be Enhanced**:

1. **Editor Mode Options** ❌
   - Currently hardcoded to `wysiwyg` mode
   - Missing: `ir` (instant rendering, Typora-like) and `sv` (split view) options
   - **Impact**: Users can't choose their preferred editing experience

2. **Upload Configuration** ❌
   - No `upload` config implemented
   - Missing: image/file upload, drag-drop, clipboard paste
   - **Impact**: Can't upload images directly in editor

3. **Theme Support** ❌
   - No theme configuration (classic/dark)
   - No content theme options
   - No code highlighting theme
   - **Impact**: Fixed appearance, no dark mode

4. **Advanced Features Missing** ❌
   - No outline view
   - No character counter
   - No auto-completion (emoji/@mentions)
   - No resize handle
   - No cache configuration
   - No typewriter mode

5. **Toolbar Limitations** ⚠️
   - Basic toolbar only (missing upload, link, emoji, record, etc.)
   - No custom toolbar buttons
   - No fullscreen, preview toggles
   - **Impact**: Limited editing capabilities

6. **Method Exposure** ❌
   - No methods exposed to parent component
   - Can't call `getHTML()`, `insertValue()`, `getSelection()`, etc.
   - **Impact**: Limited programmatic control

7. **Callback Hooks Missing** ⚠️
   - Only `input` callback implemented
   - Missing: `focus`, `blur`, `select`, `ctrlEnter`, `after`
   - **Impact**: Limited event handling

8. **CDN Configuration** ⚠️
   - `cdn: ''` set but not configurable
   - May cause issues with external resources
   - **Impact**: Limited flexibility for self-hosted deployments

### Refactoring Opportunities

#### Priority 1: Critical Enhancements
1. **Add Upload Support** 🔥
   - Integrate with MrDoc's upload API
   - Support drag-drop and clipboard paste
   - Configure max size, allowed types
   - Custom upload handler for backend integration

2. **Expose Editor Methods** 🔥
   - Use `defineExpose()` to expose Vditor instance methods
   - Allow parent components to call `getHTML()`, `insertValue()`, etc.
   - Enable programmatic content manipulation

3. **Add Mode Prop** 🔥
   - Make `mode` configurable via prop
   - Default to 'wysiwyg' but allow 'ir' and 'sv'
   - Better user experience flexibility

#### Priority 2: Important Features
4. **Theme Support**
   - Add `theme` and `contentTheme` props
   - Support dark mode
   - Integrate with global app theme

5. **Enhanced Toolbar**
   - Add more toolbar buttons (upload, link, emoji, fullscreen)
   - Support custom toolbar configuration via prop
   - Make toolbar customizable

6. **Outline & Advanced Features**
   - Add outline view option
   - Character counter
   - Resize handle
   - Cache configuration

#### Priority 3: Nice to Have
7. **Auto-completion**
   - Emoji picker
   - @mentions integration
   - Custom hint extensions

8. **Event Hooks**
   - Expose all callback events
   - Better integration with parent components

9. **Static Rendering Support**
   - Create separate component for markdown preview
   - Use `Vditor.preview()` for read-only views
   - Better for doc display pages

### Recommended Refactoring Plan

**Phase 1: Enhanced EditorVditor.vue**
- Add upload configuration with API integration
- Expose editor methods via `defineExpose()`
- Add `mode`, `theme`, `height` props
- Enhanced toolbar configuration
- Add missing callbacks (focus, blur, select)

**Phase 2: Create VditorPreview.vue**
- Separate component for markdown rendering
- Use `Vditor.preview()` static method
- For doc detail/display pages (read-only)
- Support theme switching

**Phase 3: Advanced Features**
- Outline view integration
- Character counter
- Auto-completion extensions
- Resize handle
- Cache configuration

**Phase 4: Backend Integration**
- Wire upload to `/api/v1/uploads` or Django media handling
- Image management integration
- File attachment handling

### Vditor CDN Configuration Issue & Fix (2026-01-16)

**Problem**: Empty CDN configuration (`cdn: ''`) causes Vditor to fail loading resources

**Error**:
```
GET http://localhost:5173/dist/js/lute/lute.min.js net::ERR_ABORTED 404 (Not Found)
```

**Root Cause**:
- When `cdn: ''`, Vditor uses relative paths like `/dist/js/...`
- These paths don't exist in Vite dev server (they're in node_modules)
- Vite doesn't serve node_modules files unless explicitly configured

**Solution**: Use unpkg CDN for all environments
```typescript
const cdnRoot = 'https://unpkg.com/vditor@3.11.2'
```

**Why CDN is better than bundling**:
1. Vditor's dist folder is 10MB+ (lute.min.js, mermaid, echarts, etc.)
2. No build-time asset copying needed
3. Reliable delivery via unpkg (with jsdelivr as alternative)
4. Works identically in dev and production
5. Version-locked to 3.11.2

**Alternative CDNs**:
- unpkg: `https://unpkg.com/vditor@3.11.2`
- jsdelivr: `https://cdn.jsdelivr.net/npm/vditor@3.11.2`

**For self-hosted deployments**: Copy `node_modules/vditor/dist` to `static/vditor` and use `cdn: '/static/vditor'`

### Vditor customWysiwygToolbar Error (2026-01-16)

**Problem**: Runtime error during save operation
```
Uncaught TypeError: vditor.options.customWysiwygToolbar is not a function
    at customWysiwygToolbar (vditor.js:7462:30)
```

**Root Cause**: Manual i18n loading conflicted with Vditor's internal initialization sequence

**Previous Code (Problematic)**:
```typescript
const zhCN = await import('vditor/dist/js/i18n/zh_CN')
editor = new Vditor(el.value, {
  lang: 'zh_CN',
  i18n: (zhCN as any).default || zhCN,  // ❌ Manual i18n injection
})
```

**Fixed Code**:
```typescript
editor = new Vditor(el.value, {
  lang: 'zh_CN',  // ✅ Let Vditor load i18n from CDN automatically
  // i18n option removed
})
```

**Why This Fixes It**:
1. Vditor expects to load i18n files from CDN in a specific order
2. Manual i18n injection bypasses internal initialization logic
3. This causes `customWysiwygToolbar` function to be undefined
4. Letting Vditor handle i18n loading maintains proper initialization sequence

**Additional Improvements**:
- Added try-catch for better error reporting
- Added 'inline-code' to toolbar
- Improved null safety in `after` callback

### Vditor WYSIWYG vs IR Mode (2026-01-16)

**Problem**: WYSIWYG mode's `customWysiwygToolbar` error persists even after proper i18n configuration

**Final Solution**: Switch to IR (Instant Rendering) mode

**Comparison**:

| Feature | WYSIWYG Mode | IR Mode (Instant Rendering) |
|---------|--------------|----------------------------|
| Stability | ⚠️ Issues with CDN resources | ✅ Very stable |
| Performance | Slower (full WYSIWYG) | ✅ Faster (instant rendering) |
| Experience | Word-like editing | ✅ Typora-like (recommended) |
| Official Status | Older implementation | ✅ Recommended by Vditor team |
| CDN Compatibility | ❌ customWysiwygToolbar errors | ✅ Works perfectly |
| Markdown View | Needs mode switch | ✅ Always visible (optional) |

**Implementation**:
```typescript
editor = new Vditor(el.value, {
  mode: 'ir',  // Instant Rendering (Typora-like)
  // ... other config
})
```

**Why IR Mode is Better**:
1. **Stability**: No initialization errors with CDN resources
2. **Performance**: Faster rendering, lower memory usage
3. **UX**: Typora-like experience preferred by many users
4. **Markdown-friendly**: See markdown syntax while editing
5. **Official recommendation**: Vditor team recommends IR as default

**Edit Mode Switching**: Users can still switch between modes using the 'edit-mode' toolbar button

### Django APPEND_SLASH and API URL Design (2026-01-16)

**Problem**: 301 redirect when POSTing to `/api/v1/docs`

**Root Cause**: Django's `APPEND_SLASH` middleware behavior

**How Django APPEND_SLASH Works**:
1. Request comes to `/api/v1/docs` (no trailing slash)
2. Django checks if URL pattern exists
3. If not found, Django tries `/api/v1/docs/` (with slash)
4. If found with slash, returns 301 redirect
5. **Problem**: Browser follows redirect but changes POST → GET

**Why This Breaks API Calls**:
- POST /docs → 301 redirect → GET /docs/ ❌
- PUT /docs/123 → 301 redirect → GET /docs/123/ ❌
- DELETE requests also affected

**Solution**: Always use trailing slashes in frontend API calls

**Best Practices for Django REST APIs**:
```typescript
// ✅ CORRECT: With trailing slashes
'/api/v1/docs/'           // List/Create
'/api/v1/docs/123/'       // Retrieve/Update/Delete
'/api/v1/projects/'       // Collections
'/api/v1/users/me/'       // Singular resources

// ❌ WRONG: Without trailing slashes
'/api/v1/docs'
'/api/v1/docs/123'
```

**Alternative Solutions** (not recommended for existing Django projects):
1. Disable APPEND_SLASH in settings.py (breaks other URLs)
2. Use nginx rewrite rules (adds complexity)
3. Keep trailing slashes (✅ simplest and most compatible)

## Technical Decisions
<!-- 
  WHAT: Architecture and implementation choices you've made, with reasoning.
  WHY: You'll forget why you chose a technology or approach. This table preserves that knowledge.
  WHEN: Update whenever you make a significant technical choice.
  EXAMPLE:
    | Use JSON for storage | Simple, human-readable, built-in Python support |
    | argparse with subcommands | Clean CLI: python todo.py add "task" |
-->
<!-- Decisions made with rationale -->
| Decision | Rationale |
|----------|-----------|
| Use DRF + SimpleJWT for `/api/v1` auth | Aligns migration plan Phase 1; modern token flow with refresh |
| Add drf-spectacular for OpenAPI/Swagger | Auto-doc generation at `/api/v1/schema` + `/docs` |
| Standardize response envelope `{code,data,msg}` with API-Version header | Consistent client handling and versioning for new endpoints |
| Keep `/api/` & `/api_app/` untouched during migration | Avoid regression while rolling out `/api/v1` |
| Use Vite + Vue 3 + TS with Pinia/Router/Axios | Matches migration plan Phase 4 stack and supports modular SPA |

## Issues Encountered
<!-- 
  WHAT: Problems you ran into and how you solved them.
  WHY: Similar to errors in task_plan.md, but focused on broader issues (not just code errors).
  WHEN: Document when you encounter blockers or unexpected challenges.
  EXAMPLE:
    | Empty file causes JSONDecodeError | Added explicit empty file check before json.load() |
-->
<!-- Errors and how they were resolved -->
| Issue | Resolution |
|-------|------------|
|       |            |

## Resources
<!-- 
  WHAT: URLs, file paths, API references, documentation links you've found useful.
  WHY: Easy reference for later. Don't lose important links in context.
  WHEN: Add as you discover useful resources.
  EXAMPLE:
    - Python argparse docs: https://docs.python.org/3/library/argparse.html
    - Project structure: src/main.py, src/utils.py
-->
<!-- URLs, file paths, API references -->
-

## Visual/Browser Findings
<!-- 
  WHAT: Information you learned from viewing images, PDFs, or browser results.
  WHY: CRITICAL - Visual/multimodal content doesn't persist in context. Must be captured as text.
  WHEN: IMMEDIATELY after viewing images or browser results. Don't wait!
  EXAMPLE:
    - Screenshot shows login form has email and password fields
    - Browser shows API returns JSON with "status" and "data" keys
-->
<!-- CRITICAL: Update after every 2 view/browser operations -->
<!-- Multimodal content must be captured as text immediately -->
-

---
<!-- 
  REMINDER: The 2-Action Rule
  After every 2 view/browser/search operations, you MUST update this file.
  This prevents visual information from being lost when context resets.
-->
*Update this file after every 2 view/browser/search operations*
*This prevents visual information from being lost*
