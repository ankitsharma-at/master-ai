# 🚀 Quick Start Guide

## Current Status

✅ **Build Complete** - All 35 Python files have valid syntax
❌ **Server Not Running** - Dependencies need to be installed

---

## Option 1: Run with Docker (Recommended)

### Prerequisites
- Docker installed
- Docker Compose installed

### Steps

```bash
# 1. Build and run
docker-compose up --build

# 2. In another terminal, test:
curl http://localhost:8000/health/

# 3. Test the API:
curl -X POST http://localhost:8000/task/ \
  -H "Content-Type: application/json" \
  -d '{"command": "What is machine learning?"}'
```

---

## Option 2: Run Locally with Virtual Environment

### Steps

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
# Edit .env with your API keys:
# - ANTHROPIC_API_KEY (for Claude)
# - OPENAI_API_KEY (for GPT)
# - GOOGLE_API_KEY (for Gemini)

# 4. Run the server
uvicorn api.main:app --reload

# 5. Test:
curl http://localhost:8000/health/
```

---

## Option 3: Install System-wide (Not Recommended)

```bash
# Warning: This may affect your system Python installation
pip install -r requirements.txt --break-system-packages
uvicorn api.main:app --reload
```

---

## Testing the API

### Health Check
```bash
curl http://localhost:8000/health/
```

Expected response:
```json
{"status": "ok"}
```

### Simple Task (Direct LLM)
```bash
curl -X POST http://localhost:8000/task/ \
  -H "Content-Type: application/json" \
  -d '{"command": "Explain quantum computing in simple terms"}'
```

Expected response:
```json
{
  "session_id": "...",
  "result": "Quantum computing uses...",
  "tool_used": "direct_llm",
  "match_type": "direct_llm",
  "complexity": "simple",
  "runtime_ms": 1500,
  "success": true
}
```

### Complex Task (Tool Generation)
```bash
curl -X POST http://localhost:8000/task/ \
  -H "Content-Type: application/json" \
  -d '{"command": "Create a JSON to CSV converter"}'
```

Expected response:
```json
{
  "session_id": "...",
  "result": {...},
  "tool_used": "json_to_csv_converter",
  "tool_version": "1.0.0",
  "match_type": "generate",
  "complexity": "moderate",
  "runtime_ms": 4500,
  "success": true
}
```

### Reuse Tool (Second Request)
```bash
curl -X POST http://localhost:8000/task/ \
  -H "Content-Type: application/json" \
  -d '{"command": "Convert JSON to CSV format"}'
```

Expected response:
```json
{
  "match_type": "reuse",
  "runtime_ms": 150,  # 30x faster!
  "success": true
}
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health/` | GET | Health check |
| `/task/` | POST | Execute command |
| `/tools/` | GET | List all tools |
| `/tools/{name}` | GET | Get tool details |
| `/health/registry` | GET | Registry status |

---

## Environment Variables

Required in `.env`:

```env
# LLM Provider (choose one)
LLM_PROVIDER=anthropic  # or openai, gemini

# API Keys (add the one you're using)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...

# Supabase (already configured in .env)
SUPABASE_URL=https://...supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# Optional
LLM_MODEL=claude-sonnet-4-20250514
ENABLE_DIRECT_LLM=true
REUSE_THRESHOLD=0.85
ADAPT_THRESHOLD=0.60
```

---

## Troubleshooting

### Server Won't Start

```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill any process on port 8000
kill -9 $(lsof -ti:8000)

# Try different port
uvicorn api.main:app --port 8001
```

### Import Errors

```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Docker Issues

```bash
# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up
```

---

## Next Steps

1. ✅ Build is complete
2. 🔧 Install dependencies (Docker or venv)
3. ⚙️ Configure `.env` with API keys
4. 🚀 Start the server
5. 🎯 Test with curl commands
6. 📊 Monitor in Supabase dashboard

---

## Project Summary

- **Build Status**: ✅ Complete (35 files, all valid)
- **Architecture**: Supabase + pgvector + FastAPI
- **LLM Support**: Claude, GPT, Gemini
- **Smart Routing**: Direct LLM + Tool Generation
- **Database**: 5 tables with RLS (already deployed)

Run with Docker or create a virtual environment to start the API!
