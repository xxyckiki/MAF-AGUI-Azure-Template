import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agent_framework_ag_ui import add_agent_framework_fastapi_endpoint
from src.services.agent import copilot_agent
from src.exceptions import register_exception_handlers

# 是否为开发环境
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

app = FastAPI(
    title="Flight Agent API",
    description="AI Agent for flight price queries with AG-UI support",
    version="1.0.0",
)

# 注册全局异常处理器
register_exception_handlers(app, debug=DEBUG)

# CORS 配置 - 允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 AG-UI 端点（CopilotKit 连接用）
add_agent_framework_fastapi_endpoint(
    app=app,
    agent=copilot_agent,
    path="/copilotkit",
)


@app.get("/")
async def root():
    return {"message": "Flight Agent API", "docs": "/docs", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
