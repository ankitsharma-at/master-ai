# Autonomous AI Operating System

**A self-improving AI platform powered by Supabase, pgvector, and LLMs**

## What Is This?

An AI system that learns with every task:
- First time you ask for a tool → It generates and validates one (4-6 seconds)
- Second time → It reuses the cached tool (100-300ms)
- Over time → System becomes smarter and faster

**Key Innovation**: Semantic search with pgvector enables finding similar tools by *meaning*, not just exact matches.

## Architecture

```
User Command
    ↓
Intent Parser (LLM)
    ↓
Semantic Search (pgvector)
    ↓
┌────────────────────────────────┐
│ Similarity Score Decision:    │
│  • ≥ 0.85 → REUSE (100-300ms) │
│  • 0.60-0.85 → ADAPT (1-2s)   │
│  • < 0.60 → GENERATE (4-6s)   │
└────────────────────────────────┘
    ↓
Docker Sandbox Execution
    ↓
Store in Supabase
    ↓
Return Result
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| **API** | FastAPI + Uvicorn |
| **Database** | Supabase (PostgreSQL) |
| **Vector Search** | pgvector |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) |
| **LLM** | Claude (Anthropic) or GPT (OpenAI) |
| **Execution** | Docker sandboxing |
| **Logging** | structlog |

## Database Schema

Your Supabase database has 5 tables:

### 1. `tools` (Tool Metadata)
- ID, name, description, category
- Reliability score (0-100)
- Use count, success count
- Status (active/deprecated/failed)

### 2. `tool_embeddings` (pgvector)
- Tool ID
- 384-dimensional embedding vector
- Powers semantic similarity search

### 3. `tool_usage` (Analytics)
- Every execution logged
- Match type (reuse/adapt/generate)
- Runtime, success status
- Similarity score

### 4. `sessions` (Tracking)
- Session ID
- User ID
- Expiration timestamp

### 5. `tool_versions` (Version History)
- Tool ID references
- Version number
- Code path

## Quick Start

### 1. Clone & Install

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Configure

Your `.env` is pre-configured with Supabase. Just add LLM key:

```env
# Add to .env
ANTHROPIC_API_KEY=sk-ant-your-key
# OR
OPENAI_API_KEY=sk-your-key
```

### 3. Run

```bash
# Start API
uvicorn api.main:app --reload

# Or with Docker
docker-compose up --build
```

### 4. Test

```bash
# Health check
curl http://localhost:8000/health/

# Execute command
curl -X POST http://localhost:8000/task/ \
  -H "Content-Type: application/json" \
  -d '{"command": "Create a JSON formatter"}'
```

**First request**: 4-6 seconds  
**Second request**: ~150ms (reuse!)

## API Reference

### POST /task/
Execute a natural language command.

```bash
curl -X POST http://localhost:8000/task/ \
  -H "Content-Type: application/json" \
  -d '{
    "command": "Extract tables from PDF",
    "session_id": "optional-session-id"
  }'
```

Response:
```json
{
  "session_id": "abc-123",
  "result": {...},
  "tool_used": "pdf_table_extractor",
  "version": "1.0.0",
  "match_type": "reuse",
  "runtime_ms": 150,
  "success": true
}
```

### GET /tools/
List all tools.

```bash
curl http://localhost:8000/tools/
curl http://localhost:8000/tools/?category=data_pipeline
```

### GET /tools/{name}
Get tool details.

```bash
curl http://localhost:8000/tools/json_formatter
```

### DELETE /tools/{name}
Deprecate a tool.

```bash
curl -X DELETE http://localhost:8000/tools/json_formatter
```

### GET /health/
Health check endpoints.

```bash
curl http://localhost:8000/health/
curl http://localhost:8000/health/registry
```

## How Semantic Search Works

When you send: `"Format JSON with indentation"`

1. **Embed**: Convert to 384-dim vector `[0.123, -0.456, ...]`
2. **Search**: pgvector finds similar tools in Supabase
3. **Score**: Calculate cosine similarity
4. **Route**:
   - Score ≥ 0.85 → REUSE existing tool
   - Score 0.60-0.85 → ADAPT existing
   - Score < 0.60 → GENERATE new

Example search (Supabase RPC):
```sql
SELECT * FROM search_tools(
  query_embedding := '[0.123, ...]',
  match_count := 3
);
```

## Self-Improvement Lifecycle

### Day 1 (Learning)
```
Request: "Format JSON"          → GENERATE (4.2s)
Request: "Validate email"        → GENERATE (5.1s)
Request: "Summarize text"        → GENERATE (3.8s)
Request: "Format JSON again"     → REUSE (0.15s) ← Cache hit!
```

### Week 1 (Growing)
```
Total tools: 15-20
Reuse rate: 30%
Avg latency: 2.5s
```

### Week 4 (Mature)
```
Total tools: 50-70
Reuse rate: 80%
Avg latency: 400ms
```

## Example Commands

Try these:

```bash
# Data processing
"Create a CSV parser that extracts specific columns"
"Build a JSON schema validator"
"Convert between date formats"

# Text processing
"Summarize long text into bullet points"
"Extract all email addresses from text"
"Count word frequency in text"

# Web/integration
"Fetch data from an API endpoint"
"Parse XML and extract specific tags"
"Validate URLs and check HTTP status"

# Math/logic
"Calculate statistics (mean, median, mode)"
"Solve basic equations"
"Convert between units"
```

## Monitoring Queries

### Most Used Tools
```sql
SELECT name, use_count, success_count, reliability_score
FROM tools
WHERE status = 'active'
ORDER BY use_count DESC
LIMIT 10;
```

### Reuse Rate
```sql
SELECT
  match_type,
  COUNT(*) as executions,
  AVG(runtime_ms) as avg_ms
FROM tool_usage
GROUP BY match_type;
```

### Recent Executions
```sql
SELECT
  t.name as tool,
  u.match_type,
  u.runtime_ms,
  u.success,
  u.similarity_score
FROM tool_usage u
JOIN tools t ON t.id = u.tool_id
ORDER BY u.created_at DESC
LIMIT 20;
```

### Tool Quality
```sql
SELECT
  name,
  reliability_score,
  success_count::float / NULLIF(use_count, 0) as success_rate
FROM tools
WHERE use_count > 0
ORDER BY success_rate DESC;
```

## Configuration

All settings in `.env`:

```env
# LLM Configuration
LLM_PROVIDER=anthropic           # or "openai"
LLM_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-...

# Similarity Thresholds
REUSE_THRESHOLD=0.85             # Higher = stricter matching
ADAPT_THRESHOLD=0.60             # Lower = more generation

# Sandbox Limits
SANDBOX_TIMEOUT_SECONDS=30       # Max execution time
SANDBOX_MEMORY_LIMIT=256m        # Memory per container
SANDBOX_CPU_LIMIT=0.5            # CPU cores

# Validation
MIN_RELIABILITY_SCORE=75         # Accept tools ≥ 75%
MAX_DEBUG_ITERATIONS=3           # Auto-fix attempts
```

## Security Features

### Row-Level Security (RLS)
- All tables have RLS enabled
- Public read access to tools
- Service role only for writes
- User-scoped session access

### Docker Sandbox
- Isolated containers per execution
- No network access (unless needed)
- Memory limits enforced
- CPU quotas applied
- Strict timeouts

### Code Validation
- Static analysis by Critic agent
- Checks for:
  - Proper function signature
  - Error handling
  - No hardcoded secrets
  - No shell injection risks
  - Reliability scoring (0-100)

## Performance Metrics

| Metric | Time | Notes |
|--------|------|-------|
| Semantic search | 20-50ms | pgvector query |
| Tool generation | 4-6s | LLM + validation |
| Code validation | 1-2s | Critic agent |
| Sandbox startup | 500-800ms | Docker container |
| **Tool reuse** | **100-300ms** | **Fast!** |
| Embedding creation | 50-100ms | sentence-transformers |

## Deployment

### Option 1: Docker Compose
```bash
docker-compose up -d
```

### Option 2: Heroku/Railway
```bash
git push heroku main
```

### Option 3: Kubernetes
See `DEPLOYMENT.md` for full guide.

## Seeding with Starter Tools

Pre-populate your registry:

```bash
python scripts/seed_registry.py
```

Adds 3 tools:
- `text_summarizer` - Summarizes text
- `json_formatter` - Formats JSON
- `email_validator` - Validates emails

## Running Analytics

```bash
python scripts/benchmark.py
```

Output:
```
REGISTRY STATISTICS
============================================================
  Total Tools: 15
  Total Uses: 342
  Success Rate: 94.74%
  Avg Reliability: 87/100

  Usage by Match Type:
    reuse: 256 executions
    generate: 86 executions

  Tool Details:
    json_formatter: 45 uses, 43 successes, 95% reliability
    text_summarizer: 38 uses, 36 successes, 92% reliability
    ...
```

## Troubleshooting

### Module Not Found
```bash
pip install -r requirements.txt
```

### Supabase Connection Failed
Check `.env` has:
- `SUPABASE_URL=https://...supabase.co`
- `SUPABASE_SERVICE_KEY=eyJ...`

### LLM API Error
Add your key to `.env`:
- `ANTHROPIC_API_KEY=sk-ant-...`
- or `OPENAI_API_KEY=sk-...`

### Tools Not Being Reused
Lower `REUSE_THRESHOLD` in `.env` for broader matching.

### Docker Issues
Tools fall back to local execution (less secure).

## Costs

### Supabase
- **Free**: 500MB storage, 2GB bandwidth
- **Pro**: $25/month
- Your usage: ~1KB per tool

### LLM API
- **Claude Sonnet**: $3 per 1M tokens
- **GPT-4**: $10 per 1M tokens
- Per tool: 500-1000 tokens → $0.01-0.02

### Estimation
- First 100 requests: ~$1-2
- Next 1000 requests: ~$0.50 (mostly reuse)
- Decreases over time!

## Project Structure

```
autonomous-ai-os/
├── core/               # Orchestration logic
│   ├── orchestrator.py
│   ├── intent_parser.py
│   ├── router.py
│   └── config.py
│
├── registry/           # Tool storage
│   ├── db.py (Supabase)
│   ├── embedder.py
│   ├── search.py (pgvector)
│   └── schemas.py
│
├── memory/             # Context management
│   ├── episodic.py
│   ├── working.py
│   └── schemas.py
│
├── agents/             # LLM agents
│   ├── generator.py
│   ├── critic.py
│   ├── debugger.py
│   └── adapter.py
│
├── execution/          # Sandbox
│   ├── sandbox.py (Docker)
│   └── loader.py
│
├── api/                # REST endpoints
│   ├── main.py (FastAPI)
│   └── routes/
│
├── tools/              # Generated code
├── scripts/            # Utilities
├── tests/              # Test suite
└── docs/               # Documentation
```

## Documentation

- `SETUP_GUIDE.md` - Step-by-step setup
- `QUICKSTART.md` - 3-minute guide
- `DEPLOYMENT.md` - Production deployment
- `PROJECT_SUMMARY.txt` - Complete overview

## Next Steps

1. ✅ Database ready (Supabase migrations applied)
2. 🔧 Add LLM API key to `.env`
3. 🚀 Start API: `uvicorn api.main:app --reload`
4. 📊 Send commands and watch it learn
5. 📈 Monitor reuse rate in Supabase
6. 🎯 Deploy when ready

## License

MIT

---

**Built with**: Supabase, pgvector, FastAPI, Docker, Claude/GPT

**The system learns. Every task makes it smarter. Start building!** 🚀
