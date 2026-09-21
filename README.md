# MCQ Practice

A small single-user Streamlit app for timed MCQ practice. Pick chapters, the number of questions and a time
limit, take the test, and review the results with correct answers and explanations. No accounts and no test
history: a test lives in the browser session only.

## Run locally

```bash
pip install -r requirements.txt
python scripts/create_db.py        # creates qbank.db (first time only)
python scripts/load_data.py        # validates data/chapter*_mcq.json and loads it
streamlit run app.py
```

Re-run `load_data.py` whenever you fix or add chapters. It upserts on (chapter, number), so it never duplicates.

## Question status

Only `verified` questions are served by default. The sidebar checkbox **Include unverified questions** also serves
`draft` ones (on by default; change with `MCQ_INCLUDE_UNVERIFIED=0`). Questions marked `needs_review` are never served.

After checking a chapter against the PDF:

```sql
UPDATE questions SET status = 'verified' WHERE chapter = 1 AND review_note IS NULL;
```

## Project layout

```
app.py             entrypoint: page config, password gate, screen router
mcq/config.py      paths and settings (env-overridable)
mcq/models.py      dataclasses: Question, TestSession, Outcome, Result
mcq/db.py          read-only SQLite access (the only file with SQL)
mcq/service.py     build test, record answers, deadline rules, scoring, retake
mcq/render.py      markdown + image rendering ({{image}} token)
mcq/state.py       session-state helpers / screen switching
mcq/auth.py        optional password gate
views/home.py      chapter / count / time selection
views/exam.py      countdown, question, navigator, submit
views/results.py   score, per-chapter table, review with explanations
scripts/           create_db.py, load_data.py, schema.sql
tests/             pytest: service logic + end-to-end flow (Streamlit AppTest)
data/              chapter*_mcq.json and images/  (not in this download)
```

## How the timer works

The deadline is `started_at + time limit`, stored with the test. The countdown redraws every second but always shows
`deadline - now`, so a throttled background tab cannot drift. When the time runs out the test is submitted
automatically and the results screen opens with a "Time's up" notice. Answers arriving after the deadline are
rejected.

A test is held in the browser session, so **refreshing the page during a test ends it**.

## Deploy (Streamlit Community Cloud)

The app only reads `qbank.db`, so it works on hosts with a read-only or temporary filesystem.

1. Put the project in a **private** GitHub repo. Commit `qbank.db`, `data/images/`, `mcq/`, `views/`, `app.py`,
   `requirements.txt` and `.streamlit/`. Do not commit the source PDFs (`docs/` is git-ignored); the question text
   comes from a commercial book, so keep the repo and the app private.
2. On share.streamlit.io choose the repo and set `app.py` as the entrypoint.
3. In the app's **Secrets** add: `APP_PASSWORD = "choose-a-password"`. The app then asks for it once per session.

Any host that can run `streamlit run app.py` works as well (Railway, Render, Fly.io, a VPS, Cloud Run).

## Tests

```bash
pip install pytest
python -m pytest tests -q
```
