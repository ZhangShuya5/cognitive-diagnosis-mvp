# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

认知诊断作业 — 基于 DINA 模型（Deterministic Inputs, Noisy "And" gate）的学生知识状态推断系统。采用 Superpowers 插件工作流规范，分阶段交付。

## 技术栈

- **后端**: Python 3.9+ / Flask 3.x + Flask-CORS（已锁定，不升级至 Flask 3.2 破坏性 API）
- **数据库**: SQLite（文件位于 `instance/cognitive_diag.db`）
- **计算**: NumPy + Pandas
- **前端**: 原生 HTML，CDN 引入 ECharts（禁止使用 React/Vue 等框架）

## 常用命令

```bash
# 激活虚拟环境（Windows Git Bash）
source venv/Scripts/activate

# 启动 Flask 开发服务器（debug 模式，端口 5000）
python app.py

# 初始化/重置数据库
python database.py

# 环境验证（检查所有依赖能否正常导入）
python init_data.py

# 安装依赖
pip install -r requirements.txt
```

## 架构设计

### 分层结构

```
app.py          → Flask 路由层（页面渲染 + API 端点）
database.py     → 数据持久层（SQLite 连接工厂 + 表结构初始化）
dina_model.py   → 领域算法层（DINA 模型核心：Q 矩阵、滑移/猜测参数、状态推断）
init_data.py    → 数据初始化层（环境验证 + 模拟作答数据生成）
```

### 关键设计决策

1. **数据库连接模式**: `database.py` 使用 `get_connection()` 工厂函数返回 `sqlite3.Row` 连接，各模块不应直接硬编码数据库路径，统一通过此入口获取。
2. **Flask 配置**: 数据库路径通过 `app.config["DATABASE"]` 注入，`database.py` 独立运行时走自身的路径推导逻辑，两者使用同一文件。
3. **CORS**: 已全局开启，前端通过 CDN ECharts 直接 fetch API 即可。

### Windows 编码注意事项

`init_data.py` 顶部有 GBK 终端 UTF-8 输出修复逻辑（`sys.stdout = io.TextIOWrapper(...)`）。新增 Python 文件若包含中文或特殊字符输出，需复制此处理，或全程使用 ASCII 标记符。

## Superpowers 工作流阶段

| 阶段 | 状态 | 说明 |
|---|---|---|
| **环境初始化** | ✅ 已完成 | 项目骨架、虚拟环境、依赖安装、环境验证通过 |
| **SDD 建模** | ✅ 已完成 | PRD、ER 图、API 契约、README 设计文档产出 |
| **TDD 算法实现** | ✅ 已完成 | DINA 核心逻辑 + 43 个测试用例全部通过 |
| **前端可视化** | ✅ 已完成 | ECharts 雷达图仪表盘 + LLM 建议接口 |
| 集成与交付 | ⏳ 待开始 | 联调、演示、提交 |

### 阶段切换协议

- 每个阶段的代码文件需在模块 docstring 中标注 `阶段：<阶段名称>`
- 阶段完成后必须输出：交付物清单、验证结果、下一阶段准入条件
- 切换到新阶段前，先更新 `CLAUDE.md` 的阶段状态表

## 文件约定

- 所有 Python 文件头使用中文 docstring，标注所属阶段
- SQLite 表名暂用 `_env_check` 占位，后续阶段会替换为正式表（`students`, `items`, `responses`, `q_matrix`）
- 前端 `index.html` 为骨架占位，SDD 阶段结束后逐步填充 ECharts 可视化
- `instance/` 目录已加入 `.gitkeep`，`.db` 文件不纳入版本控制
