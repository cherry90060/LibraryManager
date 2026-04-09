# 代码修改速查表

## 关键代码变更对比

### 1. 导入语句

```python
# ❌ 旧代码
import hashlib

# ✅ 新代码
import hashlib  # 仅用于兼容旧密码
from werkzeug.security import generate_password_hash, check_password_hash
```

---

### 2. 密码匹配验证 (login)

```python
# ❌ 旧代码 - 直接比对两个 SHA-256 哈希
if user and user['password_hash'] == hash_password(password):
    # 登录逻辑
    pass

# ✅ 新代码 - 自动检测格式并升级
if user:
    stored_hash = user['password_hash']
    is_password_valid = False
    needs_upgrade = False
    
    if stored_hash.startswith('pbkdf2:sha256:'):
        # 新格式 - 直接验证
        is_password_valid = check_password_hash(stored_hash, password)
    else:
        # 旧格式 - 兼容验证并升级
        is_password_valid = _verify_legacy_password(stored_hash, password)
        if is_password_valid:
            needs_upgrade = True
    
    if is_password_valid:
        if needs_upgrade:
            # 自动升级密码格式
            new_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
            db.execute('UPDATE users SET password_hash = ? WHERE id = ?', 
                      (new_hash, user['id']))
            db.commit()
        
        # 登录逻辑
        pass
```

---

### 3. 密码生成 (register / add_reader / edit_reader)

```python
# ❌ 旧代码
password_hash = hash_password(password)

# ✅ 新代码
password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
```

或者使用封装好的 hash_password 函数：

```python
# ✅ 也可以这样（调用新的 hash_password）
password_hash = hash_password(password)
# hash_password 函数内部使用 generate_password_hash
```

---

### 4. hash_password 函数

```python
# ❌ 旧代码
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ✅ 新代码
def hash_password(password):
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
```

---

### 5. 新增辅助函数

```python
# ✅ 新代码（用于向后兼容）
def _verify_legacy_password(stored_hash, password):
    """验证旧格式密码（SHA-256）"""
    return stored_hash == hashlib.sha256(password.encode()).hexdigest()
```

---

## 影响的主要函数/路由

| 组件 | 旧实现 | 新实现 | 改动重点 |
|------|-------|--------|--------|
| `hash_password()` | SHA-256 无盐 | PBKDF2+SHA256 有盐 | 完全重写 |
| `/register` | `hash_password()` | `generate_password_hash()` | 直接调用 |
| `/login` | 直接比对 → `check_password_hash()` | 自动升级机制 | **核心改动** |
| `/readers/add` | `hash_password()` | `generate_password_hash()` | 直接调用 |
| `/readers/edit` | `hash_password()` | `generate_password_hash()` | 直接调用 |
| `init_db()` | 管理员密码用 SHA-256 | 用 `generate_password_hash()` | 一行改动 |
| `add_users.py` | `hash_password()` | `generate_password_hash()` | 移除旧函数 |

---

## 密码格式速查

```python
# SHA-256 格式（旧）
# 特征：64 个十六进制字符，无特殊前缀
old_hash = "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92"

# PBKDF2+SHA256 格式（新）
# 特征：以 pbkdf2:sha256: 开头，包含盐值和迭代次数
new_hash = "pbkdf2:sha256:260000$DxHNTjYtS4L6qJ9k$c5e3f7d8a9b1c2d3e4f5g6h7i8j9k0l1m2n3o4p5q6r7s8t9"

# Python 中的检测方式
if password_hash.startswith('pbkdf2:sha256:'):
    # 新格式
    from werkzeug.security import check_password_hash
    is_valid = check_password_hash(password_hash, user_input)
else:
    # 旧格式
    import hashlib
    is_valid = password_hash == hashlib.sha256(user_input.encode()).hexdigest()
```

---

## 常见操作速查

### 查看用户密码格式

```sql
-- SQLite 查询
SELECT 
    username,
    CASE 
        WHEN password_hash LIKE 'pbkdf2:sha256:%' THEN '新格式'
        ELSE '旧格式'
    END as 密码格式,
    substr(password_hash, 1, 30) as 哈希前缀
FROM users;
```

### 统计已升级用户

```sql
-- 统计新旧格式用户数
SELECT 
    '新格式' as 格式, COUNT(*) as 用户数
FROM users 
WHERE password_hash LIKE 'pbkdf2:sha256:%'
UNION ALL
SELECT 
    '旧格式' as 格式, COUNT(*) as 用户数
FROM users 
WHERE password_hash NOT LIKE 'pbkdf2:sha256:%';
```

### 手动升级单个用户密码

```python
from werkzeug.security import generate_password_hash
import sqlite3

conn = sqlite3.connect('library.db')
cursor = conn.cursor()

username = 'admin'
new_password = 'admin123'
new_hash = generate_password_hash(new_password, method='pbkdf2:sha256', salt_length=16)

cursor.execute('UPDATE users SET password_hash = ? WHERE username = ?', 
               (new_hash, username))
conn.commit()
print(f"已手动升级用户 {username} 的密码")
```

---

## 关键实现细节

### 自动升级的工作流程

```
用户输入密码
    ↓
查询数据库获取 password_hash
    ↓
检测 password_hash 格式
    ├─ 包含 'pbkdf2:sha256:' → 使用 check_password_hash()
    └─ 否则 → 使用 _verify_legacy_password() (SHA-256)
    ↓
如果验证成功
    ├─ 如果是旧格式 → 生成新格式哈希 → 更新数据库
    └─ 如果是新格式 → 直接跳过升级
    ↓
返回登录结果
```

### 性能考量

- **新密码验证**: ~40-60ms (PBKDF2 计算)
- **旧密码验证**: ~5-10ms (SHA-256 计算) + ~50ms (生成新哈希)
= **总计**: ~55-60ms (首次登录旧密码用户，包括升级)

---

## 错误处理

### 常见异常

```python
# ImportError
try:
    from werkzeug.security import generate_password_hash
except ImportError:
    print("Error: werkzeug not installed. Run: pip install werkzeug")

# 密码验证失败
if not is_password_valid:
    flash('用户名或密码错误', 'danger')
    # 不要泄露是用户不存在还是密码错误
    # （安全最佳实践）
```

---

## 回滚清单（如需要）

如果需要回滚到旧系统（**强烈不建议**）：

1. [ ] 停止应用服务
2. [ ] 恢复 `app_simple.py` 到旧版本
3. [ ] 恢复 `add_users.py` 到旧版本
4. [ ] 移除 `from werkzeug.security import ...` 导入
5. [ ] 恢复 `import hashlib` 为唯一的导入
6. [ ] 删除 `_verify_legacy_password()` 函数
7. [ ] 将 `hash_password()` 改回 SHA-256 实现
8. [ ] 恢复所有路由中的密码处理逻辑
9. [ ] 重启应用

**后果**: 已升级为新格式的密码将无法验证，这些用户需要密码重置。

---

## 最后检查清单

部署前确保：

- [ ] 已安装 werkzeug >= 2.0
- [ ] `app_simple.py` 包含 werkzeug 导入
- [ ] `add_users.py` 包含 werkzeug 导入  
- [ ] `hash_password()` 函数使用 `generate_password_hash()`
- [ ] `_verify_legacy_password()` 函数存在
- [ ] `/login` 路由包含自动升级逻辑
- [ ] 所有密码生成都使用新方式
- [ ] 数据库备份已完成
- [ ] 测试环境验证通过

---

**修改摘要**: 9 个文件/函数，共 15+ 处代码改动，完整的向后兼容性和自动升级机制。
