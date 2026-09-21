"""Central settings. Every path/setting can be overridden with an environment variable."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DB_PATH = Path(os.getenv("MCQ_DB_PATH", ROOT / "qbank.db"))
DATA_DIR = Path(os.getenv("MCQ_DATA_DIR", ROOT / "data"))  # image paths in the DB are relative to this folder

LETTERS = ("A", "B", "C", "D", "E")
IMAGE_TOKEN = "{{image}}"

DEFAULT_QUESTIONS = 20
MINUTES_PER_QUESTION = 1.5     # used to suggest a time limit
MAX_MINUTES = 600

# "Include unverified" also serves questions with status 'draft'. Questions marked 'needs_review' are never served.
INCLUDE_UNVERIFIED_DEFAULT = os.getenv("MCQ_INCLUDE_UNVERIFIED", "1") == "1"
