# 权限抽象层设计文档

## 1. 概述

### 1.1 设计目标
- **统一权限判断**：将分散在视图层的权限逻辑抽象为可复用的 Policy 类
- **易于测试**：权限逻辑独立，便于编写单元测试
- **符合 DRF 规范**：基于 DRF 的 Permission 系统实现
- **完整保留原有规则**：不改变现有权限语义
- **易于扩展**：新增权限规则时只需扩展 Policy 类

### 1.2 当前权限规则梳理

#### 文集（Project）权限
| role 值 | 说明 | role_value | 访问规则 |
|---------|------|------------|----------|
| 0 | 公开 | - | 所有人可读，仅创建者/协作者可写 |
| 1 | 私密 | - | 仅创建者/协作者可读可写 |
| 2 | 指定用户 | 用户名列表 | role_value 包含的用户+创建者+协作者可读可写 |
| 3 | 访问码 | 访问码字符串 | 验证访问码后可读，仅创建者/协作者可写 |

#### 协作者（ProjectCollaborator）权限
| role 值 | 说明 |
|---------|------|
| 0 | 可新建文档，可修改/删除自己新建的文档 |
| 1 | 可新建文档，可修改/删除文集中的所有文档 |

#### 文档（Doc）状态
| status 值 | 说明 | 访问规则 |
|-----------|------|----------|
| 0 | 草稿 | 仅创建者可访问 |
| 1 | 发布 | 遵循文集权限规则 |

#### 特殊角色
- **超级用户（is_superuser）**：拥有所有权限

---

## 2. 架构设计

### 2.1 模块结构

```
app_api_v1/
├── permissions/
│   ├── __init__.py
│   ├── base.py              # 基础权限类
│   ├── project.py           # 文集权限
│   ├── doc.py               # 文档权限
│   └── utils.py             # 权限工具函数
├── policies/
│   ├── __init__.py
│   ├── project_policy.py    # 文集访问策略
│   └── doc_policy.py        # 文档访问策略
└── tests/
    └── test_permissions.py  # 权限测试
```

### 2.2 设计模式

采用 **Policy Pattern（策略模式）** + **DRF Permission System**：

1. **Policy 层**：纯业务逻辑判断，不依赖 DRF
   - 输入：用户、资源对象、操作类型
   - 输出：布尔值（允许/拒绝）
   - 可独立测试，可在视图/序列化器/服务层复用

2. **Permission 层**：DRF 集成层
   - 调用 Policy 层的判断方法
   - 处理匿名用户、错误处理
   - 返回 DRF 标准的权限结果

---

## 3. 核心实现

### 3.1 基础类设计

#### 3.1.1 BasePolicy（基础策略类）

```python
# app_api_v1/policies/base.py
from django.contrib.auth.models import User, AnonymousUser
from typing import Optional
from enum import Enum


class Action(Enum):
    """操作类型枚举"""
    VIEW = "view"           # 查看
    CREATE = "create"       # 创建
    UPDATE = "update"       # 更新
    DELETE = "delete"       # 删除
    MANAGE = "manage"       # 管理（修改权限、协作者等）


class BasePolicy:
    """
    权限策略基类

    所有权限策略类应继承此类并实现具体的权限判断方法
    """

    @staticmethod
    def is_superuser(user) -> bool:
        """判断是否为超级用户"""
        return user and user.is_authenticated and user.is_superuser

    @staticmethod
    def is_authenticated(user) -> bool:
        """判断用户是否已认证"""
        return user and user.is_authenticated

    @staticmethod
    def is_creator(user, obj) -> bool:
        """判断用户是否为创建者"""
        if not user or not user.is_authenticated:
            return False
        return obj.create_user == user
```

---

### 3.2 文集权限策略

#### 3.2.1 ProjectAccessPolicy（文集访问策略）

```python
# app_api_v1/policies/project_policy.py
from .base import BasePolicy, Action
from app_doc.models import Project, ProjectCollaborator
from django.contrib.auth.models import User


class ProjectAccessPolicy(BasePolicy):
    """
    文集访问策略

    实现文集的权限判断逻辑：
    - role=0: 公开
    - role=1: 私密
    - role=2: 指定用户
    - role=3: 访问码
    """

    @staticmethod
    def is_collaborator(user, project: Project) -> bool:
        """判断用户是否为文集协作者"""
        if not user or not user.is_authenticated:
            return False
        return ProjectCollaborator.objects.filter(
            project=project,
            user=user
        ).exists()

    @staticmethod
    def get_collaborator_role(user, project: Project) -> Optional[int]:
        """获取协作者的角色（0或1），如果不是协作者返回None"""
        if not user or not user.is_authenticated:
            return None
        try:
            colla = ProjectCollaborator.objects.get(project=project, user=user)
            return colla.role
        except ProjectCollaborator.DoesNotExist:
            return None

    @staticmethod
    def is_role2_permitted_user(user, project: Project) -> bool:
        """判断用户是否在 role=2 的许可用户列表中"""
        if not user or not user.is_authenticated:
            return False
        if project.role != 2:
            return False
        # role_value 存储的是用户名列表（字符串）
        return str(user.username) in project.role_value

    @staticmethod
    def has_read_permission(user, project: Project, viewcode: str = None) -> bool:
        """
        判断用户是否有读取文集的权限

        Args:
            user: 用户对象
            project: 文集对象
            viewcode: 访问码（用于 role=3 的情况）

        Returns:
            bool: 是否有读权限
        """
        # 超级用户拥有所有权限
        if ProjectAccessPolicy.is_superuser(user):
            return True

        # 创建者拥有所有权限
        if ProjectAccessPolicy.is_creator(user, project):
            return True

        # 协作者拥有读权限
        if ProjectAccessPolicy.is_collaborator(user, project):
            return True

        # 根据文集的 role 判断
        if project.role == 0:
            # 公开文集：所有人可读
            return True

        elif project.role == 1:
            # 私密文集：仅创建者和协作者可读（前面已判断）
            return False

        elif project.role == 2:
            # 指定用户可见：判断用户是否在许可列表中
            return ProjectAccessPolicy.is_role2_permitted_user(user, project)

        elif project.role == 3:
            # 访问码可见：验证访问码
            if viewcode and project.role_value == viewcode:
                return True
            return False

        return False

    @staticmethod
    def has_write_permission(user, project: Project) -> bool:
        """
        判断用户是否有写入文集的权限（创建/更新/删除文档）

        Args:
            user: 用户对象
            project: 文集对象

        Returns:
            bool: 是否有写权限
        """
        # 必须是认证用户
        if not ProjectAccessPolicy.is_authenticated(user):
            return False

        # 超级用户拥有所有权限
        if ProjectAccessPolicy.is_superuser(user):
            return True

        # 创建者拥有所有权限
        if ProjectAccessPolicy.is_creator(user, project):
            return True

        # 协作者拥有写权限
        if ProjectAccessPolicy.is_collaborator(user, project):
            return True

        return False

    @staticmethod
    def has_manage_permission(user, project: Project) -> bool:
        """
        判断用户是否有管理文集的权限（修改权限、协作者、文集设置等）

        Args:
            user: 用户对象
            project: 文集对象

        Returns:
            bool: 是否有管理权限
        """
        # 必须是认证用户
        if not ProjectAccessPolicy.is_authenticated(user):
            return False

        # 超级用户拥有所有权限
        if ProjectAccessPolicy.is_superuser(user):
            return True

        # 仅创建者有管理权限
        if ProjectAccessPolicy.is_creator(user, project):
            return True

        return False

    @staticmethod
    def can_perform_action(user, project: Project, action: Action,
                          viewcode: str = None) -> bool:
        """
        统一的权限判断入口

        Args:
            user: 用户对象
            project: 文集对象
            action: 操作类型（枚举）
            viewcode: 访问码（可选）

        Returns:
            bool: 是否允许执行该操作
        """
        if action == Action.VIEW:
            return ProjectAccessPolicy.has_read_permission(user, project, viewcode)
        elif action in [Action.CREATE, Action.UPDATE, Action.DELETE]:
            return ProjectAccessPolicy.has_write_permission(user, project)
        elif action == Action.MANAGE:
            return ProjectAccessPolicy.has_manage_permission(user, project)
        else:
            return False
```

---

### 3.3 文档权限策略

#### 3.3.1 DocAccessPolicy（文档访问策略）

```python
# app_api_v1/policies/doc_policy.py
from .base import BasePolicy, Action
from .project_policy import ProjectAccessPolicy
from app_doc.models import Doc, Project, ProjectCollaborator
from django.contrib.auth.models import User
from typing import Optional


class DocAccessPolicy(BasePolicy):
    """
    文档访问策略

    文档的权限继承自所属文集，同时考虑：
    - 文档状态（草稿/发布）
    - 协作者角色（role=0/1）
    """

    @staticmethod
    def get_doc_project(doc: Doc) -> Optional[Project]:
        """获取文档所属的文集"""
        try:
            return Project.objects.get(id=doc.top_doc)
        except Project.DoesNotExist:
            return None

    @staticmethod
    def is_draft(doc: Doc) -> bool:
        """判断文档是否为草稿状态"""
        return doc.status == 0

    @staticmethod
    def has_read_permission(user, doc: Doc, viewcode: str = None) -> bool:
        """
        判断用户是否有读取文档的权限

        Args:
            user: 用户对象
            doc: 文档对象
            viewcode: 访问码（用于 role=3 的情况）

        Returns:
            bool: 是否有读权限
        """
        # 超级用户拥有所有权限
        if DocAccessPolicy.is_superuser(user):
            return True

        # 草稿状态：仅创建者可读
        if DocAccessPolicy.is_draft(doc):
            return DocAccessPolicy.is_creator(user, doc)

        # 获取文档所属文集
        project = DocAccessPolicy.get_doc_project(doc)
        if not project:
            return False

        # 发布状态：遵循文集权限
        return ProjectAccessPolicy.has_read_permission(user, project, viewcode)

    @staticmethod
    def has_create_permission(user, project: Project) -> bool:
        """
        判断用户是否有在文集中创建文档的权限

        Args:
            user: 用户对象
            project: 文集对象

        Returns:
            bool: 是否有创建权限
        """
        # 必须是认证用户
        if not DocAccessPolicy.is_authenticated(user):
            return False

        # 超级用户拥有所有权限
        if DocAccessPolicy.is_superuser(user):
            return True

        # 创建者拥有创建权限
        if DocAccessPolicy.is_creator(user, project):
            return True

        # 协作者拥有创建权限（role=0 和 role=1 都可以创建）
        if ProjectAccessPolicy.is_collaborator(user, project):
            return True

        return False

    @staticmethod
    def has_update_permission(user, doc: Doc) -> bool:
        """
        判断用户是否有更新文档的权限

        协作者权限：
        - role=0: 只能修改自己创建的文档
        - role=1: 可以修改所有文档

        Args:
            user: 用户对象
            doc: 文档对象

        Returns:
            bool: 是否有更新权限
        """
        # 必须是认证用户
        if not DocAccessPolicy.is_authenticated(user):
            return False

        # 超级用户拥有所有权限
        if DocAccessPolicy.is_superuser(user):
            return True

        # 获取文档所属文集
        project = DocAccessPolicy.get_doc_project(doc)
        if not project:
            return False

        # 文集创建者拥有所有权限
        if DocAccessPolicy.is_creator(user, project):
            return True

        # 文档创建者可以修改自己的文档
        if DocAccessPolicy.is_creator(user, doc):
            return True

        # 协作者权限判断
        colla_role = ProjectAccessPolicy.get_collaborator_role(user, project)
        if colla_role is not None:
            if colla_role == 1:
                # role=1 的协作者可以修改所有文档
                return True
            elif colla_role == 0:
                # role=0 的协作者只能修改自己创建的文档
                return DocAccessPolicy.is_creator(user, doc)

        return False

    @staticmethod
    def has_delete_permission(user, doc: Doc) -> bool:
        """
        判断用户是否有删除文档的权限

        协作者权限：
        - role=0: 只能删除自己创建的文档
        - role=1: 可以删除文集中的任何文档

        Args:
            user: 用户对象
            doc: 文档对象

        Returns:
            bool: 是否有删除权限
        """
        # 必须是认证用户
        if not DocAccessPolicy.is_authenticated(user):
            return False

        # 超级用户拥有所有权限
        if DocAccessPolicy.is_superuser(user):
            return True

        # 获取文档所属文集
        project = DocAccessPolicy.get_doc_project(doc)
        if not project:
            return False

        # 文集创建者拥有所有权限
        if DocAccessPolicy.is_creator(user, project):
            return True

        # 协作者删除权限判断
        colla_role = ProjectAccessPolicy.get_collaborator_role(user, project)
        if colla_role is not None:
            if colla_role == 1:
                # role=1 协作者可以删除文集中的任何文档
                return True
            elif colla_role == 0:
                # role=0 协作者只能删除自己创建的文档
                return DocAccessPolicy.is_creator(user, doc)

        return False

    @staticmethod
    def can_perform_action(user, doc: Doc, action: Action,
                          viewcode: str = None) -> bool:
        """
        统一的权限判断入口

        Args:
            user: 用户对象
            doc: 文档对象
            action: 操作类型（枚举）
            viewcode: 访问码（可选）

        Returns:
            bool: 是否允许执行该操作
        """
        if action == Action.VIEW:
            return DocAccessPolicy.has_read_permission(user, doc, viewcode)
        elif action == Action.UPDATE:
            return DocAccessPolicy.has_update_permission(user, doc)
        elif action == Action.DELETE:
            return DocAccessPolicy.has_delete_permission(user, doc)
        else:
            return False
```

---

### 3.4 DRF Permission 集成

#### 3.4.1 ProjectPermission（DRF 权限类）

```python
# app_api_v1/permissions/project.py
from rest_framework import permissions
from ..policies.project_policy import ProjectAccessPolicy
from ..policies.base import Action


class ProjectPermission(permissions.BasePermission):
    """
    文集权限类（DRF 集成）

    使用方法：
    class ProjectViewSet(viewsets.ModelViewSet):
        permission_classes = [ProjectPermission]
    """

    message = "您没有权限访问该文集"

    def has_permission(self, request, view):
        """
        视图级权限：判断用户是否有访问该视图的权限

        对于列表操作（GET /api/v1/projects），所有用户都可以访问
        对于创建操作（POST /api/v1/projects），需要认证用户
        """
        # 列表和检索操作：所有人可访问（后续由 has_object_permission 过滤）
        if request.method in permissions.SAFE_METHODS:
            return True

        # 创建操作：需要认证用户
        if request.method == 'POST':
            return request.user and request.user.is_authenticated

        return True

    def has_object_permission(self, request, view, obj):
        """
        对象级权限：判断用户是否有访问该文集对象的权限

        Args:
            request: 请求对象
            view: 视图对象
            obj: 文集对象
        """
        # 从 cookie 中获取访问码
        viewcode = request.COOKIES.get(f'viewcode-{obj.id}')

        # GET、HEAD、OPTIONS 请求：读权限
        if request.method in permissions.SAFE_METHODS:
            return ProjectAccessPolicy.has_read_permission(
                request.user, obj, viewcode
            )

        # PUT、PATCH 请求：写权限
        elif request.method in ['PUT', 'PATCH']:
            # 根据操作类型细分
            # 如果是修改权限设置，需要管理权限
            if 'role' in request.data or 'role_value' in request.data:
                return ProjectAccessPolicy.has_manage_permission(request.user, obj)
            # 普通更新，需要写权限
            return ProjectAccessPolicy.has_write_permission(request.user, obj)

        # DELETE 请求：管理权限
        elif request.method == 'DELETE':
            return ProjectAccessPolicy.has_manage_permission(request.user, obj)

        return False


class ProjectManagePermission(permissions.BasePermission):
    """
    文集管理权限类（用于协作者、权限设置等管理接口）

    使用方法：
    @action(detail=True, methods=['post'], permission_classes=[ProjectManagePermission])
    def add_collaborator(self, request, pk=None):
        ...
    """

    message = "您没有权限管理该文集"

    def has_object_permission(self, request, view, obj):
        """仅文集创建者和超级用户可管理"""
        return ProjectAccessPolicy.has_manage_permission(request.user, obj)
```

#### 3.4.2 DocPermission（DRF 权限类）

```python
# app_api_v1/permissions/doc.py
from rest_framework import permissions
from ..policies.doc_policy import DocAccessPolicy
from ..policies.project_policy import ProjectAccessPolicy
from app_doc.models import Project


class DocPermission(permissions.BasePermission):
    """
    文档权限类（DRF 集成）

    使用方法：
    class DocViewSet(viewsets.ModelViewSet):
        permission_classes = [DocPermission]
    """

    message = "您没有权限访问该文档"

    def has_permission(self, request, view):
        """
        视图级权限：判断用户是否有访问该视图的权限

        对于列表操作（GET /api/v1/docs），所有用户都可以访问
        对于创建操作（POST /api/v1/docs），需要认证用户且有文集写权限
        """
        # 列表和检索操作：所有人可访问（后续由 has_object_permission 过滤）
        if request.method in permissions.SAFE_METHODS:
            return True

        # 创建操作：需要认证用户且检查文集权限
        if request.method == 'POST':
            if not (request.user and request.user.is_authenticated):
                return False

            # 检查是否有指定文集ID
            project_id = request.data.get('top_doc') or request.data.get('project_id')
            if not project_id:
                return False

            try:
                project = Project.objects.get(id=project_id)
                return DocAccessPolicy.has_create_permission(request.user, project)
            except Project.DoesNotExist:
                return False

        return True

    def has_object_permission(self, request, view, obj):
        """
        对象级权限：判断用户是否有访问该文档对象的权限

        Args:
            request: 请求对象
            view: 视图对象
            obj: 文档对象
        """
        # 从 cookie 中获取访问码
        project = DocAccessPolicy.get_doc_project(obj)
        viewcode = request.COOKIES.get(f'viewcode-{project.id}') if project else None

        # GET、HEAD、OPTIONS 请求：读权限
        if request.method in permissions.SAFE_METHODS:
            return DocAccessPolicy.has_read_permission(request.user, obj, viewcode)

        # PUT、PATCH 请求：更新权限
        elif request.method in ['PUT', 'PATCH']:
            return DocAccessPolicy.has_update_permission(request.user, obj)

        # DELETE 请求：删除权限
        elif request.method == 'DELETE':
            return DocAccessPolicy.has_delete_permission(request.user, obj)

        return False
```

---

## 4. 权限工具函数

```python
# app_api_v1/permissions/utils.py
from app_doc.models import Project, ProjectCollaborator
from django.contrib.auth.models import User
from typing import List


def get_user_readable_projects(user) -> List[int]:
    """
    获取用户有浏览权限的文集ID列表

    Args:
        user: 用户对象

    Returns:
        List[int]: 文集ID列表
    """
    if not user or not user.is_authenticated:
        # 游客：只能看到公开文集(role=0)和访问码文集(role=3)
        return list(Project.objects.filter(role__in=[0, 3]).values_list('id', flat=True))

    # 超级用户：所有文集
    if user.is_superuser:
        return list(Project.objects.all().values_list('id', flat=True))

    # 协作文集ID列表
    colla_project_ids = list(
        ProjectCollaborator.objects.filter(user=user).values_list('project_id', flat=True)
    )

    # 自己创建的文集ID列表
    own_project_ids = list(
        Project.objects.filter(create_user=user).values_list('id', flat=True)
    )

    # 公开文集和访问码文集
    public_project_ids = list(
        Project.objects.filter(role__in=[0, 3]).values_list('id', flat=True)
    )

    # 指定用户可见的文集
    role2_project_ids = list(
        Project.objects.filter(
            role=2,
            role_value__contains=str(user.username)
        ).values_list('id', flat=True)
    )

    # 合并所有ID（去重）
    all_ids = set(own_project_ids) | set(colla_project_ids) | set(public_project_ids) | set(role2_project_ids)
    return list(all_ids)


def get_user_writable_projects(user) -> List[int]:
    """
    获取用户有写权限的文集ID列表

    Args:
        user: 用户对象

    Returns:
        List[int]: 文集ID列表
    """
    if not user or not user.is_authenticated:
        return []

    # 超级用户：所有文集
    if user.is_superuser:
        return list(Project.objects.all().values_list('id', flat=True))

    # 协作文集ID列表
    colla_project_ids = list(
        ProjectCollaborator.objects.filter(user=user).values_list('project_id', flat=True)
    )

    # 自己创建的文集ID列表
    own_project_ids = list(
        Project.objects.filter(create_user=user).values_list('id', flat=True)
    )

    # 合并（去重）
    all_ids = set(own_project_ids) | set(colla_project_ids)
    return list(all_ids)


def get_user_manageable_projects(user) -> List[int]:
    """
    获取用户有管理权限的文集ID列表（仅自己创建的文集）

    Args:
        user: 用户对象

    Returns:
        List[int]: 文集ID列表
    """
    if not user or not user.is_authenticated:
        return []

    # 超级用户：所有文集
    if user.is_superuser:
        return list(Project.objects.all().values_list('id', flat=True))

    # 仅返回自己创建的文集
    return list(Project.objects.filter(create_user=user).values_list('id', flat=True))
```

---

## 5. 使用示例

### 5.1 在 ViewSet 中使用

```python
# app_api_v1/views/project.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from ..permissions.project import ProjectPermission, ProjectManagePermission
from ..permissions.utils import get_user_readable_projects
from app_doc.models import Project


class ProjectViewSet(viewsets.ModelViewSet):
    """文集 ViewSet"""
    queryset = Project.objects.all()
    permission_classes = [ProjectPermission]

    def get_queryset(self):
        """根据用户权限过滤文集列表"""
        user = self.request.user
        readable_ids = get_user_readable_projects(user)
        return Project.objects.filter(id__in=readable_ids)

    @action(detail=True, methods=['post'],
            permission_classes=[ProjectManagePermission])
    def add_collaborator(self, request, pk=None):
        """添加协作者（需要管理权限）"""
        project = self.get_object()
        # ... 实现添加协作者的逻辑
        return Response({'status': 'success'})

    @action(detail=True, methods=['get'])
    def tree(self, request, pk=None):
        """获取文集文档树（需要读权限）"""
        project = self.get_object()
        # ProjectPermission 会自动检查读权限
        # ... 实现获取文档树的逻辑
        return Response({'tree': []})
```

### 5.2 在 APIView 中使用

```python
# app_api_v1/views/doc.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..policies.doc_policy import DocAccessPolicy
from ..policies.base import Action
from app_doc.models import Doc


class DocDetailView(APIView):
    """文档详情视图"""

    def get(self, request, doc_id):
        try:
            doc = Doc.objects.get(id=doc_id)
        except Doc.DoesNotExist:
            return Response({'error': '文档不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 从 cookie 获取访问码
        project = DocAccessPolicy.get_doc_project(doc)
        viewcode = request.COOKIES.get(f'viewcode-{project.id}') if project else None

        # 检查读权限
        if not DocAccessPolicy.has_read_permission(request.user, doc, viewcode):
            return Response({'error': '无权限访问'}, status=status.HTTP_403_FORBIDDEN)

        # 返回文档数据
        return Response({
            'id': doc.id,
            'name': doc.name,
            'content': doc.content
        })
```

### 5.3 在服务层使用

```python
# app_api_v1/services/doc_service.py
from ..policies.doc_policy import DocAccessPolicy
from ..policies.project_policy import ProjectAccessPolicy
from app_doc.models import Doc, Project


class DocService:
    """文档业务逻辑服务"""

    @staticmethod
    def create_doc(user, project_id: int, name: str, content: str):
        """创建文档"""
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return None, "文集不存在"

        # 检查创建权限
        if not DocAccessPolicy.has_create_permission(user, project):
            return None, "无权限在该文集中创建文档"

        # 创建文档
        doc = Doc.objects.create(
            name=name,
            pre_content=content,
            content=content,
            top_doc=project_id,
            create_user=user,
            status=1
        )
        return doc, None
```

---

## 6. 单元测试

### 6.1 测试结构

```python
# app_api_v1/tests/test_permissions.py
from django.test import TestCase
from django.contrib.auth.models import User
from app_doc.models import Project, ProjectCollaborator, Doc
from ..policies.project_policy import ProjectAccessPolicy
from ..policies.doc_policy import DocAccessPolicy


class ProjectAccessPolicyTestCase(TestCase):
    """文集权限策略测试"""

    def setUp(self):
        """测试数据准备"""
        # 创建用户
        self.owner = User.objects.create_user(username='owner', password='pass')
        self.collaborator = User.objects.create_user(username='collaborator', password='pass')
        self.normal_user = User.objects.create_user(username='normal', password='pass')
        self.superuser = User.objects.create_user(
            username='admin', password='pass', is_superuser=True
        )

        # 创建文集
        self.public_project = Project.objects.create(
            name='公开文集', role=0, create_user=self.owner
        )
        self.private_project = Project.objects.create(
            name='私密文集', role=1, create_user=self.owner
        )
        self.role2_project = Project.objects.create(
            name='指定用户文集', role=2,
            role_value='normal', create_user=self.owner
        )
        self.viewcode_project = Project.objects.create(
            name='访问码文集', role=3,
            role_value='secret123', create_user=self.owner
        )

        # 添加协作者
        ProjectCollaborator.objects.create(
            project=self.private_project,
            user=self.collaborator,
            role=1
        )

    def test_public_project_read_permission(self):
        """测试公开文集的读权限"""
        # 所有人都可以读取公开文集
        self.assertTrue(
            ProjectAccessPolicy.has_read_permission(self.owner, self.public_project)
        )
        self.assertTrue(
            ProjectAccessPolicy.has_read_permission(self.normal_user, self.public_project)
        )
        self.assertTrue(
            ProjectAccessPolicy.has_read_permission(None, self.public_project)
        )

    def test_private_project_read_permission(self):
        """测试私密文集的读权限"""
        # 创建者可以读取
        self.assertTrue(
            ProjectAccessPolicy.has_read_permission(self.owner, self.private_project)
        )
        # 协作者可以读取
        self.assertTrue(
            ProjectAccessPolicy.has_read_permission(self.collaborator, self.private_project)
        )
        # 普通用户不能读取
        self.assertFalse(
            ProjectAccessPolicy.has_read_permission(self.normal_user, self.private_project)
        )
        # 游客不能读取
        self.assertFalse(
            ProjectAccessPolicy.has_read_permission(None, self.private_project)
        )

    def test_role2_project_read_permission(self):
        """测试指定用户文集的读权限"""
        # 创建者可以读取
        self.assertTrue(
            ProjectAccessPolicy.has_read_permission(self.owner, self.role2_project)
        )
        # 指定用户可以读取
        self.assertTrue(
            ProjectAccessPolicy.has_read_permission(self.normal_user, self.role2_project)
        )
        # 非指定用户不能读取
        self.assertFalse(
            ProjectAccessPolicy.has_read_permission(self.collaborator, self.role2_project)
        )

    def test_viewcode_project_read_permission(self):
        """测试访问码文集的读权限"""
        # 创建者可以读取（无需访问码）
        self.assertTrue(
            ProjectAccessPolicy.has_read_permission(self.owner, self.viewcode_project)
        )
        # 普通用户提供正确访问码可以读取
        self.assertTrue(
            ProjectAccessPolicy.has_read_permission(
                self.normal_user, self.viewcode_project, viewcode='secret123'
            )
        )
        # 普通用户提供错误访问码不能读取
        self.assertFalse(
            ProjectAccessPolicy.has_read_permission(
                self.normal_user, self.viewcode_project, viewcode='wrong'
            )
        )
        # 普通用户不提供访问码不能读取
        self.assertFalse(
            ProjectAccessPolicy.has_read_permission(
                self.normal_user, self.viewcode_project
            )
        )

    def test_write_permission(self):
        """测试写权限"""
        # 创建者有写权限
        self.assertTrue(
            ProjectAccessPolicy.has_write_permission(self.owner, self.private_project)
        )
        # 协作者有写权限
        self.assertTrue(
            ProjectAccessPolicy.has_write_permission(self.collaborator, self.private_project)
        )
        # 普通用户没有写权限
        self.assertFalse(
            ProjectAccessPolicy.has_write_permission(self.normal_user, self.private_project)
        )

    def test_manage_permission(self):
        """测试管理权限"""
        # 创建者有管理权限
        self.assertTrue(
            ProjectAccessPolicy.has_manage_permission(self.owner, self.private_project)
        )
        # 协作者没有管理权限
        self.assertFalse(
            ProjectAccessPolicy.has_manage_permission(self.collaborator, self.private_project)
        )
        # 超级用户有管理权限
        self.assertTrue(
            ProjectAccessPolicy.has_manage_permission(self.superuser, self.private_project)
        )


class DocAccessPolicyTestCase(TestCase):
    """文档权限策略测试"""

    def setUp(self):
        """测试数据准备"""
        # 创建用户
        self.owner = User.objects.create_user(username='owner', password='pass')
        self.collaborator_role0 = User.objects.create_user(username='colla0', password='pass')
        self.collaborator_role1 = User.objects.create_user(username='colla1', password='pass')
        self.normal_user = User.objects.create_user(username='normal', password='pass')

        # 创建文集
        self.project = Project.objects.create(
            name='测试文集', role=0, create_user=self.owner
        )

        # 添加协作者
        ProjectCollaborator.objects.create(
            project=self.project, user=self.collaborator_role0, role=0
        )
        ProjectCollaborator.objects.create(
            project=self.project, user=self.collaborator_role1, role=1
        )

        # 创建文档
        self.published_doc_by_owner = Doc.objects.create(
            name='已发布文档（创建者）',
            top_doc=self.project.id,
            create_user=self.owner,
            status=1
        )
        self.draft_doc_by_owner = Doc.objects.create(
            name='草稿文档（创建者）',
            top_doc=self.project.id,
            create_user=self.owner,
            status=0
        )
        self.doc_by_colla0 = Doc.objects.create(
            name='协作者0的文档',
            top_doc=self.project.id,
            create_user=self.collaborator_role0,
            status=1
        )

    def test_draft_read_permission(self):
        """测试草稿文档的读权限"""
        # 创建者可以读取自己的草稿
        self.assertTrue(
            DocAccessPolicy.has_read_permission(self.owner, self.draft_doc_by_owner)
        )
        # 其他人不能读取草稿
        self.assertFalse(
            DocAccessPolicy.has_read_permission(self.collaborator_role1, self.draft_doc_by_owner)
        )

    def test_published_read_permission(self):
        """测试已发布文档的读权限"""
        # 所有人都可以读取公开文集的已发布文档
        self.assertTrue(
            DocAccessPolicy.has_read_permission(self.owner, self.published_doc_by_owner)
        )
        self.assertTrue(
            DocAccessPolicy.has_read_permission(self.normal_user, self.published_doc_by_owner)
        )

    def test_update_permission_role0(self):
        """测试 role=0 协作者的更新权限"""
        # role=0 协作者可以修改自己创建的文档
        self.assertTrue(
            DocAccessPolicy.has_update_permission(self.collaborator_role0, self.doc_by_colla0)
        )
        # role=0 协作者不能修改其他人的文档
        self.assertFalse(
            DocAccessPolicy.has_update_permission(self.collaborator_role0, self.published_doc_by_owner)
        )

    def test_update_permission_role1(self):
        """测试 role=1 协作者的更新权限"""
        # role=1 协作者可以修改所有文档
        self.assertTrue(
            DocAccessPolicy.has_update_permission(self.collaborator_role1, self.published_doc_by_owner)
        )
        self.assertTrue(
            DocAccessPolicy.has_update_permission(self.collaborator_role1, self.doc_by_colla0)
        )

    def test_delete_permission(self):
        """测试删除权限"""
        # 文集创建者可以删除所有文档
        self.assertTrue(
            DocAccessPolicy.has_delete_permission(self.owner, self.doc_by_colla0)
        )
        # role=0 协作者只能删除自己的文档
        self.assertTrue(
            DocAccessPolicy.has_delete_permission(self.collaborator_role0, self.doc_by_colla0)
        )
        self.assertFalse(
            DocAccessPolicy.has_delete_permission(self.collaborator_role0, self.published_doc_by_owner)
        )
        # role=1 协作者可以删除文集中的任何文档
        self.assertTrue(
            DocAccessPolicy.has_delete_permission(self.collaborator_role1, self.published_doc_by_owner)
        )
        self.assertTrue(
            DocAccessPolicy.has_delete_permission(self.collaborator_role1, self.doc_by_colla0)
        )
```

### 6.2 测试运行

```bash
# 运行所有权限测试
python manage.py test app_api_v1.tests.test_permissions

# 运行特定测试类
python manage.py test app_api_v1.tests.test_permissions.ProjectAccessPolicyTestCase

# 运行特定测试方法
python manage.py test app_api_v1.tests.test_permissions.ProjectAccessPolicyTestCase.test_public_project_read_permission
```

---

## 7. 权限测试矩阵

### 7.1 文集权限矩阵

| 角色 / 文集类型 | role=0 (公开) | role=1 (私密) | role=2 (指定用户) | role=3 (访问码) |
|----------------|--------------|--------------|------------------|----------------|
| **游客** | ✅ 读 | ❌ | ❌ | ✅ 读（需访问码） |
| **普通用户** | ✅ 读 | ❌ | ✅ 读（在列表中） | ✅ 读（需访问码） |
| **协作者** | ✅ 读 ✅ 写 | ✅ 读 ✅ 写 | ✅ 读 ✅ 写 | ✅ 读 ✅ 写 |
| **创建者** | ✅ 读 ✅ 写 ✅ 管理 | ✅ 读 ✅ 写 ✅ 管理 | ✅ 读 ✅ 写 ✅ 管理 | ✅ 读 ✅ 写 ✅ 管理 |
| **超级用户** | ✅ 读 ✅ 写 ✅ 管理 | ✅ 读 ✅ 写 ✅ 管理 | ✅ 读 ✅ 写 ✅ 管理 | ✅ 读 ✅ 写 ✅ 管理 |

### 7.2 文档权限矩阵（协作者）

| 操作 / 协作者角色 | role=0 | role=1 |
|-------------------|--------|--------|
| **创建文档** | ✅ | ✅ |
| **修改自己的文档** | ✅ | ✅ |
| **修改他人的文档** | ❌ | ✅ |
| **删除自己的文档** | ✅ | ✅ |
| **删除他人的文档** | ❌ | ✅ |

### 7.3 文档状态权限矩阵

| 角色 / 文档状态 | status=0 (草稿) | status=1 (发布) |
|----------------|-----------------|-----------------|
| **创建者** | ✅ 读 ✅ 写 | ✅ 读 ✅ 写 |
| **协作者** | ❌ | ✅ 读 ✅ 写（根据角色） |
| **其他用户** | ❌ | ✅ 读（遵循文集权限） |

---

## 8. 迁移步骤

### 8.1 Phase 1.5：权限抽象层实现

#### 步骤 1：创建目录结构（第1天）
```bash
mkdir -p app_api_v1/policies
mkdir -p app_api_v1/permissions
mkdir -p app_api_v1/tests
```

#### 步骤 2：实现 Policy 层（第2-3天）
1. 实现 `policies/base.py`
2. 实现 `policies/project_policy.py`
3. 实现 `policies/doc_policy.py`
4. 实现 `permissions/utils.py`

#### 步骤 3：编写单元测试（第4-5天）
1. 实现 `tests/test_permissions.py`
2. 编写文集权限测试用例（覆盖所有 role）
3. 编写文档权限测试用例（覆盖所有场景）
4. 运行测试，确保所有用例通过

#### 步骤 4：实现 DRF Permission 层（第6天）
1. 实现 `permissions/project.py`
2. 实现 `permissions/doc.py`

#### 步骤 5：集成测试（第7天）
1. 在测试环境中创建 API 端点
2. 测试所有权限场景
3. 修复发现的问题

### 8.2 验收标准

- [ ] 所有单元测试通过（覆盖率 > 90%）
- [ ] 权限测试矩阵中的所有场景验证通过
- [ ] 文档完整（包括使用示例）
- [ ] 代码 Review 通过

---

## 9. 最佳实践

### 9.1 权限判断原则

1. **最小权限原则**：默认拒绝，明确授权
2. **早失败原则**：越早判断权限越好，避免不必要的数据库查询
3. **缓存优化**：频繁的权限判断可以考虑缓存协作者关系
4. **日志记录**：记录权限拒绝的日志，便于排查问题

### 9.2 代码规范

1. **命名规范**：
   - Policy 类以 `Policy` 结尾
   - Permission 类以 `Permission` 结尾
   - 方法名以 `has_*_permission` 或 `can_*` 格式

2. **文档规范**：
   - 每个方法都要有 docstring
   - 注明参数类型和返回值类型
   - 说明特殊场景

3. **测试规范**：
   - 每个权限判断方法至少有一个对应的测试用例
   - 覆盖正常场景和异常场景
   - 测试方法名清晰描述测试意图

### 9.3 性能优化

1. **减少数据库查询**：
   - 使用 `select_related` 和 `prefetch_related` 优化关联查询
   - 在 ViewSet 的 `get_queryset` 中预加载权限相关数据

2. **缓存策略**：
   ```python
   from django.core.cache import cache

   def is_collaborator_cached(user, project):
       cache_key = f'is_collaborator:{user.id}:{project.id}'
       result = cache.get(cache_key)
       if result is None:
           result = ProjectAccessPolicy.is_collaborator(user, project)
           cache.set(cache_key, result, timeout=300)  # 5分钟缓存
       return result
   ```

3. **批量权限判断**：
   ```python
   def filter_readable_projects(user, projects):
       """批量过滤可读文集"""
       readable_ids = get_user_readable_projects(user)
       return [p for p in projects if p.id in readable_ids]
   ```

---

## 10. 常见问题

### 10.1 访问码如何处理？

访问码存储在 cookie 中，格式为 `viewcode-{project_id}`。在 Permission 类中：

```python
viewcode = request.COOKIES.get(f'viewcode-{obj.id}')
has_permission = ProjectAccessPolicy.has_read_permission(request.user, obj, viewcode)
```

### 10.2 如何处理匿名用户？

Policy 层会检查用户是否为 `None` 或未认证：

```python
if not user or not user.is_authenticated:
    # 匿名用户逻辑
```

### 10.3 如何扩展新的权限规则？

1. 在 `Action` 枚举中添加新的操作类型
2. 在对应的 Policy 类中实现 `has_*_permission` 方法
3. 编写测试用例验证新规则
4. 在 `can_perform_action` 方法中添加新的分支

### 10.4 旧代码如何迁移？

旧代码可以逐步迁移，Policy 层可以在旧视图中直接使用：

```python
# 旧视图中使用 Policy
from app_api_v1.policies.project_policy import ProjectAccessPolicy

def old_view(request, pro_id):
    project = Project.objects.get(id=pro_id)
    if not ProjectAccessPolicy.has_read_permission(request.user, project):
        return render(request, '403.html')
    # ...
```

---

## 11. 后续优化方向

1. **权限缓存机制**：对频繁的权限判断结果进行缓存
2. **权限日志审计**：记录敏感操作的权限判断过程
3. **权限预加载**：在序列化器中预加载用户权限信息
4. **权限 API**：提供批量权限查询接口（`POST /api/v1/permissions/check`）
5. **权限可视化**：在前端显示用户对资源的权限

---

## 附录

### A. 相关文件清单

| 文件路径 | 说明 |
|---------|------|
| `app_api_v1/policies/base.py` | 基础策略类 |
| `app_api_v1/policies/project_policy.py` | 文集权限策略 |
| `app_api_v1/policies/doc_policy.py` | 文档权限策略 |
| `app_api_v1/permissions/base.py` | 基础权限类 |
| `app_api_v1/permissions/project.py` | 文集 DRF 权限 |
| `app_api_v1/permissions/doc.py` | 文档 DRF 权限 |
| `app_api_v1/permissions/utils.py` | 权限工具函数 |
| `app_api_v1/tests/test_permissions.py` | 权限单元测试 |

### B. 参考资料

- [Django REST Framework Permissions](https://www.django-rest-framework.org/api-guide/permissions/)
- [Django Auth System](https://docs.djangoproject.com/en/4.2/topics/auth/)
- 原项目代码：
  - `app_doc/models.py:6-271`（数据模型）
  - `app_doc/views.py:1108-1130`（文集权限检查）
  - `app_api/utils.py:6-34`（权限工具函数）
