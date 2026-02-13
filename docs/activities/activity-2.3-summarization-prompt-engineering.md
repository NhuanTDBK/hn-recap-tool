# Activity 2.3: Summarization Prompt Engineering

## Overview
Design, test, and optimize prompt templates for generating high-quality summaries from HackerNews post content. Establish a prompt versioning system to enable A/B testing and continuous improvement of summary quality.

## Prerequisites
- ✅ Activity 1.3: URL crawler and Markdown conversion (provides markdown content)
- ✅ Activity 1.5: RocksDB content storage (content retrieval)
- Activity 2.1: Basic summarization (database schema)

## Objectives
1. Design effective prompt templates for different summary styles
2. Establish prompt versioning and tracking system
3. Create evaluation framework for summary quality
4. Support A/B testing of prompt variants
5. Enable personalized prompts based on user preferences
6. Document prompt best practices and guidelines

---

## Technical Details

### Prompt Design Principles

**Core Requirements:**
- Output length: 2-3 sentences (~50-80 words)
- Clear, concise language
- Focus on key insights, not just facts
- Avoid clickbait or sensationalism
- Maintain technical accuracy

**Content Priorities:**
1. Main thesis/argument
2. Novel insights or findings
3. Practical implications
4. Technical approach (if applicable)

---

## Prompt Variants

### Variant 1: Basic (Default)

**Purpose:** General-purpose summary for all users

**Template:**
```
You are a technical content curator for HackerNews readers.

Summarize the following article in 2-3 clear, concise sentences.
Focus on:
- The main point or argument
- Why it matters to developers/tech professionals
- Any novel insights or practical takeaways

Article content:
{markdown_content}

Output only the summary, no preamble or explanation.
```

**Expected Output Example:**
> "This article explores how Stripe rebuilt their payment orchestration layer using event sourcing. The new architecture reduced payment failures by 40% and improved debugging capabilities through complete event replay. Key insight: domain events as the source of truth enabled better observability than traditional CRUD operations."

---

### Variant 2: Technical

**Purpose:** For users who prefer technical depth

**Template:**
```
You are a senior engineer reviewing technical content for your team.

Summarize the following technical article in 2-3 sentences.
Focus on:
- Technical approach and architecture decisions
- Implementation details and trade-offs
- Performance characteristics or benchmarks

Keep the language precise and technical. Assume the reader has strong engineering background.

Article content:
{markdown_content}

Output only the summary, no preamble.
```

**Expected Output Example:**
> "The system uses a distributed hash table with consistent hashing (virtual nodes, replication factor 3) to partition data across nodes. Writes go through a Paxos-based consensus protocol with quorum reads/writes (W+R>N). Benchmarks show 50k writes/sec at p99 latency of 12ms on commodity hardware."

---

### Variant 3: Business Impact

**Purpose:** For users interested in industry implications

**Template:**
```
You are a tech industry analyst summarizing news for business leaders.

Summarize the following article in 2-3 sentences.
Focus on:
- Business impact and market implications
- Strategic insights for companies
- Industry trends or competitive dynamics

Use clear, non-technical language accessible to business stakeholders.

Article content:
{markdown_content}

Output only the summary, no preamble.
```

**Expected Output Example:**
> "Meta's new AI model demonstrates that open-source approaches can compete with proprietary models from OpenAI and Anthropic. This threatens the moat of closed-source AI companies and may accelerate commoditization of foundational models. Companies may shift value capture from model licensing to application-layer differentiation."

---

### Variant 4: Concise (Ultra-brief)

**Purpose:** For users who want minimal summaries

**Template:**
```
Summarize the following article in ONE sentence (max 30 words).
Capture only the single most important point.

Article content:
{markdown_content}

Output only the summary, no preamble.
```

**Expected Output Example:**
> "SQLite's new JSONB implementation outperforms PostgreSQL by storing JSON in a compact binary format with faster parsing and lower memory overhead."

---

### Variant 5: Personalized (Memory-Enhanced)

**Purpose:** For Option 2 users with memory/preferences enabled

**Template:**
```
You are a personalized content curator for a specific user.

User preferences:
- Preferred topics: {user_topics}
- Summary style: {user_style}
- Past feedback: {user_feedback_summary}

Summarize the following article in 2-3 sentences, tailored to this user's interests.
Emphasize aspects relevant to their preferred topics.
Use their preferred style ({user_style}).

Article content:
{markdown_content}

Output only the summary, no preamble.
```

**Template Variables:**
- `{user_topics}`: e.g., ["distributed systems", "rust", "databases"]
- `{user_style}`: e.g., "technical", "concise", "business"
- `{user_feedback_summary}`: e.g., "User prefers implementation details over high-level concepts"

**Expected Output Example (for distributed systems enthusiast):**
> "The article describes Pinterest's migration from sharded MySQL to a distributed event log architecture using Kafka and Flink. The new system eliminated cross-shard transactions and reduced data inconsistencies from ~2% to <0.01%. The CAP theorem trade-off: they chose eventual consistency for better availability and partition tolerance."

---

## Prompt Storage (Simple Approach)

### File Structure

**Keep prompts as markdown files:**
```
backend/app/infrastructure/prompts/
├── basic.md
├── technical.md
├── business.md
├── concise.md
└── personalized.md
```

### Prompt File Format

**Example: `basic.md`**
```markdown
# Basic Summarization Prompt

You are a technical content curator for HackerNews readers.

Summarize the following article in 2-3 clear, concise sentences.
Focus on:
- The main point or argument
- Why it matters to developers/tech professionals
- Any novel insights or practical takeaways

Article content:
{markdown_content}

Output only the summary, no preamble or explanation.
```

**Loading prompts:**
- Read markdown file at runtime
- Replace `{markdown_content}` with actual content
- No database storage needed
- Version control via git (simple git history)

---

## Evaluation Framework: LLM-as-Judge

### Quality Metrics (Automated with LLM)

**Use LLM to evaluate summary quality on 5 dimensions:**

**1. Length Compliance (Rule-based)**
- Target: 2-3 sentences (50-80 words)
- Measure: Word count
- Pass: 40-100 words
- **Weight:** 20%

**2. Factual Accuracy (LLM-judged)**
- LLM compares summary against source content
- Checks for hallucinations or inaccuracies
- Scoring: 0-10 scale
- **Weight:** 30%

**3. Information Density (LLM-judged)**
- Does summary capture key insights?
- Are important details preserved?
- Is it concise without losing meaning?
- Scoring: 0-10 scale
- **Weight:** 25%

**4. Clarity & Readability (LLM-judged)**
- Is the summary easy to understand?
- Does it flow naturally?
- Is technical jargon appropriate for audience?
- Scoring: 0-10 scale
- **Weight:** 15%

**5. Relevance (LLM-judged)**
- Does it capture "why this matters"?
- Is it relevant to HN audience?
- Does it highlight novel insights?
- Scoring: 0-10 scale
- **Weight:** 10%

### LLM-as-Judge Prompt

```markdown
# Summary Quality Evaluation

You are evaluating the quality of a HackerNews article summary.

## Original Article (first 500 words):
{article_content}

## Generated Summary:
{summary}

## Evaluation Criteria:

Rate each dimension on a scale of 0-10:

**Factual Accuracy (0-10):**
- Does the summary contain any factual errors or hallucinations?
- Are all claims verifiable in the source article?
- 10 = Perfect accuracy, 0 = Contains false information

**Information Density (0-10):**
- Does it capture the most important points?
- Is it concise without losing key insights?
- 10 = Perfect balance, 0 = Misses key points or too verbose

**Clarity & Readability (0-10):**
- Is it easy to understand?
- Does it flow naturally?
- 10 = Crystal clear, 0 = Confusing or poorly written

**Relevance (0-10):**
- Does it highlight why this matters to developers?
- Does it capture novel insights?
- 10 = Highly relevant, 0 = Misses the point

## Output Format (JSON only):
{
  "factual_accuracy": <score>,
  "information_density": <score>,
  "clarity": <score>,
  "relevance": <score>,
  "overall_score": <weighted average>,
  "reasoning": "<brief explanation of scores>",
  "issues": ["<specific issue 1>", "<issue 2>"] // if any
}
```

### Scoring Calculation

**Overall Score Formula:**
```
Overall = (
  Factual_Accuracy * 0.30 +
  Information_Density * 0.25 +
  Clarity * 0.15 +
  Relevance * 0.10 +
  Length_Compliance * 0.20
) / 10 * 100

Result: 0-100% score
Pass Threshold: ≥80%
```

### Automated Testing Script

**Location:** `scripts/evaluate_prompts.py`

**Test Process:**
1. Load test dataset (5 diverse HN posts)
2. Generate summaries with each prompt variant
3. For each summary:
   - Check length compliance (rule-based)
   - Send to LLM judge for quality scoring
   - Calculate overall score
4. Calculate pass rate (% of summaries ≥80%)
5. Generate detailed report

**Test Dataset Requirements:**
- **5 posts only** (small for quick iteration)
- Mix of content types (technical, business, research)
- Mix of lengths (short blog post, medium article, long paper)
- Mix of complexity (beginner, intermediate, advanced)
- Should represent typical HN front page diversity

**Output:**
```
Prompt Evaluation Report
========================
Test Dataset: 5 posts
Evaluation Model: gpt-4o-mini

Variant: basic.md
---------------------
Summaries Generated: 5
Pass Rate: 100% (5/5 passed ≥80% score) ✓
Average Overall Score: 86.4%

Dimension Scores (avg):
- Factual Accuracy: 9.2/10 ✓
- Information Density: 8.4/10 ✓
- Clarity: 8.8/10 ✓
- Relevance: 8.0/10 ✓
- Length Compliance: 100% ✓

Individual Scores:
1. Post #1 (Technical blog): 88% ✓
2. Post #2 (Business article): 85% ✓
3. Post #3 (Research paper): 87% ✓
4. Post #4 (Short post): 90% ✓
5. Post #5 (Long-form): 82% ✓

Variant: technical.md
---------------------
Pass Rate: 80% (4/5 passed) ✓
Average Overall Score: 83.2%

Individual Scores:
1. Post #1: 90% ✓
2. Post #2: 78% ✗ (too technical for business content)
3. Post #3: 88% ✓
4. Post #4: 82% ✓
5. Post #5: 78% ✗

Variant: concise.md
---------------------
Pass Rate: 60% (3/5 passed) ✗ BELOW THRESHOLD
Average Overall Score: 76.8%

Issues:
- Post #1: 72% - Missed key technical detail
- Post #3: 75% - Information density too low

Recommendations:
✓ basic.md: APPROVED (100% pass rate)
✓ technical.md: APPROVED (80% pass rate)
✗ concise.md: NEEDS IMPROVEMENT (60% pass rate)
⚠️ business.md: NOT TESTED YET
⚠️ personalized.md: NOT TESTED YET
```

### Pass/Fail Criteria

**Prompt Variant Approval:**
- **PASS:** ≥80% of test summaries score ≥80% overall
- **FAIL:** <80% pass rate → requires iteration

**Individual Summary Quality:**
- **Excellent:** ≥90% overall score
- **Good:** 80-89% overall score
- **Acceptable:** 70-79% overall score (not passing)
- **Poor:** <70% overall score (needs rework)

---

## Personalization Strategy (Option 2)

### User Preference Integration

**Read from user config:**
```python
# Pseudocode
user_config = get_user(user_id).config
summarization_prefs = user_config['summarization']

# Select prompt variant
if summarization_prefs['enable_memory']:
    variant = 'personalized'
    template = load_prompt(variant, version='current')

    # Inject user context
    prompt = template.format(
        user_topics=summarization_prefs['preferred_topics'],
        user_style=summarization_prefs['style'],
        user_feedback_summary=get_feedback_summary(user_id),
        markdown_content=content
    )
else:
    # Option 1: Use default variant
    variant = summarization_prefs['style'] or 'basic'
    template = load_prompt(variant, version='current')
    prompt = template.format(markdown_content=content)
```

### Feedback Loop

**Collect feedback:**
- User rates summary (1-5 stars)
- Optional text feedback
- Track read time and engagement

**Update preferences:**
```sql
-- Store feedback in summaries table
UPDATE summaries
SET user_feedback = jsonb_set(
    COALESCE(user_feedback, '{}'::jsonb),
    '{rating}',
    '4'::jsonb
)
WHERE id = ?;
```

**Use feedback to improve:**
- Analyze low-rated summaries for patterns
- Adjust user's `preferred_topics` based on engagement
- Switch prompt variant if consistently low ratings

---

## Prompt Best Practices

### Do's
✅ Use clear, specific instructions
✅ Provide examples in few-shot learning
✅ Specify output format explicitly
✅ Focus on "what matters" not "what happened"
✅ Test on diverse content (technical, business, narrative)
✅ Version and track all prompt changes

### Don'ts
❌ Don't ask for opinions or speculation
❌ Don't use vague terms like "interesting" or "important"
❌ Don't require external knowledge beyond the article
❌ Don't generate clickbait-style summaries
❌ Don't exceed target length (2-3 sentences)
❌ Don't change prompts without A/B testing

---

## Testing & Validation

### Unit Tests

**Location:** `tests/infrastructure/prompts/test_summarization_prompts.py`

**Test Cases:**
1. **test_prompt_length_compliance**
   - Generate summaries with each variant
   - Assert 40-100 words

2. **test_prompt_no_hallucination**
   - Generate summary
   - Check all facts appear in source content

3. **test_variant_consistency**
   - Same content, same variant → similar summary
   - Run 5 times, check overlap

4. **test_personalization_injection**
   - Mock user preferences
   - Verify personalized prompt includes user context

### Integration Tests

**Location:** `tests/integration/test_prompt_evaluation.py`

**Test Scenarios:**
1. Load all prompt variants from filesystem
2. Generate summaries for test dataset
3. Validate quality metrics within thresholds
4. Compare across variants for consistency

---

## Acceptance Criteria

- [ ] All 5 prompt variants written as markdown files
- [ ] Prompt loader utility implemented (read .md files)
- [ ] `prompt_type` column added to `summaries` table
- [ ] LLM-as-judge evaluation prompt created
- [ ] **Test dataset prepared (5 diverse HN posts)** - Small for quick iteration
- [ ] Evaluation script implemented (`scripts/evaluate_prompts.py`)
- [ ] **All prompt variants achieve ≥80% pass rate** (4/5 posts must score ≥80%)
- [ ] Evaluation report generated showing dimension scores per post
- [ ] Failed samples analyzed and prompts iterated if needed
- [ ] Personalization logic for Option 2 users
- [ ] Default prompt chosen (highest pass rate variant)
- [ ] Documentation of prompt best practices
- [ ] Git repository set up for version control

**Quality Gate:**
- At least 3 of 5 prompt variants must achieve ≥80% pass rate (4/5 posts passing)
- Selected default prompt should achieve 100% pass rate (5/5 posts) if possible
- No variant should have <60% pass rate (indicates fundamental issues)

---

## Related Activities

**Upstream Dependencies:**
- ✅ Activity 1.3: URL crawler (provides markdown content)
- ✅ Activity 1.5: RocksDB content storage (content retrieval)
- Activity 2.1: Basic summarization (database schema, LLM integration)

**Downstream Dependencies:**
- Activity 2.4: Batch summarization pipeline (uses prompt variants)
- Phase 6: Memory System (feedback loop for personalization)

---

## Notes & Assumptions

### Design Decisions

**Why multiple variants?**
- Different users have different preferences
- Technical vs non-technical readers need different depth
- Easy to test and compare quality

**Why markdown files instead of database?**
- Simple to edit and version control via git
- Easy to review changes via git diff
- No database schema needed
- Can edit prompts without deployment
- Git history provides versioning for free

**Why manual testing instead of automated A/B?**
- Start simple, optimize later
- Small user base initially (quality > stats)
- Manual review catches nuances
- Can always add automated testing later

### Future Considerations

**A/B Testing (Next Release):**
- Automated A/B testing infrastructure
- Randomly assign users to prompt variants
- Track engagement metrics (CTR, read time, ratings)
- Statistical significance testing
- Auto-promote winning variants
- Currently: Manual evaluation is sufficient for MVP

**Multi-language support:**
- Add language parameter to user config
- Translate prompts to multiple languages
- Or instruct LLM to output in target language

**Few-shot learning:**
- Include example summaries in prompt
- "Here are 3 examples of good summaries..."
- May improve consistency and quality

**Chain-of-thought prompting:**
- Ask LLM to first extract key points
- Then synthesize into summary
- May improve factual accuracy

**Prompt caching:**
- Cache prompt template + system instructions
- Reduces token usage for repeated summaries
- Supported by some LLM providers (Anthropic)

---

## Implementation Checklist

**Setup:**
- [ ] Create `backend/app/infrastructure/prompts/` directory
- [ ] Write all 5 prompt variant markdown files (basic.md, technical.md, etc.)
- [ ] Implement simple prompt loader utility (read markdown file)
- [ ] Add `prompt_type` column to `summaries` table

**LLM-as-Judge Evaluation:**
- [ ] Create LLM judge evaluation prompt (judge.md)
- [ ] Prepare test dataset (5 diverse HN posts)
- [ ] Implement evaluation script (`scripts/evaluate_prompts.py`)
- [ ] Add scoring calculation (weighted average)
- [ ] Add pass/fail detection (≥80% threshold per post)

**Testing & Iteration:**
- [ ] Run evaluation on all 5 prompt variants
- [ ] Generate detailed report with dimension scores
- [ ] Analyze failed samples (score <80%)
- [ ] Iterate on prompts that fail to meet 80% pass rate
- [ ] Re-run evaluation after iterations
- [ ] Verify at least 3 variants pass ≥80% threshold

**Finalization:**
- [ ] Choose default prompt (highest pass rate, ≥85%)
- [ ] Document evaluation results
- [ ] Document prompt engineering guidelines
- [ ] Set up git versioning for prompt files

---

**Estimated Effort:** 6-8 hours
**Priority:** High (critical for summary quality)
**Status:** Ready to implement

---

**Last Updated:** 2025-02-13
