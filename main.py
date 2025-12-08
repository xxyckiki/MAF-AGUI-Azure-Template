import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agent_framework_ag_ui import add_agent_framework_fastapi_endpoint
from src.services.agent import copilot_agent
from src.exceptions import register_exception_handlers
from agent_framework.observability import setup_observability

# Load environment variables from .env file
load_dotenv()

# Check if running in debug mode
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# Configure OpenTelemetry - Agent Framework has built-in Azure Monitor support
# Reference: https://learn.microsoft.com/azure/ai-services/agents/how-to/observability
setup_observability()

app = FastAPI(
    title="Flight Agent API",
    description="AI Agent for flight price queries with AG-UI support",
    version="1.0.0",
)

# Register global exception handlers
register_exception_handlers(app, debug=DEBUG)

# CORS configuration - allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register AG-UI endpoint for CopilotKit connection
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
