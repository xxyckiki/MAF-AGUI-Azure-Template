# 项目待办事项清单

## 🔥 高优先级（生产必备）

### ⬜ 1. 添加 OpenTelemetry 监控
**预计时间：30 分钟**

**目标：**
- 请求链路追踪
- 性能监控
- 结构化日志

**需要安装：**
```bash
uv add opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi
```

**文件位置：**
```
src/
└── telemetry.py  # 新建配置文件
```

**功能：**
- 自动追踪所有 API 请求
- 记录 workflow 各步骤耗时
- 追踪 agent 调用性能

---

### ⬜ 2. 配置 CI/CD 自动部署
**预计时间：15-30 分钟**

**目标：**
- 自动化部署流程
- push 到 GitHub 后自动部署到 Azure

**方式选择：**

#### 🚀 方式 1：Azure 自动 CI/CD（推荐新手）
**优点：** 最简单，Azure 自动配置一切

**步骤：**
1. 在 Azure Portal 创建 Container App
2. 选择 Deployment source: "GitHub"
3. 授权并选择你的仓库
4. Azure 自动创建 `.github/workflows/` 文件

**结果：**
- ✅ push 后自动构建 + 部署
- ✅ 无需手动配置 secrets
- ✅ 5-10 分钟完成部署

---

#### ⚙️ 方式 2：自定义 GitHub Actions（更灵活）
**优点：** 完全控制部署流程

**文件位置：**
```
.github/
└── workflows/
    └── deploy.yml  # CI/CD 配置
```

**流程：**
```yaml
1. test 阶段        # 运行测试 + 代码检查
   ↓
2. build 阶段       # 构建 Docker 镜像
   ↓
3. deploy 阶段      # 部署到 Azure
```

**需要配置的 GitHub Secrets：**
```
AZURE_CREDENTIALS    # Azure 服务主体凭证
ACR_USERNAME         # Container Registry 用户名
ACR_PASSWORD         # Container Registry 密码
```

**完整 workflow 示例：**
```yaml
# .github/workflows/deploy.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: <your-registry>.azurecr.io
  IMAGE_NAME: maf
  RESOURCE_GROUP: maf-rg
  CONTAINER_APP: maf-app

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync
      - name: Run tests
        run: uv run pytest tests/
      - name: Run linter
        run: uv run ruff check .

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Log in to ACR
        uses: azure/docker-login@v1
        with:
          login-server: ${{ env.REGISTRY }}
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}
      - name: Build and push
        run: |
          docker build -t ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} .
          docker push ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - uses: azure/container-apps-deploy-action@v1
        with:
          resourceGroup: ${{ env.RESOURCE_GROUP }}
          containerAppName: ${{ env.CONTAINER_APP }}
          imageToDeploy: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
```

**对比选择：**
| 特性 | Azure 自动 | 自定义 GitHub Actions |
|------|-----------|---------------------|
| 设置难度 | ⭐ 简单 | ⭐⭐⭐ 中等 |
| 灵活性 | 固定流程 | 完全自定义 |
| 自动测试 | ❌ 无 | ✅ 有 |
| 多环境 | ❌ 单环境 | ✅ dev/staging/prod |

**建议：** 先用 Azure 自动方式快速上线，后期需要时切换到自定义方式

---

## ⚡ 中优先级（提升开发体验）

### ⬜ 3. 添加 pre-commit 配置
**预计时间：15 分钟**

**目标：**
- 自动代码检查
- 防止提交低质量代码

**文件位置：**
```
.pre-commit-config.yaml  # 项目根目录
```

**需要安装：**
```bash
uv add --dev pre-commit
pre-commit install
```

**功能：**
- commit 前自动运行 Ruff
- 自动格式化代码
- 检查常见错误

---

## 💾 未来扩展（有数据库需求时）

### ⏸️ 4. 添加数据持久化层
**仅在需要时添加**

**触发条件：**
- 需要持久化 session（Redis）
- 需要保存对话历史（数据库）

**需要添加：**
```
src/
├── models/         # 数据库表定义（SQLAlchemy）
├── db/             # 数据库连接配置
└── repositories/   # 数据访问层
```

---

## 🚫 不需要添加

### ❌ Terraform
**原因：**
- 项目规模较小
- 手动部署到 Azure Container Apps 更简单
- 不需要复杂的基础设施管理

**何时考虑：**
- 团队协作需要基础设施版本控制
- 需要管理多环境（dev/staging/prod）
- 服务数量超过 5 个


## 🎯 当前项目状态

**已完成：**
- ✅ FastAPI 应用结构
- ✅ 两个 agent（flight + chart）
- ✅ Workflow 实现
- ✅ Session 管理（内存）
- ✅ API 端点（AG-UI /copilotkit）
- ✅ Ruff 配置（代码格式化）
- ✅ 异常处理（exceptions.py）
- ✅ 单元测试（pytest - 21 tests passed）
- ✅ Dockerfile + docker-compose（前后端一键启动）
- ✅ MCP 工具集成（chart-generator）
- ✅ CopilotKit 前端（Next.js）

**待添加：**
- ⬜ 监控追踪（OpenTelemetry）
- ⬜ CI/CD 配置
- ⬜ pre-commit 配置

---

## 📚 参考资源

**OpenTelemetry：**
- 官方文档：https://opentelemetry.io/docs/languages/python/
- FastAPI 集成：https://opentelemetry-python-contrib.readthedocs.io/

**CI/CD：**
- GitHub Actions 文档：https://docs.github.com/actions
- Azure Container Apps CI/CD：https://learn.microsoft.com/azure/container-apps/github-actions
- Azure 服务主体创建：https://learn.microsoft.com/cli/azure/create-an-azure-service-principal-azure-cli

---

_最后更新：2025-11-30_
