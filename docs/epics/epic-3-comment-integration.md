# Epic 3: HN Comment Integration - Community Wisdom Extraction

**Epic ID:** EPIC-003
**Priority:** P1 - High (MVP Enhancement)
**Timeline:** 3-4 weeks (post-MVP v1)
**Status:** Not Started
**Dependencies:** Epic 1 (digest system must exist)

---

## Epic Goal

Extract and surface valuable insights from HackerNews comment threads to enrich summaries with community wisdom, practical perspectives, and expert opinions - leveraging HN's unique characteristic of high-quality technical discussions.

---

## Epic Description

### Product Vision Context

From brainstorming insights:
- **"HN comments often contain more value than the posts themselves"**
- **"No existing tool does this well - clear differentiation"**
- **"Opinion synthesis is CRITICAL"** (especially for CTOs/decision-makers)

HackerNews discussions frequently contain:
- Real-world experience reports ("I used this in production, here's what happened")
- Expert technical analysis and critiques
- Alternative approaches and trade-offs
- Implementation gotchas and best practices
- Community consensus or disagreement signals

### What We're Building

A comment intelligence system that:
- **Fetches comment threads** for HN posts in daily digest
- **Filters for quality** using signals: upvotes, user karma, thread depth, relevance
- **Extracts valuable insights** up to 3 levels deep in comment threads
- **Summarizes community wisdom** into digestible insights
- **Integrates into summaries** as "Community Insights" section
- **Surfaces consensus/disagreement** (e.g., "Most commenters agree X, but Y raises concerns about Z")

### Success Criteria

**User Value:**
- Users discover insights they wouldn't find by skimming comments manually
- Community perspective adds practical context to articles
- Readers trust community insights (4/5+ credibility rating)

**Quality Metrics:**
- Extracted comments are relevant to the post (95%+ relevance)
- Quality filtering works (no spam, low-value comments)
- Community insights add new information (not redundant with article summary)

**Engagement:**
- Users read community insights section (70%+ read rate)
- Users find community insights valuable (4/5+ usefulness rating)
- Time savings: users don't need to manually browse HN comments

---

## User Stories

### Story 1: Comment Data Pipeline with Quality Filtering

**As a** system
**I need** to fetch and filter high-quality HN comments
**So that** only valuable community insights are surfaced to users

**Acceptance Criteria:**
- [ ] Integrate HN Comments API for each post in daily digest
- [ ] Fetch comment threads up to 3 levels deep
- [ ] Implement quality scoring algorithm using:
  - Comment upvote count (higher = better)
  - Commenter karma (established users more credible)
  - Thread depth (root comments + 1-2 reply levels)
  - Comment length (too short = low signal, too long = edge case)
  - Time posted (early insightful comments vs. late noise)
- [ ] Filter out: [deleted], [flagged], very short comments (< 20 chars)
- [ ] Rank comments by quality score
- [ ] Store comments with metadata in database
- [ ] Handle edge cases: posts with no comments, spam threads, rate limits

**Technical Notes:**
- HN Comments API: https://github.com/HackerNews/API
- Quality scoring: weighted algorithm (tune weights based on testing)
- Consider comment text analysis (keyword relevance to post topic)
- Limit: top 10-15 comments per post (avoid processing thousands)

**Quality Scoring Formula (initial):**
```
score = (upvotes * 2) + (karma / 100) + depth_bonus - length_penalty
depth_bonus: root=10, level1=5, level2=2
length_penalty: < 50 chars = -5, > 1000 chars = -3
```

---

### Story 2: Community Insight Extraction & Summarization

**As a** user
**I want** to see key insights from HN comment discussions
**So that** I understand community consensus, practical experience, and expert opinions without reading hundreds of comments

**Acceptance Criteria:**
- [ ] Analyze filtered comments to identify themes:
  - Real-world experience ("I used this at [company], here's what we learned")
  - Technical critiques or alternatives ("This approach has X limitation, consider Y")
  - Implementation advice ("Gotcha: watch out for Z")
  - Community consensus or disagreement
- [ ] Use LLM to extract and summarize key insights from top comments
- [ ] Generate "Community Insights" section with:
  - 3-5 key points from discussions
  - Consensus signals ("Most commenters agree...", "Divided opinion on...")
  - Notable perspectives from high-karma users
  - Practical warnings or gotchas
- [ ] Attribute insights generically ("One commenter with production experience notes...")
- [ ] Handle cases: no valuable comments → skip section
- [ ] Quality check: insights are non-redundant with article summary

**Technical Notes:**
- LLM prompt: "Extract key insights from these HN comments. Focus on: practical experience, technical critiques, implementation advice, community consensus."
- Consider comment grouping by theme before summarization
- Avoid direct quotes (privacy/attribution concerns) → paraphrase
- Length target: 3-5 bullet points, ~150-200 words total

---

### Story 3: Integration into Daily Digest & UI

**As a** user
**I want** community insights visually integrated into my digest
**So that** I can easily find and read community perspectives alongside article summaries

**Acceptance Criteria:**
- [ ] Add "Community Insights" section to summary template (after AI Opinions)
- [ ] UI design: clearly distinguish community insights from article summary
- [ ] Visual indicators: comment icon, "From HN Discussion" label
- [ ] Link to original HN comment thread ("View full discussion on HN")
- [ ] Mobile-responsive display
- [ ] Show/hide toggle if user prefers to skip community insights
- [ ] Graceful handling: no comments → section doesn't appear
- [ ] Performance: comment processing doesn't delay digest delivery

**Technical Notes:**
- UI component: collapsible section or inline display
- Link format: https://news.ycombinator.com/item?id={post_id}
- Consider lazy-loading comments (fetch on-demand vs. batch with digest)
- Email version: abbreviated community insights (3 points max)

---

## Technical Stack

**Backend:**
- HN Comments API integration
- PostgreSQL table: hn_comments (post_id, comment_id, text, score, metadata)
- Quality filtering algorithm (Python)
- LLM API for comment summarization

**Frontend:**
- Community Insights UI component
- Show/hide toggle
- Link to HN discussion

**Processing:**
- Add comment fetching to daily digest pipeline
- Parallel processing: comments fetched alongside article summaries
- Timeout handling: don't block digest if comment processing fails

---

## Risks & Mitigation

### Risk 1: Comment Quality Varies Widely
**Risk:** Even filtered comments contain noise, irrelevant tangents
**Mitigation:**
- Conservative quality threshold (better to miss some good comments than include bad ones)
- LLM filtering: prompt to skip irrelevant/low-value content
- User feedback: "Was this insight useful?" to tune algorithm
- Manual spot-check during beta to calibrate filters

### Risk 2: Processing Time Impact
**Risk:** Fetching/processing comments delays daily digest delivery
**Mitigation:**
- Parallel processing (comments fetch alongside summaries)
- Timeout: if comment processing > 5 min, skip and deliver digest
- Optimize: fetch only top-level + 1 reply level initially
- Consider async: deliver digest, add comments later (progressive enhancement)

### Risk 3: Attribution & Privacy Concerns
**Risk:** Surfacing user comments without attribution or with attribution that feels invasive
**Mitigation:**
- Paraphrase, don't quote directly
- Generic attribution ("A commenter with startup experience notes...")
- No usernames in summaries
- Link to full thread for context

### Risk 4: Comment Thread Signal-to-Noise
**Risk:** For some posts, comments are pure noise (flame wars, off-topic)
**Mitigation:**
- Detect low-quality threads: high downvote ratio, [flagged] comments, short comments
- Skip community insights section if no valuable comments found
- LLM prompt: "If comments are low-quality or off-topic, return empty"

---

## Dependencies

**Internal:**
- Epic 1: Daily digest system (this enhances existing summaries)
- Epic 1: LLM infrastructure (reuse for comment summarization)

**External:**
- HN Comments API

---

## Definition of Done

- [ ] All 3 stories completed with acceptance criteria met
- [ ] Comment fetching and filtering pipeline operational
- [ ] Quality scoring algorithm produces relevant comments (95%+ relevance in spot-check)
- [ ] Community insights integrated into daily digest
- [ ] UI displays community insights clearly and distinctly
- [ ] Link to original HN thread works correctly
- [ ] Comment processing doesn't delay digest delivery
- [ ] Beta users validate: insights are valuable and non-redundant
- [ ] Code deployed to production
- [ ] User feedback collected on community insights quality

---

## Success Metrics (Post-Launch)

**Engagement:**
- 70%+ of users read community insights section
- Click-through to HN thread: 20%+ (shows interest in full discussion)
- Users don't disable/hide community insights (< 10% opt-out)

**Quality:**
- Community insights rated 4/5+ for usefulness (user survey)
- Insights rated 4/5+ for credibility (user survey)
- Insights add new information (not redundant): 90%+ non-redundancy

**Technical:**
- Comment quality filtering: 95%+ relevance (manual spot-check)
- Processing time impact: < 5 minutes added to digest generation
- Comment fetch success rate: > 95% (handle API failures gracefully)

**User Feedback:**
- Users report: "I learn more from community insights than I would browsing HN comments manually"
- CTOs/decision-makers find community perspective valuable for "hype vs. reality" assessment

---

## Future Enhancements (Post-Epic)

**Not in scope for Epic 3, but potential future work:**
- Sentiment analysis (detect community enthusiasm vs. skepticism)
- Identify expert commenters (HN power users, domain experts)
- Thread structure analysis (find deep technical sub-threads)
- User preference: comment insight detail level (brief vs. comprehensive)
- Comment-based topic signals (trending discussions, controversial topics)

---

## Notes

- HN comment quality is a competitive advantage - no existing tool does this well
- Start conservative on quality filtering (better to miss some good comments than include noise)
- Community insights are especially valuable for "Show HN" and controversial posts
- This feature differentiates from pure LLM summarizers (community perspective, not just AI analysis)
- Track user feedback closely - this is experimental and may need iteration

---

**Related Epics:**
- Epic 1: Topic-Clustered Daily Digest (foundation)
- Epic 2: Personalization System (user preferences may extend to comment insights)
- Future: Opinion Synthesis (community insights feed into broader opinion analysis)
