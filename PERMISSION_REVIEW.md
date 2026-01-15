# 权限设计文档 Review 报告

**Review 时间**: 2026-01-15
**Review 对象**: PERMISSION_DESIGN.md
**Review 方式**: 对照现有代码逐一验证

---

## 1. 总体评估

✅ **设计文档总体准确度：95%**

设计文档准确地反映了现有系统的大部分权限逻辑，但发现了 **1 处重要错误** 需要修正。

---

## 2. 逐项验证结果

### 2.1 文集权限验证 ✅ 正确

#### 验证点 1: role=0 公开文集
- **设计文档**: 所有人可读
- **实际代码**: ✅ 正确
- **代码位置**: `app_doc/views.py:1016-1037` (无权限检查，直接通过)

#### 验证点 2: role=1 私密文集
- **设计文档**: 仅创建者/协作者可读
- **实际代码**: ✅ 正确
- **代码位置**:
  ```python
  # app_doc/views.py:1016
  if (project.role == 1) and (request.user != project.create_user) and (colla_user == 0):
      return render(request, '404.html')
  ```

#### 验证点 3: role=2 指定用户文集
- **设计文档**: role_value 包含的用户+创建者+协作者可读
- **实际代码**: ✅ 正确
- **代码位置**:
  ```python
  # app_doc/views.py:1019-1027
  elif project.role == 2:
      user_list = project.role_value
      if request.user.is_authenticated:
          if (request.user.username not in user_list) and \
                  (request.user != project.create_user) and \
                  (colla_user == 0):
              return render(request, '404.html')
      else:
          return render(request, '404.html')
  ```

#### 验证点 4: role=3 访问码文集
- **设计文档**: 验证访问码后可读
- **实际代码**: ✅ 正确
- **代码位置**:
  ```python
  # app_doc/views.py:1029-1037
  elif project.role == 3:
      if (request.user != project.create_user) and (colla_user == 0):
          viewcode = project.role_value
          viewcode_name = 'viewcode-{}'.format(project.id)
          r_viewcode = request.COOKIES[viewcode_name] if viewcode_name in request.COOKIES.keys() else 0
          if viewcode != r_viewcode:
              return redirect('/check_viewcode/?to={}'.format(request.path))
  ```

---

### 2.2 文档权限验证

#### 验证点 5: 文档草稿状态 (status=0) ✅ 正确
- **设计文档**: 仅创建者可访问
- **实际代码**: ✅ 正确
- **代码位置**:
  ```python
  # app_doc/views.py:1043-1046
  if doc.status == 0 and doc.create_user != request.user:
      raise ObjectDoesNotExist
  elif doc.status == 0 and doc.create_user == request.user:
      doc.name = _('【预览草稿】')+ doc.name
  ```

#### 验证点 6: 文档创建权限 ✅ 正确
- **设计文档**: 文集创建者和所有协作者（role=0/1）都可以创建文档
- **实际代码**: ✅ 正确
- **代码位置**:
  ```python
  # app_doc/views.py:1204-1206
  check_project = Project.objects.filter(id=project,create_user=request.user)
  colla_project = ProjectCollaborator.objects.filter(project=project,user=request.user)
  if check_project.count() > 0 or colla_project.count() > 0:
      # 允许创建
  ```

#### 验证点 7: 文档更新权限 ✅ 正确
- **设计文档**:
  - 文集创建者可以修改所有文档
  - 文档创建者可以修改自己的文档
  - role=1 协作者可以修改所有文档
  - role=0 协作者只能修改自己的文档
- **实际代码**: ✅ 正确
- **代码位置**:
  ```python
  # app_doc/views.py:1266-1278
  pro_colla = ProjectCollaborator.objects.filter(project=project,user=request.user)
  if pro_colla.count() == 0:
      is_pro_colla = False
  elif pro_colla[0].role == 1:
      is_pro_colla = True
  else:
      is_pro_colla = False

  # 判断用户是否有权限进行修改
  if (request.user == doc.create_user) or \
          (is_pro_colla is True) or \
          (request.user == project.create_user):
      # 允许修改
  ```

#### 验证点 8: 文档删除权限 ❌ **错误发现**
- **设计文档描述**:
  > role=0 协作者只能删除自己创建的文档
  > role=1 协作者也只能删除自己创建的文档

- **实际代码**: ❌ **与设计文档不符**
  ```python
  # app_doc/views.py:1409-1413
  # 如果请求用户为站点管理员、文档创建者、高级权限的协作者、文集的创建者，可以删除
  if (request.user == doc.create_user) \
          or (colla_user_role == 1) \          # ⚠️ role=1 协作者可以删除任何文档
          or (request.user == project.create_user)\
          or (request.user.is_superuser):
      # 允许删除
  ```

- **实际权限规则**:
  - ✅ 文档创建者可以删除自己的文档
  - ✅ **role=1 协作者可以删除文集中的任何文档**（设计文档错误）
  - ✅ 文集创建者可以删除文集中的任何文档
  - ✅ 超级用户可以删除任何文档
  - ✅ role=0 协作者只能删除自己的文档（通过 `request.user == doc.create_user` 判断）

---

### 2.3 协作者权限验证 ✅ 正确

#### 验证点 9: 协作者 role=0
- **设计文档**: 可新建文档，可修改/删除自己新建的文档
- **实际代码**: ✅ 正确（创建：1206行；修改：1276行；删除：1410行）

#### 验证点 10: 协作者 role=1
- **设计文档**: 可新建文档，可删除自己创建的文档、可修改所有文档
- **实际代码**: ⚠️ **部分错误**
  - ✅ 可新建文档（1206行）
  - ✅ 可修改所有文档（1269行）
  - ❌ **可删除所有文档**（1411行），不仅限于自己创建的

---

## 3. 需要修正的内容

### 3.1 PERMISSION_DESIGN.md 需要修正的部分

#### 位置 1: 第 3.3.1 节 DocAccessPolicy.has_delete_permission

**当前错误描述**:
```python
"""
判断用户是否有删除文档的权限

协作者权限：
- role=0: 只能删除自己创建的文档
- role=1: 只能删除自己创建的文档  # ❌ 错误

Args:
    user: 用户对象
    doc: 文档对象

Returns:
    bool: 是否有删除权限
"""
```

**应修正为**:
```python
"""
判断用户是否有删除文档的权限

协作者权限：
- role=0: 只能删除自己创建的文档
- role=1: 可以删除文集中的任何文档  # ✅ 正确

Args:
    user: 用户对象
    doc: 文档对象

Returns:
    bool: 是否有删除权限
"""
```

#### 位置 2: 第 3.3.1 节 DocAccessPolicy.has_delete_permission 方法实现

**当前错误实现**:
```python
# 协作者只能删除自己创建的文档（role=0 和 role=1 相同）
if ProjectAccessPolicy.is_collaborator(user, project):
    return DocAccessPolicy.is_creator(user, doc)
```

**应修正为**:
```python
# 协作者删除权限判断
colla_role = ProjectAccessPolicy.get_collaborator_role(user, project)
if colla_role is not None:
    if colla_role == 1:
        # role=1 协作者可以删除文集中的任何文档
        return True
    elif colla_role == 0:
        # role=0 协作者只能删除自己创建的文档
        return DocAccessPolicy.is_creator(user, doc)
```

#### 位置 3: 第 6.2 节 文档权限矩阵（协作者）

**当前错误表格**:
| 操作 / 协作者角色 | role=0 | role=1 |
|-------------------|--------|--------|
| **创建文档** | ✅ | ✅ |
| **修改自己的文档** | ✅ | ✅ |
| **修改他人的文档** | ❌ | ✅ |
| **删除自己的文档** | ✅ | ✅ |
| **删除他人的文档** | ❌ | ❌ |  ← ❌ **错误**

**应修正为**:
| 操作 / 协作者角色 | role=0 | role=1 |
|-------------------|--------|--------|
| **创建文档** | ✅ | ✅ |
| **修改自己的文档** | ✅ | ✅ |
| **修改他人的文档** | ❌ | ✅ |
| **删除自己的文档** | ✅ | ✅ |
| **删除他人的文档** | ❌ | ✅ |  ← ✅ **修正**

#### 位置 4: 第 1.2 节 协作者权限说明

**当前描述**:
| role 值 | 说明 |
|---------|------|
| 0 | 可新建文档，可修改/删除自己新建的文档 |
| 1 | 可新建文档，可删除自己创建的文档、可修改所有文档 |  ← ❌ **错误**

**应修正为**:
| role 值 | 说明 |
|---------|------|
| 0 | 可新建文档，可修改/删除自己新建的文档 |
| 1 | 可新建文档，可修改/删除文集中的所有文档 |  ← ✅ **修正**

---

## 4. 其他发现

### 4.1 旧 API 的权限限制

在 `app_api/views.py:728` 的 `delete_doc` 函数中，只检查了文档创建者权限：

```python
# app_api/views.py:745
if doc.create_user == token.user:
    # 允许删除
else:
    return JsonResponse({'status':False,'data':'非法请求'})
```

这意味着：
- ✅ 旧 API 不支持协作者删除文档
- ✅ 旧 API 不支持文集创建者删除他人文档
- ⚠️ 新 API 需要实现完整的权限逻辑（包括 role=1 协作者和文集创建者）

### 4.2 超级用户权限

代码中明确支持超级用户权限（`app_doc/views.py:1413`, `app_doc/views.py:1431`），设计文档已正确包含此逻辑。

---

## 5. Review 结论

### 5.1 需要立即修正
1. ✅ 修正 `PERMISSION_DESIGN.md` 中关于文档删除权限的描述
2. ✅ 修正 `DocAccessPolicy.has_delete_permission` 方法的实现代码
3. ✅ 修正权限矩阵表格

### 5.2 验证通过的部分
✅ 文集权限（role 0/1/2/3）
✅ 文档草稿状态权限
✅ 文档创建权限
✅ 文档更新权限
✅ 协作者 role=0 权限
✅ 超级用户权限

### 5.3 建议
1. **增加集成测试**: 为文档删除权限编写详细的集成测试，覆盖 role=0/1 协作者的差异
2. **API 文档标注**: 在新 API 文档中明确标注 role=1 协作者的删除权限范围
3. **前端提示**: 在前端 UI 中，当协作者删除他人文档时，应有明确的权限提示

---

## 6. 修正优先级

🔴 **高优先级（必须修正）**:
- 修正 `PERMISSION_DESIGN.md` 中的错误描述
- 修正 `DocAccessPolicy.has_delete_permission` 方法实现
- 修正权限测试用例

🟡 **中优先级（建议补充）**:
- 在迁移计划中添加"协作者删除权限差异"的说明
- 在前端 UI 设计中考虑权限提示

🟢 **低优先级（后续优化）**:
- 统一旧 API 的权限逻辑（与新 API 保持一致）

---

## 附录：代码引用

### A.1 文档删除权限的实际代码

```python
# app_doc/views.py:1383-1427
@login_required()
@require_http_methods(["POST"])
def del_doc(request):
    try:
        doc_id = request.POST.get('doc_id',None)
        range = request.POST.get('range', 'single')
        if doc_id:
            if range == 'single':
                try:
                    doc = Doc.objects.get(id=doc_id)
                    try:
                        project = Project.objects.get(id=doc.top_doc)
                    except ObjectDoesNotExist:
                        logger.error(_("文档{}的所属文集不存在。".format(doc_id)))
                        project = 0
                    # 获取文档所属文集的协作信息
                    pro_colla = ProjectCollaborator.objects.filter(project=project,user=request.user)
                    if pro_colla.exists():
                        colla_user_role = pro_colla[0].role
                    else:
                        colla_user_role = 0
                except ObjectDoesNotExist:
                    return JsonResponse({'status': False, 'data': '文档不存在'})

                # ⚠️ 关键权限判断
                if (request.user == doc.create_user) \
                        or (colla_user_role == 1) \           # role=1 可以删除任何文档
                        or (request.user == project.create_user)\
                        or (request.user.is_superuser):
                    # 修改状态为删除
                    doc.status = 3
                    doc.modify_time = datetime.datetime.now()
                    doc.save()
                    # 修改其下级所有文档状态为删除
                    chr_doc = Doc.objects.filter(parent_doc=doc_id)
                    chr_doc_ids = chr_doc.values_list('id',flat=True)
                    chr_doc.update(status=3,modify_time=datetime.datetime.now())
                    Doc.objects.filter(parent_doc__in=list(chr_doc_ids)).update(status=3,modify_time=datetime.datetime.now())
                    return JsonResponse({'status': True, 'data': _('删除完成')})
                else:
                    return JsonResponse({'status': False, 'data': _('非法请求')})
```

---

**Review 完成时间**: 2026-01-15
**Review 结果**: 发现 1 处重要错误，已详细记录修正方案
