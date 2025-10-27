# Epic 1: Topic-Clustered Daily Digest with Structured Summaries

**Epic ID:** EPIC-001
**Priority:** P0 - Critical (MVP Core)
**Timeline:** 6-8 weeks
**Status:** Not Started

---

## Epic Goal

Build the foundational HackerNews Knowledge Graph Builder that delivers daily topic-clustered digests with rich, structured learning summaries - differentiating from all existing HN tools by transforming news consumption into systematic knowledge building.

---

## Epic Description

### Product Vision Context

This epic implements the core value proposition identified in brainstorming: shifting from shallow post-by-post summaries (existing tools) to topic-clustered knowledge building with educational summaries. This is the MVP that proves the concept and validates market demand.

### What We're Building

A daily digest system that:
- Fetches top HackerNews stories (configurable, default 30)
- Groups posts by topic (2-3 topics per day) using intelligent clustering
- Generates structured learning summaries for each post:
  - Overview paragraph
  - Motivation (why this exists/matters)
  - Related works (context, what came before)
  - How it works (technical explanation)
  - Performance (results, benchmarks, trade-offs)
  - AI-generated opinions/analysis (expert perspective)
- Delivers via email notification + web app for full interaction

### Success Criteria

**User Value:**
- Users can understand HN landscape in 10-15 minutes (vs. 1+ hour browsing)
- Summaries enable learning, not just awareness
- Topic clustering reveals connections between posts

**Technical Validation:**
- Topic clustering accuracy > 80% (subjective evaluation)
- Summary quality rated 4/5+ by beta users
- System processes daily digest in < 30 minutes
- Email delivery success rate > 99%

**Business Validation:**
- 10-20 beta users actively engage (open rate > 40%)
- Average time-on-site > 5 minutes
- User feedback validates differentiation from existing tools

---

## User Stories

### Story 1: HN Data Pipeline & Topic Clustering

**As a** system
**I need** to fetch HackerNews stories and cluster them by topic
**So that** users receive organized, topic-based digests instead of chronological lists

**Acceptance Criteria:**
- [ ] Integrate HN API to fetch top stories (configurable count, default 30)
- [ ] Fetch article content for each HN post
- [ ] Implement topic clustering algorithm (LLM-based or embedding similarity)
- [ ] Group posts into 2-3 coherent topics per day
- [ ] Store clustered data in PostgreSQL
- [ ] Handle edge cases (fetch failures, rate limits, malformed content)
- [ ] Topic quality evaluated: posts within topics are semantically related

**Technical Notes:**
- HN API: https://github.com/HackerNews/API
- Clustering approach: TBD (evaluate LLM-based vs. embedding similarity)
- Consider using sentence transformers for embeddings
- Store raw HN data + processed clusters

---

### Story 2: Structured Summary Generation Engine

**As a** user
**I want** to receive rich, educational summaries of HN posts
**So that** I can learn and understand topics deeply, not just skim headlines

**Acceptance Criteria:**
- [ ] Design structured summary template with 6 sections:
  1. Overview paragraph
  2. Motivation (why this matters)
  3. Related works (context)
  4. How it works (technical explanation)
  5. Performance (benchmarks, trade-offs)
  6. AI opinions/analysis
- [ ] Integrate LLM API (OpenAI/Anthropic/open-source)
- [ ] Create prompt engineering for summary generation
- [ ] Handle different post types (Show HN, Ask HN, articles, papers)
- [ ] Generate summaries for all posts in daily digest
- [ ] Summary quality: coherent, accurate, educational (manual QA)
- [ ] Processing time: < 2 minutes per post average

**Technical Notes:**
- LLM selection: evaluate cost vs. quality (GPT-4, Claude, Llama)
- Prompt templates per post type
- Error handling for LLM failures
- Consider caching/reprocessing strategy

---

### Story 3: Email + Web Delivery System

**As a** user
**I want** to receive my daily digest via email and access it on web
**So that** I can read conveniently and interact with the content

**Acceptance Criteria:**
- [ ] Build web application with authentication (email/password)
- [ ] Display daily digest with topic clusters and summaries
- [ ] Implement email delivery system (SendGrid/Postmark/SES)
- [ ] Email template: summary + link to web app for full content
- [ ] Web UI: clean, readable, mobile-responsive
- [ ] Daily job scheduler to trigger digest generation and delivery
- [ ] User can view current digest + past digests (history)
- [ ] Email delivery success rate > 99%

**Technical Notes:**
- Frontend: React/Next.js (TBD)
- Backend: FastAPI or Django
- Email service: evaluate cost and deliverability
- Scheduler: cron job or task queue (Celery, cloud scheduler)
- User authentication: basic email/password initially

---

## Technical Stack

**Backend:**
- Python (FastAPI or Django)
- PostgreSQL for data storage
- LLM API (OpenAI/Anthropic/local model)
- HN API client

**Frontend:**
- React/Next.js (or similar modern framework)
- Mobile-responsive design

**Infrastructure:**
- Cloud hosting (AWS/GCP/Render/Vercel)
- Email service (SendGrid/Postmark/AWS SES)
- Task scheduler (cron/Celery/cloud scheduler)

**Key Dependencies:**
- HackerNews API
- LLM API provider
- Email delivery service

---

## Risks & Mitigation

### Risk 1: Topic Clustering Quality
**Risk:** Clustering algorithm produces incoherent or too many/few topics
**Mitigation:**
- Prototype multiple approaches (LLM-based, embedding similarity, hybrid)
- Manual evaluation with real HN data
- Fallback: manual topic assignment for MVP beta

### Risk 2: LLM Cost/Quality Trade-off
**Risk:** High-quality summaries too expensive, or cheap models produce poor summaries
**Mitigation:**
- Evaluate multiple LLM providers (OpenAI, Anthropic, open-source)
- Start with quality (GPT-4/Claude), optimize cost later
- Implement usage tracking and cost monitoring

### Risk 3: Email Deliverability
**Risk:** Emails land in spam, low open rates
**Mitigation:**
- Use reputable email service (SendGrid/Postmark)
- Proper SPF/DKIM/DMARC setup
- Warm up sending domain gradually
- Monitor deliverability metrics

### Risk 4: Processing Time
**Risk:** Daily digest generation takes too long (> 1 hour)
**Mitigation:**
- Parallel processing for summaries
- Optimize LLM prompts for speed
- Start generation early (e.g., 5am) to deliver by 7am

---

## Dependencies

**External:**
- HackerNews API (public, no auth required)
- LLM API provider account and API keys
- Email service account and configuration
- Cloud hosting account

**Internal:**
- None (this is first epic)

---

## Definition of Done

- [ ] All 3 stories completed with acceptance criteria met
- [ ] Topic clustering produces 2-3 coherent topics per day
- [ ] Structured summaries are educational and accurate (4/5+ quality)
- [ ] Daily digest delivered via email + accessible on web
- [ ] System runs automated daily without manual intervention
- [ ] 10-20 beta users successfully onboarded and receiving digests
- [ ] User feedback collected and documented
- [ ] Code deployed to production environment
- [ ] Basic monitoring and alerting in place

---

## Success Metrics (Post-Launch)

**Engagement:**
- Email open rate > 40%
- Web app visit rate > 60% of email opens
- Average time on site > 5 minutes
- Returning users > 70% week-over-week

**Quality:**
- Summary quality rating 4/5+ (user survey)
- Topic coherence rating 4/5+ (user survey)
- User reports 50%+ time savings vs. manual HN browsing

**Technical:**
- System uptime > 99%
- Daily digest delivery on-time > 95%
- Processing time < 30 minutes per digest

---

## Notes

- This epic is the foundation for all future features
- Quality over speed - prioritize summary quality in MVP
- Gather extensive user feedback for iteration
- Keep scope tight - resist feature creep during MVP
- Document learnings for Epic 2 & 3 implementation

---

**Next Epic:** Epic 2 - Personalization System (Onboarding + Feedback Loop)
