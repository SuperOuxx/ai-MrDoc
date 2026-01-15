# 前台文档站前后端分离迁移方案（Vue 3 + DRF + JWT + /api/v1）

## 1. 目标与范围
- 迁移范围：仅“前台文档站”（文集浏览/管理、文档浏览/编辑、搜索、分享、个人中心等前台功能）。
- 保留规则：完整保留现有权限规则（role=0/1/2/3 + viewcode + 协作者/创建者/超级用户逻辑）。
- 认证方案：引入 JWT（新接口），旧 `/api/` 与 `/api_app/` 保留并行。
- 版本化：新增 `/api/v1/`，与旧接口并行运行。

## 2. 现状梳理（关键点）
- 后端：单体 Django 应用，模板渲染 + 部分 DRF API。
- 旧 API：
  - `/api/`（函数式视图 + token query param + `csrf_exempt`）
  - `/api_app/`（DRF APIView + `AppAuth` 读 query param token）
- 前台页面路由集中在 `app_doc/urls.py`，模板位于 `template/app_doc/`。
- 现有权限判断分散在视图层与业务函数中，逻辑与模板耦合。

## 3. 目标形态概述
- 前端：Vue 3 SPA（路由与状态管理接管模板页面）
- 后端：
  - 新增 `/api/v1/`（DRF + JWT）
  - 旧 `/api/`、`/api_app/` 保持不变
  - 权限判断抽象为统一 Permission/Policy
- 部署：前端静态站独立部署，后端提供 API + 媒体文件

## 4. 迁移分阶段方案（每步改动点 + 影响面）

### Phase 0：准备与梳理（只读）
**改动点**
- 盘点前台路由、模板、前端交互与 API 调用点。
- 确认功能清单、优先级、是否需要替换编辑器。

**影响面**
- 仅文档与方案层面，无代码变更。

**验收点**
- 输出前台功能列表 + 依赖 API 清单。

---

### Phase 1：API v1 基础与认证
**改动点**
- 新增 `/api/v1/` 路由入口与应用（建议 `app_api_v1`）。
- 引入 JWT（建议 `djangorestframework-simplejwt`）。
- 新增用户认证接口：
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/refresh`
  - `GET /api/v1/users/me`
- 统一 API 响应结构（建议 `{"code":0,"data":...,"msg":""}`）。
- **API 版本管理策略**：
  - 响应头返回 `API-Version: 1.0`
  - 引入 `drf-spectacular` 生成 OpenAPI 3.0 文档（替代 swagger）
  - 定义 API 废弃策略：v1 稳定 6 个月后，旧 `/api/` 标记为 deprecated
  - 文档地址：`/api/v1/docs/` (Swagger UI) 和 `/api/v1/schema/` (OpenAPI Schema)

**影响面**
- 后端设置：`INSTALLED_APPS`、`REST_FRAMEWORK`、`urls.py`。
- 无影响旧 API 与现有模板逻辑。

**验收点**
- 用 JWT 完成登录与访问受保护资源的闭环。
- API 文档自动生成并可访问。
- 版本信息在响应头中正确返回。

---

### Phase 1.5：权限抽象层实现（新增）
**改动点**
- 创建权限抽象层目录结构：
  - `app_api_v1/policies/` (业务逻辑层)
  - `app_api_v1/permissions/` (DRF 集成层)
- 实现权限策略类：
  - `BasePolicy`: 基础策略类
  - `ProjectAccessPolicy`: 文集权限策略（支持 role=0/1/2/3）
  - `DocAccessPolicy`: 文档权限策略（支持协作者 role=0/1 差异）
- 实现 DRF Permission 类：
  - `ProjectPermission`: 文集权限类
  - `DocPermission`: 文档权限类
  - `ProjectManagePermission`: 文集管理权限类
- 编写完整的单元测试（覆盖率 > 90%）。
- 编写权限工具函数：
  - `get_user_readable_projects()`
  - `get_user_writable_projects()`
  - `get_user_manageable_projects()`

**影响面**
- 新增代码文件，不影响现有功能。
- 为后续 API 实现提供统一的权限判断基础。

**验收点**
- 所有权限单元测试通过（覆盖所有 role 场景）。
- 权限测试矩阵中的所有场景验证通过。
- 文档完整（包括使用示例）。
- 代码 Review 通过。

**实施周期**
- 预计 7 天（详见 `PERMISSION_DESIGN.md` 第 8.1 节）

---

### Phase 2a：核心资源 API（文集/文档）- 只读接口（拆分）
**改动点**
- 文集 GET API：
  - `GET /api/v1/projects` (列表，支持分页、搜索、role 筛选)
  - `GET /api/v1/projects/{id}` (详情)
  - `GET /api/v1/projects/{id}/tree` (文档树)
- 文档 GET API：
  - `GET /api/v1/docs/{id}` (详情)
  - `GET /api/v1/docs/{id}/neighbors` (上下篇)
- 权限规则应用：使用 Phase 1.5 实现的 Permission 类。
- 响应数据优化：
  - 文集列表返回文档数量、协作者数量等统计信息
  - 文档详情返回文集信息、权限信息、编辑器模式等

**影响面**
- 需要新增 serializers、viewsets。
- 不影响旧模板功能（并行运行）。

**验收点**
- 文集列表 → 文集详情 → 文档树 → 文档详情闭环可用。
- 权限过滤正确（用户只能看到有权限的文集和文档）。
- 访问码验证逻辑正确（role=3 文集）。
- API 文档完整。

---

### Phase 2b：核心资源 API（文集/文档）- 写入接口（拆分）
**改动点**
- 文集写入 API：
  - `POST /api/v1/projects` (创建)
  - `PUT /api/v1/projects/{id}` (更新基本信息)
  - `PATCH /api/v1/projects/{id}` (部分更新)
  - `DELETE /api/v1/projects/{id}` (删除)
  - `PUT /api/v1/projects/{id}/role` (修改权限设置，需管理权限)
- 文档写入 API：
  - `POST /api/v1/docs` (创建)
  - `PUT /api/v1/docs/{id}` (更新)
  - `PATCH /api/v1/docs/{id}` (部分更新)
  - `DELETE /api/v1/docs/{id}` (软删除)
- 权限规则统一迁移（role=0/1/2/3 + viewcode + 协作者/创建者/超级用户）。
- 业务逻辑迁移：
  - 文档历史记录（更新时自动保存历史）
  - 文档标签处理
  - 文档排序逻辑
  - 下级文档状态联动（删除时）

**影响面**
- 需要新增 serializers、permissions、service 层。
- 不影响旧模板功能（并行运行）。

**验收点**
- 文集/文档的 CRUD 闭环可用。
- 权限判断正确（协作者 role=0/1 的差异正确实现）。
- 文档历史记录正确保存。
- 标签关联正确。

---

### Phase 3：补齐前台能力（模板/标签/搜索/分享/上传/协作者）
**改动点**
- 协作者管理 API（新增）：
  - `GET /api/v1/projects/{id}/collaborators` (协作者列表)
  - `POST /api/v1/projects/{id}/collaborators` (添加协作者)
  - `PUT /api/v1/projects/{id}/collaborators/{user_id}` (修改协作者角色)
  - `DELETE /api/v1/projects/{id}/collaborators/{user_id}` (移除协作者)
  - `GET /api/v1/users/collaborations` (我协作的文集列表)
- 模板、标签、搜索、分享、上传等 API：
  - `/api/v1/doc-templates/*` (文档模板)
  - `/api/v1/tags/*` (标签管理)
  - `/api/v1/search` (全文搜索)
  - `/api/v1/shares/*` (文档分享)
  - `/api/v1/uploads/*` (图片/附件上传)
- 迁移原模板中依赖的管理能力（个人中心相关 API）：
  - `/api/v1/users/me/projects` (我的文集)
  - `/api/v1/users/me/docs` (我的文档)
  - `/api/v1/users/me/collections` (我的收藏)
  - `/api/v1/users/me/images` (图片管理)

**影响面**
- 新增相关 Serializer 与 Permission。
- 旧 API 并行，无破坏性修改。

**验收点**
- 协作者管理功能完整（增删改查）。
- 模板插入、标签管理、搜索、分享、上传可用。
- 个人中心相关功能可用。

---

### Phase 4：Vue 前台接入（并行）
**改动点**
- 构建 Vue 3 SPA，使用 `/api/v1/`。
- **前端架构设计**（详细化）：
  - 状态管理：Pinia（推荐）或 Vuex
  - 路由管理：Vue Router
  - HTTP 客户端：Axios + 拦截器（自动添加 JWT、刷新 token）
  - UI 组件库：Element Plus / Ant Design Vue（可选）
  - Token 存储：localStorage + httpOnly cookie（双重保护）
  - 错误处理：统一错误拦截器 + 重试机制
  - 权限守卫：路由守卫 + 组件级权限指令
- 页面路由映射：
  - `/` → 文集列表
  - `/project/:id` → 文集详情/文档树
  - `/doc/:id` → 文档详情
  - `/doc/create` → 文档创建
  - `/doc/edit/:id` → 文档编辑
  - `/user/*` → 个人中心
  - `/project/:id/collaborators` → 协作者管理
  - `/project/:id/settings` → 文集设置
- **编辑器集成方案**：
  - Markdown：Vditor（继续复用）
    - 验证 Vditor 在 Vue 3 中的兼容性
    - 封装为 Vue 组件（`<VditorEditor>`）
    - 支持图片拖拽上传（调用 `/api/v1/uploads/images`）
  - 富文本：Tiptap
    - 功能对比：需覆盖原有编辑器能力
    - 封装为 Vue 组件（`<RichTextEditor>`）
  - 在线表格：Handsontable / x-spreadsheet（替换 Luckysheet）
    - Luckysheet 已停止维护，需评估替代方案
    - 数据格式转换方案（旧格式 → 新编辑器）
- **图片上传策略**：
  - 方案 1：直接上传到后端 `/api/v1/uploads/images`
  - 方案 2：后端提供 OSS 签名，前端直传 OSS（性能优化）
- **访问码处理**：
  - 检测 403 响应 + `code=3`（需要访问码）
  - 弹窗输入访问码，验证后存储到 cookie
  - 后续请求自动携带 cookie

**影响面**
- 前端路由与模板并行，入口可通过 Nginx 或 Django 配置分流。
- 旧模板仍可使用，作为回退路径。

**验收点**
- Vue 前台核心功能可用（浏览、创建、编辑）。
- 编辑器集成正常（Vditor、Tiptap、表格编辑器）。
- 图片上传功能正常。
- 访问码验证流程正确。
- 老模板仍可访问。

---

### Phase 4.5：监控、灰度与降级（新增）
**改动点**
- **性能监控**：
  - 后端：Django Debug Toolbar（开发）+ APM 工具（如 Sentry、New Relic）
  - 前端：Sentry 错误监控 + 性能埋点
  - 慢查询告警：记录查询时间 > 1s 的 SQL
- **灰度发布策略**：
  - Nginx 路由规则：部分用户流量导向 Vue 前端
  - 灰度条件：Cookie（`beta_user=1`）或 IP 白名单
  - 灰度比例：10% → 30% → 50% → 100%（逐步放量）
- **降级开关**：
  - 一键回退到旧模板（Nginx 配置或 Django 中间件）
  - 旧 API 保持可用（至少 6 个月）
  - 数据库回滚方案（migration 可逆）
- **监控指标**：
  - API 成功率、响应时间、错误率
  - 前端页面加载时间、白屏时间
  - 用户行为漏斗（登录 → 创建文集 → 创建文档）

**影响面**
- 运维配置调整（Nginx、监控服务）。
- 需要灰度发布的运维策略配合。

**验收点**
- 监控大盘正常显示关键指标。
- 灰度策略可正常切换用户流量。
- 降级开关测试通过（一键回退）。
- 慢查询告警正常触发。

---

### Phase 5：切换与收尾
**改动点**
- 逐步切换前台入口到 Vue。
- 保留旧 API 一段时间，确保兼容与回滚。

**影响面**
- 用户访问入口变化，需要灰度策略与运维配合。

**验收点**
- 前台访问完全走 Vue + `/api/v1/`，旧模板进入维护状态。

## 5. 每步关键改动点列表（文件级）
- 新增 `app_api_v1/`（views/serializers/permissions/policies/urls/tests）。
- `MrDoc/settings.py`：
  - 加入 JWT 认证类、默认权限、分页策略。
  - 配置 `drf-spectacular`（API 文档生成）。
  - 配置 Sentry（错误监控）。
  - 保留现有 `rest_framework` 配置不变或新增扩展字段。
- `MrDoc/urls.py`：新增 `path('api/v1/', include(...))`。
- 保持 `app_api/` 与 `app_api_app/` 原有逻辑，避免影响旧功能。
- **数据库迁移**（新增）：
  - 检查现有字段是否需要调整（如 `role_value` 存储格式）。
  - 为高频查询字段添加索引（`Project.role`, `Doc.top_doc`, `Doc.status`）。
  - 数据迁移脚本（如需格式转换）。

## 6. 权限与规则保持策略
- role=1 私密：仅创建者/协作者可读。
- role=2 指定用户：`role_value` 包含用户名，且创建者/协作者可读。
- role=3 访问码：非创建者/协作者必须校验 viewcode。
- role=0 公开：所有人可读，写操作仍需创建者/协作者。

建议将权限判断集中为：
- `ProjectAccessPolicy`
- `DocAccessPolicy`

## 7. 风险与影响评估
- 认证切换：JWT 与旧 token 并行时需避免混淆。
- 权限逻辑散落：迁移不慎可能导致访问异常。
- 编辑器替换：富文本/表格编辑器兼容性风险。
- 并行阶段：API 版本同时存在，文档/前端需要严格指向 v1。

## 8. 测试与验证建议
- **API 单元测试覆盖**：
  - 权限测试：文集/文档/权限规则（覆盖所有 role 场景）
  - 业务逻辑测试：创建/更新/删除/查询
  - 边界测试：参数错误、权限不足、资源不存在
- **权限矩阵测试**（关键）：
  - 文集权限：role 0/1/2/3 × 游客/普通用户/协作者/创建者/超级用户
  - 文档权限：协作者 role 0/1 × 创建/修改/删除操作
  - 草稿状态：仅创建者可访问
- **Vue E2E 测试覆盖**：
  - 登录 → 创建文集 → 创建文档 → 编辑 → 保存
  - 搜索 → 查看文档 → 收藏
  - 分享文档 → 验证分享码
  - 访问码验证流程
- **并发测试**：
  - 多用户同时编辑同一文档
  - 多用户同时修改文集权限
- **回归测试**：
  - 旧模板仍可用（确保并行期无破坏）
  - 旧 API 仍可正常调用
- **跨域测试**：
  - 前后端分离后的 CORS 配置
  - Cookie 跨域传递（访问码）

## 9. 建议的实施顺序（可执行清单）
1) 建立 `/api/v1/` 框架 + JWT 登录 + API 文档生成（Phase 1）
2) **权限抽象层实现与测试**（Phase 1.5，**7 天**）
3) 文集/文档 GET API（只读，Phase 2a）
4) **Vue SPA 骨架 + 展示页面**（与后端并行开发，Phase 4）
5) 文集/文档 POST/PUT/DELETE API（Phase 2b）
6) 协作者管理 + 模板/搜索/分享/上传 API（Phase 3）
7) Vue 前台功能完整化（编辑器集成、图片上传）（Phase 4）
8) **灰度发布与监控**（Phase 4.5）
9) 入口切换与旧模板退役（Phase 5）

## 10. 后续可选优化
- 将权限判断抽到服务层，避免视图层堆叠。
- 统一返回结构与错误码。
- 逐步下线旧 `/api/` 与 `/api_app/`（稳定 6 个月后）。
- 权限缓存机制（Redis 缓存协作者关系）。
- 权限日志审计（记录敏感操作）。
- 批量权限查询接口（`POST /api/v1/permissions/check`）。

---

## 11. 部署架构（新增）

### 11.1 Nginx 配置示例

```nginx
# Vue 前端（静态文件）
location / {
    root /var/www/mrdoc-frontend/dist;
    try_files $uri $uri/ /index.html;
}

# API 反向代理
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}

# 媒体文件
location /media/ {
    alias /var/www/mrdoc/media/;
    expires 7d;
}

# 灰度发布（可选）
location / {
    # 检查 cookie 或 IP 白名单
    if ($cookie_beta_user = "1") {
        root /var/www/mrdoc-frontend-beta/dist;
    }
    root /var/www/mrdoc-frontend/dist;
    try_files $uri $uri/ /index.html;
}
```

### 11.2 前端构建产物部署

- 构建命令：`npm run build`
- 部署路径：`/var/www/mrdoc-frontend/dist/`
- CDN 配置：静态资源（JS/CSS/图片）上传到 CDN

### 11.3 媒体文件访问

- 路径保持：`/media/` 路径不变
- Nginx 直接提供静态文件服务
- 可选：上传到 OSS（阿里云 OSS、腾讯云 COS 等）

### 11.4 WebSocket 支持（如需实时协作）

```nginx
location /ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

---

## 12. 交付物清单（新增）

### 12.1 文档交付物

- [ ] API 文档（OpenAPI 3.0 规范，自动生成）
- [ ] 权限判断流程图（Mermaid 或 draw.io）
- [ ] 前端组件设计文档（组件树、状态管理设计）
- [ ] 部署手册（生产环境 checklist）
- [ ] 回滚手册（出现问题时的应急方案）
- [ ] 数据库迁移记录（migration 文件 + 说明）
- [ ] 测试报告（单元测试覆盖率、E2E 测试结果）

### 12.2 代码交付物

- [ ] `app_api_v1/` 完整代码（含 tests）
- [ ] Vue 3 前端代码（含 E2E 测试）
- [ ] Nginx 配置文件（含灰度策略）
- [ ] Docker 配置文件（可选）
- [ ] CI/CD 配置（GitHub Actions / GitLab CI）

### 12.3 运维交付物

- [ ] 监控大盘配置（Grafana / Sentry）
- [ ] 灰度发布脚本
- [ ] 回滚脚本
- [ ] 数据库备份恢复方案

---

## 13. 编辑器迁移详细方案（新增）

### 13.1 Vditor（Markdown 编辑器）

**验证清单**：
- [ ] Vditor 在 Vue 3 中的兼容性测试
- [ ] 是否有官方 Vue 3 wrapper（或使用 `@vueup/vue-quill` 类似方案）
- [ ] 图片拖拽上传集成（调用 `/api/v1/uploads/images`）
- [ ] 工具栏自定义配置
- [ ] 预览模式与编辑模式切换

**迁移步骤**：
1. 封装为 Vue 组件 `<VditorEditor>`
2. Props 设计：`v-model:content`, `readonly`, `height`, `toolbar` 等
3. 事件设计：`@save`, `@change`, `@upload` 等
4. 测试：创建、编辑、保存、图片上传

### 13.2 Tiptap（富文本编辑器）

**功能对比**：
- [ ] 是否支持原有编辑器的所有格式（粗体、斜体、表格、代码块等）
- [ ] 是否支持自定义扩展（如特殊块、嵌入视频等）
- [ ] 协同编辑支持（如需实时协作）

**数据格式转换**：
- 旧富文本格式：HTML
- Tiptap 格式：JSON（ProseMirror 格式）
- 转换方案：后端提供转换接口 `/api/v1/docs/{id}/convert`

### 13.3 Handsontable / x-spreadsheet（表格编辑器）

**Luckysheet 替换原因**：
- 已停止维护（最后更新 2021 年）
- 安全漏洞风险

**替代方案对比**：
| 特性 | Handsontable | x-spreadsheet | Luckysheet |
|------|-------------|---------------|------------|
| 开源 | 商业版+社区版 | 开源（MIT） | 开源（MIT） |
| Vue 3 支持 | ✅ | ✅ | ❌ |
| 维护状态 | 活跃 | 活跃 | 停止 |
| 功能完整度 | 高 | 中 | 高 |

**推荐方案**：x-spreadsheet（免费、MIT 许可证）

**数据格式转换**：
- Luckysheet 格式：JSON（自定义格式）
- x-spreadsheet 格式：JSON（兼容 Excel）
- 转换工具：编写转换脚本 `luckysheet_to_xspreadsheet.py`

---

## 14. 风险点与应对措施（补充）

### 14.1 权限逻辑迁移风险

**风险**：
- 权限判断逻辑复杂，迁移时可能遗漏边界情况
- 协作者 role=0/1 的细微差异容易出错

**应对措施**：
- ✅ Phase 1.5 先行实现权限抽象层，独立测试
- ✅ 编写完整的权限测试矩阵（覆盖所有 role 场景）
- ✅ 代码 Review 重点检查权限逻辑
- ✅ 灰度发布时重点监控权限相关错误

### 14.2 编辑器兼容性风险

**风险**：
- Vditor/Tiptap 在 Vue 3 中可能有兼容性问题
- Luckysheet 停止维护，需要替换

**应对措施**：
- ✅ Phase 4 前先进行编辑器 PoC（概念验证）
- ✅ 准备降级方案：保留旧编辑器入口（iframe 嵌入）
- ✅ 提供数据格式转换工具

### 14.3 并发编辑冲突

**风险**：
- 多用户同时编辑同一文档，可能出现数据覆盖

**应对措施**：
- ✅ 引入乐观锁机制（version 字段）
- ✅ 前端检测冲突，提示用户
- ✅ 后续可引入 CRDT 或 OT 算法（实时协作）

### 14.4 性能瓶颈

**风险**：
- 文集列表查询慢（权限过滤复杂）
- 文档树查询慢（递归查询）

**应对措施**：
- ✅ 添加数据库索引（`Project.role`, `Doc.top_doc`）
- ✅ 引入缓存（Redis 缓存文档树、协作者关系）
- ✅ 分页加载（文集列表、文档列表）
- ✅ 监控慢查询，优化 SQL

---

## 15. 关键里程碑与时间估算（新增）

| Phase | 任务 | 预计工作量 | 依赖 |
|-------|------|-----------|------|
| Phase 0 | 准备与梳理 | 2 天 | - |
| Phase 1 | API 基础与认证 | 3 天 | - |
| **Phase 1.5** | **权限抽象层** | **7 天** | Phase 1 |
| Phase 2a | 只读 API | 5 天 | Phase 1.5 |
| Phase 2b | 写入 API | 7 天 | Phase 1.5 |
| Phase 3 | 补齐前台能力 | 10 天 | Phase 2b |
| Phase 4 | Vue 前台接入 | 15 天 | Phase 2a（并行） |
| Phase 4.5 | 监控与灰度 | 5 天 | Phase 4 |
| Phase 5 | 切换与收尾 | 3 天 | Phase 4.5 |
| **总计** | | **约 57 天（2-3 个月）** | |

**注意**：
- Phase 4 可与 Phase 2a/2b/3 并行开发（前端与后端同步进行）
- 实际时间取决于团队规模、经验和项目复杂度
- 建议预留 20% 缓冲时间（约 70 天）

---
