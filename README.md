
We are born too early to have cured migraine. I am deeply sorry for that.

Dedicated to my twin.

---

# migraine

Private, non-commercial research tooling for the care of one migraine patient:

- **Headache diary analysis** (`src/preprocessing`, `src/report`): turns the patient's diary into a summary report for their doctor. The diary data is never committed to this repository.
- **r/migraine case research**: finds first-hand reports in r/migraine that resemble the patient's symptom pattern, triggers and treatment history, so the options can be discussed with their doctor.

## Approach

Reddit declined the request for official Data API access in October 2026, and its public API closes in March 2027. The case research therefore uses **[Arctic Shift](https://github.com/ArthurHeitmann/arctic_shift)**, a public, community-run archive of Reddit content. It covers r/migraine from 2009 to the present: about 160k posts and 2.1M comments. Reddit has not licensed this data, so it is used only for private, non-commercial case research, and nothing from it is republished.

Instead of collecting a few thousand threads through live API searches, the subreddit's posts are downloaded once into a local database. They are then narrowed in stages, from cheap and broad to expensive and precise, until a short list is left for a person to read:

1. **Regular expressions and keywords** grouped by the patient's features (aura, medications, triggers, hormonal factors…). Transparent and cheap, and aimed at recall: 160k posts become a few thousand candidates.
2. **Local embeddings** rank the candidates by similarity to a short, de-identified patient profile. The model runs on this machine, so the candidates and the profile stay local. No trained classifier is needed until there are labelled examples.
3. **An LLM reads only the shortlist** (a few hundred threads, with their comments, which are fetched only at this point). It fills in fixed fields: features, triggers, treatments tried, what helped, outcome, and a similarity score with a short reason.
4. **A person reviews the top results.** Their verdicts are used to tune the earlier stages.

The headache diary never leaves this machine. Only the de-identified profile and public post text are sent to the LLM.

## Pipeline

```
                    Arctic Shift API (r/migraine, 2009 → today)
                                      │
                       ingest (one-time + incremental)
                       drop authors, drop deleted/removed
                                      ▼
   ┌──────────────── data/migraine.duckdb (local, gitignored) ────────────────┐
   │  posts (~160k)   comments (shortlist only)   screening   runs            │
   └──────────────────────────────────────────────────────────────────────────┘
                                      │
   1. filter   regex / keyword flags        resources/screening/patterns.yaml
               160k ──► ~5–20k candidates
                                      │
   2. rank     local embedding similarity   resources/screening/profile.yaml
               candidates ──► top ~1k       (patient profile, local only)
                                      │
   3. read     fetch comments for the top ~300 threads
               LLM fills structured fields + similarity score 0–3 + reason
                                      │
   4. review   top ~50 as a table/report ──► verdicts tune stages 1–2
```

| Stage | Module (planned) | Command (planned) | Output |
|---|---|---|---|
| ingest | `clients/arctic_shift.py`, `services/ingest.py` | `python -m main.ingest` | `posts` table |
| filter | `services/screen.py` | `python -m main.screen --stage filter` | regex flags in `screening` |
| rank | `services/screen.py` | `python -m main.screen --stage rank` | similarity score in `screening` |
| read | `services/screen.py`, LLM client | `python -m main.screen --stage read` | comments + LLM fields in `screening` |
| review | `report/` | `python -m main.review` | ranked table / report |

Status: the stages above are planned. What exists today is the original Reddit API client and collector (below), which needs official credentials and is kept for reference.

## Data handling

- **Only content is kept:** post title and text, comment text, scores, timestamps, flair and permalink. **Usernames and author fields are dropped when the data is collected** and never written to disk (see `src/models/reddit.py`).
- Posts and comments that were deleted or removed on Reddit are excluded, even when the archive still has their text.
- No attempt is made to identify, profile or contact any user.
- Data is stored locally in `data/`, which is gitignored and never committed. The patient profile (`resources/screening/profile.yaml`) is also local only.
- No redistribution, no publication of verbatim content, no sale, and no training of AI or machine-learning models.
- Requests to Arctic Shift are throttled (about 1 per second) with a descriptive User-Agent. Comments are fetched only for shortlisted threads.
- Data is deleted when the case work ends.

## Original Reddit API collector

Built for the declined official-access request and kept for reference. It is a read-only "script" app client for r/migraine: it pages through the `new`, `top` and `hot` listings, runs subreddit-restricted searches, and fetches comment trees. It throttles to about 1 request per second, backs off on HTTP 429 and refreshes its OAuth token. It never posts, comments, votes or sends messages.

## Layout

```
src/
  clients/        Reddit API client (OAuth, rate limiting, pagination) and its config model
  models/         settings, constants and data models (post/comment without author)
  services/       collection: listings + searches -> deduplicated posts with comments -> JSONL
  main/           command-line entry points
  resources/      app_config.yaml and reddit/search_terms.yaml
  preprocessing/  headache diary cleaning
  report/         diary statistics, plots and PDF report
test/             offline tests against mocked API responses
data/             local only, gitignored
```

## Usage

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest
```

Original collector (needs Reddit API credentials in `.env`, see `.env.example`):

```bash
PYTHONPATH=src python -m main.collect                            # listings + search_terms.yaml
PYTHONPATH=src python -m main.collect --no-listings --query "aura numbness"
```

The output is `data/reddit/reddit_<timestamp>.jsonl`, with one post per line and its comments nested.
