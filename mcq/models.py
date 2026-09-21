"""Plain data classes. No Streamlit and no database code in here."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Question:
    id: int
    chapter: int
    number: int
    stem_md: str
    image_path: str | None
    options: dict[str, str]
    correct: str
    explanation_md: str


@dataclass
class TestSession:
    """One in-progress (or finished) test. Lives in st.session_state; nothing is persisted."""

    questions: list[Question]
    time_limit_sec: int
    started_at: float = field(default_factory=time.time)
    answers: dict[int, str] = field(default_factory=dict)   # question id -> chosen letter
    flagged: set[int] = field(default_factory=set)          # question ids flagged for review
    current: int = 0                                         # index of the question on screen
    submitted_at: float | None = None
    end_reason: str | None = None                            # "submitted" | "time_up"

    @property
    def deadline(self) -> float:
        return self.started_at + self.time_limit_sec

    @property
    def finished(self) -> bool:
        return self.submitted_at is not None

    @property
    def question_ids(self) -> frozenset[int]:
        return frozenset(q.id for q in self.questions)

    def remaining(self, at: float | None = None) -> float:
        at = time.time() if at is None else at
        return max(0.0, self.deadline - at)

    def expired(self, at: float | None = None) -> bool:
        return self.remaining(at) <= 0


@dataclass(frozen=True)
class Outcome:
    question: Question
    selected: str | None
    flagged: bool

    @property
    def is_correct(self) -> bool:
        return self.selected == self.question.correct

    @property
    def status(self) -> str:
        if self.selected is None:
            return "unanswered"
        return "correct" if self.is_correct else "wrong"


@dataclass(frozen=True)
class ChapterStat:
    chapter: int
    total: int
    correct: int

    @property
    def percent(self) -> float:
        return 100 * self.correct / self.total if self.total else 0.0


@dataclass(frozen=True)
class Result:
    outcomes: tuple[Outcome, ...]
    duration_sec: float
    time_limit_sec: int

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def correct(self) -> int:
        return sum(o.status == "correct" for o in self.outcomes)

    @property
    def wrong(self) -> int:
        return sum(o.status == "wrong" for o in self.outcomes)

    @property
    def unanswered(self) -> int:
        return sum(o.status == "unanswered" for o in self.outcomes)

    @property
    def percent(self) -> float:
        return 100 * self.correct / self.total if self.total else 0.0

    @property
    def by_chapter(self) -> list[ChapterStat]:
        totals: dict[int, list[int]] = {}
        for o in self.outcomes:
            t = totals.setdefault(o.question.chapter, [0, 0])
            t[0] += 1
            t[1] += o.is_correct
        return [ChapterStat(ch, n, c) for ch, (n, c) in sorted(totals.items())]
