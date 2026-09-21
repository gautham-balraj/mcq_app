"""Optional single-password gate. Enabled only when APP_PASSWORD is set (env var or Streamlit secrets)."""
import hmac
import os

import streamlit as st


def _expected_password() -> str | None:
    """Password from the APP_PASSWORD env var or Streamlit secrets, or None if neither is configured.

    st.secrets is only touched when a secrets file exists: on some Streamlit versions merely reading it
    without a secrets.toml shows a red "No secrets found" banner in the app, even inside try/except.
    """
    if os.getenv("APP_PASSWORD"):
        return os.environ["APP_PASSWORD"]
    try:
        if st.secrets.load_if_toml_exists():
            return st.secrets.get("APP_PASSWORD") or None
    except Exception:  # unreadable or malformed secrets file: behave as "no password configured"
        pass
    return None


def require_password() -> None:
    """Stop the script with a login form unless the correct password was entered in this session."""
    expected = _expected_password()
    if not expected or st.session_state.get("authenticated"):
        return

    st.title("🔒 MCQ Practice")
    with st.form("login"):
        entered = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Enter")
    if submitted:
        if hmac.compare_digest(entered.encode(), expected.encode()):
            st.session_state["authenticated"] = True
            st.rerun()
        st.error("Incorrect password.")
    st.stop()