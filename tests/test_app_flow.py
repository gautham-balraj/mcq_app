"""End-to-end flow through the real Streamlit script (no browser needed)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from mcq import service

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _button(at, label):
    return next(b for b in at.button if b.label == label)


@pytest.fixture()
def started(bank):
    at = AppTest.from_file(APP, default_timeout=15).run()
    assert not at.exception
    at.multiselect[0].select(1).select(2).run()
    at.number_input[0].set_value(6).run()       # 6 questions
    at.number_input[1].set_value(3).run()       # 3 minutes
    _button(at, "Start test").click().run()
    assert not at.exception
    return at


def test_home_lists_chapters_and_disables_start_until_selected(bank):
    at = AppTest.from_file(APP, default_timeout=15).run()
    assert not at.exception
    assert _button(at, "Start test").disabled
    assert "Chapter 1 · 7 questions" in at.multiselect[0].options[0]


def test_unverified_toggle_changes_available_questions(bank):
    at = AppTest.from_file(APP, default_timeout=15).run()
    at.sidebar.checkbox[0].uncheck().run()
    assert "Chapter 1 · 5 questions" in at.multiselect[0].options[0]


def test_start_shows_first_question_with_no_preselected_answer(started):
    t = started.session_state["test"]
    assert started.session_state["phase"] == "exam"
    assert len(t.questions) == 6 and t.time_limit_sec == 180
    assert started.radio[0].value is None
    assert len(started.radio[0].options) == 5


def test_answer_is_stored_and_survives_navigation(started):
    t = started.session_state["test"]
    first = t.questions[0]
    started.radio[0].set_value("C").run()
    assert t.answers[first.id] == "C"
    _button(started, "Next →").click().run()
    assert started.radio[0].value is None
    _button(started, "← Previous").click().run()
    assert started.radio[0].value == "C"


def test_question_with_image_renders_between_text_parts(started):
    from mcq import db

    t = started.session_state["test"]
    t.questions[0] = next(q for q in db.load_questions([1], True) if q.image_path)
    t.current = 0
    started.run()
    assert not started.exception
    assert not any("Image not found" in w.value for w in started.warning)
    assert len(started.get("image")) == 1
    kinds = [el.type for el in started.main]
    i = kinds.index("image")
    assert kinds[i - 1] == "markdown" and kinds[i + 1] == "markdown"   # text before and after the figure


def test_flag_is_stored(started):
    t = started.session_state["test"]
    started.checkbox[0].check().run()
    assert t.questions[0].id in t.flagged


def test_time_running_out_ends_test_and_shows_results(started):
    t = started.session_state["test"]
    started.radio[0].set_value("B").run()
    t.started_at -= 10_000                     # simulate the deadline passing
    started.run()
    assert not started.exception
    assert started.session_state["phase"] == "results"
    assert any("Time's up" in w.value for w in started.warning)
    assert t.end_reason == "time_up"


def test_answers_after_deadline_are_not_counted(started):
    t = started.session_state["test"]
    first = t.questions[0]
    t.started_at -= 10_000
    assert not service.record_answer(t, first.id, "A")
    assert first.id not in t.answers


def test_results_show_score_review_and_explanations(started):
    t = started.session_state["test"]
    started.radio[0].set_value(t.questions[0].correct).run()
    service.finish(t, "submitted")
    started.session_state["phase"] = "results"
    started.run()
    assert not started.exception
    metrics = {m.label: m.value for m in started.metric}
    assert metrics["Score"] == "1 / 6"
    assert any("Test submitted" in s.value for s in started.success)
    assert len(started.expander) == 6 and started.expander[0].label == "View explanation"
    assert "Explanation" in started.expander[0].markdown[0].value


def test_review_filter_and_retry_missed(started):
    t = started.session_state["test"]
    started.radio[0].set_value(t.questions[0].correct).run()
    service.finish(t, "submitted")
    started.session_state["phase"] = "results"
    started.run()
    started.radio[0].set_value("Unanswered").run()
    assert len(started.expander) == 5
    _button(started, "Retry 5 missed").click().run()
    assert started.session_state["phase"] == "exam"
    assert len(started.session_state["test"].questions) == 5


def test_new_test_returns_home(started):
    service.finish(started.session_state["test"], "submitted")
    started.session_state["phase"] = "results"
    started.run()
    _button(started, "New test").click().run()
    assert started.session_state["phase"] == "home"
    assert "test" not in started.session_state


def test_password_gate(bank, monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "s3cret")
    at = AppTest.from_file(APP, default_timeout=15).run()
    assert at.text_input[0].label == "Password" and not at.multiselect
    at.text_input[0].set_value("wrong").run()
    at.button[0].click().run()
    assert at.error and not at.multiselect
    at.text_input[0].set_value("s3cret").run()
    at.button[0].click().run()
    assert at.multiselect


def test_missing_database_shows_friendly_error(tmp_path, monkeypatch):
    from mcq import config
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "missing.db")
    at = AppTest.from_file(APP, default_timeout=15).run()
    assert not at.exception
    assert "create_db.py" in at.error[0].value
