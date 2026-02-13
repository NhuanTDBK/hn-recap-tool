# Memory Storage API & Tool Calling Design

## Overview

The memory system should expose operations via **LLM tool calling**, allowing agents to:
1. Read existing memory to avoid duplicates and understand context
2. Search memory via BM25 to find related past entries
3. Write/update/delete memory entries atomically
4. Get memory summaries for injection into prompts

This makes memory operations explicit, logged, and auditable. The MemoryExtractionAgent and DiscussionAgent can reason about what they're storing and why.

---

## Memory Storage API (Tool Definitions)

### 1. `write_memory` — Add or update a memory entry

```python
{
    "type": "function",
    "function": {
        "name": "write_memory",
        "description": "Write or update a memory entry about the user. Durable entries go to MEMORY.md, ephemeral to daily notes.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Short identifier for the memory (e.g., 'role', 'interested_in_rust', 'opinion_on_crypto')"
                },
                "value": {
                    "type": "string",
                    "description": "The memory content (natural language, no code)"
                },
                "category": {
                    "type": "string",
                    "enum": ["preference", "work_context", "personal_context", "reading_history"],
                    "description": "Memory category"
                },
                "durability": {
                    "type": "string",
                    "enum": ["durable", "daily"],
                    "description": "durable = MEMORY.md (persists indefinitely), daily = memory/YYYY-MM-DD.md (auto-expires in 90 days)"
                },
                "source": {
                    "type": "string",
                    "description": "Where this memory came from (e.g., 'discussion:uuid', 'explicit_mention', 'batch_extraction')"
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Confidence score (0-1). Only writes to MEMORY.md if >= 0.7"
                }
            },
            "required": ["key", "value", "category", "durability"]
        }
    }
}
```

### 2. `read_memory` — Get all memory entries in a category

```python
{
    "type": "function",
    "function": {
        "name": "read_memory",
        "description": "Read all memory entries in a specific category to understand user context.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["preference", "work_context", "personal_context", "reading_history"],
                    "description": "Memory category to read"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of entries to return (default: 20)",
                    "default": 20
                }
            },
            "required": ["category"]
        }
    }
}
```

### 3. `search_memory` — BM25 search

```python
{
    "type": "function",
    "function": {
        "name": "search_memory",
        "description": "Search user memory using full-text BM25 search. Useful for finding related past context.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'kubernetes', 'python async', 'distributed systems')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of results (default: 5)",
                    "default": 5
                },
                "category": {
                    "type": "string",
                    "enum": ["preference", "work_context", "personal_context", "reading_history", "all"],
                    "description": "Filter by category or search all (default: all)",
                    "default": "all"
                }
            },
            "required": ["query"]
        }
    }
}
```

### 4. `get_memory_context` — Formatted context for injection

```python
{
    "type": "function",
    "function": {
        "name": "get_memory_context",
        "description": "Get formatted memory context string for injection into agent prompts (~1500 tokens).",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Article topic or discussion topic (e.g., 'PostgreSQL 18'). Used for BM25 search."
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Max tokens in returned context (default: 1500)",
                    "default": 1500
                }
            },
            "required": ["topic"]
        }
    }
}
```

### 5. `update_memory` — Update an existing entry

```python
{
    "type": "function",
    "function": {
        "name": "update_memory",
        "description": "Update an existing memory entry (modify value, change category, etc.)",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The memory key to update"
                },
                "value": {
                    "type": "string",
                    "description": "New value"
                },
                "category": {
                    "type": "string",
                    "enum": ["preference", "work_context", "personal_context", "reading_history"],
                    "description": "Category (optional, keeps current if not specified)"
                }
            },
            "required": ["key", "value"]
        }
    }
}
```

### 6. `delete_memory` — Remove an entry

```python
{
    "type": "function",
    "function": {
        "name": "delete_memory",
        "description": "Delete a memory entry (e.g., user says they forgot something or want to remove a belief).",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The memory key to delete"
                }
            },
            "required": ["key"]
        }
    }
}
```

---

## MemoryExtractionAgent Implementation

The daily batch extraction job uses tool calling with prefilled system prompt:

```python
MEMORY_EXTRACTION_SYSTEM_PROMPT = """
You are a memory extraction agent for HN Pal. Your job is to read a user's interactions
from the past 24 hours and extract meaningful knowledge about the user.

RULES:
1. Search existing memory FIRST using `search_memory()` before writing new entries.
   - Avoid duplicates
   - Merge related facts instead of creating new entries
   - If an entry exists, use `update_memory()` instead of `write_memory()`

2. Only extract genuinely meaningful information:
   - User preferences: communication style, topic interests, digest format
   - Work context: role, company, projects, tech stack, goals
   - Personal context: opinions, hobbies, learning goals
   - Reading history: what they read, reactions, discussions

3. Confidence scoring:
   - Clear facts from explicit mentions: 0.9-1.0
   - Patterns from behavior: 0.7-0.9
   - Weak signals: 0.5-0.7
   - Don't write entries with confidence < 0.7 to durable memory

4. Use natural language only:
   - Store opinions, preferences, and context
   - Never store code snippets or technical implementations
   - Be specific: "interested in Rust async runtime design" > "likes Rust"

5. Durability decisions:
   - Durable: user role, projects, long-term goals, confirmed opinions
   - Daily: reading patterns, temporary observations, day-specific context

AVAILABLE TOOLS:
- search_memory() — find related past entries before writing
- write_memory() — add new durable or daily memory
- update_memory() — modify existing entries
- delete_memory() — remove entries
- read_memory() — get all entries in a category
- get_memory_context() — get formatted context string

WORKFLOW:
1. For each extracted fact:
   a. search_memory() to check for related existing entries
   b. If exists: use update_memory() with new value
   c. If new: use write_memory()
   d. Set confidence based on signal strength
2. Log each operation with source (discussion, reaction, batch, etc.)
"""


class MemoryExtractionAgent:
    def __init__(self, user_id: str, llm_client):
        self.user_id = user_id
        self.llm = llm_client
        self.memory_api = MemoryStorageAPI(user_id)
        
    async def extract_from_interactions(self, interactions: list[dict]) -> dict:
        """
        interactions = [
            {"type": "reaction", "post_id": "...", "reaction": "👍", "title": "PostgreSQL 18"},
            {"type": "discussion", "messages": [...], "article_title": "..."},
            {"type": "save", "post_title": "..."},
        ]
        """
        interaction_text = self._format_interactions(interactions)
        
        messages = [
            {
                "role": "user",
                "content": f"Extract meaningful memories from these interactions:\n\n{interaction_text}"
            }
        ]
        
        tools = [
            self.memory_api.write_memory.openai_schema(),
            self.memory_api.search_memory.openai_schema(),
            self.memory_api.update_memory.openai_schema(),
            self.memory_api.read_memory.openai_schema(),
        ]
        
        # Tool-use loop
        while True:
            response = await self.llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                system=MEMORY_EXTRACTION_SYSTEM_PROMPT,
            )
            
            if response.stop_reason == "end_turn":
                break
            
            if response.stop_reason == "tool_calls":
                # Process tool calls
                tool_results = []
                for tool_call in response.tool_calls:
                    result = await self._execute_tool(tool_call)
                    tool_results.append({
                        "tool_use_id": tool_call.id,
                        "content": result,
                    })
                
                # Add all to message history
                messages.append({"role": "assistant", "content": response.content})
                messages.append({
                    "role": "user",
                    "content": [{"type": "tool_result", **tr} for tr in tool_results]
                })
        
        return {
            "user_id": self.user_id,
            "date": datetime.now().date(),
            "status": "completed",
            "tool_calls_made": len([tc for tc in response.tool_calls if tc.type == "function"]),
        }
    
    async def _execute_tool(self, tool_call) -> str:
        """Execute a tool call and return result."""
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        
        if name == "write_memory":
            return await self.memory_api.write_memory(**args)
        elif name == "search_memory":
            return await self.memory_api.search_memory(**args)
        elif name == "update_memory":
            return await self.memory_api.update_memory(**args)
        elif name == "read_memory":
            return await self.memory_api.read_memory(**args)
```

---

## MemoryStorageAPI Implementation

```python
class MemoryStorageAPI:
    """Unified API for memory operations. Can be called by agents or directly."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.memory_dir = Path(f"data/memory/{user_id}")
        self.bm25_index = BM25MemoryIndex(user_id)
        
    async def write_memory(
        self,
        key: str,
        value: str,
        category: str,
        durability: str = "durable",
        source: str = "",
        confidence: float = 1.0,
    ) -> str:
        """Write a memory entry and return confirmation."""
        
        # Check confidence threshold for durable writes
        if durability == "durable" and confidence < 0.7:
            return f"Entry '{key}' confidence {confidence:.1%} below 0.7 threshold. Would write to daily notes instead."
        
        # Search for duplicates
        similar = await self.search_memory(f"{key} {value}", limit=3)
        if similar:
            return f"Similar entries found. Consider using update_memory() instead:\n{similar}"
        
        # Write to appropriate tier
        if durability == "durable":
            await self._merge_to_memory_md(key, value, category, confidence, source)
        else:
            await self._append_to_daily_notes(key, value, category, source)
        
        # Reindex
        await self.bm25_index.rebuild()
        
        return f"✓ Memory written: {category}/{key} (confidence: {confidence:.1%})"
    
    async def search_memory(self, query: str, limit: int = 5, category: str = "all") -> str:
        """Search memory via BM25 and return formatted results."""
        results = await self.bm25_index.search(query, limit=limit, category=category)
        
        if not results:
            return f"No memories found matching '{query}'"
        
        formatted = "Search results:\n"
        for i, result in enumerate(results, 1):
            formatted += f"\n{i}. [{result['category']}] {result['key']}\n"
            formatted += f"   {result['value']}\n"
            formatted += f"   (score: {result['score']:.2f})\n"
        
        return formatted
    
    async def update_memory(self, key: str, value: str, category: str = None) -> str:
        """Update an existing memory entry."""
        # Find and update entry
        # ... implementation
        return f"✓ Memory updated: {key}"
    
    async def delete_memory(self, key: str) -> str:
        """Delete a memory entry."""
        # Find and remove entry
        # ... implementation
        return f"✓ Memory deleted: {key}"
    
    async def read_memory(self, category: str, limit: int = 20) -> str:
        """Read all memories in a category."""
        entries = await self._load_from_memory_md(category, limit)
        if not entries:
            return f"No memories in {category}"
        
        formatted = f"\n**{category.replace('_', ' ').title()}:**\n"
        for entry in entries:
            formatted += f"- {entry['key']}: {entry['value']}\n"
        return formatted
    
    async def get_memory_context(self, topic: str, max_tokens: int = 1500) -> str:
        """Get formatted memory context for injection into prompts."""
        # 1. Load core MEMORY.md
        core = await self._load_from_memory_md("all", limit=100)
        
        # 2. BM25 search for topic-relevant entries
        search_results = await self.search_memory(topic, limit=5)
        
        # 3. Recent daily notes
        recent = await self._load_recent_daily_notes(days=7)
        
        # 4. Assemble and truncate
        context = f"## User Memory\n\n{core}\n\n{search_results}\n\n## Recent Activity\n{recent}"
        return truncate_to_tokens(context, max_tokens)
    
    async def _merge_to_memory_md(self, key: str, value: str, category: str, confidence: float, source: str):
        """Merge entry into MEMORY.md (add/update)."""
        # ... implementation
        pass
    
    async def _append_to_daily_notes(self, key: str, value: str, category: str, source: str):
        """Append entry to memory/YYYY-MM-DD.md."""
        # ... implementation
        pass
```

---

## BM25 Index Architecture

BM25 is now tightly integrated with the memory API:

```python
class BM25MemoryIndex:
    """
    Full-text search index over user memory.
    Built at startup, rebuilt after daily extraction.
    """
    
    def __init__(self, user_id: str, k1: float = 1.5, b: float = 0.75):
        self.user_id = user_id
        self.k1 = k1
        self.b = b
        self.documents: list[dict] = []
        self.inverted_index: dict[str, set[int]] = {}
        self.doc_lengths: list[int] = []
        self.avg_doc_length: float = 0
        self.loaded = False
    
    async def rebuild(self):
        """Rebuild index from MEMORY.md and recent daily notes."""
        # Clear
        self.documents = []
        self.inverted_index = {}
        self.doc_lengths = []
        
        # Load MEMORY.md
        memory_file = Path(f"data/memory/{self.user_id}/MEMORY.md")
        if memory_file.exists():
            content = memory_file.read_text()
            for section in self._parse_sections(content):
                self._add_document(section)
        
        # Load recent daily notes (90 days)
        for daily_file in self._get_recent_daily_files(days=90):
            content = daily_file.read_text()
            for section in self._parse_sections(content):
                self._add_document(section)
        
        # Compute statistics
        self.doc_lengths = [len(d["tokens"]) for d in self.documents]
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 1
        self.loaded = True
    
    async def search(self, query: str, limit: int = 5, category: str = "all") -> list[dict]:
        """BM25 search and return ranked results."""
        if not self.loaded:
            await self.rebuild()
        
        query_tokens = tokenize(query.lower())
        scores = [0.0] * len(self.documents)
        n = len(self.documents)
        
        for token in query_tokens:
            if token not in self.inverted_index:
                continue
            
            docs_with_token = self.inverted_index[token]
            df = len(docs_with_token)
            idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
            
            for doc_idx in docs_with_token:
                # Skip if category filter active and doesn't match
                if category != "all" and self.documents[doc_idx]["category"] != category:
                    continue
                
                tf = self.documents[doc_idx]["token_counts"].get(token, 0)
                dl = self.doc_lengths[doc_idx]
                
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * dl / self.avg_doc_length)
                scores[doc_idx] += idf * (numerator / denominator)
        
        # Rank and return
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        results = []
        for doc_idx, score in ranked[:limit]:
            if score > 0:
                results.append({
                    **self.documents[doc_idx],
                    "score": score,
                })
        
        return results
    
    def _add_document(self, section: dict):
        """Add document to index (from MEMORY.md or daily notes)."""
        doc_id = len(self.documents)
        tokens = tokenize(section["content"].lower())
        token_counts = Counter(tokens)
        
        doc = {
            "id": doc_id,
            "category": section["category"],
            "key": section.get("key", ""),
            "value": section["content"],
            "source": section.get("source", ""),
            "tokens": tokens,
            "token_counts": token_counts,
        }
        self.documents.append(doc)
        
        # Update inverted index
        for token in token_counts:
            self.inverted_index.setdefault(token, set()).add(doc_id)
```

---

## Data Flow: Explicit Memory Capture During Discussion

When user says "remember this", the DiscussionAgent calls memory tools:

```
User Message: "Remember that I'm presenting on DB perf next week"
     ↓
DiscussionAgent detects trigger via LLM
     ↓
LLM calls write_memory(
    key="upcoming_presentation_db_perf",
    value="Presenting on database performance next week",
    category="personal_context",
    durability="durable",
    source="explicit_mention_in_discussion",
    confidence=0.95
)
     ↓
MemoryStorageAPI.write_memory()
     ├→ Search for duplicates/similar
     ├→ Write to MEMORY.md
     ├→ Rebuild BM25 index
     └→ Return "✓ Memory written"
     ↓
LLM receives confirmation
     ↓
Bot responds: "Got it, I'll remember that you're presenting on database performance next week."
```

---

## Data Flow: Daily Batch Extraction with Search

```
Daily Batch Job starts (23:00 UTC)
     ↓
Collect interactions from past 24h
     ↓
MemoryExtractionAgent.extract_from_interactions()
     ↓
For each potential memory:
     ├→ search_memory(key_phrase) to find related entries
     ├→ If found: update_memory() instead of write_memory()
     ├→ If new: write_memory() with confidence score
     └→ Tool results accumulated
     ↓
LLM processes tool results and decides next action
     ↓
update_memory(
    key="interested_in",
    value="Rust async runtime design, PostgreSQL performance optimization",
)
     ↓
BM25 index rebuilt
     ↓
memory/2026-02-13.md written with daily observations
     ↓
Job completes and logs to memory_extraction_runs table
```

---

## Benefits of This Design

| Benefit | Impact |
| --- | --- |
| **Tool calling** | Agent knows what it's storing, can reason about conflicts, auditable |
| **Search before write** | Automatic deduplication, intelligent merging instead of duplication |
| **BM25 search** | Agent can retrieve context during extraction, zero external dependencies |
| **Confidence scoring** | Prevents low-confidence facts from cluttering MEMORY.md |
| **Explicit operations** | Every memory operation is logged and traceable |
| **Multi-tier storage** | Natural language facts live in files, metadata mirrors in PostgreSQL for queries |
| **Token budget** | Agent stays aware of token usage when retrieving context |

