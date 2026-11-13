# Recommendation exploration

Mixes a few posts **outside the reader's profile** into the recommendations, so the profile can grow and not only narrow. It is off until `RECOMMENDATION_EXPLORE_ENABLED=true`. The base feature is described in [recommendations.md](recommendations.md).

## Why

The base system is pure exploitation. The model reads the Saves and returns every candidate that matches. Only posts it already thinks fit are ever shown, so the reader can only react to a narrow slice, and the profile learns from that slice alone. Exploring fixes this by showing a small, controlled share of posts that the profile would not pick, and learning from the reaction.

Two things make exploring safe:

- A **quality** rating that ignores taste, so we explore good posts and not junk.
- A **record per topic**, so exploring is deliberate: untried topics get a chance, and topics the reader keeps rejecting stop coming back.

## How it works

The model labels and rates. The code decides how much to explore and what. The model is a poor random number generator, so it never makes that choice.

| Step | Who | What |
|------|-----|------|
| 1 | Code | Reads the topic record from the picks already sent |
| 2 | Model | One call, as before. Returns `picks` (each with a `topic`) and, if asked, up to 8 `explore` offers with a `quality` from 1 to 5 |
| 3 | Code | Applies the fit cut-off to `picks`. These are the **exploit** picks |
| 4 | Code | Works out the explore budget from the number of exploit picks |
| 5 | Code | Picks the explore posts by Thompson sampling over topics |
| 6 | Code | Stores and sends exploit picks first, then explore picks |

There is still one LLM call per run. Exploring adds about 8 short entries to the answer and a topic label to each pick, not a second call.

### Topics

Every pick has a short lower-case `topic` such as `databases` or `llm agents`. The prompt lists the labels already in use (the 40 most sent), with how the reader reacted to each, and asks the model to reuse them. Labels are lower-cased and trimmed in code, so `LLM Agents` and `llm agents` are one topic. Near-duplicates with different words (`database internals` and `databases`) are **not** merged by code; the prompt asks the model to avoid them.

### The topic record

For each topic, the code looks at the picks sent in the last 90 days and what the reader did with each:

| Outcome | Counts as | Weight |
|---------|-----------|--------|
| Save | yes | 1.0 |
| More, with no verdict | yes | 0.3 |
| Not for me | no | 1.0 |
| Sent, no reaction at all, at least a day old | no | 0.2 |
| 💡 Why only | nothing | 0 |
| Sent today | not judged yet | - |

Each weight fades with a half-life of `RECOMMENDATION_TOPIC_HALF_LIFE_DAYS` (30), so an old rejection stops counting after a while. The record is a Beta distribution: `Beta(1 + yes, 1 + no)`. A topic with no history is `Beta(1, 1)`, which is the widest possible guess.

The record comes only from picks that were sent. Saves made in the Streaming topic shape the profile through the model, but they do not carry a topic label, so they do not move this record.

### The explore budget

`RECOMMENDATION_EXPLORE_RATIO` is the share of **all** picks that explore. With `e` exploit picks the run may send `ratio / (1 - ratio) * e` explore picks. At 0.2 that is one explore pick for every four exploit picks.

- The number is rounded up or down at random, so small runs average out to the ratio over a day.
- A run with no exploit picks can still explore once, with probability equal to the ratio.
- `RECOMMENDATION_EXPLORE_MAX_PER_DAY` (3) is a hard ceiling per local day. When it is used up, the model is not even asked for explore offers.
- While fewer than 20 picks have been sent, the ratio is raised to at least 0.4. There is little taste to exploit yet.
- With `RECOMMENDATION_DAILY_MAX` set, explore picks count toward the cap and only fill the room that exploit picks leave.

### Which posts are explored

From the model's offers, the code keeps those that:

1. have `quality >= RECOMMENDATION_EXPLORE_MIN_QUALITY` (4),
2. are not already an exploit pick,
3. are not on a topic in **cooldown**.

It then draws a random number for each remaining offer from its topic's `Beta(1 + yes, 1 + no)` and takes the highest draws, at most one post per topic. This is Thompson sampling:

- an untried topic has a wide spread and wins often,
- a topic the reader keeps saving wins often,
- a topic the reader keeps rejecting or ignoring almost never wins.

### Feedback

| Reader does | Effect |
|-------------|--------|
| Saves an explore pick | The topic's record gains a strong yes. It wins more draws and the model sees the Save |
| Taps Not for me on an explore pick | The record gains a strong no, **and** the topic goes into cooldown for `RECOMMENDATION_EXPLORE_COOLDOWN_DAYS` (30). It is not explored again, but the rest of the profile is untouched |
| Ignores an explore pick | A very weak no. Silence is noisy, and an unfamiliar topic deserves more than one try |
| Taps Not for me on an exploit pick | A strong no on the record. No cooldown, because the model already sees these in `<not_for_me>` |

## What the reader sees

An explore pick looks like any other, with a small label above the title: `🧭 Outside your usual`. The label stays when the reader taps **More**. The **Why** button shows the stored reason, which the model starts with "Outside your usual:" or "Next to your interest in ...:". The buttons are unchanged.

The label is deliberate. It sets the expectation that a miss is fine and keeps a miss from feeling like the bot got worse.

## Data

Migration `alembic/versions/20261110_add_recommendation_exploration.py` adds three columns to `recommendations`:

| Column | Meaning |
|--------|---------|
| `topic` | Topic label. `NULL` on picks made before exploring existed |
| `kind` | `exploit` or `explore`. Existing rows backfill to `exploit` |
| `quality` | 1-5 quality rating. Set on explore picks only |

`fit_score` is `2` on explore picks. The prompt defines fit 2 as "a stretch", which is what an explore pick is.

Topic labels are stored on every pick, **even while exploring is off**. Turn the flag on later and the record already exists.

## Settings

All in `backend/.env`.

| Variable | Default | Meaning |
|----------|---------|---------|
| `RECOMMENDATION_EXPLORE_ENABLED` | `false` | Kill switch. Off means no explore offers are requested and none are sent |
| `RECOMMENDATION_EXPLORE_RATIO` | `0.2` | Share of all picks that explore |
| `RECOMMENDATION_EXPLORE_MAX_PER_DAY` | `3` | Hard ceiling per local day. `0` turns exploring off |
| `RECOMMENDATION_EXPLORE_MIN_QUALITY` | `4` | Lowest quality (1-5) that may be explored |
| `RECOMMENDATION_EXPLORE_COOLDOWN_DAYS` | `30` | Days a rejected explore topic is left alone |
| `RECOMMENDATION_TOPIC_HALF_LIFE_DAYS` | `30` | Days for an outcome's weight to halve |

## Judging whether it works

`run_recommendations.py --dry-run` prints, besides the picks:

- the explore picks that would be sent, and every offer the model made,
- the outcome counts per kind for picks already sent:

```
exploit  judged=40 saved=14 (35%) rejected=6 opened=9 ignored=11
explore  judged=9  saved=2  (22%) rejected=3 opened=1 ignored=3
```

Keep exploring if both hold after a few weeks:

- the explore save rate is at least about a third of the exploit rate,
- the number of distinct topics the reader saves is flat or rising.

If exploring mostly produces rejections, lower `RECOMMENDATION_EXPLORE_RATIO` or raise `RECOMMENDATION_EXPLORE_MIN_QUALITY`. To stop at once, set `RECOMMENDATION_EXPLORE_ENABLED=false` and recreate `scheduler`.

The same numbers can be read from the database:

```sql
SELECT kind, count(*) AS sent FROM recommendations WHERE sent_at IS NOT NULL GROUP BY kind;
```

## Deploying

1. Run `alembic upgrade head` (the deploy script already does).
2. Recreate **both** `scheduler` and `bot`. The bot holds the **More** handler that keeps the label, the scheduler holds the job.
3. Leave `RECOMMENDATION_EXPLORE_ENABLED=false` for a few days to collect topic labels, then switch it on. Run `--dry-run` first and read the explore offers.

## Code map

| Path | Role |
|------|------|
| `app/domain/exploration.py` | Topic record, explore budget, Thompson sampling, metrics. Pure, takes a random source |
| `app/domain/recommendation.py` | `topic` on picks, `explore` on the ranking result, `NewPick` |
| `app/application/use_cases/recommendation.py` | Loads the record, asks for offers, applies the budget, stores both kinds |
| `app/infrastructure/agents/recommendation_agent.py` | `<topics>` and `<explore_limit>` input, `parse_explore` (never raises) |
| `app/infrastructure/prompts/recommendation_system.md` | Topic and Explore instructions |
| `app/infrastructure/repositories/postgres/recommendation_repo.py` | `get_sent_history`, `count_explore_for_day`, `get_kind` |
| `app/presentation/bot/formatters/digest_formatter.py` | The `🧭` label |

## Known limits

- **Topic drift.** The model may label the same subject differently over time. The shared vocabulary and the prompt reduce this; code only merges labels that are equal after trimming and lower-casing.
- **Shared profile.** Everyone in the group shares one record, so a topic one member rejects counts against everyone.
- **Saves outside the recommendations topic** have no label and do not move the record.
- **Low volume.** Hourly runs have few candidates, so the daily ratio and ceiling do most of the work, not the per-run draw.
- **Explore offers are bounded to 8 per run** and come only from that run's candidates (summaries since the last run).
- A broken or missing `explore` list never fails a run. The exploit picks are sent as usual.
- The SQL is covered by compile-time tests only, like the rest of the feature. The first production run is the real check.
