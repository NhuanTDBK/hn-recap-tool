# Recommendations

Picks posts the reader is likely to want, learned from what they **Save**, and sends them to their own forum topic. The goal is to scroll less in the Streaming topic, which stays unchanged.

The job runs several times a day (default 08:30, 12:30, 16:30, 20:30 in Asia/Ho_Chi_Minh). Each run makes one LLM call.

## How it picks

The model acts like a personal editor with a clippings folder: saved posts are examples of taste, and the taste is derived again on every run.

| Signal | Source | Weight |
|--------|--------|--------|
| Save | `user_activity_log` action `save` | strong yes |
| 👎 Not for me | action `not_for_me` | strong no |
| More, with no other verdict | action `show_more` | weak yes |
| Recommended and left untouched, last 14 days | `recommendations` with no activity | weak no |

- If a post has both a Save and a Not for me tap, the newer tap wins.
- 💡 Why only counts as engagement. It does not change the verdict.
- The model returns a **fit** from 3 to 5 per post and the interests it inferred. Code keeps `fit >= RECOMMENDATION_MIN_FIT` (3, so everything the model returns), sorts best first, and cuts to the day's remaining room (if a cap is set).
- There is **no daily limit** by default (`RECOMMENDATION_DAILY_MAX=0`). Set it above 0 to add a ceiling. Either way a quiet day sends few posts, and nothing is padded.
- If the model's reply cannot be parsed twice, the run sends nothing. There is no fallback to "top by score".

## One run

1. Resend unsent picks from earlier runs (up to one day old).
2. Stop with `too_soon` if the last run started under `RECOMMENDATION_MIN_GAP_MINUTES` ago (unless `--force`).
3. If `RECOMMENDATION_DAILY_MAX` is above 0, stop with `daily_cap_reached` when the day already has that many picks. No LLM call is made.
4. Stop with `too_few_saves` if there are under `RECOMMENDATION_MIN_SAVES` saves.
5. Load candidates: summaries for this feed newer than the last run (at most `RECOMMENDATION_LOOKBACK_HOURS` back), live crawled stories, not already saved, rejected or recommended. At most 150, highest score first.
6. One LLM call ranks them.
7. Store the run and picks, then send each pick (there is no header message), marking each sent as Telegram accepts it.

### Why posts are not repeated

- The candidate filter leaves out every post ever recommended, and the next run only looks past the last run's start time.
- `recommendations` has `UNIQUE (user_id, post_id)`, and picks are inserted with `ON CONFLICT DO NOTHING`. Two runs that overlap cannot both send the same post.
- The day is the local date in `RECOMMENDATION_TIMEZONE`. A cap, if set, counts every pick stored for that date.

## Messages and buttons

Each pick is one message with `[📖 More] [🔖 Save]` and `[💡 Why] [👎 Not for me]`.

| Button | `callback_data` prefix | Effect |
|--------|------------------------|--------|
| More | `show_more_` | Shows the full summary, logs `show_more` |
| Save | `save_post_` | Logs `save` |
| Why | `why_rec_` | Popup with the stored reason (no LLM call), logs `why` |
| Not for me | `not_for_me_` | Logs `not_for_me`, relabels the button `👎 Noted` |

Handlers are in `app/presentation/bot/handlers/callbacks.py`. Taps in the group are stored against the group's `users` row (`_resolve_feed_user`), so every member's taps shape one shared profile.

## Data

Picks are kept apart from `deliveries` on purpose. A `deliveries` row hides the post from Streaming and breaks the reaction handlers, which expect one row per post.

- `recommendation_runs`: one row per run. `created_at` is the run's start time, used as the next run's window start. Also stores the inferred interests, signal counts, model and tokens.
- `recommendations`: one row per pick: `fit_score`, `reason`, `rank`, `message_id`, `sent_at` (null while unsent).

Migration: `alembic/versions/20261109_add_recommendations.py`.

## Settings

All in `backend/.env`; see `backend/.env.example`.

| Variable | Default | Meaning |
|----------|---------|---------|
| `RECOMMENDATION_ENABLED` | `false` | Registers the scheduler job |
| `TELEGRAM_RECOMMENDATION_TOPIC_ID` | unset | Forum topic for the picks. Unset means nothing is sent |
| `RECOMMENDATION_MODEL` | unset | Ranking model. Unset uses `OPENAI_MODEL`. Production uses `deepseek-v4-pro` |
| `RECOMMENDATION_DAILY_MAX` | `0` | Optional ceiling per local day, across all runs. `0` = no limit |
| `RECOMMENDATION_MIN_FIT` | `3` | Lowest fit that is sent |
| `RECOMMENDATION_HOURS` | `8,12,16,20` | Local hours the job fires |
| `RECOMMENDATION_MINUTE` | `30` | Minute of each hour |
| `RECOMMENDATION_MIN_GAP_MINUTES` | `120` | A run this soon after the last does nothing |
| `RECOMMENDATION_TIMEZONE` | `Asia/Ho_Chi_Minh` | Zone for the hours and the day boundary |
| `RECOMMENDATION_MIN_SAVES` | `5` | Fewer saves than this: skip |
| `RECOMMENDATION_LOOKBACK_HOURS` | `36` | Longest window for candidates |
| `RECOMMENDATION_IGNORED_DAYS` | `14` | How far back untouched picks count as a weak no |

## Operating it

```bash
# Preview: one LLM call, nothing is written or sent. Shows signals, interests, picks and what the cut-off dropped.
.venv/bin/python backend/scripts/run_recommendations.py --dry-run

# Run now. Does nothing if the last run was under the minimum gap ago.
.venv/bin/python backend/scripts/run_recommendations.py

# Run anyway, still within the day's cap (if set)
.venv/bin/python backend/scripts/run_recommendations.py --force

# Backfill: take candidates from a local date (e.g. the first day), not the last run's start
.venv/bin/python backend/scripts/run_recommendations.py --since 2026-11-09
.venv/bin/python backend/scripts/run_recommendations.py --force
```

The exit code is 1 for `ranking_failed`, `send_failed`, `no_topic` and `no_group`.

On the VM a ranking call takes about 3 minutes with the Pro model. Run it detached (`nohup ... > log &`) and read the log, because a dropped ssh session kills a foreground run.

**Deploying changes:** rebuild the image, then recreate **both** `scheduler` and `bot`. The bot holds the button handlers, the scheduler holds the job. Editing `.env` also needs a recreate. Run `df -h /` before a build: the production disk is 19 GB, and one build used about 2 GB (`docker builder prune -af` and `docker image prune -f` give it back afterwards).

## Code map

| Path | Role |
|------|------|
| `app/domain/recommendation.py` | Constants, dataclasses, `classify_activity` |
| `app/application/use_cases/recommendation.py` | One run: guards, selection, cap, sending |
| `app/infrastructure/agents/recommendation_agent.py` | Prompt input, JSON parsing, the LLM call with one retry |
| `app/infrastructure/prompts/recommendation_system.md` | System prompt (static, so it caches) |
| `app/infrastructure/repositories/postgres/recommendation_repo.py` | Queries and conflict-safe insert |
| `app/presentation/bot/handlers/recommendation_delivery.py` | Sends the picks |
| `scripts/run_recommendations.py` | CLI and the function the scheduler calls |
| `scripts/run_scheduler.py` | `schedule_recommendations` registers the cron job |

## Known limits

- The profile is shared by everyone in the group, since taps are stored against the group row.
- "Untouched" is a noisy signal: people skip posts for many reasons.
- The profile can narrow over time, because only things like what was saved or picked feed back in.
- `agent_calls` shows a cost of 0 for `deepseek-*` models because they are missing from the pricing table. Token counts are recorded.
- The SQL queries are covered by compile-time tests, not by a test database. The first production run is the real check.
