"""Results screen: score, per-chapter breakdown, and a reviewable list of every question."""
import streamlit as st

from mcq import config, render, service, state
from mcq.models import Outcome, Result

_FILTERS = ("All", "Correct", "Wrong", "Unanswered", "Flagged")
_ICONS = {"correct": "✅", "wrong": "❌", "unanswered": "⏭️"}


def _matches(o: Outcome, choice: str) -> bool:
    return {
        "All": True,
        "Correct": o.status == "correct",
        "Wrong": o.status == "wrong",
        "Unanswered": o.status == "unanswered",
        "Flagged": o.flagged,
    }[choice]


def _options_markdown(o: Outcome) -> str:
    q, lines = o.question, []
    for letter in config.LETTERS:
        text = q.options[letter]
        if letter == q.correct and letter == o.selected:
            lines.append(f"- ✅ **{letter}.** {text} — *your answer, correct*")
        elif letter == q.correct:
            lines.append(f"- ✅ **{letter}.** {text} — *correct answer*")
        elif letter == o.selected:
            lines.append(f"- ❌ **{letter}.** {text} — *your answer*")
        else:
            lines.append(f"- {letter}. {text}")
    return "\n".join(lines)


def _summary(r: Result) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Score", f"{r.correct} / {r.total}")
    c2.metric("Percentage", f"{r.percent:.0f}%")
    c3.metric("Wrong · Skipped", f"{r.wrong} · {r.unanswered}")
    c4.metric("Time used", service.format_clock(r.duration_sec), help=f"Limit: {service.format_clock(r.time_limit_sec)}")


def _actions(r: Result) -> None:
    missed = r.wrong + r.unanswered
    new_col, retry_col, _ = st.columns([1, 1.4, 1])
    if new_col.button("New test", type="primary"):
        state.reset()
    if retry_col.button(f"Retry {missed} missed", disabled=missed == 0):
        state.start(service.retake(r))


def _by_chapter(r: Result) -> None:
    stats = r.by_chapter
    if len(stats) < 2:
        return
    st.subheader("By chapter")
    st.dataframe(
        [
            {"Chapter": f"Chapter {s.chapter}", "Correct": s.correct, "Questions": s.total, "Score (%)": round(s.percent)}
            for s in stats
        ],
        hide_index=True,
        column_config={
            "Score (%)": st.column_config.ProgressColumn("Score (%)", min_value=0, max_value=100, format="%d")
        },
    )


def _review(r: Result) -> None:
    st.subheader("Review")
    counts = {name: sum(_matches(o, name) for o in r.outcomes) for name in _FILTERS}
    choice = st.radio(
        "Show",
        _FILTERS,
        horizontal=True,
        format_func=lambda name: f"{name} ({counts[name]})",
        label_visibility="collapsed",
        key="review_filter",
    )

    shown = [(pos, o) for pos, o in enumerate(r.outcomes, start=1) if _matches(o, choice)]
    if not shown:
        st.info("Nothing to show for this filter.")
    for pos, o in shown:
        q = o.question
        with st.container(border=True):
            flag = " · 🚩 flagged" if o.flagged else ""
            st.markdown(f"**{_ICONS[o.status]} Question {pos}** · Chapter {q.chapter}, Q{q.number}{flag}")
            render.stem(q.stem_md, q.image_path)
            st.markdown(_options_markdown(o))
            if o.selected is None:
                st.caption("You did not answer this question.")
            with st.expander("View explanation"):
                render.markdown(q.explanation_md)


def show() -> None:
    t = state.get_test()
    if t is None or not t.finished:
        state.go("home")

    st.title("Results")
    if t.end_reason == "time_up":
        st.warning("⏰ **Time's up!** The test ended automatically. Only answers given before the deadline were counted.")
    else:
        st.success("Test submitted.")

    result = service.score(t)
    _summary(result)
    _actions(result)
    _by_chapter(result)
    _review(result)
