# Final Setup Guide - Autonomous AI OS

## Project Status: ✅ READY TO RUN

Your autonomous AI system is fully built and configured. Here's how to start it:

## Step 1: Update Environment File

Your `.env` file already has Supabase credentials. Just add your LLM API key:

```bash
# Edit .env and add:
ANTHROPIC_API_KEY=sk-ant-your-key-here
# OR
OPENAI_API_KEY=sk-your-key-here
```

## Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- fastapi, uvicorn (API server)
- supabase (database client)
- sentence-transformers (embeddings)
- anthropic or openai (LLM integration)
- structlog (logging)
- docker (sandbox execution)

## Step 3: Database Already Setup ✅

Your Supabase database already has:
- ✅ `tools` table (tool metadata)
- ✅ `tool_embeddings` table (pgvector)
- ✅ `tool_usage` table (analytics)
- ✅ `sessions` table (tracking)
- ✅ `search_tools()` function (semantic search)
- ✅ RLS policies (security)

## Step 4: Start the API

**Option A: Direct Python**
```bash
uvicorn api.main:app --reload --port 8000 --reload-dir api --reload-dir core
```

**Option B: Docker**
```bash
docker-compose up --build
```

Server starts at: **http://localhost:8000**

## Step 5: Test It

### Basic Health Check
```bash
curl http://localhost:8000/health/
```

### Execute Your First Command
```bash
curl -X POST http://localhost:8000/task/ \
  -H "Content-Type: application/json" \
  -d '{
    "command": "Create a JSON formatter that pretty-prints JSON data"
  }'
```
# for direct LLM testing
```bash
curl -X POST http://localhost:8000/task/ \
  -H "Content-Type: application/json" \
  -d '{
    "command": "What is recursion ?"
  }'
```
Expected response:
```json
{
  "session_id": "abc-123...",
  "result": {"formatted": "{...}"},
  "tool_used": "json_formatter",
  "match_type": "generate",
  "runtime_ms": 4200,
  "success": true
}
```

### Execute Same Command Again (It Gets Faster!)
```bash
curl -X POST http://localhost:8000/task/ \
  -H "Content-Type: application/json" \
  -d '{
    "command": "Create a JSON formatter that pretty-prints JSON data"
  }'
```

Now returns in ~150ms with `"match_type": "reuse"`!

## Step 6: Monitor in Supabase

Go to your Supabase dashboard and run:

```sql
-- See all tools
SELECT name, description, reliability_score, use_count 
FROM tools 
ORDER BY use_count DESC;

-- See embeddings (pgvector)
SELECT tool_id, created_at 
FROM tool_embeddings;

-- See usage analytics
SELECT match_type, COUNT(*), AVG(runtime_ms)
FROM tool_usage
GROUP BY match_type;
```

## Step 7: Seed with Starter Tools (Optional)

```bash
python scripts/seed_registry.py
```

This adds 3 pre-built tools:
- `text_summarizer` - Summarizes text
- `json_formatter` - Formats JSON data
- `email_validator` - Validates email addresses

## Step 8: Run Analytics

```bash
python scripts/benchmark.py
```

Shows:
- Total tools in registry
- Reuse rate
- Average reliability score
- Usage by match type

## Project Structure

```
autonomous-ai-os/
├── core/
│   ├── orchestrator.py      # Main agent loop
│   ├── intent_parser.py     # Parse NL commands
│   ├── router.py            # Route: reuse/adapt/generate
│   └── config.py            # Config management
│
├── registry/
│   ├── db.py                # Supabase CRUD
│   ├── embedder.py          # Generate embeddings
│   ├── search.py            # pgvector search
│   └── schemas.py           # Data models
│
├── memory/
│   ├── episodic.py          # Session history
│   ├── working.py           # Request context
│   └── schemas.py           # Memory models
│
├── agents/
│   ├── generator.py         # LLM code generation
│   ├── critic.py            # Code validation
│   ├── debugger.py          # Fix errors
│   └── adapter.py           # Adapt tools
│
├── execution/
│   ├── sandbox.py           # Docker execution
│   └── loader.py            # Tool management
│
├── api/
│   ├── main.py              # FastAPI app
│   └── routes/
│       ├── tasks.py         # POST /task/
│       ├── tools.py         # Registry endpoints
│       └── health.py        # Health checks
│
└── scripts/
    ├── seed_registry.py     # Add starter tools
    └── benchmark.py         # Analytics
```

## How It Works

### Self-Improvement Cycle

```
First Request (Generate):
  └─> 4-6 seconds
     └─> LLM generates tool
        └─> Critic validates (score ≥ 75)
           └─> Code saved to disk
              └─> Embedding stored in pgvector
                 └─> Returns result

Second Request (Reuse):
  └─> 100-300ms
     └─> Semantic search finds tool
        └─> Load from disk
           └─> Execute
              └─> Return result

Self-Improvement:
  └─> Every tool stays in registry
     └─> Similar requests automatically reuse
        └─> System becomes faster with usage
```

### Semantic Search (pgvector)

When you send a command like:
```
"Format JSON with nice indentation"
```

The system:
1. Embeds your command: `[0.123, -0.456, ...]`
2. Calls `search_tools()` RPC function
3. Finds similar tools via cosine similarity
4. Returns best match with similarity score
5. If score ≥ 0.85 → REUSE (fast!)
6. If score 0.60-0.85 → ADAPT
7. If score < 0.60 → GENERATE

## Configuration Options

Edit `.env` to customize:

```env
# Similarity threshold for reusing tools
REUSE_THRESHOLD=0.85        # Higher = stricter matching

# Threshold for adapting vs generating
ADAPT_THRESHOLD=0.60         # Lower = more generation

# LLM model selection
LLM_MODEL=claude-sonnet-4-20250514  # or claude-opus

# Sandbox settings
SANDBOX_TIMEOUT_SECONDS=30   # Max tool runtime
SANDBOX_MEMORY_LIMIT=256m    # Memory per container

# Validation
MIN_RELIABILITY_SCORE=75     # Accept tools ≥ 75%
MAX_DEBUG_ITERATIONS=3       # Auto-fix attempts
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/task/` | Execute command (main) |
| GET | `/tools/` | List all tools |
| GET | `/tools/{name}` | Get tool details |
| DELETE | `/tools/{name}` | Deprecate tool |
| GET | `/health/` | API health check |
| GET | `/health/registry` | Registry status |

## Example Commands to Try

```bash
# Data processing
"Create a CSV parser that extracts specific columns"
"Build a JSON schema validator"

# Text processing
"Summarize long text into bullet points"
"Extract all email addresses from text"

# File operations
"Convert CSV to JSON format"
"Parse XML and extract specific tags"

# Web tasks
"Scrape a webpage and extract all links"
"Check if a website is up and responding"

# Math/calculation
"Calculate statistics (mean, median, mode)" 
"Convert between temperature units"
```

## Monitoring & Debugging

### Check Logs
```bash
# Structured logs show everything
# All operations log to console with structlog
uvicorn api.main:app --reload
```

### Query Supabase

```sql
-- Most used tools
SELECT name, use_count, success_count 
FROM tools 
ORDER BY use_count DESC 
LIMIT 10;

-- Recent executions
SELECT tool_used, match_type, runtime_ms, success 
FROM tool_usage 
ORDER BY created_at DESC 
LIMIT 20;

-- Reuse rate
SELECT 
  COUNT(*) FILTER (WHERE match_type = 'reuse') as reuse_count,
  COUNT(*) FILTER (WHERE match_type = 'generate') as gen_count,
  COUNT(*) as total
FROM tool_usage;
```

## Troubleshooting

### Error: "Module not found"

```bash
pip install -r requirements.txt
```

### Error: "Supabase connection failed"

Check `.env` file has:
- `SUPABASE_URL=https://...supabase.co`
- `SUPABASE_SERVICE_KEY=eyJ...`

### Error: "LLM API key invalid"

Add your key to `.env`:
- `ANTHROPIC_API_KEY=sk-ant-...`
- or `OPENAI_API_KEY=sk-...`

### Error: "Docker not available"

Tools run locally as fallback (less secure but works).

### Tools not being reused

Check similarity score in logs. If < 0.85, tools won't be reused. Lower `REUSE_THRESHOLD` if needed.

## Performance Expectations

| Metric | Time | Notes |
|--------|------|-------|
| Generate tool | 4-6s | LLM call + validation |
| Validate code | 1-2s | Critic agent |
| Save to DB | 50-100ms | Supabase insert |
| Semantic search | 20-50ms | pgvector query |
| Execute tool | 100-300ms | Docker sandbox |
| **Reuse tool** | **100-300ms** | **Fast!** |

## Costs

### Supabase (Database)
- **Free tier**: 500MB + 2GB bandwidth
- **Pro tier**: $25/month for more
- Your system uses minimal storage (~1KB per tool)

### LLM API
- **Claude Sonnet**: ~$3 per 1M input tokens
- **GPT-4**: ~$10 per 1M input tokens
- Average tool generation: 500-1000 tokens
- Cost per new tool: ~$0.01-0.02

### Estimation
- First 100 requests: ~$1-2 (mostly generation)
- Next 1000 requests: ~$0.50 (mostly reuse)
- System becomes more efficient over time!

## What Happens on Each Request

1. **User sends command**: "Format JSON nicely"
2. **Intent Parser**: Extracts structure → `{name: "json_formatter", category: "data_pipeline", ...}`
3. **Embedder**: Creates 384-dim vector from description
4. **pgvector Search**: Queries Supabase for similar tools
5. **Router Decision**:
   - If similarity ≥ 0.85: Reuse (100-300ms)
   - If similarity 0.60-0.85: Adapt (1-2s)
   - If similarity < 0.60: Generate (4-6s)
6. **Generate** (if needed):
   - LLM writes Python code
   - Critic validates (checks structure, security, error handling)
   - Score 0-100 (must be ≥ 75)
   - If failed, up to 3 auto-fix iterations
7. **Save**: Code to disk, metadata to Supabase, embedding to pgvector
8. **Execute**: Run in Docker sandbox with limits
9. **Persist**: Record success/failure, runtime, similarity to Supabase
10. **Return**: Result to user

## Self-Improvement Examples

### Week 1 (Learning)
- 100 requests total
- 80% generation, 20% reuse
- Avg latency: 3 seconds
- Tools in registry: 15-20

### Week 2 (Caching)
- 200 requests total
- 50% generation, 50% reuse
- Avg latency: 1.5 seconds
- Tools in registry: 30-40

### Week 4 (Mature)
- 500 requests total
- 20% generation, 80% reuse
- Avg latency: 300ms
- Tools in registry: 50-70

## Next Steps

1. **Start the API** and send test commands
2. **Watch the reuse rate** increase in Supabase
3. **Adjust thresholds** based on your needs
4. **Add authentication** with Supabase Auth
5. **Deploy to production** (see DEPLOYMENT.md)

---

**Your autonomous AI is ready! Start coding and watch it learn.** 🚀
