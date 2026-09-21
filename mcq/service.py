"""Test logic: building a test, recording answers, enforcing the deadline, scoring.

Pure Python (no Streamlit, no SQL) so it is easy to unit test.
"""
from __future__ import annotations

import random
import time
from typing import Sequence

from . import config
from .models import Outcome, Question, Result, TestSession


def suggested_minutes(n_questions: int) -> int:
    return max(1, round(n_questions * config.MINUTES_PER_QUESTION))


def build_test(
    pool: Sequence[Question],
    n_questions: int,
    minutes: int,
    rng: random.Random | None = None,
    now: float | None = None,
) -> TestSession:
    """Pick `n_questions` at random from `pool` (mixed across chapters) and start the clock."""
    if not pool:
        raise ValueError("No questions available for this selection.")
    rng = rng or random
    n = max(1, min(n_questions, len(pool)))
    return TestSession(
        questions=rng.sample(list(pool), n),
        time_limit_sec=int(minutes * 60),
        started_at=time.time() if now is None else now,
    )


def record_answer(t: TestSession, question_id: int, letter: str, at: float | None = None) -> bool:
    """Store an answer. Returns False (and stores nothing) if the test is over or the input is invalid."""
    at = time.time() if at is None else at
    if t.finished or t.expired(at):
        return False
    if question_id not in t.question_ids or letter not in config.LETTERS:
        return False
    t.answers[question_id] = letter
    return True


def set_flag(t: TestSession, question_id: int, flagged: bool) -> None:
    if t.finished or question_id not in t.question_ids:
        return
    (t.flagged.add if flagged else t.flagged.discard)(question_id)


def finish(t: TestSession, reason: str = "submitted", at: float | None = None) -> None:
    """End the test. A submit that arrives after the deadline counts as 'time_up' and is stamped at the deadline."""
    if t.finished:
        return
    at = time.time() if at is None else at
    if at >= t.deadline:
        reason = "time_up"
    t.submitted_at = min(at, t.deadline)
    t.end_reason = reason


def score(t: TestSession) -> Result:
    outcomes = tuple(Outcome(q, t.answers.get(q.id), q.id in t.flagged) for q in t.questions)
    end = t.submitted_at if t.submitted_at is not None else time.time()
    return Result(outcomes=outcomes, duration_sec=max(0.0, end - t.started_at), time_limit_sec=t.time_limit_sec)


def retake(result: Result) -> TestSession | None:
    """A new test from the questions that were wrong or unanswered (None if there are none)."""
    missed = [o.question for o in result.outcomes if not o.is_correct]
    if not missed:
        return None
    return build_test(missed, len(missed), suggested_minutes(len(missed)))


def format_clock(seconds: float) -> str:
    """72 -> '01:12', 3725 -> '1:02:05'."""
    s = int(round(seconds))
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
