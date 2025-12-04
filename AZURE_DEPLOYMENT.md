# Azure 部署指南

## 项目概述

本项目是基于 Microsoft Agent Framework + CopilotKit + Azure OpenAI 的 AI Agent 模板，支持 Docker 化部署到 Azure Container Apps。

---

## 部署架构

```
GitHub Repository
    ↓ (git push to main)
    ├─→ Backend CI/CD (GitHub Actions)
    │       ↓ (build Docker image)
    │   Azure Container Registry (mafagentacr)
    │       ↓ (deploy)
    │   Azure Container App (mafagent)
    │       ↓ (authenticate)
    │   Azure OpenAI (Managed Identity)
    │
    └─→ Frontend CI/CD (GitHub Actions)
            ↓ (build Next.js)
        Azure Static Web Apps (maf-frontend)
            ↓ (connect to backend)
        Backend API (BACKEND_URL env var)
```

---

## 前置准备

### 本地环境

- ✅ Python 3.13 + uv
- ✅ Docker + docker-compose
- ✅ Azure CLI (`az login` 已完成)
- ✅ GitHub 账号
- ✅ Azure 订阅

### Azure 资源

- Azure OpenAI 服务 (`llmmvptest1`)
  - 部署名称：`gpt-5-nano`
  - 端点：`https://llmmvptest1.openai.azure.com/`

---

## 部署步骤

### 第一步：创建 Azure Container Registry

1. 访问 [Azure Portal](https://portal.azure.com)
2. 搜索 **Container Registry** → 创建
3. 填写配置：
   - **Registry name**: `mafagentacr`（必须全球唯一）
   - **Resource group**: `llmmvp`（或新建）
   - **Location**: `Japan East`
   - **Pricing plan**: `Basic`
4. 点击 **Review + create** → **Create**
5. 创建完成后，进入 Registry
6. 左侧 **Settings → Access keys**
7. 开启 **Admin user** ✅

---

### 第二步：创建 Azure Container App

#### 2.1 基础配置

1. 搜索 **Container Apps** → 创建
2. **Basics** 标签页：
   - **Resource group**: `llmmvp`
   - **Container app name**: `mafagent`
   - **Region**: `Japan East`（与 Registry 同区）
   - **Optimize for Azure Functions**: ❌ 不勾选

3. **Container** 标签页：
   - **Use quickstart image**: ✅ 勾选（先用示例镜像创建）
   - **Image source**: `Azure Container Registry`
   - **Registry**: `mafagentacr`

4. 点击 **Review + create** → **Create**

#### 2.2 配置 Ingress（重要！）

1. 进入创建好的 Container App
2. 左侧 **Networking → Ingress**
3. 配置：
   - **Ingress**: ✅ Enabled
   - **Ingress traffic**: `Accepting traffic from anywhere`
   - **Ingress type**: `HTTP`
   - **Target port**: `8000` ⚠️（默认是 80，必须改成 8000）
4. 点击 **Save**

---

### 第三步：配置 Managed Identity 认证

#### 3.1 开启 Managed Identity

1. Container App → **Settings → Identity**
2. **System assigned** 标签页
3. **Status** 改成 **On**
4. 点击 **Save**
5. 记下生成的 **Object (principal) ID**

#### 3.2 授权访问 Azure OpenAI

1. 搜索你的 Azure OpenAI 资源：`llmmvptest1`
2. 左侧 **Access control (IAM)**
3. 点击 **+ Add → Add role assignment**
4. **Role** 标签页：
   - 选择 **Cognitive Services OpenAI User**
   - 点击 **Next**
5. **Members** 标签页：
   - **Assign access to**: `Managed identity`
   - 点击 **+ Select members**
   - **Managed identity**: 选择 `Container App (1)`
   - 在列表中选择 `mafagent`
   - 点击 **Select**
6. 点击 **Review + assign** → **Assign**

---

### 第四步：配置环境变量

1. Container App → **Application → Containers** 或 **Settings → Environment variables**
2. 点击 **Edit and deploy** 或 **Add**
3. 添加以下环境变量：

| Name | Value |
|------|-------|
| `AZURE_OPENAI_ENDPOINT` | `https://llmmvptest1.openai.azure.com/` |
| `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME` | `gpt-5-nano` |

4. 点击 **Save**

> ⚠️ **注意**：不需要 `AZURE_OPENAI_API_KEY`，因为使用 Managed Identity 认证。

---

### 第五步：配置 GitHub Actions CI/CD

#### 5.1 配置自动部署

1. Container App → **Settings → Deployment**
2. 点击 **Continuous deployment** 标签页
3. 点击 **Sign in with GitHub** 并授权
4. 配置：
   - **Organization**: `xxyckiki`
   - **Repository**: `maf-copilotkit-agent-template`
   - **Branch**: `main`
5. **Registry settings**：
   - **Repository source**: `Azure Container Registry`
   - **Registry**: `mafagentacr`
   - **Image**: `mafagent`
   - **Dockerfile location**: `./Dockerfile`
6. **Azure access**：
   - **Authentication type**: `User-assigned Identity` ✅
7. 点击 **Start continuous deployment**

#### 5.2 修复自动生成的 Workflow

Azure 生成的 workflow 文件可能有占位符错误，需要手动修复：

**文件路径**：`.github/workflows/mafagent-AutoDeployTrigger-*.yml`

修复前：
```yaml
_dockerfilePathKey_: _dockerfilePath_
_targetLabelKey_: _targetLabel_
```

修复后：
```yaml
dockerfilePath: ./Dockerfile
```

提交修复：
```bash
git add .
git commit -m "Fix workflow dockerfile path"
git push
```

---

### 第六步：修改代码支持云端部署

#### 6.1 使用 ChainedTokenCredential

**文件**：`src/services/agent.py`

```python
import os
from azure.identity import ManagedIdentityCredential, AzureCliCredential, ChainedTokenCredential
from agent_framework.azure import AzureOpenAIChatClient


def get_credential():
    """Get credential based on environment."""
    # 云端优先使用 Managed Identity，本地用 Azure CLI
    return ChainedTokenCredential(
        ManagedIdentityCredential(),  # 云端
        AzureCliCredential(),          # 本地
    )


# Create the chat client
chat_client = AzureOpenAIChatClient(
    credential=get_credential(),
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-5-nano"),
)
```

#### 6.2 推送代码触发部署

```bash
git add .
git commit -m "Use ChainedTokenCredential for Managed Identity"
git push
```

---

## 验证部署

### 查看部署状态

1. **GitHub Actions**：https://github.com/xxyckiki/maf-copilotkit-agent-template/actions
   - 等待 workflow 变成 ✅ 绿色

2. **Azure Container App Revisions**：
   - Container App → **Application → Revisions and replicas**
   - 新的 Revision 状态变成 **Running** ✅

### 测试 API

访问你的应用 URL：

```
https://mafagent.bravebeach-3e2d28d0.japaneast.azurecontainerapps.io
```

预期响应：
```json
{
  "message": "Flight Agent API",
  "docs": "/docs",
  "version": "1.0.0"
}
```

API 文档：
```
https://mafagent.bravebeach-3e2d28d0.japaneast.azurecontainerapps.io/docs
```

---

## 常见问题排查

### 1. 服务启动后立即关闭

**症状**：
```
INFO: Application startup complete.
INFO: Shutting down
```

**原因**：Ingress Target port 配置错误

**解决**：
- 检查 **Networking → Ingress → Target port** 是否为 `8000`
- 如果不是，改成 `8000` 并保存
- 推送空 commit 触发重新部署：
  ```bash
  git commit --allow-empty -m "Trigger redeploy"
  git push
  ```

---

### 2. Azure CLI not found 错误

**症状**：
```
AzureCliCredential.get_token failed: Azure CLI not found on path
```

**原因**：DefaultAzureCredential 尝试 Azure CLI 认证失败

**解决**：使用 `ChainedTokenCredential`，优先尝试 Managed Identity

---

### 3. Managed Identity 认证失败

**检查清单**：

1. ✅ Container App 已开启 System-assigned Managed Identity
2. ✅ Managed Identity 已被授予 `Cognitive Services OpenAI User` 角色
3. ✅ 环境变量 `AZURE_OPENAI_ENDPOINT` 和 `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME` 已配置
4. ✅ 代码使用 `ManagedIdentityCredential` 或 `ChainedTokenCredential`

---

### 4. Docker 镜像构建失败

**检查**：
- Dockerfile 路径是否正确（`./Dockerfile`）
- GitHub Actions workflow 文件是否有占位符错误
- Container Registry Admin user 是否已开启

---

### 5. 前端构建失败：依赖冲突

**症状**：
```
npm error ERESOLVE could not resolve
npm error peer @ag-ui/client@"0.0.40-alpha.7"
```

**解决**：
- 使用 `npm install --legacy-peer-deps`
- 修改 workflow 添加手动构建步骤

---

### 6. 前端构建失败：Node.js 版本

**症状**：
```
You are using Node.js 18.20.8. For Next.js, Node.js version ">=20.9.0" is required.
```

**解决**：
- workflow 中设置 `node-version: '20'`

---

### 7. 前端能打开但无响应（三个点一直转）

**可能原因**：
1. 环境变量 `BACKEND_URL` 未配置
2. 后端 URL 配置错误
3. 后端服务未启动（scaled to 0）
4. CORS 问题

**解决**：
1. 检查 Static Web App 的环境变量是否正确
2. 触发空 commit 重新部署：`git commit --allow-empty -m "Redeploy" && git push`
3. 等待后端唤醒（首次请求需要 5-10 秒）
4. 检查浏览器 F12 Console 和 Network 标签页的错误信息

---

## CI/CD 工作流程

### 后端部署流程

```
1. 开发者 git push 到 main 分支
    ↓
2. GitHub Actions 自动触发 (mafagent-AutoDeployTrigger-*.yml)
    ↓
3. 构建 Docker 镜像
    ↓
4. 推送到 Azure Container Registry
    ↓
5. 部署到 Azure Container App
    ↓
6. 健康检查通过 → 流量切换到新版本
```

### 前端部署流程

```
1. 开发者 git push 到 main 分支
    ↓
2. GitHub Actions 自动触发 (azure-static-web-apps-*.yml)
    ↓
3. 安装 Node.js 20
    ↓
4. npm install --legacy-peer-deps
    ↓
5. npm run build (生成 .next 目录)
    ↓
6. 部署到 Azure Static Web Apps
    ↓
7. 全球 CDN 分发 → 用户访问
```

---

## 认证方式对比

| 方式 | 本地开发 | Azure 云端 | 安全性 | 复杂度 |
|------|---------|-----------|-------|-------|
| **API Key** | ✅ | ✅ | ⚠️ 中 | ⭐ 简单 |
| **Azure CLI** | ✅ | ❌ | ✅ 高 | ⭐ 简单 |
| **Managed Identity** | ❌ | ✅ | ✅ 最高 | ⭐⭐ 中等 |
| **ChainedTokenCredential** | ✅ | ✅ | ✅ 最高 | ⭐⭐ 中等 |

**推荐**：使用 `ChainedTokenCredential(ManagedIdentityCredential(), AzureCliCredential())`

---

## 成本估算

| 资源 | 配置 | 月成本（估算） |
|------|------|--------------|
| Container Registry | Basic | ~$5 |
| Container App | 按需计费（缩容到 0） | ~$0-20 |
| Static Web Apps | Free 计划 | $0 |
| Azure OpenAI | 按 token 计费 | 取决于使用量 |

**总计**：约 $5-25/月（不含 OpenAI token 费用）

**注意**：
- Container App 在无流量时可以缩容到 0，节省成本
- Static Web Apps 免费额度：100 GB 带宽/月，足够个人项目使用
- OpenAI 费用取决于实际调用量和模型选择

---

## 项目配置文件

### 关键文件清单

```
.
├── .github/
│   └── workflows/
│       ├── mafagent-AutoDeployTrigger-*.yml    # 后端 CI/CD
│       └── azure-static-web-apps-*.yml         # 前端 CI/CD
├── frontend/
│   ├── src/
│   │   └── app/
│   │       ├── api/
│   │       │   └── copilotkit/
│   │       │       └── route.ts                # 前端 API 路由（连接后端）
│   │       ├── page.tsx                        # 主页面
│   │       └── layout.tsx                      # 布局
│   ├── package.json                            # 前端依赖
│   └── Dockerfile                              # 前端容器配置（本地开发用）
├── src/
│   └── services/
│       └── agent.py                            # Agent 配置（Managed Identity）
├── Dockerfile                                  # 后端容器配置
├── docker-compose.yml                          # 本地开发环境
├── .env                                        # 本地环境变量（不提交）
└── AZURE_DEPLOYMENT.md                         # 本文档
```

### 环境变量配置

**本地开发**（`.env` 文件）：
```env
AZURE_OPENAI_ENDPOINT=https://llmmvptest1.openai.azure.com/
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-5-nano
```

**Azure Container App - Backend**（Environment variables）：
```
AZURE_OPENAI_ENDPOINT=https://llmmvptest1.openai.azure.com/
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-5-nano
```

**Azure Static Web Apps - Frontend**（Environment variables）：
```
BACKEND_URL=https://mafagent.bravebeach-3e2d28d0.japaneast.azurecontainerapps.io
```

---

## 第七步：前端部署到 Azure Static Web Apps

### 7.1 创建 Static Web App

1. 访问 [Azure Portal](https://portal.azure.com)
2. 搜索 **Static Web Apps** → 创建
3. **Basics** 标签页：
   - **Resource group**: `llmmvp`（与后端同组）
   - **Name**: `maf-frontend`
   - **Plan type**: `Free`
   - **Region**: `East Asia`（或就近区域）
   - **Source**: `GitHub`
   - **GitHub account**: 授权你的账号

4. **Build Details** 标签页：
   - **Organization**: `xxyckiki`
   - **Repository**: `maf-copilotkit-agent-template`
   - **Branch**: `main`
   - **Build Presets**: `Next.js`
   - **App location**: `/frontend`
   - **Api location**: (留空)
   - **Output location**: (留空)

5. 点击 **Review + create** → **Create**

### 7.2 配置前端环境变量

1. 等待 Static Web App 创建完成
2. 进入 `maf-frontend` 资源
3. 左侧 **Settings → Environment variables**
4. 选择 **Production** 环境
5. 点击 **+ Add**
6. 添加环境变量：
   - **Name**: `BACKEND_URL`
   - **Value**: `https://mafagent.bravebeach-3e2d28d0.japaneast.azurecontainerapps.io`
7. 点击 **Apply**

### 7.3 修复 CI/CD Workflow（如果需要）

Azure 会自动创建 workflow 文件并推送到你的仓库。如果遇到依赖冲突问题，需要修改 workflow：

**问题 1：npm 依赖冲突**

```
npm error ERESOLVE could not resolve
npm error peer @ag-ui/client@"0.0.40-alpha.7" from @ag-ui/langgraph@0.0.19
```

**问题 2：Node.js 版本不匹配**

```
You are using Node.js 18.20.8. For Next.js, Node.js version ">=20.9.0" is required.
```

**解决方案**：修改 `.github/workflows/azure-static-web-apps-*.yml`

```yaml
jobs:
  build_and_deploy_job:
    runs-on: ubuntu-latest
    name: Build and Deploy Job
    steps:
      - uses: actions/checkout@v3
        with:
          submodules: true
          lfs: false
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'  # Next.js 16 需要 Node 20+
      - name: Install dependencies with legacy peer deps
        run: npm install --legacy-peer-deps
        working-directory: ./frontend
      - name: Build application
        run: npm run build
        working-directory: ./frontend
      - name: Deploy to Azure Static Web Apps
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN_* }}
          repo_token: ${{ secrets.GITHUB_TOKEN }}
          action: "upload"
          app_location: "/frontend"
          api_location: ""
          output_location: ""
          skip_app_build: true  # 使用前面手动构建的结果
```

提交修改：
```bash
git add .
git commit -m "Fix: Frontend build with Node 20 and legacy-peer-deps"
git push
```

### 7.4 验证前端部署

1. **查看部署状态**：
   - Static Web App → **Overview**
   - Status 显示 **Ready** ✅
   - 找到前端 URL（类似 `https://happy-bay-03eea5e00.3.azurestaticapps.net`）

2. **访问前端**：
   - 点击 **Visit your site** 或直接访问 URL
   - 应该能看到聊天界面

3. **测试功能**：
   - 在聊天框输入：`"查询 12 月 15 日从上海到北京的航班价格"`
   - 应该能看到 AI Agent 返回航班信息
   - 请求生成图表：`"给我画个柱状图"`
   - 验证 chart_agent 正常工作

4. **查看日志**（如果有问题）：
   - 浏览器按 F12 打开开发者工具
   - **Console** 标签页：查看前端日志
   - **Network** 标签页：查看 API 请求
   - 检查 `/api/copilotkit` 请求是否成功

---

## 完整部署验证

### 后端验证

**访问后端 API**：
```
https://mafagent.bravebeach-3e2d28d0.japaneast.azurecontainerapps.io
```

**预期响应**：
```json
{
  "message": "Flight Agent API",
  "docs": "/docs",
  "version": "1.0.0"
}
```

**API 文档**：
```
https://mafagent.bravebeach-3e2d28d0.japaneast.azurecontainerapps.io/docs
```

### 前端验证

**访问前端**：
```
https://happy-bay-03eea5e00.3.azurestaticapps.net
```

**测试命令**：
1. `"查询 12 月 15 日从上海到北京的航班价格"`
2. `"给我画个柱状图"`
3. `"从上海到纽约的航班多少钱？"`

### 端到端测试

1. 在前端聊天框输入航班查询请求
2. 观察前端显示 AI 思考过程（三个点动画）
3. 后端自动从 scaled-to-zero 状态唤醒（首次请求可能需要 5-10 秒）
4. 查看返回的航班价格信息
5. 请求生成图表，验证 workflow 正常（flight_agent → chart_agent）

---

## 下一步

### 进一步优化

1. **自定义域名**
   - Static Web Apps：配置自定义域名和 SSL 证书
   - Container App：配置自定义域名

2. **监控和告警**
   - 配置 Application Insights
   - 设置资源使用告警
   - 配置日志分析

3. **安全加固**
   - 限制 CORS 到特定域名
   - 配置 API 认证
   - 启用 Azure WAF

4. **性能优化**
   - 配置 CDN 加速
   - 优化 Container App 最小/最大副本数
   - 配置缓存策略

---

## 参考资源

- [Azure Container Apps 文档](https://learn.microsoft.com/azure/container-apps/)
- [Azure Static Web Apps 文档](https://learn.microsoft.com/azure/static-web-apps/)
- [Managed Identity 文档](https://learn.microsoft.com/azure/active-directory/managed-identities-azure-resources/)
- [GitHub Actions 文档](https://docs.github.com/actions)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [CopilotKit 文档](https://docs.copilotkit.ai/)
- [Next.js 文档](https://nextjs.org/docs)

---

## 支持

如有问题，请查看：
- **GitHub Issues**: https://github.com/xxyckiki/maf-copilotkit-agent-template/issues
- **后端日志**：Container App → **Monitoring → Log stream**
- **前端日志**：
  - GitHub Actions 构建日志
  - 浏览器 F12 开发者工具
- **部署历史**：
  - Container App → **Application → Revisions**
  - Static Web App → **Deployment history**

---

_最后更新：2025-12-04_
