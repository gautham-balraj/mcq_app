"""Session-state helpers: which screen is showing and which test is in progress."""
import streamlit as st
from typing import Optional
from .models import TestSession

_PHASE = "phase"   # "home" | "exam" | "results"
_TEST = "test"

def get_test() -> Optional[TestSession]:
    return st.session_state.get(_TEST)


def current_phase() -> str:
    return st.session_state.setdefault(_PHASE, "home")


def go(phase: str) -> None:
    """Switch screen and rerun the app (stops the current script run)."""
    st.session_state[_PHASE] = phase
    st.rerun()


def start(test: TestSession) -> None:
    st.session_state[_TEST] = test
    go("exam")


def reset() -> None:
    st.session_state.pop(_TEST, None)
    go("home")
