"""Home screen: choose chapters, number of questions and time limit, then start."""
import streamlit as st

from mcq import chapter_titles, config, db, service, state

def show() -> None:
    st.title("📝 MCQ Practice")
    st.caption("Choose your chapters, set the number of questions and a time limit, then start.")

    include_unverified = st.sidebar.checkbox(
        "Include unverified questions",
        value=config.INCLUDE_UNVERIFIED_DEFAULT,
        help="Unticked: only questions you have marked as verified. Ticked: also draft questions.",
    )

    counts = db.chapter_counts(include_unverified)
    titles = chapter_titles.load()          # <-- new
    if not counts:
        st.warning(
            "No questions available. Load your data with `python scripts/load_data.py`, "
            "or tick **Include unverified questions** in the sidebar."
        )
        return

    with st.container(border=True):
        chapters = st.multiselect(
            "Chapters",
            options=list(counts),
            format_func=lambda c: chapter_titles.label(c, counts[c], titles),
            placeholder="Choose one or more chapters",
        )
        available = sum(counts[c] for c in chapters)

        if not chapters:
            st.info("Select at least one chapter to continue.")
        else:
            left, right = st.columns(2)
            n_questions = left.number_input(
                "Number of questions",
                min_value=1,
                max_value=available,
                value=min(config.DEFAULT_QUESTIONS, available),
                step=1,
                help=f"{available} questions available in the selected chapters.",
            )
            minutes = right.number_input(
                "Time limit (minutes)",
                min_value=1,
                max_value=config.MAX_MINUTES,
                value=min(service.suggested_minutes(n_questions), config.MAX_MINUTES),
                step=1,
                help=f"Suggested: {config.MINUTES_PER_QUESTION:g} minutes per question.",
            )
            st.caption(
                f"{n_questions} question(s) picked at random · {minutes} min "
                f"(≈ {minutes * 60 / n_questions:.0f} s per question)"
            )

    if st.button("Start test", type="primary", disabled=not chapters):
        pool = db.load_questions(chapters, include_unverified)
        state.start(service.build_test(pool, int(n_questions), int(minutes)))
