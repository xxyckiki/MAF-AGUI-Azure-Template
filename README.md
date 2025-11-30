# MAF - Microsoft Agent Framework Demo

A full-stack AI agent application using Microsoft Agent Framework with FastAPI backend and CopilotKit frontend.

## Features

- 🤖 **AI Agents**: Flight price query agent + Chart generation agent
- 🔄 **Workflow**: Sequential workflow connecting flight query → chart generation
- 🎨 **CopilotKit UI**: Modern chat interface with AG-UI protocol
- 🐳 **Docker Ready**: One-command deployment for both frontend and backend

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              CopilotKit Chat UI                      │    │
│  │         (port 3000)                                  │    │
│  └──────────────────────┬──────────────────────────────┘    │
└─────────────────────────┼───────────────────────────────────┘
                          │ AG-UI Protocol
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              /copilotkit endpoint                    │    │
│  │         (port 8000)                                  │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │           Microsoft Agent Framework                  │    │
│  │  ┌─────────────┐         ┌─────────────┐            │    │
│  │  │ Flight Agent│ ──────▶ │ Chart Agent │            │    │
│  │  └─────────────┘         └─────────────┘            │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Azure CLI (logged in with `az login`)
- Azure OpenAI resource

### 1. Clone and Configure

```bash
# Copy environment variables
cp .env.example .env

# Edit .env with your Azure OpenAI settings
```

### 2. Start with Docker Compose (One Command!)

```bash
docker-compose up --build
```

This will:
- Build and start the Python backend on http://localhost:8000
- Build and start the Next.js frontend on http://localhost:3000

### 3. Open the App

Visit http://localhost:3000 and start chatting with the AI agent!

## Development

### Backend Only

```bash
# Install dependencies
uv sync

# Run the server
uv run uvicorn main:app --reload
```

### Frontend Only

```bash
cd frontend

# Install dependencies
npm install --legacy-peer-deps

# Run dev server
npm run dev
```

### Run Tests

```bash
uv run pytest -v
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | Required |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name | `gpt-4o` |
| `AZURE_OPENAI_API_VERSION` | API version | `2024-12-01-preview` |
| `DEBUG` | Enable debug mode | `true` |
| `BACKEND_URL` | Backend URL (for frontend) | `http://localhost:8000` |

## Project Structure

```
maf/
├── main.py                 # FastAPI entry point
├── src/
│   ├── services/
│   │   ├── agent.py        # Agent definitions
│   │   ├── tools.py        # Agent tools
│   │   └── workflow.py     # Sequential workflow
│   └── exceptions.py       # Exception handling
├── tests/                  # Unit tests
├── frontend/               # Next.js + CopilotKit
│   ├── src/app/
│   │   ├── page.tsx        # Chat UI
│   │   └── api/copilotkit/ # API route
│   └── Dockerfile
├── Dockerfile              # Backend Dockerfile
├── docker-compose.yml      # One-command deployment
└── pyproject.toml          # Python dependencies
```

## License

MIT
