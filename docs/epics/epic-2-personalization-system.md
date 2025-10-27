# Epic 2: Personalization System - Onboarding + Feedback Loop

**Epic ID:** EPIC-002
**Priority:** P0 - Critical (MVP Core)
**Timeline:** 4-6 weeks (can overlap with Epic 1)
**Status:** Not Started
**Dependencies:** Partial dependency on Epic 1 (web app infrastructure)

---

## Epic Goal

Enable personalized HN digests by solving the cold-start problem through career/persona-based onboarding and creating an engagement feedback loop where user signals continuously improve content relevance and summary adaptation.

---

## Epic Description

### Product Vision Context

This epic addresses two critical needs identified in brainstorming:
1. **Cold-start problem:** What content to show new users on Day 1?
2. **Continuous improvement:** How to make digests more valuable over time?

The solution: intelligent onboarding that captures user context + feedback mechanisms that learn preferences.

### What We're Building

A personalization engine that:
- **Onboards new users** with career/persona questions:
  - "What do you do?" (role: backend engineer, CTO, indie hacker, etc.)
  - "What are you working with?" (tech stack: Python, Rust, databases, etc.)
  - "What are you curious about?" (learning goals: ML, distributed systems, etc.)
- **Generates starter topics** based on persona profile
- **Captures user feedback** through voting (upvote/downvote summaries)
- **Tracks engagement** (reads, skips, time spent, clicks)
- **Adapts content** based on accumulated signals
- **Supports topic interest lists** (explicitly follow certain topics)

### Success Criteria

**User Value:**
- New users receive relevant content from Day 1 (70%+ relevance rating)
- Content relevance improves week-over-week (measurable engagement increase)
- Users feel the system "understands" them (qualitative feedback)

**Engagement Metrics:**
- Onboarding completion rate > 80%
- Users vote on 30%+ of summaries
- 2-3 topics added to interest list per user on average
- Week 2 engagement > Week 1 (showing improvement)

**Technical Validation:**
- Recommendation algorithm produces measurably different content per persona
- Feedback signals correctly influence future recommendations
- System adapts within 3-5 days of user interaction

---

## User Stories

### Story 1: Career/Persona-Based Onboarding Flow

**As a** new user
**I want** to answer simple questions about my role and interests
**So that** I receive relevant HN content from Day 1 without manual configuration

**Acceptance Criteria:**
- [ ] Design onboarding UI with 3 key questions:
  1. "What do you do?" - Role selection (dropdown + free text)
  2. "What are you working with?" - Tech stack (multi-select tags + custom)
  3. "What are you curious about?" - Learning goals (multi-select + custom)
- [ ] Create persona→topic mapping logic
- [ ] Common roles pre-configured: Backend Engineer, Frontend Engineer, Full-Stack, DevOps/SRE, Engineering Manager, CTO/Founder, Indie Hacker, Domain Specialist
- [ ] Common tech tags pre-configured: Python, JavaScript, Go, Rust, Java, Databases, Cloud, ML/AI, Systems, Security, etc.
- [ ] Store user profile in database
- [ ] Generate initial topic preferences from onboarding data
- [ ] Skip onboarding option (use generic default topics)
- [ ] Onboarding can be re-run / profile updated later

**Technical Notes:**
- UI component: multi-step form (3 screens or single page)
- Persona mapping: rule-based initially, can enhance with ML later
- Database schema: user_profiles table with JSON fields for flexibility

**Example Mappings:**
- Backend Engineer + Python + Databases → topics: distributed systems, database internals, Python performance
- CTO/Founder + Cloud + ML → topics: AI trends, scalability, strategic tech decisions
- Indie Hacker + JavaScript + SaaS → topics: startup tools, productivity hacks, monetization

---

### Story 2: User Voting & Feedback System

**As a** user
**I want** to upvote/downvote summaries and add topics to my interest list
**So that** the system learns my preferences and shows me more relevant content

**Acceptance Criteria:**
- [ ] Add voting UI to each summary (thumbs up/down or similar)
- [ ] Add "Add to interest list" button per topic
- [ ] Track voting data: user_id, summary_id, vote (up/down), timestamp
- [ ] Track interest list: user_id, topic, added_date
- [ ] Track implicit signals: read (scroll/time), skip, click-through to original
- [ ] Display user's interest list in profile/settings
- [ ] Allow removing topics from interest list
- [ ] Voting state persists (show voted summaries as voted)
- [ ] Feedback data queryable for recommendation engine

**Technical Notes:**
- Database schema: user_votes table, user_interests table, user_activity table
- Consider analytics events for implicit signals (frontend tracking)
- Privacy: user feedback data is private, not shared

---

### Story 3: Basic Recommendation Engine

**As a** user
**I want** the system to adapt content based on my feedback
**So that** my daily digest becomes more relevant over time

**Acceptance Criteria:**
- [ ] Implement recommendation algorithm that considers:
  - User profile (role, tech stack, learning goals)
  - Voting history (upvoted topics/keywords, downvoted topics)
  - Interest list (explicitly followed topics)
  - Engagement patterns (time spent, read vs. skip)
- [ ] Algorithm produces personalized topic selection for daily digest
- [ ] Users with similar profiles get different content based on their feedback
- [ ] "Explore vs. Exploit" balance: 70% known interests, 30% discovery
- [ ] Topics in interest list get priority coverage
- [ ] Algorithm performance: measurable improvement in engagement over time
- [ ] Fallback to persona-based defaults if insufficient feedback data

**Technical Notes:**
- Start simple: collaborative filtering or content-based filtering
- Consider: TF-IDF on upvoted content, topic similarity scores
- Track engagement metrics to validate algorithm effectiveness
- Future enhancement: more sophisticated ML models

**Algorithm Approach (MVP):**
1. Score topics based on:
   - User profile match (role + tech stack)
   - Interest list (high weight)
   - Upvote history (medium weight)
   - Downvote history (negative weight)
   - Engagement (time spent - medium weight)
2. Select top 2-3 topics per day
3. Include 1 "exploration" topic outside usual preferences

---

## Technical Stack

**Backend:**
- PostgreSQL tables: user_profiles, user_votes, user_interests, user_activity
- Recommendation engine: Python service (can be integrated into main backend)
- Simple collaborative/content-based filtering (scikit-learn or manual)

**Frontend:**
- Onboarding flow UI (React components)
- Voting UI components
- Profile/settings page for interest list management

**Data:**
- User profile schema (role, tech_stack, learning_goals)
- Feedback data schema (votes, interests, activity)
- Topic taxonomy (consistent topic naming across system)

---

## Risks & Mitigation

### Risk 1: Onboarding Friction
**Risk:** Users abandon onboarding, never complete profile setup
**Mitigation:**
- Make onboarding optional (skip → generic defaults)
- Keep it SHORT (3 questions, < 2 minutes)
- Allow profile updates later
- Show immediate value (preview personalized topics)

### Risk 2: Insufficient Feedback Data
**Risk:** Users don't vote enough, system can't learn preferences
**Mitigation:**
- Make voting EASY (prominent UI, one-click)
- Track implicit signals (don't rely only on explicit votes)
- Prompt for feedback after first week ("Help us improve")
- Show impact of feedback ("We're showing you more X based on your votes")

### Risk 3: Recommendation Algorithm Quality
**Risk:** Algorithm doesn't produce better results than random
**Mitigation:**
- Start with simple, proven approaches (collaborative filtering)
- A/B test: personalized vs. generic content
- Track engagement metrics to validate improvement
- Iterate based on data, not assumptions

### Risk 4: Cold-Start for Uncommon Personas
**Risk:** Niche roles/interests don't map well to HN content
**Mitigation:**
- Broad fallback categories (e.g., "systems" vs. specific tech)
- Allow manual topic selection in onboarding
- Generic defaults as safety net
- User can always adjust via feedback

---

## Dependencies

**Internal:**
- Epic 1: Web app infrastructure (user auth, database)
- Epic 1: Topic clustering (need consistent topic taxonomy)

**External:**
- None (self-contained personalization logic)

---

## Definition of Done

- [ ] All 3 stories completed with acceptance criteria met
- [ ] Onboarding flow tested with 10+ beta users
- [ ] Onboarding completion rate > 80%
- [ ] Voting system captures user feedback reliably
- [ ] Recommendation algorithm produces personalized topic selection
- [ ] Users with different profiles receive observably different content
- [ ] Engagement metrics show week-over-week improvement (for users who vote)
- [ ] Profile/settings page allows interest list management
- [ ] Code deployed to production
- [ ] User feedback collected on personalization quality

---

## Success Metrics (Post-Launch)

**Onboarding:**
- Completion rate > 80%
- Average time to complete < 3 minutes
- Users feel setup was easy (qualitative feedback)

**Engagement:**
- Users vote on 30%+ of summaries
- 2-3 topics added to interest list per user
- Week 2 engagement > Week 1 for active users

**Personalization Quality:**
- Users rate content relevance 4/5+ (survey)
- Engagement metrics (time spent, click-through) improve week-over-week
- Users report "it understands me" in feedback

**Technical:**
- Recommendation algorithm produces different topic sets for different personas
- Feedback loop measurably influences content selection
- System adapts within 3-5 days of user feedback

---

## Notes

- Keep onboarding SIMPLE - avoid analysis paralysis
- Make voting frictionless - one-click interaction
- Start with simple recommendation algorithm, iterate based on data
- Communicate to users how their feedback is used ("We noticed you like X, here's more")
- Track everything - data will guide improvements

---

**Next Epic:** Epic 3 - HN Comment Integration (Community Wisdom Extraction)
