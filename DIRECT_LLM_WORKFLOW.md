# Direct LLM Workflow - Smart Task Routing

## Overview

The system now intelligently routes tasks based on complexity:

1. **Simple tasks** → Execute directly with LLM (fast, cheap)
2. **Complex tasks** → Generate and cache tools (reusable)

---

## How It Works

### Decision Flow

```
User Command
    ↓
[Intent Parser] → Extract task structure
    ↓
[Complexity Evaluator] → Analyze task
    ↓
┌─────────────────────────────────────┐
│  Complexity Decision:               │
│                                     │
│  SIMPLE → direct_llm (1-2s)       │
│  • Q&A                               │
│  • Text transformation              │
│  • Analysis                         │
│  • Summarization                    │
│  • Explanations                     │
│                                     │
│  COMPLEX → tool (4-6s → reuse)    │
│  • File operations                  │
│  • API integrations                 │
│  • Data pipelines                   │
│  • Repeated tasks                   │
│  • Requires code execution          │
└─────────────────────────────────────┘
    ↓
Execute (Direct LLM or Tool)
    ↓
Store Result
    ↓
Return to User
```

---

## Examples

### Simple Tasks → Direct LLM

```bash
# Q&A
"What is the capital of France?"
→ Complexity: simple
→ Match type: direct_llm
→ Time: 1.2s
→ Cost: $0.0001

# Text Analysis
"Summarize this article in 3 bullet points"
→ Complexity: simple
→ Match type: direct_llm
→ Time: 2.1s

# Explanation
"Explain how neural networks work"
→ Complexity: simple
→ Match type: direct_llm
→ Time: 1.8s
```

### Complex Tasks → Tool Generation

```bash
# File Operations
"Create a CSV parser that extracts specific columns"
→ Complexity: moderate
→ Match type: generate
→ Time: 4.2s
→ Next time: 0.15s (reuse)

# Data Pipeline
"Build a JSON to XML converter with validation"
→ Complexity: complex
→ Match type: generate
→ Time: 5.1s

# API Integration
"Create a tool that fetches weather data from API"
→ Complexity: complex
→ Match type: generate
```

---

## Complexity Evaluation

The system evaluates tasks on multiple factors:

| Factor | Simple (Direct LLM) | Complex (Tool) |
|--------|-------------------|---------------|
| **Execution** | One-time answer | Repeated execution |
| **State** | No state needed | Requires variables |
| **Files** | No file I/O | Reads/writes files |
| **APIs** | No external APIs | API calls needed |
| **Code** | No code execution | Requires running code |
| **Reuse** | Unlikely to repeat | Will be reused |

### Complexity Levels

1. **Simple** → Direct LLM
   - Q&A
   - Text transformation
   - Analysis and summarization
   - Explanations
   - Quick calculations

2. **Moderate** → Tool (usually)
   - Simple data processing
   - One-time file operations
   - Basic transformations

3. **Complex** → Tool (always)
   - Data pipelines
   - API integrations
   - Complex transformations
   - Multi-step operations

---

## Response Format

### Direct LLM Response

```json
{
  "session_id": "abc-123",
  "result": "Paris is the capital of France...",
  "tool_used": "direct_llm",
  "tool_version": "n/a",
  "match_type": "direct_llm",
  "complexity": "simple",
  "reasoning": "Simple Q&A task, no tool needed",
  "runtime_ms": 1200,
  "success": true
}
```

### Tool Response

```json
{
  "session_id": "abc-123",
  "result": {"parsed": [...]},
  "tool_used": "csv_parser",
  "tool_version": "1.0.0",
  "match_type": "reuse",
  "complexity": "complex",
  "runtime_ms": 150,
  "success": true
}
```

---

## Cost Comparison

| Task Type | Direct LLM | Tool (First) | Tool (Reuse) |
|-----------|-----------|--------------|--------------|
| Simple Q&A | $0.0001 | $0.02 | $0 |
| Text Analysis | $0.0005 | $0.02 | $0 |
| Data Pipeline | N/A | $0.02 | $0 |
| API Integration | N/A | $0.02 | $0 |

**Direct LLM is 10-200x cheaper for simple tasks!**

---

## Configuration

### Enable/Disable Direct LLM

```env
# .env
ENABLE_DIRECT_LLM=true   # Enable smart routing (default)
ENABLE_DIRECT_LLM=false  # Always use tools
```

### When to Disable

Disable direct LLM if:
- You want all tasks to create reusable tools
- Building a tool library for future use
- Training the system on diverse tasks

### When to Enable

Enable direct LLM for:
- Mixed usage (simple Q&A + complex tools)
- Cost savings on simple tasks
- Faster responses for simple queries

---

## Use Cases

### Use Direct LLM For

1. **Customer Support Chatbot**
   - Q&A sessions
   - Explaining concepts
   - Quick answers

2. **Documentation Assistant**
   - Summarizing text
   - Explaining code
   - Writing documentation

3. **Analysis Tasks**
   - Sentiment analysis
   - Text classification
   - Quick insights

### Use Tools For

1. **Data Processing**
   - CSV/JSON parsing
   - Format conversion
   - Data validation

2. **Automation**
   - Report generation
   - File processing
   - Scheduled tasks

3. **Integrations**
   - API wrappers
   - Database operations
   - External services

---

## Technical Implementation

### New Agents

1. **ComplexityEvaluator**
   - Analyzes task complexity
   - Recommends direct_llm or tool
   - Factors: code execution, file I/O, reuse potential

2. **DirectLLMExecutor**
   - Executes simple tasks directly
   - No tool generation
   - Optimized prompts per category

### Modified Orchestrator

```python
async def run(user_input, session_id):
    # Parse intent
    intent = await parse_intent(user_input)

    # Evaluate complexity
    complexity = await complexity_evaluator.evaluate(user_input, intent)

    # Route based on recommendation
    if complexity["recommendation"] == "direct_llm":
        # Execute directly
        result = await direct_llm.execute(user_input, intent)
        match_type = "direct_llm"
    else:
        # Tool path (existing logic)
        result = await tool_execution_flow(...)

    return {
        "result": result,
        "match_type": match_type,
        "complexity": complexity["complexity"]
    }
```

---

## Benefits

### 1. Cost Savings
- Simple tasks: 10-200x cheaper
- No unnecessary tool generation
- Direct LLM responses

### 2. Speed
- Simple tasks: 1-2 seconds (vs 4-6s)
- No validation overhead
- No tool storage

### 3. Flexibility
- Best of both worlds
- Tools for complex tasks
- Direct LLM for simple tasks

### 4. Efficiency
- No tool bloat
- Registry stays focused
- Better organization

---

## Monitoring

### Query Statistics

```sql
-- Direct LLM vs Tool usage
SELECT
  match_type,
  COUNT(*) as executions,
  AVG(runtime_ms) as avg_ms,
  SUM(CASE WHEN success THEN 1 ELSE 0 END)::float / COUNT(*) as success_rate
FROM tool_usage
GROUP BY match_type;
```

### Expected Results

```
match_type   | executions | avg_ms | success_rate
-------------|-----------|--------|--------------
direct_llm   | 500       | 1500   | 0.98
generate     | 80        | 4500   | 0.92
reuse        | 420       | 180    | 0.99
```

---

## Example Session

```bash
# Simple task → Direct LLM
curl -X POST http://localhost:8000/task/ \
  -d '{"command": "What is machine learning?"}'

Response:
{
  "match_type": "direct_llm",
  "complexity": "simple",
  "runtime_ms": 1400
}

# Complex task → Tool
curl -X POST http://localhost:8000/task/ \
  -d '{"command": "Create a CSV parser"}'

Response:
{
  "match_type": "generate",
  "complexity": "moderate",
  "runtime_ms": 4200
}

# Same CSV task (reuse)
curl -X POST http://localhost:8000/task/ \
  -d '{"command": "Parse CSV files"}'

Response:
{
  "match_type": "reuse",
  "complexity": "moderate",
  "runtime_ms": 150
}
```

---

## Summary

The system now intelligently routes tasks:

- **Simple tasks** → Direct LLM (fast, cheap)
- **Complex tasks** → Tools (reusable, powerful)

This gives you the best of both worlds:
- Speed for simple queries
- Persistence for complex operations
- Cost optimization across all tasks

---

**Enable with:** `ENABLE_DIRECT_LLM=true` in `.env`
