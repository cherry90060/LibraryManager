# LibraryManager - 智慧图书馆管理系统

<div align="center">

![LibraryManager Logo](https://img.shields.io/badge/LibraryManager-v1.0.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.13+-green.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-yellow.svg)
![License](https://img.shields.io/badge/License-MIT-red.svg)
![Responsive](https://img.shields.io/badge/Responsive-Yes-success.svg)

一个现代化、智能的图书馆管理系统，提供完整的图书管理、借阅服务和智能推荐功能。

</div>

---

## 📋 项目简介

**LibraryManager** 是一个基于 Python Flask 开发的现代化图书馆管理系统，旨在为图书馆工作人员和读者提供高效、便捷的图书管理解决方案。系统采用响应式设计，完美适配各种设备，为用户提供一致的优质体验。

### 🎯 设计理念
- **简洁易用** - 直观友好的用户界面，降低使用门槛
- **功能完整** - 覆盖图书管理全流程，满足各类需求
- **轻量部署** - 零配置，开箱即用，无需复杂依赖
- **智能集成** - 自动获取图书封面，AI推荐与书籍解读功能
- **安全可靠** - 密码加密存储，权限控制严格

### 📌 适用场景
- **学校图书馆** - 管理校园图书资源
- **公共图书馆** - 服务社区读者
- **企业图书馆** - 管理内部资料
- **个人藏书** - 整理个人图书收藏

---

## ✨ 已实现功能

### 👥 用户管理模块
- ✅ 用户注册与登录
- ✅ 角色权限管理（普通用户/管理员）
- ✅ 用户信息维护
- ✅ 密码安全加密存储（SHA256）
- ✅ 用户状态管理（启用/禁用）
- ✅ 读者信息管理

### 📚 图书管理模块
- ✅ 图书信息录入与编辑
- ✅ 图书分类管理
- ✅ 图书搜索与筛选
- ✅ 图书状态跟踪
- ✅ 批量导入功能
- ✅ 自动获取图书封面（Google Books API、Open Library API）
- ✅ 图书库存管理
- ✅ 图书封面本地缓存

### 📖 借阅管理模块
- ✅ 在线借书申请
- ✅ 借阅请求审批流程
- ✅ 借阅记录管理
- ✅ 归还处理
- ✅ 逾期提醒与罚款计算
- ✅ 借阅历史查询
- ✅ 取货码系统（凭码取书）
- ✅ 取货确认功能
- ✅ 未取货自动取消
- ✅ 用户自主撤销借阅请求

### 🤖 AI智能模块
- ✅ AI图书推荐（基于用户需求智能推荐）
- ✅ 书籍内容解读（上传书籍文件进行AI分析）
- ✅ AI API配置管理
- ✅ 支持多种AI服务提供商

### 📊 数据统计模块
- ✅ 借阅数据统计
- ✅ 图书分类占比分析
- ✅ 月度借阅量趋势
- ✅ 读者类型分布
- ✅ 数据可视化展示

### 📱 公告管理模块
- ✅ 公告发布与管理
- ✅ 公告模板管理
- ✅ 公告推送记录
- ✅ 公告详情查询

### 🔧 系统管理模块
- ✅ 系统设置管理
- ✅ 用户权限控制
- ✅ 请求限流保护
- ✅ 缓存管理
- ✅ 数据库管理

### 🎨 界面特色
- ✅ 现代化响应式设计
- ✅ Bootstrap 5 框架
- ✅ 移动端友好界面
- ✅ 直观的操作流程
- ✅ 美观的视觉设计
- ✅ 美化的弹窗交互（Bootstrap模态框）

---

## 🛠️ 技术栈

### 后端技术
| 技术 | 说明 |
|------|------|
| **Python 3.13+** | 现代化编程语言 |
| **Flask** | 轻量级Web框架 |
| **SQLite3** | 嵌入式数据库，无需额外配置 |
| **hashlib** | 安全密码哈希（SHA256） |
| **datetime** | 日期时间处理 |
| **requests** | HTTP请求处理 |
| **urllib3** | 重试机制支持 |

### 前端技术
| 技术 | 说明 |
|------|------|
| **HTML5** | 现代网页标准 |
| **Bootstrap 5** | 响应式UI框架 |
| **JavaScript (ES6+)** | 交互功能 |
| **CSS3** | 样式设计 |
| **Bootstrap Icons** | 图标库 |

### 第三方API
| API | 用途 |
|-----|------|
| **Google Books API** | 获取图书信息和封面 |
| **Open Library API** | 获取图书信息和封面 |
| **AI API** | 智能图书推荐与书籍解读 |

### 技术特点
- **零依赖设计** - 最小化外部依赖，提高稳定性
- **SQLite集成** - 嵌入式数据库，无需额外配置
- **响应式布局** - 完美适配桌面端和移动端
- **安全认证** - 多层安全防护措施
- **缓存系统** - 提升性能，减少API调用
- **限流保护** - 防止恶意请求，保障系统稳定
- **重试机制** - 网络请求自动重试，提高可靠性

---

## � 快速开始

### 环境要求
- **Python 3.13+** - 现代化编程语言
- **现代浏览器** - Chrome、Firefox、Safari、Edge

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/yourusername/LibraryManager.git
cd LibraryManager
```

2. **安装依赖**
```bash
pip install flask requests
```

3. **启动应用**
```bash
python app_simple.py
```

4. **访问系统**
打开浏览器访问：http://127.0.0.1:5000

### 默认账户

| 用户类型 | 用户名 | 密码 | 权限 |
|---------|--------|------|------|
| 管理员 | admin | admin123 | 完整系统权限 |

---

## � 项目结构

```
LibraryManager/
├── 📄 app_simple.py              # 主应用程序
├── 📄 library.db                 # SQLite数据库文件
├── 📁 static/                    # 静态资源目录
│   ├── 📁 book_covers/            # 图书封面存储
│   ├── 📁 css/                    # CSS样式文件
│   │   └── 📄 announcement.css    # 公告相关样式
│   └── 📁 js/                     # JavaScript文件
│       └── 📄 main_simple.js      # 前端脚本
├── 📁 templates/                 # 模板文件目录
│   ├── 📄 base_simple.html       # 基础模板
│   ├── 📄 index_simple.html      # 首页模板
│   ├── 📄 login_simple.html      # 登录页面
│   ├── 📄 register_simple.html   # 注册页面
│   ├── 📄 books_simple.html      # 图书列表
│   ├── 📄 book_detail_simple.html # 图书详情
│   ├── 📄 my_loans_simple.html   # 我的借阅
│   ├── 📄 admin_simple.html      # 管理面板
│   ├── 📄 book_management_simple.html # 图书管理
│   ├── 📄 loan_management_simple.html # 借阅管理
│   ├── 📄 readers_simple.html    # 读者管理
│   ├── 📄 add_reader_simple.html # 添加读者
│   ├── 📄 edit_reader_simple.html # 编辑读者
│   ├── 📄 announcement_management_simple.html # 公告管理
│   ├── 📄 ai_api_config.html     # AI API配置
│   ├── 📄 ai_recommendation.html # AI推荐
│   └── 📄 dashboard.html         # 仪表盘
└── 📄 README.md                  # 项目说明文档
```

---

## 📊 数据库结构

### 用户表 (`users`)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 用户ID (主键) |
| username | TEXT | 用户名 |
| email | TEXT | 邮箱 |
| password_hash | TEXT | 密码哈希 |
| is_admin | INTEGER | 是否管理员 |
| is_active | INTEGER | 是否激活 |
| created_at | TIMESTAMP | 创建时间 |

### 图书表 (`books`)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 图书ID (主键) |
| isbn | TEXT | ISBN |
| title | TEXT | 书名 |
| author | TEXT | 作者 |
| category | TEXT | 分类 |
| description | TEXT | 描述 |
| total_copies | INTEGER | 总册数 |
| available_copies | INTEGER | 可用册数 |
| publisher | TEXT | 出版社 |
| publish_date | TEXT | 出版日期 |
| status | TEXT | 状态 |
| cover_image | TEXT | 封面图片 |
| created_at | TIMESTAMP | 创建时间 |

### 借阅表 (`loans`)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 借阅ID (主键) |
| user_id | INTEGER | 用户ID (外键) |
| book_id | INTEGER | 图书ID (外键) |
| loan_date | TIMESTAMP | 借阅日期 |
| due_date | TIMESTAMP | 应还日期 |
| return_date | TIMESTAMP | 归还日期 |
| is_returned | INTEGER | 是否已归还 |
| fine_amount | REAL | 罚款金额 |
| pickup_code | TEXT | 取货码 |
| pickup_confirmed | INTEGER | 是否已取货 |

### 借阅请求表 (`loan_requests`)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 请求ID (主键) |
| user_id | INTEGER | 用户ID (外键) |
| book_id | INTEGER | 图书ID (外键) |
| request_date | TIMESTAMP | 请求日期 |
| status | TEXT | 状态 |
| admin_id | INTEGER | 审批管理员ID |
| approval_date | TIMESTAMP | 审批日期 |
| rejection_reason | TEXT | 拒绝原因 |
| pickup_code | TEXT | 取货码 |
| pickup_confirmed | INTEGER | 是否已取货 |

### AI API配置表 (`ai_api_config`)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 配置ID (主键) |
| provider_name | TEXT | 服务提供商名称 |
| api_endpoint | TEXT | API端点 |
| api_key | TEXT | API密钥 |
| is_active | INTEGER | 是否激活 |
| created_at | TIMESTAMP | 创建时间 |

### 图书封面缓存表 (`book_cover_cache`)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 缓存ID (主键) |
| book_name | TEXT | 书名 |
| cover_url | TEXT | 封面URL |
| cover_local_path | TEXT | 本地存储路径 |
| book_info | TEXT | 图书信息 |
| created_at | TIMESTAMP | 创建时间 |
| expire_at | TIMESTAMP | 过期时间 |

---

## 🔧 核心功能说明

### 1. 用户认证系统
- 使用SHA256进行密码哈希存储
- 基于会话的用户认证
- 角色权限控制（普通用户/管理员）

### 2. 借阅流程
1. 用户提交借阅申请
2. 管理员审批借阅请求
3. 系统生成取货码
4. 用户凭取货码取书
5. 管理员确认取货
6. 创建借阅记录

### 3. 取货码系统
- 6位字母数字组合
- 当天有效
- 未取货自动取消

### 4. AI智能功能
- **图书推荐**：根据用户需求智能推荐图书
- **书籍解读**：上传书籍文件，AI分析内容并生成解读报告

### 5. 图书封面自动获取
- 从Google Books API获取
- 从Open Library API获取
- 本地缓存机制

---

## 🎯 功能演示

### 用户端功能
1. **注册登录** - 安全的用户认证
2. **浏览图书** - 分类搜索图书信息
3. **借阅申请** - 在线借书申请流程
4. **个人中心** - 查看借阅历史和状态
5. **撤销请求** - 管理待审批的借阅请求
6. **AI推荐** - 获取智能图书推荐
7. **书籍解读** - 上传书籍获取AI解读

### 管理员功能
1. **图书管理** - 添加、编辑、删除图书
2. **用户管理** - 用户权限和账户管理
3. **借阅处理** - 审核借阅申请，确认取货
4. **数据统计** - 借阅报表和分析
5. **公告管理** - 公告发布与管理
6. **AI配置** - 管理AI API配置

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

---

## 🙏 致谢

- 感谢 **Flask** 社区提供的优秀框架
- 感谢 **Bootstrap** 团队的美观UI组件
- 感谢 **Python** 社区的强大生态系统
- 感谢 **Google Books API**、**Open Library API** 提供的图书信息

---

<div align="center">

### ⭐ 如果这个项目对您有帮助，请给我们一个 Star！

Made with ❤️ by LibraryManager Team

</div>
