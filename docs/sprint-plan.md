# HackerNews Knowledge Graph Builder - Sprint Plan

**Project:** HackerNews Knowledge Graph Builder MVP
**Timeline:** 8 weeks (4 × 2-week sprints)
**Goal:** Launch MVP with 10-20 beta users
**Prepared by:** Bob (Scrum Master) 🏃
**Date:** 2025-10-21

---

## Sprint Overview

| Sprint | Duration | Focus | Stories | MVP Critical |
|--------|----------|-------|---------|--------------|
| Sprint 1 | Week 1-2 | Foundation: Data Collection & API | 1.1, 1.2, 1.3 | ✅ Critical |
| Sprint 2 | Week 3-4 | Core Value: Processing & Delivery | 2.1, 2.2, 2.3 | ✅ Critical |
| Sprint 3 | Week 5-6 | Personalization | 3.1, 3.2, 3.3 | ✅ Critical |
| Sprint 4 | Week 7-8 | Community Insights + Polish | 4.1, 4.2, 4.3 + Polish | ⚠️ Nice-to-have |

**Key Dependencies:**
- Sprint 2 depends on Sprint 1 (needs data collection working)
- Sprint 3 depends on Sprint 2 (needs digest system working)
- Sprint 4 depends on Sprint 1 & 2 (enhances existing system)

---

## Sprint 1: Foundation - Data Collection & API (Week 1-2)

**Goal:** Establish data pipeline and API skeleton so the team can build features on top

### Stories

#### Story 1.1: HackerNews Data Collection Background Job
**Priority:** P0 - Critical
**Estimate:** 5 story points
**Assignee:** TBD (Backend Developer)

**Tasks:**
1. Set up Python project structure (Poetry, config files)
2. Implement HN Algolia API client
3. Build post fetching logic (front page stories)
4. Implement article content extraction (trafilatura)
5. Add gzip compression for content storage
6. Build comment tree fetching (3 levels deep)
7. Create JSONL file writers with date partitioning
8. Add error handling, retry logic, timeouts
9. Implement logging and monitoring
10. Create cron/APScheduler job configuration
11. Test with 30 posts, verify storage structure

**Acceptance:** Data collection runs successfully, stores to JSONL files

---

#### Story 1.2: FastAPI Application with User Authentication
**Priority:** P0 - Critical
**Estimate:** 3 story points
**Assignee:** TBD (Backend Developer)

**Tasks:**
1. Set up FastAPI project structure
2. Implement user registration endpoint (`POST /api/auth/register`)
3. Implement login endpoint with JWT (`POST /api/auth/login`)
4. Implement profile endpoint (`GET /api/auth/me`)
5. Add bcrypt password hashing
6. Create JSONL user storage
7. Add input validation (email, password)
8. Configure CORS for frontend
9. Set up FastAPI auto-docs (Swagger)
10. Test authentication flow end-to-end

**Acceptance:** Users can register, login, get JWT token, access protected endpoints

---

#### Story 1.3: Data Access API Endpoints
**Priority:** P0 - Critical
**Estimate:** 3 story points
**Assignee:** TBD (Backend Developer)

**Tasks:**
1. Implement `GET /api/digests` (list digest dates)
2. Implement `GET /api/digests/{date}` (get raw posts)
3. Implement `GET /api/posts/{post_id}` (single post details)
4. Add JWT authentication middleware to all endpoints
5. Add JSONL file reading with gzip decompression
6. Implement Redis caching for frequently accessed data
7. Add pagination (limit, offset)
8. Implement error handling (404, 500)
9. Add request logging
10. Test with Postman/curl

**Acceptance:** Frontend can fetch digests via authenticated API

---

### Sprint 1 Definition of Done
- [ ] Data collection job runs daily without manual intervention
- [ ] HN stories, content, and comments stored to JSONL files
- [ ] User authentication working (register, login, JWT)
- [ ] API endpoints return digest data
- [ ] All endpoints have proper error handling
- [ ] Basic logging in place
- [ ] API documentation auto-generated
- [ ] Code reviewed and merged
- [ ] Deployed to dev environment

### Sprint 1 Risks
- **Risk:** HN API rate limits or downtime
  **Mitigation:** Add delays between requests, implement retry logic

- **Risk:** Article extraction failures (paywalls, JS-heavy sites)
  **Mitigation:** Use trafilatura with fallback to raw HTML, log failures

---

## Sprint 2: Core Value - Topic Clustering & Delivery (Week 3-4)

**Goal:** Deliver the first end-to-end digest with topic clustering and summaries

### Stories

#### Story 2.1: Topic Clustering Engine
**Priority:** P0 - Critical
**Estimate:** 5 story points
**Assignee:** TBD (Backend Developer + ML/Data)

**Tasks:**
1. Implement embedding generation (OpenAI API or sentence-transformers)
2. Build K-means clustering algorithm
3. Add HDBSCAN as alternative clustering option
4. Implement topic label generation via LLM
5. Create topic assignment logic (each post → one topic)
6. Add edge case handling (< 10 posts, very diverse)
7. Store clustering results to JSONL
8. Add cost tracking for embeddings
9. Implement quality metrics (coherence logging)
10. Test with 30 posts, verify 2-3 coherent topics

**Acceptance:** Posts clustered into 2-3 labeled topics daily

---

#### Story 2.2: Structured Summary Generation Engine
**Priority:** P0 - Critical
**Estimate:** 8 story points
**Assignee:** TBD (Backend Developer + ML)

**Tasks:**
1. Set up LLM API client (Claude or GPT-4)
2. Implement token counting (tiktoken)
3. Build direct summarization for short articles (< 8K tokens)
4. Build hierarchical summarization for long articles (> 8K tokens)
5. Create 6-section summary prompt templates
6. Add different prompts for post types (Show HN, Ask HN, articles)
7. Include top 3 comments in summarization context
8. Implement parallel processing (asyncio, batch 5-10 posts)
9. Add error handling (LLM failures, timeouts)
10. Store summaries to JSONL
11. Implement cost tracking and daily budget monitoring
12. Test with 30 posts, verify summary quality

**Acceptance:** 30 posts summarized daily in < 20 minutes with quality summaries

---

#### Story 2.3: Digest Assembly & Delivery
**Priority:** P0 - Critical
**Estimate:** 8 story points
**Assignee:** TBD (Backend + Frontend Developers)

**Tasks:**
**Backend:**
1. Build digest assembly logic (group by topic, order)
2. Implement Redis caching for assembled digests
3. Create `GET /api/digests/{date}/processed` endpoint
4. Build HTML email template (Jinja2)
5. Integrate SendGrid or Postmark API
6. Add email delivery scheduling (7 AM)
7. Implement email tracking (delivery status, open rates)

**Frontend:**
8. Set up Next.js project structure
9. Create digest view page (topic clusters)
10. Implement expandable summary UI (accordion)
11. Add "View on HN" and "Read article" links
12. Make mobile-responsive
13. Integrate with API (SWR for caching)

**Testing:**
14. Test full flow: collection → processing → delivery
15. Verify email delivery and web view

**Acceptance:** Users receive daily digest via email and can view on web

---

### Sprint 2 Definition of Done
- [ ] Topic clustering produces 2-3 coherent topics daily
- [ ] 30 posts summarized with 6-section format
- [ ] Summaries rated 4/5+ by beta testers
- [ ] Email delivery working (> 99% success rate)
- [ ] Web app displays digest with expandable summaries
- [ ] Mobile-responsive UI
- [ ] Processing completes in < 30 minutes
- [ ] LLM costs tracked and within budget (~$1.60/day)
- [ ] Code reviewed and merged
- [ ] Deployed to dev environment
- [ ] **MILESTONE:** First end-to-end digest delivered!

### Sprint 2 Risks
- **Risk:** LLM API rate limits or high costs
  **Mitigation:** Use parallel processing wisely, implement caching, monitor costs daily

- **Risk:** Summary quality issues
  **Mitigation:** Test with beta users early, iterate on prompts

- **Risk:** Email deliverability issues
  **Mitigation:** Use reputable service (SendGrid/Postmark), implement retry logic

---

## Sprint 3: Personalization (Week 5-6)

**Goal:** Add user preferences so digests adapt to individual learning styles

### Stories

#### Story 3.1: User Preference Settings
**Priority:** P0 - Critical
**Estimate:** 3 story points
**Assignee:** TBD (Backend + Frontend Developers)

**Tasks:**
**Backend:**
1. Create preference data model (tone, length, reading time, language)
2. Implement `GET /api/users/me/preferences` endpoint
3. Implement `PUT /api/users/me/preferences` endpoint
4. Add input validation for preference values
5. Store preferences in JSONL + Redis cache

**Frontend:**
6. Create settings page UI
7. Add radio buttons/dropdowns for each preference
8. Implement save functionality with feedback
9. Add "Reset to defaults" button
10. Make mobile-responsive

**Testing:**
11. Test preference save/retrieve flow
12. Verify defaults work correctly

**Acceptance:** Users can set and save preferences (tone, length, reading time, language)

---

#### Story 3.2: Adaptive Summary Generation Based on Preferences
**Priority:** P0 - Critical
**Estimate:** 5 story points
**Assignee:** TBD (Backend Developer + ML)

**Tasks:**
1. Create LLM prompt templates for each tone (ELI5, Technical, Executive, Balanced)
2. Create prompt templates for each length (Short, Standard, Long)
3. Add language customization to prompts
4. Implement post selection based on reading time preference
5. Build caching strategy (standard vs. custom summaries)
6. Implement on-demand custom summary generation
7. Add cost tracking for custom preferences
8. Test with different preference combinations
9. Verify fallback to standard summaries works

**Acceptance:** Summaries adapt to user preferences with correct tone/length/language

---

#### Story 3.3: Preference-Based Digest Assembly
**Priority:** P0 - Critical
**Estimate:** 5 story points
**Assignee:** TBD (Backend + Frontend Developers)

**Tasks:**
**Backend:**
1. Implement `GET /api/digests/{date}/personalized` endpoint
2. Add logic to fetch user preferences
3. Apply preferences to digest assembly (post count, tone, length)
4. Customize email subject line based on reading time
5. Add preference metadata to API responses

**Frontend:**
6. Display active preferences at top of digest
7. Add link to settings page
8. Adjust UI based on preferences

**Testing:**
9. Test personalized digest for different preference combos
10. Verify performance (< 2 seconds for cached, < 30s for custom)
11. Collect user feedback on preference effectiveness

**Acceptance:** Each user receives digest customized to their preferences

---

### Sprint 3 Definition of Done
- [ ] Users can set and update preferences
- [ ] Summaries adapt to tone, length, language preferences
- [ ] Reading time preference controls post count
- [ ] Personalized digests delivered via API
- [ ] Email reflects user preferences
- [ ] Custom summary generation works for non-standard preferences
- [ ] Caching strategy working (standard cached, custom on-demand)
- [ ] Cost tracking shows preference impact
- [ ] Code reviewed and merged
- [ ] Deployed to dev environment
- [ ] **MILESTONE:** Personalization working!

### Sprint 3 Risks
- **Risk:** Custom summary generation slows down digest delivery
  **Mitigation:** Implement aggressive caching, fallback to standard summaries

- **Risk:** Translation quality issues for non-English languages
  **Mitigation:** Test with native speakers, iterate on prompts

---

## Sprint 4: Community Insights + Polish (Week 7-8)

**Goal:** Add HN comment insights and polish MVP for beta launch

### Stories

#### Story 4.1: Comment Data Pipeline with Quality Filtering
**Priority:** P1 - Nice-to-have
**Estimate:** 5 story points
**Assignee:** TBD (Backend Developer)

**Tasks:**
1. Extend HN API client to fetch comment threads
2. Implement quality scoring algorithm
3. Add filtering logic (deleted, flagged, short comments)
4. Rank comments by quality score
5. Store filtered comments to JSONL
6. Add edge case handling (no comments, spam threads)
7. Implement parallel fetching with rate limiting
8. Add logging for quality score distribution
9. Test with 30 posts, verify top 10-15 high-quality comments

**Acceptance:** High-quality comments filtered and stored for each post

---

#### Story 4.2: Community Insight Extraction & Summarization
**Priority:** P1 - Nice-to-have
**Estimate:** 5 story points
**Assignee:** TBD (Backend Developer + ML)

**Tasks:**
1. Create LLM prompt for insight extraction
2. Implement comment theme identification
3. Build insight summarization (3-5 bullet points)
4. Add consensus signal detection
5. Implement generic attribution (no usernames)
6. Add quality checks (skip if low-quality comments)
7. Store insights to JSONL
8. Implement parallel processing (5-10 posts)
9. Add cost tracking (~$0.60/day)
10. Test with 30 posts, verify 95%+ relevance

**Acceptance:** Community insights extracted and summarized for each post

---

#### Story 4.3: Integration into Daily Digest & UI
**Priority:** P1 - Nice-to-have
**Estimate:** 3 story points
**Assignee:** TBD (Backend + Frontend Developers)

**Tasks:**
**Backend:**
1. Add `community_insights` field to summary API response
2. Integrate insights into digest assembly
3. Add timeout handling (5 min max for comment processing)

**Frontend:**
4. Create "Community Insights" UI section
5. Add collapsible toggle
6. Add "View full discussion on HN" link
7. Style with visual distinction (comment icon, different background)
8. Make mobile-responsive

**Email:**
9. Add abbreviated community insights to email (3 points max)

**Testing:**
10. Test full flow with comments
11. Verify graceful handling when no insights available
12. Collect user feedback on insight usefulness

**Acceptance:** Community insights integrated into digest UI and email

---

#### Story 4.4: MVP Polish & Bug Fixes
**Priority:** P0 - Critical
**Estimate:** 5 story points
**Assignee:** Full Team

**Tasks:**
1. **Testing:** Run full end-to-end tests with 10 beta users
2. **Bug Fixes:** Address all critical and high-priority bugs
3. **Performance:** Optimize slow API endpoints (< 2s response time)
4. **UX Polish:** Fix UI/UX issues reported by beta users
5. **Documentation:** Update API docs, add user guide
6. **Monitoring:** Set up error tracking and alerting
7. **Deployment:** Deploy to production environment
8. **Beta Launch:** Onboard 10-20 beta users
9. **Feedback Collection:** Set up user feedback forms
10. **Metrics:** Track key metrics (delivery success, engagement, satisfaction)

**Acceptance:** MVP ready for beta launch, no critical bugs, smooth user experience

---

### Sprint 4 Definition of Done
- [ ] Comment quality filtering working
- [ ] Community insights extracted and integrated
- [ ] UI displays insights with proper styling
- [ ] Email includes abbreviated insights
- [ ] All critical bugs fixed
- [ ] Performance optimized (API < 2s, digest processing < 30 min)
- [ ] User documentation complete
- [ ] Monitoring and alerting set up
- [ ] Deployed to production
- [ ] 10-20 beta users onboarded
- [ ] Feedback collection active
- [ ] **MILESTONE:** MVP LAUNCH! 🚀

### Sprint 4 Risks
- **Risk:** Comment processing delays digest delivery
  **Mitigation:** Implement strict timeout (5 min), progressive enhancement (deliver without insights if needed)

- **Risk:** Critical bugs found late in sprint
  **Mitigation:** Start testing early, allocate buffer time for bug fixes

---

## Success Criteria - MVP Launch (End of Week 8)

### Product Success
- ✅ Daily topic-clustered digest delivered via email + web
- ✅ Structured learning summaries (6-section format)
- ✅ Personalized topic selection based on user preferences
- ✅ 10-20 beta users actively engaged

### Quality Success
- ✅ Topic clustering coherence: 4/5+ rating
- ✅ Summary quality: 4/5+ rating (educational, accurate, clear)
- ✅ Content relevance: 70%+ for new users, improving weekly

### Technical Success
- ✅ System runs daily without manual intervention
- ✅ Email delivery success rate > 99%
- ✅ Processing time < 30 minutes per digest
- ✅ Uptime > 99%
- ✅ LLM costs within budget (~$2-3/day total)

---

## Sprint Ceremonies

### Daily Standups (15 min)
- Time: 9:00 AM daily
- Format: What did you do? What will you do? Any blockers?

### Sprint Planning (2 hours)
- Start of each sprint
- Review stories, assign tasks, estimate effort
- Identify dependencies and risks

### Sprint Review (1 hour)
- End of each sprint
- Demo completed stories to stakeholders
- Gather feedback

### Sprint Retrospective (1 hour)
- End of each sprint
- What went well? What can improve? Action items?

---

## Team Roles

| Role | Responsibilities | Sprint Load |
|------|------------------|-------------|
| Backend Developer | API, data pipeline, processing | 13-16 story points/sprint |
| Frontend Developer | Next.js UI, digest view, settings | 8-11 story points/sprint |
| ML/Data Engineer | Clustering, summarization, LLM integration | 8-10 story points/sprint |
| Scrum Master (Bob) | Sprint planning, standups, unblock team | N/A |
| Product Owner (John) | Prioritization, acceptance, stakeholder comms | N/A |

**Note:** Team may need to be cross-functional depending on available resources.

---

## Risk Management

### High Risks
1. **LLM API costs exceed budget**
   - **Mitigation:** Daily cost tracking, caching aggressive, set hard limits
2. **Processing time exceeds 30 minutes**
   - **Mitigation:** Parallel processing, optimize algorithms, reduce scope if needed
3. **Summary quality not meeting 4/5+ rating**
   - **Mitigation:** Iterate on prompts with beta users, A/B test different approaches

### Medium Risks
1. **HN API rate limits or downtime**
   - **Mitigation:** Delays between requests, retry logic, fallback to cached data
2. **Email deliverability issues**
   - **Mitigation:** Use reputable service, implement SPF/DKIM, monitor bounce rates
3. **Comment processing slows delivery**
   - **Mitigation:** Strict timeouts, skip insights if needed

---

## Post-Sprint 4: Future Enhancements (Week 9+)

After MVP launch, potential next sprints:

**Sprint 5-6: Advanced Personalization**
- Onboarding flow (3 questions: role, tech stack, interests)
- Voting system (upvote/downvote summaries)
- Interest list management
- Recommendation engine (adapt based on feedback)

**Sprint 7-8: Knowledge Graph Features**
- Cross-article synthesis
- Contextual source linking
- Spaced repetition system
- Personal knowledge graph visualization

**Sprint 9+: Scale & Monetization**
- Multi-source support (beyond HN)
- Team knowledge graphs
- MCP integration
- Premium tiers

---

**Sprint Plan Status:** Ready for Sprint 1 Kickoff
**Next Action:** Schedule Sprint 1 Planning Meeting
**Prepared by:** Bob (Scrum Master) 🏃
**Date:** 2025-10-21
