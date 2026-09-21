"""Rendering helpers for question content (markdown + the optional image)."""
import streamlit as st

from . import config


def markdown(md: str) -> None:
    if md and md.strip():
        st.markdown(md)


def image(relative_path: str) -> None:
    path = config.DATA_DIR / relative_path
    if path.is_file():
        st.image(path.read_bytes())  # bytes: independent of the host's working directory
    else:
        st.warning(f"Image not found: {relative_path}")


def stem(stem_md: str, image_path: str | None) -> None:
    """Render a question stem, placing the image exactly where the {{image}} token sits."""
    if image_path and config.IMAGE_TOKEN in stem_md:
        before, _, after = stem_md.partition(config.IMAGE_TOKEN)
        markdown(before)
        image(image_path)
        markdown(after)
    else:
        markdown(stem_md.replace(config.IMAGE_TOKEN, ""))
