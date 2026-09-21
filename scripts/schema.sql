-- MCQ question bank schema (SQLite). Safe to run repeatedly (IF NOT EXISTS).
-- The app only READS this table; tests live in memory for the duration of a session.

CREATE TABLE IF NOT EXISTS questions (
  id              INTEGER PRIMARY KEY,
  chapter         INTEGER NOT NULL,
  number          INTEGER NOT NULL,
  stem_md         TEXT    NOT NULL,                 -- markdown; contains one {{image}} token if image_path is set
  image_path      TEXT,                             -- relative to the data/ folder (e.g. images/ch01/q003.png), NULL if none
  options_json    TEXT    NOT NULL,                 -- {"A": "...", "B": "...", ..., "E": "..."}
  correct         TEXT    NOT NULL CHECK (correct IN ('A','B','C','D','E')),
  explanation_md  TEXT    NOT NULL,                 -- markdown, tables preserved
  review_note     TEXT,                             -- extraction uncertainty flag, NULL if none
  status          TEXT    NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft', 'needs_review', 'verified')),
  UNIQUE (chapter, number)
);

CREATE INDEX IF NOT EXISTS idx_questions_chapter_status
  ON questions (chapter, status);
