#  AI Module

A powerful AI-powered helpdesk system built with FastAPI, LlamaIndex, and modern AI technologies. This system provides intelligent knowledge management, automated customer support, and AI-driven ticket analysis capabilities.

## 🚀 Features

### Core AI Capabilities
- **Multi-LLM Support**: Gemini and OpenAI integration with configurable providers
- **Vector Search**: Qdrant-based vector store for semantic search and retrieval
- **RAG (Retrieval-Augmented Generation)**: Advanced knowledge retrieval and AI responses
- **Agent System**: ReAct agents with tool usage and complex reasoning capabilities

### Knowledge Management
- **Multi-Source Import**: Local files, Google Drive, web content, database queries
- **Document Processing**: Support for PDF, DOCX, PPTX, Excel, and text files
- **Web Crawling**: Crawl4AI integration for website content extraction
- **Automatic Indexing**: Background task processing with Celery

### Helpdesk Features
- **Ticket Analysis**: AI-powered ticket categorization and analysis
- **Auto-Response Generation**: Intelligent response drafting and customization
- **Response Enhancement**: Spelling correction, tone adjustment, length optimization
- **API Variable Parsing**: Extract and process API variables from tickets

### Infrastructure
- **Task Queue**: Redis + Celery for background processing
- **File Storage**: Configurable storage backends
- **Monitoring**: Flower dashboard for task monitoring
- **Docker Support**: Complete containerization setup

## 🏗️ Architecture

```
┌────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App  │    │   Celery Tasks  │    │  Vector Store   │
│                │    │                 │    │   (Qdrant)      │
│ • API Routes   │    │ • File Indexing │    │ • Embeddings    │
│ • LLM Config   │    │ • Web Crawling  │    │ • Search        │
│ • Agent Mgmt   │    │ • Reindexing    │    │ • Storage       │
└────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │      Redis      │
                    │                 │
                    │ • Task Broker   │
                    │ • Result Store  │
                    └─────────────────┘
```

## 📋 Prerequisites

- **Python**: 3.11 or 3.12
- **Poetry**: For dependency management
- **Redis**: For task queue (optional in development)
- **Qdrant**: Vector database (optional in development)

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd helpdesk-agentic
```

### 2. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# Required variables:
# - LLM provider API keys (Gemini/OpenAI)
# - Vector store configuration
# - Google Drive credentials (if using)
# - Database connections (if using)
```

### 3. Install Dependencies
```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install

# Activate virtual environment
poetry shell
```

### 4. Install Additional Dependencies (Optional)
```bash
# For web crawling (Playwright)
poetry run playwright install
poetry run playwright install-deps

# For database connectivity
# PostgreSQL: psycopg2-binary (included)
# SQL Server: pyodbc (included)
```

## 🚀 Quick Start

### Development Mode
```bash
# Start the development server
poetry run dev

# The API will be available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### Production Mode
```bash
# Start production server
poetry run prod

# Start background workers
poetry run worker

# Start task scheduler
poetry run celery -A app.tasks beat --loglevel=debug
```

## 📚 API Endpoints

### Knowledge Management
- `POST /api/v1/knowledge/import-file` - Import local files
- `POST /api/v1/knowledge/import-web` - Import web content
- `POST /api/v1/knowledge/google-drive` - Import from Google Drive
- `POST /api/v1/knowledge/query` - Query knowledge base
- `DELETE /api/v1/knowledge/delete-documents` - Remove documents

### AI Agent
- `POST /api/v1/agent/ask-question` - Complex reasoning with ReAct agent
- `POST /api/v1/agent/rag-query` - Direct RAG query
- `POST /api/v1/agent/complete` - Pure LLM completion
- `POST /api/v1/agent/chat-complete` - Chat with history

### Ask AI (Helpdesk Features)
- `POST /api/v1/ask-ai/draft-response` - Generate response drafts
- `POST /api/v1/ask-ai/auto-response` - Automated responses
- `POST /api/v1/ask-ai/ticket-analyze` - Analyze support tickets
- `POST /api/v1/ask-ai/correct-spelling` - Fix spelling errors
- `POST /api/v1/ask-ai/simplify-words` - Simplify language

## 🔧 Configuration

### LLM Providers
```python
# app/settings/llm/
LLM__PROVIDER=gemini  # or openai
LLM__GEMINI__API_KEY=your_gemini_key
LLM__OPENAI__API_KEY=your_openai_key
```

### Vector Store
```python
# app/settings/infra/vector_store/
INFRA__VECTOR_STORE__TYPE=qdrant
INFRA__VECTOR_STORE__URL=http://localhost:6333
INFRA__VECTOR_STORE__API_KEY=your_qdrant_key
```

### Task Queue
```python
# app/settings/infra/task_queue/
INFRA__TASK_QUEUE__MESSAGE_BROKER=redis://localhost:6379/0
INFRA__TASK_QUEUE__RESULT_BACKEND=redis://localhost:6379/1
```

## 🐳 Docker Deployment

### 1. Build Images
```bash
# Build main application
docker build -t helpdesk-agentic .

# Build worker image
docker build -t helpdesk-worker -f deployment/Dockerfile.worker .

# Build Celery beat image
docker build -t helpdesk-celery -f deployment/Dockerfile.worker .
```

### 2. Start Services
```bash
# Start infrastructure
docker-compose -f deployment/docker-compose.yml up -d redis qdrant

# Start application
docker run -d \
  --env-file .env \
  -p 8000:8000 \
  --network helpdesk-network \
  --name helpdesk-app \
  -v $(pwd)/data:/app/data \
  helpdesk-agentic

# Start worker
docker run -d \
  --env-file .env \
  --network helpdesk-network \
  --name helpdesk-worker \
  -v $(pwd)/data:/app/data \
  helpdesk-worker

# Start Celery beat
docker run -d \
  --env-file .env \
  --network helpdesk-network \
  --name helpdesk-celery \
  helpdesk-celery
```

### 3. Monitor Tasks
```bash
# Access Flower dashboard
open http://localhost:5555
```

## 🔍 Development

### Project Structure
```
helpdesk-agentic/
├── app/
│   ├── api/routers/          # API endpoints
│   ├── core/                 # Core functionality
│   │   ├── agents/          # AI agent management
│   │   ├── prompts/         # LLM prompts and workflows
│   │   └── tools/           # Agent tools
│   ├── models/              # Data models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   ├── settings/            # Configuration
│   └── tasks/               # Background tasks
├── deployment/               # Docker configurations
├── tests/                   # Test suite
└── data/                    # Knowledge base storage
```

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html
```

### Code Quality
```bash
# Lint code
poetry run ruff check .

# Format code
poetry run ruff format .

# Type checking
poetry run mypy app/
```

## 🌐 Web Crawling with Crawl4AI

### Windows Users
For optimal performance with web crawling, use WSL (Windows Subsystem for Linux):

1. **Install WSL Extension** in VS Code
2. **Install Ubuntu** from Microsoft Store
3. **Reopen project in WSL**: `Ctrl+Shift+P` → `WSL: Reopen Folder in WSL`
4. **Install dependencies**:
   ```bash
   poetry install
   poetry run playwright install
   poetry run playwright install-deps
   ```

## 📊 Monitoring & Logging

- **Application Logs**: Check `logs/` directory
- **Task Monitoring**: Flower dashboard at `/flower`
- **Health Check**: `GET /api/v1/health`
- **Performance**: Built-in performance logging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run linting and tests
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Contact: ticketplus0@gmail.com

---

**Built with ❤️ by the  Team**
