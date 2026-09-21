"""Exam screen: countdown, one question at a time, navigator, submit."""
import math

import streamlit as st

from mcq import config, render, service, state
from mcq.models import TestSession


# ---------------------------------------------------------------- callbacks
def _on_answer(t: TestSession, question_id: int, widget_key: str) -> None:
    service.record_answer(t, question_id, st.session_state[widget_key])


def _on_flag(t: TestSession, question_id: int, widget_key: str) -> None:
    service.set_flag(t, question_id, st.session_state[widget_key])


def _goto(t: TestSession, index: int) -> None:
    t.current = index


def _step(t: TestSession, delta: int) -> None:
    t.current = min(max(t.current + delta, 0), len(t.questions) - 1)


# ---------------------------------------------------------------- pieces
@st.fragment(run_every=1)
def _countdown(t: TestSession) -> None:
    """Redraws every second. The time shown is always deadline - now, never a tick counter."""
    left = t.remaining()
    if left <= 0:
        service.finish(t, "time_up")
        state.go("results")
    css = "danger" if left < 60 else "warn" if left < 300 else ""
    clock = service.format_clock(math.ceil(left))
    st.markdown(f'<div class="timer {css}">⏱ {clock}</div>', unsafe_allow_html=True)


@st.dialog("Submit your test?")
def _confirm_submit(t: TestSession) -> None:
    total, answered = len(t.questions), len(t.answers)
    st.write(f"You have answered **{answered} of {total}** questions.")
    if answered < total:
        st.warning(f"{total - answered} unanswered question(s) will be marked incorrect.")
    if t.flagged:
        st.info(f"{len(t.flagged)} question(s) are flagged for review.")
    keep, submit = st.columns(2)
    if keep.button("Keep working"):
        st.rerun()
    if submit.button("Submit now", type="primary"):
        service.finish(t, "submitted")
        state.go("results")


def _sidebar(t: TestSession) -> None:
    with st.sidebar:
        st.markdown("### Questions")
        st.caption("✓ answered · ⚑ flagged · highlighted = current")
        per_row = 4
        for start in range(0, len(t.questions), per_row):
            cols = st.columns(per_row, gap="small")
            for offset, col in enumerate(cols):
                i = start + offset
                if i >= len(t.questions):
                    break
                q = t.questions[i]
                mark = " ⚑" if q.id in t.flagged else " ✓" if q.id in t.answers else ""
                col.button(
                    f"{i + 1}{mark}",
                    key=f"nav_{i}",
                    type="primary" if i == t.current else "secondary",
                    on_click=_goto,
                    args=(t, i),
                )


def _question(t: TestSession) -> None:
    q = t.questions[t.current]
    st.caption(f"Chapter {q.chapter} · Question {q.number}")
    render.stem(q.stem_md, q.image_path)

    answer_key = f"ans_{q.id}"
    chosen = t.answers.get(q.id)
    st.radio(
        "Choose one answer",
        options=config.LETTERS,
        index=config.LETTERS.index(chosen) if chosen else None,
        format_func=lambda letter: f"**{letter}.** {q.options[letter]}",
        key=answer_key,
        on_change=_on_answer,
        args=(t, q.id, answer_key),
        label_visibility="collapsed",
    )

    flag_key = f"flag_{q.id}"
    st.checkbox(
        "🚩 Flag for review",
        value=q.id in t.flagged,
        key=flag_key,
        on_change=_on_flag,
        args=(t, q.id, flag_key),
    )


def _nav(t: TestSession) -> None:
    prev_col, next_col, finish_col = st.columns([1, 1, 1.3])
    prev_col.button("← Previous", key="prev", disabled=t.current == 0, on_click=_step, args=(t, -1))
    next_col.button(
        "Next →", key="next", disabled=t.current == len(t.questions) - 1, on_click=_step, args=(t, 1)
    )
    if finish_col.button("Finish test", key="finish", type="primary"):
        _confirm_submit(t)


# ---------------------------------------------------------------- entry point
def show() -> None:
    t = state.get_test()
    if t is None:
        state.go("home")
    if t.finished:
        state.go("results")
    if t.expired():  # deadline passed while the user was idle or the tab was in the background
        service.finish(t, "time_up")
        state.go("results")

    total = len(t.questions)
    _sidebar(t)

    title_col, timer_col = st.columns([2, 1], vertical_alignment="center")
    title_col.subheader(f"Question {t.current + 1} of {total}")
    with timer_col:
        _countdown(t)
    st.progress(len(t.answers) / total, text=f"{len(t.answers)} of {total} answered")

    _question(t)
    st.divider()
    _nav(t)
