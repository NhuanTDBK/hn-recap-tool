# Activity 2.5: LLM Client Integration with OpenAI Agents SDK

## Overview
Implement a unified LLM client using OpenAI Agents Python SDK for building autonomous agents with Langfuse observability and per-user token tracking. Designed for both simple summarization and future conversational bot interactions.

## Prerequisites
- Activity 2.1: Basic summarization (use case for agents)
- Activity 2.3: Prompt engineering (agent instructions)
- Phase 3: Telegram bot (future Q&A agent)

## Objectives
1. Integrate OpenAI Agents SDK for agent-based architecture
2. Set up Langfuse for observability and tracing
3. Track token usage per user for pricing
4. Create summarization agent for post processing
5. Design agent architecture for future bot interactions
6. Store usage metrics in database

---

## Technical Details

### Why OpenAI Agents SDK?

**Standard OpenAI SDK limitations:**
- ❌ No built-in multi-turn conversations
- ❌ Manual tool/function calling management
- ❌ No agent orchestration patterns
- ❌ Manual context management

**OpenAI Agents SDK advantages:**
- ✅ **Agent abstraction** - LLM + instructions + tools in one unit
- ✅ **Multi-turn conversations** - Session management built-in
- ✅ **Tool calling** - Automatic tool execution and response handling
- ✅ **Multi-agent patterns** - Agent handoffs and orchestration
- ✅ **Context management** - Dependency injection for state
- ✅ **Structured outputs** - Pydantic models for responses

**Perfect for:**
- Summarization agent (Phase 2)
- Q&A agent for Telegram bot (Phase 3)
- Discussion agent (Phase 5)
- Memory-enhanced agent (Phase 6)

---

## Architecture Design

### Agent Types

**1. Summarization Agent (Current)**
- Purpose: Generate summaries from markdown content
- Tools: None (simple text generation)
- Input: Markdown content
- Output: 2-3 sentence summary

**2. Q&A Agent (Phase 3 - Telegram Bot)**
- Purpose: Answer user questions about posts
- Tools: `search_posts`, `get_summary`, `get_post_content`
- Input: User question
- Output: Structured answer with sources

**3. Discussion Agent (Phase 5)**
- Purpose: Facilitate discussions about posts
- Tools: `get_comments`, `search_similar_posts`
- Input: User message in conversation
- Output: Conversational response

**4. Memory Agent (Phase 6)**
- Purpose: Personalized interactions with user memory
- Tools: `get_user_preferences`, `get_user_history`, `update_preferences`
- Input: User request
- Output: Personalized response

### Component Structure

```
backend/app/infrastructure/agents/
├── base.py                    # Base agent with Langfuse tracking
├── summarization_agent.py     # Summarization agent
├── qa_agent.py                # Q&A agent (future)
├── tools/                     # Agent tools
│   ├── __init__.py
│   ├── search_tools.py        # Search posts/summaries
│   └── database_tools.py      # Database queries
├── config.py                  # Agent configuration
└── token_tracker.py           # Per-user token tracking
```

---

## OpenAI Agents SDK Integration

### Installation

```bash
pip install openai-agents
pip install langfuse
pip install pydantic
```

### Basic Agent Example

```python
from agents import Agent, function_tool

# Define a tool (future use)
@function_tool
def search_posts(query: str) -> list[dict]:
    """Search HackerNews posts by keyword"""
    # Implementation
    return posts

# Create agent
agent = Agent(
    name="Summarization Agent",
    instructions="You are an expert at summarizing technical articles...",
    model="gpt-4o-mini",
    tools=[]  # No tools for summarization
)

# Run agent
result = agent.run("Summarize this article: ...")
print(result.output)
```

### Structured Output with Pydantic

```python
from pydantic import BaseModel
from agents import Agent

class Summary(BaseModel):
    summary: str
    key_points: list[str]
    technical_level: str  # "beginner", "intermediate", "advanced"

agent = Agent(
    name="Summarization Agent",
    instructions="...",
    model="gpt-4o-mini",
    output_type=Summary  # Structured output
)

result = agent.run("Summarize: ...")
summary: Summary = result.output  # Typed Pydantic object
```

---

## Langfuse Integration with Agents

### Langfuse Setup

```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    host=settings.LANGFUSE_HOST
)
```

### Agent Lifecycle Hooks

**Track agent execution with Langfuse:**

```python
from agents import Agent, lifecycle

class LangfuseObserver:
    """Langfuse observer for agent lifecycle"""

    def __init__(self, user_id: int = None):
        self.user_id = user_id
        self.trace = None
        self.generation = None

    @lifecycle.on_agent_start
    def on_start(self, agent: Agent, input: str):
        """Called when agent starts"""
        self.trace = langfuse.trace(
            name=f"agent_{agent.name}",
            user_id=str(self.user_id) if self.user_id else None,
            metadata={"agent_name": agent.name}
        )
        self.generation = self.trace.generation(
            name="agent_execution",
            model=agent.model,
            input=input
        )

    @lifecycle.on_agent_end
    def on_end(self, agent: Agent, result: any):
        """Called when agent completes"""
        if self.generation:
            self.generation.end(
                output=str(result.output),
                usage={
                    "input_tokens": result.usage.input_tokens,
                    "output_tokens": result.usage.output_tokens,
                    "total_tokens": result.usage.total_tokens
                }
            )

    @lifecycle.on_tool_start
    def on_tool_start(self, tool_name: str, args: dict):
        """Called when tool is invoked"""
        if self.trace:
            self.trace.span(
                name=f"tool_{tool_name}",
                input=args
            )

    @lifecycle.on_tool_end
    def on_tool_end(self, tool_name: str, result: any):
        """Called when tool completes"""
        pass
```

---

## Token Tracking Database Schema

```sql
-- Per-user daily token usage
CREATE TABLE user_token_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    date DATE NOT NULL,
    model VARCHAR(50) NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6) DEFAULT 0,
    request_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, date, model)
);

-- Individual agent calls
CREATE TABLE agent_calls (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    trace_id VARCHAR(255),        -- Langfuse trace ID
    agent_name VARCHAR(100) NOT NULL,
    operation VARCHAR(100),       -- "summarize", "answer_question"
    model VARCHAR(50) NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd DECIMAL(10, 6),
    latency_ms INTEGER,
    status VARCHAR(20),           -- "success", "error"
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_user_token_usage_user_date ON user_token_usage(user_id, date);
CREATE INDEX idx_agent_calls_user ON agent_calls(user_id, created_at);
CREATE INDEX idx_agent_calls_trace ON agent_calls(trace_id);
```

---

## Implementation: Base Agent with Tracking

### Configuration

```python
# backend/app/infrastructure/agents/config.py

from pydantic_settings import BaseSettings

class AgentSettings(BaseSettings):
    # OpenAI
    OPENAI_API_KEY: str
    DEFAULT_MODEL: str = "gpt-4o-mini"
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_MAX_TOKENS: int = 500

    # Langfuse
    LANGFUSE_ENABLED: bool = True
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # Rate limiting
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0

    class Config:
        env_file = ".env"

settings = AgentSettings()
```

### Token Tracker

```python
# backend/app/infrastructure/agents/token_tracker.py

from datetime import date, datetime
from decimal import Decimal

# Pricing per 1M tokens (as of 2025)
PRICING = {
    "gpt-4o-mini": {"input": 0.150, "output": 0.600},
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-realtime-preview": {"input": 5.00, "output": 20.00},
}

class TokenTracker:
    """Track token usage per user"""

    def __init__(self, db_session):
        self.db = db_session

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD"""
        if model not in PRICING:
            return 0.0

        input_cost = (input_tokens / 1_000_000) * PRICING[model]["input"]
        output_cost = (output_tokens / 1_000_000) * PRICING[model]["output"]

        return input_cost + output_cost

    def track_usage(
        self,
        user_id: int,
        agent_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        trace_id: str = None,
        operation: str = None,
        latency_ms: int = None,
        status: str = "success",
        error_message: str = None
    ):
        """Track agent usage"""
        today = date.today()
        total_tokens = input_tokens + output_tokens
        cost_usd = self.calculate_cost(model, input_tokens, output_tokens)

        # Update daily aggregate
        usage = self.db.query(UserTokenUsage).filter_by(
            user_id=user_id,
            date=today,
            model=model
        ).first()

        if usage:
            usage.input_tokens += input_tokens
            usage.output_tokens += output_tokens
            usage.total_tokens += total_tokens
            usage.cost_usd += Decimal(str(cost_usd))
            usage.request_count += 1
        else:
            usage = UserTokenUsage(
                user_id=user_id,
                date=today,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=Decimal(str(cost_usd)),
                request_count=1
            )
            self.db.add(usage)

        # Record individual call
        call = AgentCall(
            user_id=user_id,
            trace_id=trace_id,
            agent_name=agent_name,
            operation=operation,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=Decimal(str(cost_usd)),
            latency_ms=latency_ms,
            status=status,
            error_message=error_message
        )
        self.db.add(call)
        self.db.commit()

    def get_user_usage(
        self,
        user_id: int,
        start_date: date = None,
        end_date: date = None
    ) -> dict:
        """Get token usage summary for a user"""
        query = self.db.query(UserTokenUsage).filter_by(user_id=user_id)

        if start_date:
            query = query.filter(UserTokenUsage.date >= start_date)
        if end_date:
            query = query.filter(UserTokenUsage.date <= end_date)

        usage = query.all()

        return {
            "total_tokens": sum(u.total_tokens for u in usage),
            "total_cost_usd": float(sum(u.cost_usd for u in usage)),
            "requests": sum(u.request_count for u in usage),
            "by_model": self._group_by_model(usage)
        }

    def _group_by_model(self, usage: list) -> dict:
        """Group usage by model"""
        models = {}
        for u in usage:
            if u.model not in models:
                models[u.model] = {"tokens": 0, "cost": 0.0, "requests": 0}
            models[u.model]["tokens"] += u.total_tokens
            models[u.model]["cost"] += float(u.cost_usd)
            models[u.model]["requests"] += u.request_count
        return models
```

### Base Agent Wrapper

```python
# backend/app/infrastructure/agents/base.py

from agents import Agent
from langfuse import Langfuse
from typing import Optional, Any
import time

class TrackedAgent:
    """Agent wrapper with Langfuse tracking and token counting"""

    def __init__(
        self,
        agent: Agent,
        user_id: int = None,
        db_session = None,
        operation: str = None
    ):
        self.agent = agent
        self.user_id = user_id
        self.operation = operation
        self.db = db_session

        # Initialize tracking
        self.langfuse = None
        if settings.LANGFUSE_ENABLED:
            self.langfuse = Langfuse(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST
            )

        self.token_tracker = TokenTracker(db_session) if db_session else None

    def run(self, input: str, metadata: dict = None) -> Any:
        """Run agent with tracking"""
        trace = None
        generation = None
        start_time = time.time()

        try:
            # Start Langfuse trace
            if self.langfuse:
                trace = self.langfuse.trace(
                    name=f"agent_{self.agent.name}",
                    user_id=str(self.user_id) if self.user_id else None,
                    metadata={
                        **(metadata or {}),
                        "operation": self.operation,
                        "agent_name": self.agent.name
                    }
                )
                generation = trace.generation(
                    name="agent_execution",
                    model=self.agent.model,
                    input=input
                )

            # Run agent
            result = self.agent.run(input)

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract usage
            input_tokens = getattr(result.usage, 'input_tokens', 0)
            output_tokens = getattr(result.usage, 'output_tokens', 0)

            # Update Langfuse
            if generation:
                generation.end(
                    output=str(result.output),
                    usage={
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens
                    }
                )

            # Track tokens
            if self.token_tracker and self.user_id:
                self.token_tracker.track_usage(
                    user_id=self.user_id,
                    agent_name=self.agent.name,
                    model=self.agent.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    trace_id=trace.id if trace else None,
                    operation=self.operation,
                    latency_ms=latency_ms,
                    status="success"
                )

            return result

        except Exception as e:
            # Track error
            if self.token_tracker and self.user_id:
                self.token_tracker.track_usage(
                    user_id=self.user_id,
                    agent_name=self.agent.name,
                    model=self.agent.model,
                    input_tokens=0,
                    output_tokens=0,
                    trace_id=trace.id if trace else None,
                    operation=self.operation,
                    status="error",
                    error_message=str(e)
                )
            raise
```

---

## Implementation: Summarization Agent

```python
# backend/app/infrastructure/agents/summarization_agent.py

from agents import Agent
from pydantic import BaseModel
from .base import TrackedAgent
from .config import settings

class SummaryOutput(BaseModel):
    """Structured summary output"""
    summary: str
    key_points: list[str] = []
    technical_level: str = "intermediate"  # beginner, intermediate, advanced

def create_summarization_agent(
    prompt_type: str = "basic",
    use_structured_output: bool = False
) -> Agent:
    """
    Create summarization agent

    Args:
        prompt_type: Type of prompt (basic, technical, business, etc.)
        use_structured_output: Return structured output (Pydantic)

    Returns:
        Configured Agent
    """
    # Load instructions from prompt file
    instructions = load_prompt(f"{prompt_type}.md")

    # Create agent
    agent = Agent(
        name="SummarizationAgent",
        instructions=instructions,
        model=settings.DEFAULT_MODEL,
        output_type=SummaryOutput if use_structured_output else None
    )

    return agent

def summarize_post(
    markdown_content: str,
    user_id: int = None,
    prompt_type: str = "basic",
    db_session = None
) -> str:
    """
    Summarize a post using agent

    Args:
        markdown_content: Post content in markdown
        user_id: User ID for token tracking
        prompt_type: Prompt variant to use
        db_session: Database session for tracking

    Returns:
        Summary text
    """
    # Create agent
    agent = create_summarization_agent(prompt_type=prompt_type)

    # Wrap with tracking
    tracked_agent = TrackedAgent(
        agent=agent,
        user_id=user_id,
        db_session=db_session,
        operation="summarize_post"
    )

    # Run agent
    result = tracked_agent.run(
        input=markdown_content,
        metadata={"prompt_type": prompt_type}
    )

    # Extract summary
    if isinstance(result.output, SummaryOutput):
        return result.output.summary
    else:
        return str(result.output)
```

---

## Future: Q&A Agent with Tools

```python
# backend/app/infrastructure/agents/qa_agent.py (Future - Phase 3)

from agents import Agent, function_tool

@function_tool
def search_posts(query: str, limit: int = 5) -> list[dict]:
    """Search HackerNews posts by keyword"""
    # Query database
    posts = db.query(Post).filter(
        Post.title.ilike(f"%{query}%")
    ).limit(limit).all()

    return [
        {"hn_id": p.hn_id, "title": p.title, "score": p.score}
        for p in posts
    ]

@function_tool
def get_summary(hn_id: int) -> str:
    """Get summary for a specific post"""
    summary = db.query(Summary).filter_by(hn_id=hn_id).first()
    return summary.summary if summary else "No summary available"

def create_qa_agent() -> Agent:
    """Create Q&A agent for Telegram bot"""
    agent = Agent(
        name="QAAgent",
        instructions="""
        You are a helpful assistant that answers questions about HackerNews posts.
        Use the search_posts tool to find relevant posts.
        Use the get_summary tool to get summaries.
        Always cite your sources with HN IDs.
        """,
        model=settings.DEFAULT_MODEL,
        tools=[search_posts, get_summary]
    )

    return agent

# Usage in Telegram bot:
# agent = create_qa_agent()
# result = agent.run("What are the latest posts about AI?")
# send_telegram_message(result.output)
```

---

## Usage Examples

### Basic Summarization

```python
from backend.app.infrastructure.agents.summarization_agent import summarize_post

# Get markdown content
markdown = storage.get_markdown(hn_id=40000000)

# Generate summary with tracking
summary = summarize_post(
    markdown_content=markdown,
    user_id=123,  # Track tokens for this user
    prompt_type="basic",
    db_session=db
)

# Store in database
summary_record = Summary(
    hn_id=40000000,
    summary=summary,
    model="gpt-4o-mini",
    prompt_type="basic"
)
db.add(summary_record)
db.commit()
```

### Check User Usage

```python
from backend.app.infrastructure.agents.token_tracker import TokenTracker

tracker = TokenTracker(db)

# Get usage for current month
usage = tracker.get_user_usage(
    user_id=123,
    start_date=date(2025, 2, 1),
    end_date=date(2025, 2, 28)
)

print(f"Total tokens: {usage['total_tokens']:,}")
print(f"Total cost: ${usage['total_cost_usd']:.4f}")
print(f"Requests: {usage['requests']}")

# By model
for model, stats in usage['by_model'].items():
    print(f"\n{model}:")
    print(f"  Tokens: {stats['tokens']:,}")
    print(f"  Cost: ${stats['cost']:.4f}")
    print(f"  Requests: {stats['requests']}")
```

---

## Testing & Validation

### Unit Tests

**Location:** `tests/infrastructure/agents/test_summarization_agent.py`

**Test Cases:**
1. **test_create_agent**
   - Create agent with different prompt types
   - Verify configuration

2. **test_summarize_post**
   - Mock agent response
   - Verify summary generated

3. **test_token_tracking**
   - Generate summary with user_id
   - Query database
   - Verify tokens tracked

4. **test_cost_calculation**
   - Different models
   - Verify pricing accurate

5. **test_structured_output**
   - Use structured output mode
   - Verify Pydantic model returned

### Integration Tests

**Location:** `tests/integration/test_agents_e2e.py`

**Test Scenarios:**
1. End-to-end summarization with real OpenAI API
2. Langfuse trace verification
3. Multiple users, separate token tracking
4. Error handling and retry logic

### Manual Testing

```bash
# Test summarization agent
python scripts/test_agent.py --hn-id 40000000 --prompt-type basic

# Check Langfuse dashboard
# Visit: https://cloud.langfuse.com
# Filter by user_id, see traces

# Query token usage
python scripts/check_usage.py --user-id 123
```

---

## Acceptance Criteria

- [ ] OpenAI Agents SDK installed and configured
- [ ] Base `TrackedAgent` wrapper implemented
- [ ] Summarization agent created with prompt loading
- [ ] Langfuse integration working (traces visible)
- [ ] Token tracking tables created (user_token_usage, agent_calls)
- [ ] `TokenTracker` class implemented with pricing
- [ ] Per-user token counting working
- [ ] Cost calculation accurate for gpt-4o-mini
- [ ] Structured output support (Pydantic)
- [ ] Error handling and retry logic
- [ ] Configuration via environment variables
- [ ] Unit tests passing (>90% coverage)
- [ ] Integration tests with real API
- [ ] Langfuse dashboard shows agent traces
- [ ] Documentation of agent usage patterns

**Verification:**
- Generate 10 summaries with different users
- Check Langfuse dashboard shows all agent executions
- Query user_token_usage table, verify counts match
- Calculate expected cost, compare to tracked cost (±1%)

---

## Related Activities

**Upstream Dependencies:**
- Activity 2.1: Basic summarization (use case)
- Activity 2.3: Prompt engineering (agent instructions)

**Downstream Dependencies:**
- Activity 2.1: Uses summarization agent
- Phase 3: Telegram bot uses Q&A agent
- Phase 5: Discussion agent for conversations
- Phase 6: Memory-enhanced agents

---

## Notes & Assumptions

### Design Decisions

**Why OpenAI Agents SDK over standard SDK?**
- Future Telegram bot needs conversational agents
- Tool calling for database queries
- Multi-agent patterns for complex flows
- Better abstraction for autonomous behavior

**Why Langfuse?**
- Best-in-class LLM observability
- Free tier sufficient (50K traces/month)
- Native support for agents and tools
- Great debugging dashboard

**Why per-user token tracking?**
- Enable usage-based pricing
- Detect abuse/high usage users
- Budget limits per user
- Cost attribution for billing

**Why database storage?**
- Langfuse shows traces (debugging)
- Database for aggregates (billing)
- Quick queries for spending limits
- Historical analysis

### Future Considerations

**Multi-agent orchestration:**
- Manager agent routes to specialist agents
- Summarization agent → Q&A agent → Discussion agent
- Handoff patterns for complex flows

**Tool library expansion:**
- Database query tools
- Search tools (posts, summaries, comments)
- Memory tools (user preferences, history)
- External API tools (fetch URLs, search web)

**Agent fine-tuning:**
- Custom fine-tuned models for summarization
- Domain-specific agents
- Cost optimization with smaller models

**Voice agents:**
- Realtime API for voice interactions
- Voice-based Q&A in Telegram
- Lower latency for conversations

---

## Implementation Checklist

**Setup:**
- [ ] Install dependencies (openai-agents, langfuse)
- [ ] Set up environment variables
- [ ] Create database tables (migrations)

**Core Implementation:**
- [ ] Create agent config
- [ ] Implement `TokenTracker` class
- [ ] Implement `TrackedAgent` wrapper
- [ ] Create summarization agent
- [ ] Integrate with prompt loader
- [ ] Add Langfuse lifecycle hooks

**Testing:**
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Test with real OpenAI API
- [ ] Verify Langfuse traces

**Documentation:**
- [ ] Document agent usage
- [ ] Document token tracking
- [ ] Document pricing calculation
- [ ] Update Activity 2.1 to use agents

---

**Estimated Effort:** 6-8 hours
**Priority:** High (foundational for all LLM features)
**Status:** Ready to implement

---

**Last Updated:** 2025-02-13
