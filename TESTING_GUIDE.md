# 密码系统重构测试指南

## 快速测试清单

### 测试 1: 验证导入和依赖
```bash
# 进入项目目录
cd d:\LibraryManger-main

# 检查 werkzeug 是否已安装
pip list | findstr werkzeug

# 应该显示类似:
# werkzeug                      2.x.x
```

如果未安装，执行：
```bash
pip install werkzeug
```

### 测试 2: 验证旧密码自动升级（最重要）

#### 场景：现有数据库中有 SHA-256 格式的旧密码

1. **备份原始数据库**
   ```bash
   copy library.db library.db.backup
   ```

2. **启动应用**
   ```bash
   python app_simple.py
   ```

3. **尝试用旧账户登录**
   - 打开浏览器: http://localhost:5000
   - 使用现有账户（如 admin/admin123）登录
   - 观察Flask控制台输出：
     ```
     已自动将用户 admin 的密码升级为新格式
     ```

4. **验证数据库中的密码格式已更新**
   ```bash
   # 使用 SQLite 客户端或以下命令
   sqlite3 library.db "SELECT username, password_hash FROM users WHERE username='admin' LIMIT 1;"
   
   # 应该显示以 pbkdf2:sha256: 开头的新格式哈希
   ```

### 测试 3: 测试新用户注册

1. **访问注册页面**
   - 打开: http://localhost:5000/register
   
2. **注册新用户**
   - 用户名: testuser
   - 密码: test123456
   - 确认密码: test123456
   - 点击"注册"

3. **验证密码格式**
   ```bash
   sqlite3 library.db "SELECT username, password_hash FROM users WHERE username='testuser';"
   
   # 应该看到 pbkdf2:sha256: 前缀
   ```

4. **用新注册用户登录**
   - 登出当前用户
   - 用 testuser/test123456 登录
   - 应该登录成功

### 测试 4: 测试新密码验证（不涉及升级）

1. **再次尝试登录 testuser**
   - 使用 testuser/test123456 登录
   - 不应该看到升级消息（因为已是新格式）
   - 应该直接登录成功

### 测试 5: 管理界面测试

#### 5.1 添加读者
1. 以 admin 身份登录
2. 访问: http://localhost:5000/readers/add
3. 填写表单：
   - 用户名: reader001
   - 密码: reader123
   - 其他信息任意
4. 提交并验证数据库中密码格式

```bash
sqlite3 library.db "SELECT username, password_hash FROM users WHERE username='reader001';"
# 应该是新格式 pbkdf2:sha256:...
```

#### 5.2 编辑读者密码
1. 访问: http://localhost:5000/readers
2. 找到某个读者，点击"编辑"
3. 修改密码字段为新密码
4. 提交
5. 验证新密码是否以新格式存储

### 测试 6: 批量脚本测试

```bash
# 确保数据库连接正常
python -c "from add_users import add_users; print('模块加载成功')"

# 运行批量添加（可选，非必需）
# python add_users.py
```

## 故障排除

### 问题 1: ImportError: cannot import name 'generate_password_hash'

**原因**: werkzeug 版本过旧

**解决**:
```bash
pip install --upgrade werkzeug
# 或指定版本
pip install werkzeug>=2.0
```

### 问题 2: 登录时报"用户名或密码错误"

**可能原因**:
1. 用户账户不存在
2. 账户被禁用 (is_active = 0)
3. 密码输入错误

**调试**:
```bash
sqlite3 library.db "SELECT id, username, is_active FROM users WHERE username='admin';"
# 检查用户是否存在且处于激活状态
```

### 问题 3: 应用启动失败，提示"NameError: name 'generate_password_hash' is not defined"

**原因**: 导入语句有误

**检查**: 
```bash
grep -n "from werkzeug.security import" app_simple.py
# 应该在第 12 行找到
```

### 问题 4: 密码升级失败

**症状**: 登录成功但没有看到升级消息

**检查**:
1. 确认 app_simple.py 中 login 函数中有升级逻辑
2. 查看数据库中该用户的原始密码格式是否确实是旧格式

```bash
sqlite3 library.db "SELECT password_hash FROM users WHERE username='<你的用户名>';"
```

## 数据对比测试

### 创建对照组

使用旧的 SHA-256 密码手动插入数据库进行测试：

```bash
sqlite3 library.db << EOF
-- 插入一条旧格式密码的测试用户
-- password = 'legacy123'
-- SHA-256 hash = 94a2cea55d1ee2d8c47f6c5f1c9bfbe6c3f5d5a86aff3ca12020c923adc6c92
INSERT OR REPLACE INTO users (username, email, password_hash, is_admin, is_active)
VALUES ('legacy_user', 'legacy@test.com', '94a2cea55d1ee2d8c47f6c5f1c9bfbe6c3f5d5a86aff3ca12020c923adc6c92', 0, 1);
EOF
```

然后用 legacy_user/legacy123 登录，应该看到升级消息。

## 性能测试

关键时间点记录：

| 操作 | 预期时间 | 说明 |
|------|--------|------|
| 旧密码验证+升级 | < 100ms | 第一次登录某个旧密码账户 |
| 新密码验证 | < 50ms | 新注册或已升级账户登录 |
| 密码哈希生成 | < 150ms | 注册或管理员添加用户时 |

如果明显超过预期，可能是应用负载过高。

## 安全性验证

### 1. 验证盐值随机性

新生成的密码哈希应该都不同，即使密码相同：

```bash
sqlite3 library.db << EOF
-- 创建两个相同密码的用户
INSERT OR REPLACE INTO users (username, email, password_hash, is_active)
VALUES ('test_salt_1', 'test1@test.com', (SELECT password_hash FROM users LIMIT 1), 1),
       ('test_salt_2', 'test2@test.com', (SELECT password_hash FROM users LIMIT 1), 1);

-- 查看它们的密码哈希
SELECT username, substr(password_hash, 1, 30) as hash_prefix FROM users WHERE username LIKE 'test_salt_%';
EOF
```

每个用户的盐值都应该不同（即使密码相同）。

### 2. 验证 PBKDF2 迭代次数

通过解析哈希字符串验证迭代次数：

```python
# 在 Python 交互式环境中
from werkzeug.security import generate_password_hash
hash_result = generate_password_hash('test')
print(hash_result)
# 应该看到类似：pbkdf2:sha256:260000$...
# 其中 260000 是迭代次数
```

## 完整测试报告模板

使用此模板记录您的测试结果：

```markdown
## 测试报告 - 密码系统重构

**测试日期**: ____

### 环境信息
- Python 版本: ____
- Flask 版本: ____
- werkzeug 版本: ____
- 数据库: ____

### 测试结果

- [ ] 旧密码登录与升级: ____
- [ ] 新用户注册: ____
- [ ] 新密码登录: ____
- [ ] 添加读者: ____
- [ ] 编辑读者: ____
- [ ] 数据库格式检验: ____

### 性能测试
- 旧密码登录耗时: ____ms
- 新密码登录耗时: ____ms

### 问题记录
...

### 最终状态: ✅ 通过 / ❌ 失败
```

---

**建议**: 在生产环境部署前，至少执行 测试 1-5 以确保系统正常运作。
