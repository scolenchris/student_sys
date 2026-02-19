# AGENTS.md

本文件用于指导 AI 代理在本仓库中进行稳定、可回溯的改动。默认语言为中文。

## 1. 项目概览
- 项目类型：Flask + Vue3 + Element Plus 的学生成绩管理系统（前后端同仓）。
- 后端目录：`app/`（蓝图在 `app/routes/`，模型在 `app/models.py`）。
- 前端目录：`src/`（页面在 `src/views/`，接口封装在 `src/api/`，路由在 `src/router/index.js`）。
- 启动入口：`run.py`。

## 2. 运行方式
- 一体化运行（优先）：`python run.py`
  - 启动 Waitress，端口 `5173`。
  - 自动执行 `db.create_all()`。
  - 自动确保默认管理员存在（账号 `adminwds`）。
- 前端开发模式：`npm run dev`
  - Vite 端口 `5173`，`/api` 代理到 `http://127.0.0.1:5000`。
  - 此模式下需另启后端（例如 `flask --app app:create_app run --port 5000`）。

## 3. 技术与依赖
- Python 侧核心依赖：`flask`、`flask_sqlalchemy`、`flask_cors`、`waitress`、`pandas`、`openpyxl`、`docxtpl`。
- 前端核心依赖：`vue@3`、`vue-router`、`pinia`、`element-plus`、`axios`、`vite`。

## 4. 数据与配置
- 数据库：SQLite，默认文件 `school.db`（见 `config.py`）。
- 不要提交/覆盖本地数据库文件：`*.db`。
- 现有项目未接入 Alembic 迁移；变更模型时必须考虑 `db.create_all()` 的兼容性，避免直接破坏线上已有字段。

## 5. 后端改动规范
- 新接口统一放入对应蓝图：
  - 认证：`app/routes/auth.py`
  - 管理员：`app/routes/admin.py`
  - 教师：`app/routes/teacher.py`
- 返回风格保持一致：成功/失败信息优先使用 `{"msg": "..."}`。
- 涉及批量导入、回退、批处理写入时：
  - 先校验，再写库；
  - 出错必须 `rollback`；
  - 避免部分成功导致脏数据。
- 与“学年 academic_year / 入学届 entry_year / 班级快照 class_id_snapshot”相关逻辑属于核心业务约束，改动前先通读相关查询链路。

## 6. 前端改动规范
- 所有后端请求先在 `src/api/*.js` 封装，再在页面调用，不在 Vue 页面里直接拼 `axios` 请求。
- 路由权限遵循 `src/router/index.js` 的 `meta.requiresAuth` 与 `meta.role` 机制。
- 用户可见文案与后端消息以中文为主，保持现有产品语气一致。

## 7. 代码风格
- 保持现有风格：Python 以函数式路由为主，Vue 使用组合式语法与现有结构。
- 不做无关大重构，优先最小改动闭环。
- 不随意重命名数据库字段、接口路径、前端参数名；若必须修改，需同步前后端。

## 8. 提交前最小自检
- 后端语法检查：`python -m py_compile run.py app\\__init__.py app\\models.py app\\routes\\auth.py app\\routes\\teacher.py app\\routes\\admin.py`
- 前端构建检查：`npm run build`
- 若改动了导入/成绩/回退相关逻辑，至少做一次手工冒烟：
  - 登录；
  - 查询目标页面；
  - 提交一次最小样本数据；
  - 验证返回消息与页面展示一致。

## 9. 高风险区域（改动需谨慎）
- `app/routes/admin.py`：文件体量大、流程耦合高（导入、统计、回退均在此）。
- `app/models.py`：模型字段会直接影响导入、统计、成绩录入和历史数据。
- `run.py`：包含初始化逻辑与默认管理员创建逻辑，改动需防止冷启动失败。
