import random

import pytest

from mcq import db, service
from mcq.models import Question


def _pool(n=10):
    opts = {k: k for k in "ABCDE"}
    return [Question(i, 1 + i % 2, i, f"stem {i}", None, opts, "B", "expl") for i in range(1, n + 1)]


def test_build_test_caps_count_and_sets_limit():
    t = service.build_test(_pool(5), n_questions=50, minutes=2, now=1000.0)
    assert len(t.questions) == 5
    assert t.time_limit_sec == 120 and t.deadline == 1120.0


def test_build_test_is_random_but_seedable():
    a = service.build_test(_pool(), 5, 5, rng=random.Random(1))
    b = service.build_test(_pool(), 5, 5, rng=random.Random(1))
    assert [q.id for q in a.questions] == [q.id for q in b.questions]


def test_build_test_rejects_empty_pool():
    with pytest.raises(ValueError):
        service.build_test([], 5, 5)


def test_answers_accepted_before_deadline_and_rejected_after():
    t = service.build_test(_pool(3), 3, 1, now=0.0)
    qid = t.questions[0].id
    assert service.record_answer(t, qid, "A", at=59.9)
    assert not service.record_answer(t, qid, "C", at=60.0)
    assert t.answers[qid] == "A"


def test_invalid_answers_are_ignored():
    t = service.build_test(_pool(3), 3, 1, now=0.0)
    assert not service.record_answer(t, 999, "A", at=1)
    assert not service.record_answer(t, t.questions[0].id, "Z", at=1)
    assert t.answers == {}


def test_late_submit_counts_as_time_up_and_is_capped_at_deadline():
    t = service.build_test(_pool(3), 3, 1, now=0.0)
    service.finish(t, "submitted", at=500.0)
    assert t.end_reason == "time_up" and t.submitted_at == 60.0


def test_early_submit_keeps_reason_and_finish_is_idempotent():
    t = service.build_test(_pool(3), 3, 1, now=0.0)
    service.finish(t, "submitted", at=30.0)
    service.finish(t, "time_up", at=99.0)
    assert t.end_reason == "submitted" and t.submitted_at == 30.0
    assert not service.record_answer(t, t.questions[0].id, "A", at=31.0)


def test_scoring_counts_correct_wrong_unanswered_and_chapters():
    t = service.build_test(_pool(4), 4, 10, rng=random.Random(0), now=0.0)
    q1, q2, q3, _ = t.questions
    service.record_answer(t, q1.id, "B", at=1)   # correct (all keys are "B")
    service.record_answer(t, q2.id, "A", at=1)   # wrong
    service.set_flag(t, q3.id, True)             # unanswered but flagged
    service.finish(t, "submitted", at=90.0)
    r = service.score(t)
    assert (r.total, r.correct, r.wrong, r.unanswered) == (4, 1, 1, 2)
    assert r.percent == 25.0 and r.duration_sec == 90.0
    assert sum(s.total for s in r.by_chapter) == 4
    assert [o.flagged for o in r.outcomes].count(True) == 1


def test_retake_uses_only_missed_questions():
    t = service.build_test(_pool(4), 4, 10, rng=random.Random(0), now=0.0)
    for q in t.questions[:2]:
        service.record_answer(t, q.id, "B", at=1)
    service.finish(t, "submitted", at=5.0)
    again = service.retake(service.score(t))
    assert {q.id for q in again.questions} == {q.id for q in t.questions[2:]}
    assert again.answers == {}


def test_retake_returns_none_when_everything_correct():
    t = service.build_test(_pool(2), 2, 10, now=0.0)
    for q in t.questions:
        service.record_answer(t, q.id, "B", at=1)
    service.finish(t, at=2.0)
    assert service.retake(service.score(t)) is None


def test_format_clock():
    assert service.format_clock(72) == "01:12"
    assert service.format_clock(3725) == "1:02:05"
    assert service.format_clock(0) == "00:00"


def test_db_counts_respect_status_and_never_serve_needs_review(bank):
    assert db.chapter_counts(False) == {1: 5, 2: 4}
    assert db.chapter_counts(True) == {1: 7, 2: 4}          # needs_review (ch2 q5) never counted
    qs = db.load_questions([1, 2], True)
    assert len(qs) == 11 and all(isinstance(q.options, dict) and len(q.options) == 5 for q in qs)
    assert db.load_questions([], True) == []


def test_db_is_read_only(bank):
    import sqlite3
    con = db._connect()
    with pytest.raises(sqlite3.OperationalError):
        con.execute("DELETE FROM questions")
    con.close()


def test_missing_database_gives_helpful_error(tmp_path, monkeypatch):
    from mcq import config
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "nope.db")
    with pytest.raises(db.QuestionBankError, match="create_db.py"):
        db.chapter_counts(True)
