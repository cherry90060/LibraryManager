# 生产环境部署指南

## 部署前检查清单

### 1. 环境准备

- [ ] 备份生产数据库 `library.db`
  ```bash
  # Windows
  copy library.db library.db.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')
  
  # Linux/Mac
  cp library.db library.db.backup.$(date +%Y%m%d_%H%M%S)
  ```

- [ ] 备份现有 app_simple.py 和 add_users.py
  ```bash
  copy app_simple.py app_simple.py.backup
  copy add_users.py add_users.py.backup
  ```

- [ ] 检查 Python 环境
  ```bash
  python --version    # 确保 Python 3.6+
  pip --version       # 检查 pip 状态
  ```

### 2. 依赖安装

```bash
# 更新或安装 werkzeug
pip install --upgrade werkzeug

# 验证安装版本（应为 2.0+）
pip show werkzeug | grep Version
```

### 3. 代码部署

```bash
# 方案 A: 如果使用 Git
git pull origin main              # 拉取最新代码
git log --oneline -5              # 确认更新内容

# 方案 B: 手动复制（本次重构已完成）
# 直接使用已修改的文件覆盖旧文件
```

### 4. 部署验证

#### 4.1 语法检查
```bash
# Python 语法检查（不执行代码）
python -m py_compile app_simple.py
python -m py_compile add_users.py

# 如果无输出且无错误，则语法正确
```

#### 4.2 模块导入验证
```bash
# 尝试导入主模块（测试依赖是否齐全）
python -c "from app_simple import app; print('模块导入成功')"

# 预期输出: 模块导入成功
```

#### 4.3 密码函数验证
```bash
python << 'EOF'
from werkzeug.security import generate_password_hash, check_password_hash

# 测试密码生成
test_hash = generate_password_hash('test123', method='pbkdf2:sha256', salt_length=16)
print(f"生成的哈希: {test_hash[:50]}...")

# 测试密码验证
is_valid = check_password_hash(test_hash, 'test123')
print(f"密码验证: {'通过' if is_valid else '失败'}")

# 验证格式
if test_hash.startswith('pbkdf2:sha256:'):
    print("✓ 密码格式正确")
else:
    print("✗ 密码格式错误")
EOF
```

---

## 分阶段部署策略

### 方案 A: 一次性部署（推荐用于停机维护）

**适用于**: 可以接受短时间停机的系统

**步骤**:
1. 停止应用服务
2. 备份数据库
3. 部署新代码
4. 重启应用
5. 验证功能

**停机时间**: 5-10 分钟

```bash
# 停止应用（根据启动方式选择）
# 如果使用 Flask 开发服务器
Ctrl+C

# 如果使用 Gunicorn/uWSGI
sudo systemctl stop your_app_service

# 如果使用 Windows 服务
net stop your_app_service

# 等待验证后直接启动
python app_simple.py
```

### 方案 B: 灰度部署（推荐用于生产环境）

**适用于**: 需要持续服务的系统

**步骤**:

1. **准备金丝雀环境**
   - 启动第二个应用实例（不同端口，如 5001）
   - 部署新代码到这个实例

   ```bash
   # 金丝雀实例启动
   export FLASK_ENV=production
   export FLASK_PORT=5001
   python app_simple.py
   ```

2. **路由少量流量到金丝雀**
   - 配置负载均衡器将 5% 流量发送到新实例
   - 监控错误率和性能指标

3. **验证金丝雀实例**
   - 测试旧密码用户登录和升级
   - 测试新用户注册
   - 检查数据库更新

4. **逐步增加流量**
   ```
   时间  | 流量百分比 | 状态检查
   ------|---------|-------
   0h    | 5%      | 错误率监控
   1h    | 10%     | 性能监控
   2h    | 25%     | 用户反馈收集
   4h    | 50%     | 负载测试
   8h    | 100%    | 移除旧实例
   ```

5. **旧版本回滚（如需要）**
   - 保持旧实例运行 24 小时
   - 如发现问题，立即切回旧版本
   - 反向代理重新路由所有流量

### 方案 C: 蓝绿部署

**适用于**: 需要零停机时间的关键系统

**步骤**:

1. **启用蓝绿两套环境**
   ```
   蓝环境 (现有): app1, app2, app3 → 数据库 db1
   绿环境 (新的): app4, app5, app6 → 数据库 db1 (共享)
   ```

2. **部署新代码到绿环境**
   ```bash
   # 在绿环境实例启动新代码
   python app_simple.py  # 部署到 app4, app5, app6
   ```

3. **全量测试绿环境**
   ```bash
   # 运行完整测试套件
   pytest tests/
   
   # 手动测试关键路径
   # - 旧用户登录与升级
   # - 新用户注册
   # - 管理界面添加/编辑用户
   ```

4. **切换流量到绿环境**
   ```
   时刻 0: 蓝=100%, 绿=0%
   时刻 1: 蓝=90%, 绿=10% (启动切换)
   时刻 2: 蓝=50%, 绿=50% (持观察)
   时刻 3: 蓝=10%, 绿=90%
   时刻 5: 蓝=0%, 绿=100% (完全切换)
   ```

5. **保持蓝环境待命 24 小时**
   - 监控绿环境
   - 如发现严重问题，迅速切回蓝环境

---

## 实时监控和告警

### 关键指标

在部署后的 24 小时内监控以下指标：

```python
# 监控脚本示例
import time
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

metrics = {
    'login_attempts': 0,
    'login_success': 0,
    'login_failures': 0,
    'password_upgrades': 0,
    'errors': [],
    'avg_response_time': 0
}

# 在 login 函数中记录
if is_password_valid:
    metrics['login_success'] += 1
    if needs_upgrade:
        metrics['password_upgrades'] += 1
else:
    metrics['login_failures'] += 1

# 定期输出指标
def log_metrics():
    success_rate = metrics['login_success'] / max(metrics['login_attempts'], 1) * 100
    print(f"登录成功率: {success_rate:.2f}%")
    print(f"密码升级数: {metrics['password_upgrades']}")
    print(f"错误数: {len(metrics['errors'])}")
```

### 告警规则

| 指标 | 正常范围 | 告警阈值 | 处理方式 |
|------|--------|---------|---------|
| 登录失败率 | < 5% | > 10% | 检查应用日志 |
| 响应时间 | 50-100ms | > 500ms | 检查数据库负载 |
| 错误率 | < 0.1% | > 0.5% | 回滚版本 |
| CPU 使用率 | < 30% | > 70% | 扩容或优化 |

---

## 故障恢复步骤

### 如果部署后出现问题

#### 快速恢复（回滚）

```bash
# 1. 停止应用
# (根据启动方式)

# 2. 恢复备份代码
copy app_simple.py.backup app_simple.py
copy add_users.py.backup add_users.py

# 3. 恢复备份数据库（如数据被破坏）
copy library.db.backup library.db

# 4. 重启应用
python app_simple.py
```

#### 常见问题和解决方案

**问题**: 登录全部失败

**原因**: werkzeug 未安装或版本不兼容

**解决**:
```bash
pip uninstall werkzeug -y
pip install werkzeug==2.3.0
# 重启应用
```

**问题**: 某些用户无法登录（新注册的用户）

**原因**: 密码哈希生成失败

**检查**:
```python
import sqlite3
conn = sqlite3.connect('library.db')
cursor = conn.cursor()
cursor.execute("SELECT username, password_hash FROM users WHERE username = ?", ('problem_user',))
result = cursor.fetchone()
print(f"存储的哈希: {result[1][:50]}")
```

**问题**: 升级过程中数据库被锁定

**原因**: 并发更新冲突

**预防**: 确保应用单例运行，或添加数据库锁机制:

```python
# 在 login 函数中添加锁
import threading
db_lock = threading.RLock()

with db_lock:
    if needs_upgrade:
        db.execute('UPDATE users SET password_hash = ? WHERE id = ?',
                  (new_hash, user['id']))
        db.commit()
```

---

## 部署完成检查

部署成功后验证清单：

### 第 1 小时（紧急检查）
- [ ] 应用正常启动
- [ ] 数据库连接正常
- [ ] 主页可以访问
- [ ] 登录功能可用
- [ ] 错误日志中无异常

### 第 4 小时（功能检查）
- [ ] 旧用户（SHA-256）可以登录
- [ ] 新用户（PBKDF2）可以登录
- [ ] 密码升级生效（检查日志）
- [ ] 新用户注册功能正常
- [ ] 管理员可以添加/编辑用户

### 第 24 小时（稳定性检查）
- [ ] 无异常登录错误
- [ ] 无数据丢失
- [ ] 数据库备份已清理旧版本
- [ ] 性能指标正常
- [ ] 可以安全移除旧备份

### 1 周后（长期检查）
- [ ] 所有旧密码用户已升级
- [ ] 新注册用户密码格式正确
- [ ] 系统运行稳定

---

## 性能基准线

部署前后进行性能测试：

```python
# 性能测试脚本
import time
import statistics
from werkzeug.security import generate_password_hash, check_password_hash

# 生成密码（存储阶段）
times_generate = []
for _ in range(100):
    start = time.time()
    generate_password_hash('test123', method='pbkdf2:sha256', salt_length=16)
    times_generate.append(time.time() - start)

print(f"生成密码平均耗时: {statistics.mean(times_generate)*1000:.2f}ms")

# 验证密码（登录阶段）
test_hash = generate_password_hash('test123', method='pbkdf2:sha256', salt_length=16)
times_verify = []
for _ in range(100):
    start = time.time()
    check_password_hash(test_hash, 'test123')
    times_verify.append(time.time() - start)

print(f"验证密码平均耗时: {statistics.mean(times_verify)*1000:.2f}ms")
```

**预期结果**:
- 生成密码: 100-150 ms
- 验证密码: 50-100 ms

---

## 记录部署信息

创建部署日志记录：

```markdown
# 部署日志 - 2026-03-05

## 部署信息
- 版本: passwordsecurity-v1.0
- 部署者: [您的名字]
- 部署时间: 2026-03-05 14:30
- 部署方式: [一次性/灰度/蓝绿]

## 前置检查
- [x] 数据库备份完成
- [x] 代码备份完成
- [x] 依赖检查通过
- [x] 语法验证通过

## 部署过程
- 时间 14:30: 停止应用
- 时间 14:31: 部署代码
- 时间 14:32: 启动应用
- 时间 14:33: 基础功能验证通过

## 部署结果
- 预期用户: 125 个
- 已升级用户: 0 个（首次部署）
- 错误数: 0
- 平均响应时间: 65ms

## 监控持续到
- 2026-03-06 14:30

## 回滚计划
- 回滚方式: 恢复 backup 文件
- 预计时间: < 5 分钟
- 责任人: [您的名字]
```

---

## 最终提示

1. **始终备份** - 部署前后都要备份
2. **逐步验证** - 不要跳过任何验证步骤
3. **监控告警** - 设置实时告警，24 小时监控
4. **文档齐全** - 记录所有部署信息便于追查
5. **团队沟通** - 通知所有相关人员部署时间
6. **预留回滚** - 始终准备回滚方案

---

**安全部署，平稳过渡！** 🚀
