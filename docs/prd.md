# HackerNews Knowledge Graph Builder Product Requirements Document (PRD)

## Goals and Background Context

### Goals

- Build a HackerNews knowledge graph builder that transforms news consumption into systematic knowledge accumulation for mid-senior technical practitioners
- Deliver daily topic-clustered digests with educational summaries that enable learning, not just awareness
- Solve the cold-start problem through intelligent persona-based onboarding
- Create continuous improvement through user feedback loops that personalize content over time
- Surface community wisdom from HN comment threads to enrich summaries with practical perspectives
- Differentiate from existing HN tools through opinion synthesis, contextual linking, and structured learning formats
- Launch MVP with 10-20 engaged beta users within 8 weeks

### Background Context

Existing HackerNews digest tools provide shallow, post-by-post summaries optimized for news consumption - treating HN as an information broadcast. Our research identified a fundamental gap: mid-senior engineers, CTOs, and technical practitioners need a knowledge building tool, not another news reader. They want to grow expertise through continuous learning, identify trends early, and make informed technical decisions, but lack time to manually browse HN daily.

The HackerNews Knowledge Graph Builder addresses this by clustering posts into coherent topics (2-3 per day), generating structured educational summaries (motivation, context, technical depth, performance analysis, expert opinions), and building a personal knowledge graph that connects learning over time. Starting with HN as the MVP source due to its high-quality technical discussions, the architecture supports future expansion to multiple knowledge sources.

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-19 | 0.1 | Initial PRD draft | John (PM) |

## Requirements

### Functional Requirements

**FR1:** System shall fetch top HackerNews stories daily (configurable count, default 30) via HN API

**FR2:** System shall cluster HN posts into 2-3 coherent topics per day using intelligent topic classification

**FR3:** System shall generate structured learning summaries for each post containing: overview, motivation, related works, how it works, performance analysis, and AI-generated opinions

**FR4:** System shall deliver daily digest via email notification with link to web application for full interaction

**FR5:** System shall provide web application with user authentication for accessing digests and providing feedback

**FR6:** System shall implement career/persona-based onboarding with three questions: role, tech stack, and learning interests

**FR7:** System shall generate personalized starter topics based on user's onboarding profile

**FR8:** System shall allow users to upvote/downvote individual summaries to provide explicit feedback

**FR9:** System shall allow users to add topics to an "interest list" for priority coverage

**FR10:** System shall track implicit user signals (read time, skips, click-throughs) for recommendation improvement

**FR11:** System shall implement recommendation engine that adapts topic selection based on user profile and feedback

**FR12:** System shall fetch HN comment threads (up to 3 levels deep) for posts in daily digest

**FR13:** System shall filter comments using quality scoring based on upvotes, user karma, thread depth, and relevance

**FR14:** System shall extract and summarize community insights from high-quality comments (3-5 key points per post)

**FR15:** System shall integrate community insights into summaries with clear visual distinction and link to original HN thread

**FR16:** System shall maintain user reading history and expertise profile for personalization

**FR17:** System shall support "Explore vs. Exploit" modes - allowing users to deepen existing expertise or discover new areas

**FR18:** System shall limit active topic focus to 2-3 topics to prevent overwhelm

**FR19:** System shall provide user profile/settings page for managing interest list and preferences

**FR20:** System shall store daily digests with history access (view past digests)

### Non-Functional Requirements

**NFR1:** System shall process and deliver daily digest within 30 minutes of generation start

**NFR2:** Email delivery success rate shall exceed 99%

**NFR3:** System uptime shall exceed 99%

**NFR4:** Topic clustering shall achieve 80%+ coherence (posts within topics are semantically related)

**NFR5:** Summary quality shall be rated 4/5+ by users (educational value, accuracy, clarity)

**NFR6:** Web application shall be mobile-responsive and accessible on all major devices

**NFR7:** System shall handle HN API failures gracefully with fallback mechanisms and retry logic

**NFR8:** User authentication shall use secure password storage (hashing/salting) and HTTPS

**NFR9:** LLM API costs shall be monitored and optimized to support sustainable unit economics

**NFR10:** System shall be architected for future multi-source support (beyond HN) without major refactoring

**NFR11:** Database queries shall be optimized for performance (sub-second response times for user interactions)

**NFR12:** Comment processing shall not delay digest delivery (timeout after 5 minutes if needed)

**NFR13:** System shall log errors and critical events for monitoring and debugging

**NFR14:** Code shall follow Python best practices with type hints and documentation

**NFR15:** Onboarding completion rate shall exceed 80% (UX optimization metric)

## User Interface Design Goals

### Overall UX Vision

The interface should feel like a **learning companion, not a news app**. Clean, distraction-free reading experience optimized for deep content consumption. Think "Readwise meets Medium" - focused on educational value with minimal chrome. Users should feel they're building knowledge, not scrolling through feeds.

Key principles:
- **Depth over breadth** - Encourage deep reading of fewer things vs. skimming many
- **Progressive disclosure** - Show topic overview first, expand for details
- **Feedback is frictionless** - One-click voting, visible impact of personalization
- **Trust through transparency** - Show why content was selected, how system adapts

### Key Interaction Paradigms

**Topic-First Navigation**
- Daily digest presents 2-3 topic clusters as primary navigation
- Users choose topics to explore (not chronological scrolling)
- Each topic shows post count and relevance indicator

**Expand/Collapse for Depth**
- Summaries start with overview paragraph (collapsed view)
- Click to expand full 6-section learning format
- Community insights section is collapsible
- Preserves context while enabling quick scanning

**Ambient Feedback**
- Upvote/downvote buttons always visible, no modal popups
- "Add to interest list" button on topic headers
- Visual feedback on vote submission (checkmark, subtle animation)
- Weekly "personalization report" shows system adaptation

**Reading Progress**
- Mark posts as "read" automatically based on scroll/time
- Unread indicator on new posts
- History access via simple date selector

### Core Screens and Views

1. **Onboarding Flow** (3-step)
   - Screen 1: Role selection (dropdown + custom)
   - Screen 2: Tech stack (tag multi-select)
   - Screen 3: Learning interests (tag multi-select + free text)
   - Preview personalized topics before completion

2. **Daily Digest View** (primary screen)
   - Topic clusters as cards/sections
   - Each topic shows: title, post count, relevance score
   - Posts within topics: collapsed by default, expand for full summary
   - Voting UI inline with each summary
   - Community insights section (collapsible)
   - Link to original HN post/thread

3. **Profile & Settings**
   - Interest list management (add/remove topics)
   - Explore vs. Exploit mode toggle
   - Email preferences (frequency, format)
   - Update onboarding profile
   - View personalization data ("You've upvoted 23 posts about databases")

4. **History View**
   - Calendar or date selector for past digests
   - Same digest UI as current day
   - Search/filter by topic (future enhancement)

5. **Email Template**
   - Simple HTML email with topic headers
   - 1-2 sentence teasers per post
   - CTA: "Read full digest on web"
   - Link directly to web app

### Accessibility

**WCAG AA** - Standard web accessibility compliance
- Semantic HTML
- Keyboard navigation support
- Screen reader friendly
- Color contrast ratios meet AA standards
- No reliance on color alone for information

### Branding

**Minimalist, Technical, Trustworthy**
- Color palette: Neutral base (grays, whites) with accent color for interactive elements (teal/blue suggests knowledge/trust)
- Typography: Clean sans-serif for UI (Inter, SF Pro), serif for reading content (Georgia, Charter) to enhance readability
- Iconography: Simple, functional icons (no decorative clutter)
- Tone: Professional but approachable - think "smart colleague sharing insights"

**Inspiration references:**
- Readwise (reading-focused, clean)
- Linear (minimal, functional)
- Arc Browser (thoughtful interactions)

### Target Platforms

**Web Responsive** - Mobile-first design that scales to desktop
- Mobile: Optimized for one-handed reading, thumb-friendly tap targets
- Tablet: Take advantage of screen real estate for side-by-side topic/post view
- Desktop: Multi-column layout where appropriate, keyboard shortcuts

**Future consideration:** Progressive Web App (PWA) for offline reading

## Technical Assumptions

### Repository Structure

**Monorepo** - Single repository containing API backend and frontend

### Service Architecture

**API-First Monolith with Separate Data Pipeline** - Python backend with clear separation between data collection and processing

**Components:**
- **Data Collection Service:** Fetch raw data from HN API, store to parquet (scheduled job)
- **Data Processing Service:** Transform raw data, generate summaries, cluster topics (scheduled job)
- **Backend API:** FastAPI application serving processed data to clients (stateless)
- **Frontend:** Simple React/Next.js consuming API
- **Data Storage:** Parquet files for all data (raw and processed)
- **Cache:** Redis for frequently accessed items (user profiles, latest digests)

**Rationale:**
- **Separation of concerns:** Data collection independent from processing
- **Easier debugging:** Can reprocess data without re-fetching from HN
- **Cost efficiency:** Minimize LLM API calls by separating fetch from summarization
- **Scalability:** Each component can be optimized/scaled independently
- **API-first:** Enables future integrations (MCP, mobile apps, third-party)
- **Simple deployment:** All Python, can run as separate scripts/cron jobs

**Data Flow:**
```
HN API → [Data Collection] → Raw JSONL Files →
[Data Processing] → Processed JSONL Files →
Redis Cache → [API] → Frontend/Clients
```

### Testing Requirements

**Unit + Integration Testing**

**Testing Focus:**
- **Unit tests:** Core business logic (topic clustering, quality scoring, recommendation engine)
- **Integration tests:** API endpoints, parquet file operations, LLM integration
- **Manual testing:** Beta user testing, UX validation

**No CI/CD for MVP** - Manual deployment acceptable for initial launch

### Additional Technical Assumptions and Requests

**Backend Stack:**
- **Language:** Python 3.11+
- **Web Framework:** FastAPI (async, API-first)
- **Data Storage:** JSONL (JSON Lines) files - simple, human-readable, append-only
- **Cache:** Redis (user sessions, latest digests, frequently accessed data)
- **Task Scheduling:** Cron jobs or Python scheduler (for daily digest generation)
- **LLM Integration:** Direct API clients (OpenAI/Anthropic)

**Data Model:**
- **JSONL files:** Digests, posts, comments, user history (append-only, partitioned by date)
  - `data/raw/YYYY-MM-DD-posts.jsonl` - Raw HN posts
  - `data/raw/YYYY-MM-DD-comments.jsonl` - Raw comments
  - `data/processed/YYYY-MM-DD-digest.jsonl` - Processed digests with summaries
  - `data/users/user-profiles.jsonl` - User accounts
  - `data/users/user-votes.jsonl` - Voting history
- **Redis:** User profiles, current digest, interest lists, voting data (fast access)
- **No database:** Keep it simple for MVP
- **Migration path:** Can move to Parquet later if analytics/performance needs arise

**Frontend Stack:**
- **Framework:** Next.js 14+ (React, consumes API)
- **Styling:** Tailwind CSS
- **State Management:** React Context + hooks
- **API Client:** Fetch with SWR for caching

**Infrastructure & Deployment:**
- **Deployment:** Simple - Docker container on any cloud VM or Render
- **No CI/CD initially:** Manual deployment for MVP
- **Email Service:** SendGrid or Postmark
- **Monitoring:** Basic logging to stdout, simple error tracking

**External APIs:**
- **HackerNews API:** Public
- **LLM Provider:** OpenAI GPT-4 or Anthropic Claude
- **Email Service:** SendGrid/Postmark API

**Development & Tooling:**
- **Package Management:** Poetry (Python), npm (frontend)
- **Code Quality:** Black (formatting), Ruff (linting)
- **Version Control:** Git + GitHub
- **Local Development:** Docker Compose or simple python run

**Security:**
- **Authentication:** JWT tokens, bcrypt password hashing
- **HTTPS:** Required in production
- **API Keys:** Environment variables

**Performance:**
- **JSONL file organization:** Partitioned by date for efficient reads
- **Redis caching:** Latest digest, active user data
- **LLM parallel processing:** Batch summarization where possible

**Authentication (Simplified for MVP):**
- **Basic email + password** signup/login (no OAuth/social)
- **JWT tokens** for session management
- **No password reset flow** - Beta users contact admin directly for resets
- **No email verification** - Manual user approval for beta
- **Bcrypt password hashing**

**Architectural Simplicity:**
- **API-first:** All functionality exposed via REST API
- **Stateless API:** Redis for session/cache only
- **Simple data layer:** Parquet for historical data, Redis for current data
- **Future-proof:** API design supports MCP, mobile apps, integrations

## Epic List

### Epic 1: Data Collection Pipeline & Basic API
**Goal:** Establish data collection infrastructure that fetches HN stories daily, stores raw data to parquet files, and provides basic API for data access with user authentication.

### Epic 2: Data Processing - Topic Clustering & Structured Summaries
**Goal:** Build processing pipeline that transforms raw HN data into topic-clustered digests with rich educational summaries, and deliver via email + web.

### Epic 3: User Preferences & Personalization
**Goal:** Enable personalized digest experience through explicit user preferences (tone, length, reading time, language) that control how summaries are generated and delivered.

### Epic 4: HN Comment Integration - Community Wisdom Extraction
**Goal:** Enhance summaries with community insights by fetching HN comment threads, filtering for quality (upvotes, karma, relevance), and extracting 3-5 key points from high-value discussions.

---

## Epic 1: Data Collection Pipeline & Basic API

**Epic Goal:**

Establish the foundational data collection infrastructure that fetches HackerNews stories daily, stores raw data to JSONL files, provides basic FastAPI with user authentication, and proves the collection mechanism works. This epic sets up the skeleton for all future work while delivering a minimal but testable system.

### Story 1.1: HackerNews Data Collection Background Job

**As a** system operator
**I want** a background job to fetch recent HN front page stories, article content, and comments, storing raw data to JSONL files
**So that** we have complete data for processing without re-fetching

**Acceptance Criteria:**

1. Background job infrastructure: Python script with APScheduler or cron, runs daily at configurable time
2. Fetch front page stories via HN Algolia API `GET /search?tags=front_page` (configurable limit, default 30)
3. Extract story metadata: id, title, url, author, points, num_comments, created_at, type
4. Store to `data/raw/YYYY-MM-DD-posts.jsonl`
5. Fetch article content from external URLs using trafilatura for clean text extraction
6. Compress article content using gzip (store as `YYYY-MM-DD-content.jsonl.gz`)
7. Extract only main article text (no ads, navigation, boilerplate) to minimize storage
8. Fetch comment trees via HN Algolia API `GET /items/:id` (up to 3 levels deep)
9. Store comments to `data/raw/YYYY-MM-DD-comments.jsonl` with parent_id relationships
10. Error handling: retry logic (3 attempts), timeout handling (30s), rate limiting (1-2s delays between requests)
11. Logging: job start/end, success metrics, error details with context
12. Idempotent: check existing data, support `--force` flag for re-runs
13. Storage monitoring: log file sizes, estimated ~5-10 GB/year for 30 posts/day

### Story 1.2: FastAPI Application with User Authentication

**As a** developer
**I want** a basic FastAPI application with user registration and login
**So that** users can access personalized digests in future epics

**Acceptance Criteria:**

1. FastAPI app with authentication endpoints:
   - `POST /api/auth/register` - Create user (email, password)
   - `POST /api/auth/login` - Login, return JWT token
   - `GET /api/auth/me` - Get current user profile (requires auth)
2. User data stored in `data/users/user-profiles.jsonl`
3. Password hashing with bcrypt before storage
4. JWT tokens for session management (no Redis sessions required for MVP)
5. Input validation: email format, password length >= 8 characters
6. Error handling: duplicate email, invalid credentials, malformed requests
7. No password reset flow (manual admin support for beta users)
8. No email verification (manual user approval)
9. Proper HTTP status codes (200, 201, 401, 422, etc.)
10. Auto-generated API documentation via FastAPI Swagger/OpenAPI
11. CORS configured for frontend development

### Story 1.3: Data Access API Endpoints

**As a** frontend developer
**I want** API endpoints to retrieve raw HN data
**So that** I can build the web interface for viewing digests

**Acceptance Criteria:**

1. API endpoints:
   - `GET /api/digests` - List available digest dates (read JSONL filenames from data/raw)
   - `GET /api/digests/{date}` - Get raw posts for specific date
   - `GET /api/posts/{post_id}` - Get single post with content and comments
2. All endpoints require authentication (JWT token)
3. Data read from JSONL files (decompress .gz files as needed)
4. Cache frequently accessed data in Redis for performance
5. Pagination support: `limit` and `offset` parameters
6. Error handling: date not found, invalid format, file read errors
7. Response format: consistent JSON structure
8. Basic rate limiting per user (prevent abuse)
9. Request logging for debugging

---

## Epic 2: Data Processing - Topic Clustering & Structured Summaries

**Epic Goal:**

Build the processing pipeline that transforms raw HN data into topic-clustered digests with rich educational summaries, generates the 6-section learning format, and delivers via email + web. This epic creates the core value proposition that differentiates from existing HN tools.

### Story 2.1: Topic Clustering Engine

**As a** system
**I want** to automatically cluster HN posts into 2-3 coherent topics per day
**So that** users can navigate digests by theme instead of chronological lists

**Acceptance Criteria:**

1. Read raw posts from `data/raw/YYYY-MM-DD-posts.jsonl`
2. Generate embeddings for each post using title + first 200 chars (OpenAI embeddings API or sentence-transformers)
3. Cluster embeddings into 2-3 topics using K-means or HDBSCAN algorithm
4. Generate topic labels via single LLM call with clustered post titles
5. Assign each post to exactly one topic cluster
6. Handle edge cases: too few posts (< 10), very diverse posts (fallback to generic labels)
7. Store clustering results to `data/processed/YYYY-MM-DD-topics.jsonl` with format: `{topic_id, label, post_ids[]}`
8. Clustering quality target: 80%+ coherence (manual evaluation during beta)
9. Configurable: min/max topics (default 2-3), clustering algorithm selection
10. Processing time: < 5 minutes for 30 posts
11. Cost: < $0.01/day (embeddings + label generation)
12. Logging: topics generated, posts per topic, clustering metrics

### Story 2.2: Structured Summary Generation Engine

**As a** user
**I want** rich, educational summaries for each HN post
**So that** I can learn deeply instead of just reading headlines

**Acceptance Criteria:**

1. Read raw posts, article content (decompress .gz), and topic clusters from JSONL files
2. For each post, count tokens in article content using tiktoken library
3. **Short articles (< 8K tokens):** Direct LLM summarization with full article context
4. **Long articles (> 8K tokens):** Hierarchical summarization:
   - Chunk article into segments (7K tokens/chunk, split by paragraphs)
   - Generate chunk summaries in parallel (500 tokens/chunk)
   - Final LLM call synthesizes chunk summaries into 6-section format
5. Generate 6-section structured summary for each post:
   - **Overview:** 2-3 sentence introduction
   - **Motivation:** Why this exists, problem it solves
   - **Related Works:** Context, what came before
   - **How It Works:** Technical explanation
   - **Performance:** Results, benchmarks, trade-offs (if applicable)
   - **AI Opinions:** Expert analysis, hype vs. reality, pros/cons
6. Use LLM API (Claude or GPT-4) with different prompts for post types (Show HN, Ask HN, articles, papers)
7. Include top 3 HN comments preview in summarization context (from Story 1.1 data)
8. Error handling: LLM API failures (retry 3x), timeout (2 min/post), rate limits (50 req/min)
9. Store summaries to `data/processed/YYYY-MM-DD-summaries.jsonl`
10. Parallel processing: batch 5-10 posts simultaneously using asyncio
11. Summary quality target: 4/5+ rating (educational, accurate, clear) - beta user survey
12. Processing time: < 20 minutes for 30 posts (12 min average)
13. Cost monitoring: track token usage, daily budget ~$1.60/day (70% short, 30% long articles)
14. Logging: processing time per post, token counts, API errors, cost tracking

### Story 2.3: Digest Assembly & Delivery

**As a** user
**I want** to receive my daily digest via email and view it on web
**So that** I can conveniently access my personalized learning content

**Acceptance Criteria:**

1. Read processed data: topics from `topics.jsonl`, summaries from `summaries.jsonl`
2. Assemble daily digest structure:
   - Group summaries by topic cluster
   - Order topics by size/relevance
   - Include metadata: date, total posts, topics covered
3. Cache assembled digest in Redis with key `digest:{date}` (TTL: 7 days)
4. **API Endpoint:**
   - `GET /api/digests/{date}/processed` - Return full processed digest
   - Response: `{date, topics: [{label, posts: [{id, title, summary_sections, hn_url, article_url}]}]}`
   - Serve from Redis cache if available, fallback to JSONL files
   - Requires authentication (JWT)
5. **Email Delivery:**
   - Generate HTML email template using Jinja2 or similar
   - Include topic headers with 1-2 sentence teasers (from overview section)
   - CTA button: "Read full digest" linking to `https://app.url/digests/{date}`
   - Send via SendGrid or Postmark API to all active users
   - Schedule delivery at 7:00 AM (configurable per user in future)
   - Track: delivery status, bounce rates
6. **Web Frontend (Simple React View):**
   - Fetch digest via API on page load
   - Display topics as expandable card sections
   - Each post shows: title, overview (visible), full 6 sections (expand on click)
   - Collapsible UI: accordion or tabs for sections
   - Links: "View on HN" and "Read original article"
   - Mobile-responsive design
7. **Error Handling:**
   - Email failures: log and retry once after 1 hour
   - API errors: proper error messages, fallback to raw data if processed unavailable
8. **Quality Metrics:**
   - Email delivery success rate > 99%
   - Email open rate > 40% (analytics pixel tracking)
   - Web app loads digest in < 2 seconds
   - No broken links or formatting issues
9. **Scheduling:**
   - Processing job runs after data collection completes (6:30 AM)
   - Email delivery at 7:00 AM
   - Background job via cron or APScheduler
10. Logging: delivery status, open rates, errors, user engagement

---

## Epic 3: User Preferences & Personalization

**Epic Goal:**

Enable personalized digest experience through explicit user preferences (tone, length, reading time, language) that control how summaries are generated and delivered, providing immediate value without requiring behavioral learning or historical data.

### Story 3.1: User Preference Settings

**As a** user
**I want** to set my preferred tone, summary length, reading time, and output language
**So that** digests match my learning style and time constraints

**Acceptance Criteria:**

1. **Preference dimensions:**
   - **Tone:** ELI5 (simple), Technical (jargon), Executive (strategic), Balanced (default)
   - **Length:** Short (200 words), Standard (500 words), Long (1000 words)
   - **Reading Time:** Quick (5-10 min = 10 posts), Standard (15-20 min = 20 posts), Deep (30-40 min = 30 posts)
   - **Language:** English (default), Spanish, French, German, Chinese, Japanese
2. Store preferences in `data/users/user-profiles.jsonl` (append user record on update)
3. Cache in Redis `user:{user_id}:prefs` for fast access (JSON object)
4. **Onboarding integration:**
   - Optional preference selection during signup (skip = defaults)
   - Show preview of how preferences affect summaries
5. **Settings page:**
   - Radio buttons or dropdown for each preference dimension
   - Save button with immediate feedback ("Preferences updated!")
   - Reset to defaults option
6. **API Endpoint:**
   - `GET /api/users/me/preferences` - Retrieve current preferences
   - `PUT /api/users/me/preferences` - Update preferences
   - Input validation: values must match allowed options
7. Default preferences if not set: Balanced tone, Standard length, Standard reading time, English
8. Mobile-responsive settings UI
9. Changes apply to next digest generation (not retroactive)

### Story 3.2: Adaptive Summary Generation Based on Preferences

**As a** user
**I want** summaries generated according to my preferences
**So that** content matches my learning style and language

**Acceptance Criteria:**

1. **Tone customization via LLM prompts:**
   - **ELI5:** Add to prompt: "Explain concepts simply as if to someone unfamiliar with the domain. Avoid jargon, use analogies."
   - **Technical:** Add to prompt: "Use precise technical terminology. Assume advanced domain knowledge. Include implementation details."
   - **Executive:** Add to prompt: "Focus on strategic implications, business impact, and high-level trade-offs. Minimize technical details."
   - **Balanced:** Default prompt (moderate technical depth, accessible language)
2. **Length customization via LLM prompts:**
   - **Short (200 words):** Prompt: "Provide a concise summary in 2-3 sentences per section. Total length ~200 words."
   - **Standard (500 words):** Default prompt (current 6-section format)
   - **Long (1000 words):** Prompt: "Provide detailed explanations with examples. Expand technical sections. Total length ~1000 words."
3. **Language customization:**
   - Add to prompt: "Respond in {language}" (Spanish/French/German/Chinese/Japanese)
   - Use native language for all 6 summary sections
   - Preserve technical terms in English where appropriate
4. **Reading time affects post selection:**
   - Quick (10 posts): Select top 10 posts by relevance/upvotes
   - Standard (20 posts): Default selection
   - Deep (30 posts): Include all fetched posts
5. **Caching strategy:**
   - Generate and cache standard summaries (Balanced + Standard + English) for all posts
   - On-demand generation for custom preferences (ELI5, Technical, Executive, non-English)
   - Cache custom summaries for 24 hours (likely reused by users with same preferences)
6. **Cost estimation:**
   - Standard summaries: $1.60/day (cached, reused)
   - Custom preferences: +$0.10-0.50/user/day depending on customization level
   - Translation adds ~30% token cost
7. **Processing:**
   - Fetch user preferences from Redis before generating digest
   - Apply preferences to LLM prompt template
   - Store preference-specific summaries separately if needed
8. Error handling: fallback to standard summaries if custom generation fails
9. Logging: track preference usage, generation time, cost per preference type

### Story 3.3: Preference-Based Digest Assembly

**As a** user
**I want** my daily digest assembled according to my preferences
**So that** I receive the right amount and style of content consistently

**Acceptance Criteria:**

1. **Digest assembly respects reading time preference:**
   - Quick: Include 10 posts (distributed across topics)
   - Standard: Include 20 posts (default)
   - Deep: Include 30 posts (all available)
   - Selection prioritizes higher-quality posts (HN points, comment count)
2. **Apply user's tone and length preferences consistently across all summaries in digest**
3. **Email template reflects preferences:**
   - Subject line: Adjust based on reading time ("Quick Digest: 3 Topics" vs "Deep Dive: 30 Posts")
   - Include estimated reading time in email header
   - Teaser length matches summary length preference
4. **Web UI shows preference context:**
   - Display active preferences at top of digest ("Showing: Technical tone, Standard length")
   - Link to settings page to adjust
5. **Preference persistence:**
   - Once set, preferences apply to all future digests until changed
   - No need to re-select daily
6. **API endpoint:**
   - `GET /api/digests/{date}/personalized` - Returns digest customized for authenticated user
   - Fetches user preferences from Redis
   - Generates or retrieves preference-specific summaries
   - Response includes preference metadata
7. **Performance:**
   - Personalized digest assembly < 2 seconds (using cached summaries)
   - Custom summary generation (if needed) < 30 seconds total
8. **User feedback collection:**
   - After reading, prompt: "Was this the right length/tone for you?"
   - Track preference changes over time
   - Use feedback to validate preference effectiveness
9. Error handling: fallback to standard digest if personalization fails
10. Logging: track personalized digest requests, preference combinations used

---

## Epic 4: HN Comment Integration - Community Wisdom Extraction

**Epic Goal:**

Enhance summaries with community insights by fetching HN comment threads, filtering for quality using upvotes/karma/relevance scoring, and extracting 3-5 key points from high-value discussions to provide practical perspectives that complement article summaries.

### Story 4.1: Comment Data Pipeline with Quality Filtering

**As a** system
**I need** to fetch and filter high-quality HN comments
**So that** only valuable community insights are surfaced to users

**Acceptance Criteria:**

1. Integrate with HN Comments API for each post in daily digest
2. Fetch comment threads up to 3 levels deep using `GET /items/:id` endpoint
3. **Quality scoring algorithm:**
   - `score = (upvotes * 2) + (user_karma / 100) + depth_bonus - length_penalty`
   - `depth_bonus`: root comment = 10, level 1 = 5, level 2 = 2
   - `length_penalty`: < 50 chars = -5, > 1000 chars = -3
4. **Filtering rules:**
   - Remove: [deleted], [flagged], very short comments (< 20 chars)
   - Minimum quality score threshold: 15 (tunable)
   - Extract metadata: comment_id, author, author_karma, text, upvotes, parent_id, depth
5. Rank comments by quality score descending
6. Limit to top 10-15 comments per post to avoid processing thousands
7. Store filtered comments to `data/raw/YYYY-MM-DD-comments-filtered.jsonl`
8. **Edge case handling:**
   - Posts with no comments: skip comment processing
   - Spam threads (high downvote ratio, multiple [flagged]): skip entirely
   - Rate limits: 1-2s delays between comment API requests
9. **Performance:**
   - Comment fetching parallel with article content fetching (Story 1.1)
   - Processing time: < 10 minutes for 30 posts × 15 comments = 450 comments
   - API calls: ~30-60 requests/day (one per post, some nested)
10. Error handling: timeout (30s per post), retry (2x), log failures
11. Logging: comments fetched per post, quality score distribution, filter statistics

### Story 4.2: Community Insight Extraction & Summarization

**As a** user
**I want** to see key insights from HN comment discussions
**So that** I understand community consensus, practical experience, and expert opinions without reading hundreds of comments

**Acceptance Criteria:**

1. **Analyze filtered comments to identify themes:**
   - Real-world experience: "I used this at [company], here's what we learned"
   - Technical critiques or alternatives: "This approach has X limitation, consider Y"
   - Implementation advice: "Gotcha: watch out for Z"
   - Community consensus or disagreement signals
2. **LLM-based insight extraction:**
   - Prompt: "Extract key insights from these HN comments. Focus on: practical experience, technical critiques, implementation advice, community consensus. Return 3-5 bullet points."
   - Input: top 10-15 filtered comments from Story 4.1
   - Output: 3-5 key points (150-200 words total)
3. **Generate "Community Insights" section with:**
   - 3-5 key points from discussions
   - Consensus signals: "Most commenters agree...", "Divided opinion on...", "Several users report..."
   - Notable perspectives from high-karma users (karma > 5000)
   - Practical warnings or gotchas mentioned repeatedly
4. **Attribution approach:**
   - Generic attribution: "One commenter with production experience notes..."
   - No usernames in summaries (privacy)
   - Paraphrase, don't quote directly
5. **Quality checks:**
   - If no valuable comments found → skip Community Insights section entirely
   - LLM prompt includes: "If comments are low-quality or off-topic, return empty"
   - Ensure insights are non-redundant with article summary (LLM validation)
6. Store community insights to `data/processed/YYYY-MM-DD-community-insights.jsonl`
7. **Cost estimation:**
   - ~30 posts/day × $0.02/post for insight extraction = $0.60/day
   - Total comment processing cost: < $1/day
8. **Processing:**
   - Run after summary generation (Story 2.2)
   - Parallel processing: 5-10 posts simultaneously
   - Timeout: 2 min per post
9. Error handling: LLM failures (retry 2x), timeout (skip insights for that post)
10. Logging: insights generated per post, processing time, cost tracking
11. Quality target: 95%+ relevance (manual spot-check during beta)

### Story 4.3: Integration into Daily Digest & UI

**As a** user
**I want** community insights visually integrated into my digest
**So that** I can easily find and read community perspectives alongside article summaries

**Acceptance Criteria:**

1. **Add "Community Insights" section to summary template:**
   - Position: After "AI Opinions" section (7th section in expanded view)
   - Visual distinction: Different background color or icon (💬 comment icon)
   - Label: "Community Insights - From HN Discussion"
2. **UI design:**
   - Collapsible section (collapsed by default or expanded based on user preference)
   - Show/hide toggle: "View HN community insights" button
   - Clear visual separation from AI-generated content
   - Mobile-responsive display
3. **Link to original HN thread:**
   - "View full discussion on HN" link at bottom of insights
   - Link format: `https://news.ycombinator.com/item?id={post_id}`
   - Opens in new tab
4. **Graceful handling:**
   - If no community insights generated → section doesn't appear at all
   - No empty/placeholder sections
5. **Email version:**
   - Abbreviated community insights (3 points max instead of 5)
   - Same "View full discussion" link
6. **API response format:**
   - Add `community_insights` field to summary object
   - Structure: `{insights: string[], hn_discussion_url: string, has_insights: boolean}`
7. **Performance:**
   - Comment processing runs in parallel with summary generation
   - Timeout: if comment processing > 5 min, skip and deliver digest without insights
   - Progressive enhancement: deliver digest, add comments later if needed (future)
8. **User preferences:**
   - Future: allow users to hide/show community insights globally
   - MVP: insights always included when available
9. **Quality metrics:**
   - Read rate: 70%+ of users read community insights section
   - User feedback: "Was this insight useful?" thumbs up/down
   - Opt-out rate: < 10% (users don't hide insights)
10. Error handling: missing insights → section omitted gracefully
11. Logging: insights shown per digest, user engagement (expand/collapse), link clicks to HN

---

## Next Steps

After PRD approval, the following specialized experts should be engaged:

### 1. UX/UI Design Expert

**Prompt for UX Expert:**

```
You are a UX/UI expert specializing in content-heavy applications and learning platforms.

Context: We're building a HackerNews Knowledge Graph Builder - a daily digest tool that transforms HN content into structured learning experiences with topic clustering, educational summaries, and personalization.

Task: Review the PRD (sections: User Interface Design Goals, Epic Details) and create:

1. High-fidelity wireframes for core screens:
   - Onboarding flow (3 steps)
   - Daily digest view (topic clusters, expandable summaries)
   - Profile & settings page
   - Email template

2. Interaction specifications:
   - Expand/collapse behavior for summaries
   - Voting UI patterns
   - Preference selection flows
   - Mobile vs. desktop adaptations

3. Design system basics:
   - Color palette (neutral base + accent colors)
   - Typography scale (UI vs. content)
   - Component library (buttons, cards, accordions)
   - Iconography set

4. Accessibility audit:
   - WCAG AA compliance checklist
   - Keyboard navigation flows
   - Screen reader considerations

Deliverables: Figma designs + interaction specs document

Timeline: 2 weeks
```

### 2. System Architect

**Prompt for Architect:**

```
You are a system architect specializing in data pipelines and API design.

Context: We're building a HackerNews Knowledge Graph Builder with separate data collection, processing, and API services. Tech stack: Python, FastAPI, JSONL files, Redis, LLM APIs.

Task: Review the PRD (sections: Technical Assumptions, Epic Details) and create:

1. Detailed system architecture diagram:
   - Data collection service (HN API → JSONL)
   - Data processing service (clustering, summarization)
   - Backend API (FastAPI)
   - Frontend (Next.js)
   - Redis caching layer
   - LLM integration points

2. API specification (OpenAPI):
   - All endpoints with request/response schemas
   - Authentication flow (JWT)
   - Error handling patterns
   - Rate limiting strategy

3. Data models:
   - JSONL schemas for: posts, comments, summaries, user profiles, votes
   - Redis cache keys and TTLs
   - File organization structure

4. Processing pipeline design:
   - Job scheduling (cron/APScheduler)
   - Parallelization strategy (asyncio)
   - Error recovery and retry logic
   - Cost optimization (LLM API usage)

5. Deployment architecture:
   - Docker containerization
   - Environment configuration
   - Monitoring and logging strategy
   - Scalability considerations

Deliverables: Architecture diagrams + API specs + data schemas + deployment guide

Timeline: 2 weeks
```

---

**PRD Status:** Draft Complete - Pending Review

**Next Actions:**
1. Stakeholder review and approval
2. Engage UX Expert for design phase
3. Engage Architect for technical specification
4. Begin Epic 1 implementation after designs and specs are ready

**Document Prepared By:** John (PM Agent)
**Date:** 2025-10-19
