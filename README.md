
We are born too early to have cured migraine. I am deeply sorry for that.

Dedicated to my twin.

---

# migraine

Private, non-commercial research tooling for the care of one migraine patient:

- **Headache diary analysis** (`src/preprocessing`, `src/report`): turns the patient's diary into a summary report for their doctor. The diary data is never committed to this repository.
- **r/migraine case research** (`src/clients`, `src/services`, `src/main`): finds first-hand reports in r/migraine that resemble the patient's symptom pattern, triggers and treatment history, so the options can be discussed with their doctor.

## What the Reddit collector does

A single Python script, run by hand on my own computer, using a Reddit "script" app with read-only OAuth access to r/migraine only.

1. Pages through the r/migraine `new`, `top` (all time) and `hot` listings, 100 posts per request.
2. Runs keyword searches restricted to r/migraine (`/r/migraine/search?restrict_sr=1`) for the terms in `src/resources/reddit/search_terms.yaml`.
3. Fetches the comment tree of each matching thread (`/r/migraine/comments/{id}`).

It never posts, comments, votes or sends messages, and it doesn't interact with Redditors.

### Request behaviour

- About 1 request per second (`request_interval` in `src/resources/app_config.yaml`), well under the free-tier limit.
- Descriptive User-Agent: `script:migraine-case-research:v0.1 (by /u/<account>)`.
- Backs off on HTTP 429 using the `X-Ratelimit-Reset` header, and refreshes the OAuth token when it expires.
- One collection of a few thousand threads, plus occasional small re-runs to pick up new posts.

### Data handling

- **Only content is kept:** post title and text, comment text, scores, timestamps, flair and permalink. **Usernames and author fields are dropped when the data is collected** and never written to disk (see `src/models/reddit.py`).
- No attempt is made to identify, profile or contact any user.
- Data is stored locally in `data/`, which is gitignored and never committed.
- No redistribution, no publication of verbatim content, no sale, and no training of AI or machine-learning models.
- Data is deleted when the case work ends.
- Use complies with Reddit's [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy) and [Data API Terms](https://www.redditinc.com/policies/data-api-terms).

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
cp .env.example .env    # fill in REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME

PYTHONPATH=src python -m main.collect                            # listings + search_terms.yaml
PYTHONPATH=src python -m main.collect --no-listings --query "aura numbness"
pytest
```

The output is `data/reddit/reddit_<timestamp>.jsonl`, with one post per line and its comments nested.
