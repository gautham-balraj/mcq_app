"""MCQ practice app. Run with:  streamlit run app.py"""
import streamlit as st

from mcq import auth, state
from mcq.db import QuestionBankError
from views import exam, home, results

st.set_page_config(page_title="MCQ Practice", page_icon="📝", layout="centered")

_CSS = """
<style>
.timer { font-size: 1.5rem; font-weight: 700; text-align: center; padding: .3rem .6rem;
         border-radius: .6rem; background: rgba(37, 99, 235, .12); font-variant-numeric: tabular-nums; }
.timer.warn   { background: rgba(217, 119, 6, .18); color: #b45309; }
.timer.danger { background: rgba(220, 38, 38, .16); color: #dc2626; }
</style>
"""

_VIEWS = {"home": home.show, "exam": exam.show, "results": results.show}


def main() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    auth.require_password()
    try:
        _VIEWS[state.current_phase()]()
    except QuestionBankError as err:
        st.error(str(err))


main()
