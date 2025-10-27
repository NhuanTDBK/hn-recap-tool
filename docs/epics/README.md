# HackerNews Digest - Epic Roadmap

This directory contains epics for the HackerNews Knowledge Graph Builder project.

---

## MVP Epics (Priority 0 - Critical)

### Epic 1: Topic-Clustered Daily Digest with Structured Summaries
**Status:** Not Started
**Timeline:** 6-8 weeks
**File:** [epic-1-topic-clustered-digest.md](./epic-1-topic-clustered-digest.md)

**Goal:** Build the foundational digest system that delivers daily topic-clustered HN content with rich, educational summaries.

**Key Features:**
- HN data pipeline with topic clustering (2-3 topics/day)
- Structured summary generation (6-section learning format)
- Email + web delivery system

**Stories:** 3 stories (HN pipeline, summary engine, delivery system)

---

### Epic 2: Personalization System - Onboarding + Feedback Loop
**Status:** Not Started
**Timeline:** 4-6 weeks (can overlap with Epic 1)
**File:** [epic-2-personalization-system.md](./epic-2-personalization-system.md)

**Goal:** Enable personalized digests through intelligent onboarding and continuous learning from user feedback.

**Key Features:**
- Career/persona-based onboarding (3 questions)
- User voting and feedback system
- Basic recommendation engine

**Stories:** 3 stories (onboarding flow, voting system, recommendation engine)

---

## Post-MVP Epics (Priority 1 - High)

### Epic 3: HN Comment Integration - Community Wisdom Extraction
**Status:** Not Started
**Timeline:** 3-4 weeks (post-MVP v1)
**File:** [epic-3-comment-integration.md](./epic-3-comment-integration.md)

**Goal:** Extract and surface valuable insights from HN comment threads to enrich summaries with community perspectives.

**Key Features:**
- Comment data pipeline with quality filtering
- Community insight extraction & summarization
- Integration into digest UI

**Stories:** 3 stories (comment pipeline, insight extraction, UI integration)

---

## Epic Timeline & Dependencies

```
Week 1-8:    Epic 1 (Topic-Clustered Digest) - Foundation
Week 3-8:    Epic 2 (Personalization) - Overlaps with Epic 1 (depends on web app)
Week 9-12:   Epic 3 (Comment Integration) - Post-MVP enhancement

MVP Launch:  End of Week 8 (Epics 1 + 2 complete)
MVP v1.1:    End of Week 12 (Epic 3 complete)
```

---

## Success Criteria - MVP Launch (End of Week 8)

**Product:**
- Daily topic-clustered digest delivered via email + web
- Structured learning summaries (6-section format)
- Personalized topic selection based on user profile + feedback
- 10-20 beta users actively engaged

**Quality:**
- Topic clustering coherence: 4/5+ rating
- Summary quality: 4/5+ rating
- Content relevance: 70%+ (new users), improving weekly (active users)

**Technical:**
- System runs daily without manual intervention
- Email delivery success rate > 99%
- Processing time < 30 minutes per digest
- Uptime > 99%

---

## Future Epics (Not Yet Defined)

Based on brainstorming session, potential future epics include:

**Post-MVP Innovations (2-6 months):**
- Contextual Source Linking (papers, repos, blogs)
- Cross-Article Synthesis
- Spaced Repetition System
- MCP Integration (ChatGPT/Claude access)
- Shareable Summaries with Attribution
- On-Demand Summarization
- Multi-Source Support (beyond HN)

**Moonshots (6-12+ months):**
- Knowledge Graph Visualization
- AI Research Assistant Mode
- Personal Knowledge Graph as a Service
- Collective Intelligence Layer
- Team Knowledge Graphs

---

## Notes

- All epics reference insights from `docs/brainstorming-session-results.md`
- Epics 1-3 constitute the MVP as defined in brainstorming priorities
- Each epic is designed to be independently deployable and testable
- User feedback from each epic will inform subsequent epic refinement
- Focus on quality over speed - validate learnings before scaling

---

**Last Updated:** 2025-10-19
**Product Manager:** John 📋
