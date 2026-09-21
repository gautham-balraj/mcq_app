"""Validate extracted chapter JSON files and load them into SQLite.

Usage (from anywhere):
    python scripts/load_data.py                  # validate + load every data/chapter*_mcq.json
    python scripts/load_data.py --dry-run        # validate only, write nothing
    python scripts/load_data.py --skip-invalid   # load the valid questions, report the rest

Behaviour:
  * Re-runnable: upserts on (chapter, number), so fixing the JSON and reloading never duplicates rows.
  * All-or-nothing by default: if any question has an ERROR, nothing is written.
  * WARNINGS (possible truncated explanation, review flag, ...) never block loading; use them as a review list.
  * `status` is set to draft / needs_review on first insert. On reload it is preserved, except that a question
    with a non-empty `review` flag is moved back to needs_review. Mark reviewed questions 'verified' yourself.
  * `image` is stored relative to the images root (the --data-dir folder), e.g. images/ch01/q003.png.
    Values with an old folder prefix (e.g. "extraction_results/images/ch01/q003.png") and "" are normalised automatically.
"""
import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = Path(__file__).with_name("schema.sql")
LETTERS = "ABCDE"
IMAGE_TOKEN = "{{image}}"

UPSERT = """
INSERT INTO questions
  (chapter, number, stem_md, image_path, options_json, correct, explanation_md, review_note, status)
VALUES
  (:chapter, :number, :stem_md, :image_path, :options_json, :correct, :explanation_md, :review_note, :status)
ON CONFLICT (chapter, number) DO UPDATE SET
  stem_md        = excluded.stem_md,
  image_path     = excluded.image_path,
  options_json   = excluded.options_json,
  correct        = excluded.correct,
  explanation_md = excluded.explanation_md,
  review_note    = excluded.review_note,
  status         = CASE WHEN excluded.review_note IS NOT NULL THEN 'needs_review' ELSE questions.status END
"""


def resolve_image(img, data_dir: Path):
    """Return the image path relative to data_dir (posix style), None if no image. Raises ValueError."""
    if not img:  # None or ""
        return None
    img = img.replace("\\", "/")
    if img.startswith(("http://", "https://")) or Path(img).is_absolute():
        raise ValueError(f"image path must be relative, got {img!r}")
    candidates = [data_dir / img, ROOT / img]            # 'images/ch01/q003.png' or 'data/images/ch01/q003.png'
    if "images/" in img:                                   # stale prefix, e.g. 'extraction_results/images/...'
        candidates.append(data_dir / img[img.index("images/"):])
    for f in candidates:
        if f.is_file():
            try:
                return f.resolve().relative_to(data_dir.resolve()).as_posix()
            except ValueError:
                raise ValueError(f"image {img!r} is outside {data_dir.name}/")
    raise ValueError(f"image file not found: {img!r}")


def check_question(q: dict, data_dir: Path):
    """Return (row_dict, warnings). Raises ValueError with a readable message on hard errors."""
    for k in ("chapter", "number", "stem_md", "options", "correct", "explanation_md"):
        if k not in q:
            raise ValueError(f"missing key {k!r}")
    if not isinstance(q["chapter"], int) or not isinstance(q["number"], int):
        raise ValueError("chapter and number must be integers")

    opts = q["options"]
    if not isinstance(opts, dict) or set(opts) != set(LETTERS):
        raise ValueError(f"options must have exactly keys A-E, got {sorted(opts) if isinstance(opts, dict) else opts!r}")
    empty = [k for k, v in opts.items() if not str(v).strip()]
    if empty:
        raise ValueError(f"empty option text for {empty}")

    correct = q["correct"]
    if isinstance(correct, str):
        correct = [correct]
    if len(correct) != 1 or correct[0] not in LETTERS:
        raise ValueError(f"'correct' must be exactly one letter A-E, got {q['correct']!r}")

    stem = q["stem_md"]
    if not str(stem).strip():
        raise ValueError("empty stem_md")
    image = resolve_image(q.get("image"), data_dir)
    n_tok = stem.count(IMAGE_TOKEN)
    if image and n_tok != 1:
        raise ValueError(f"image is set but stem_md has {n_tok} {IMAGE_TOKEN} tokens (need exactly 1)")
    if not image and n_tok:
        raise ValueError(f"stem_md has {IMAGE_TOKEN} but image is empty")

    expl = q["explanation_md"].strip()
    if not expl:
        raise ValueError("empty explanation_md")

    review = (q.get("review") or "").strip() or None

    warns = []
    if not expl.endswith((".", ")", "|", "*", "?")):
        warns.append("explanation may be truncated (doesn't end with punctuation)")
    if re.search(r"\s\.", expl):
        warns.append("explanation contains ' .' (a word may have been dropped)")
    if len(expl) < 80:
        warns.append("very short explanation")
    if not stem.rstrip().endswith(("?", "**")):
        warns.append("stem doesn't end with a question")
    if review:
        warns.append(f"review flag: {review}")

    row = {
        "chapter": q["chapter"],
        "number": q["number"],
        "stem_md": stem,
        "image_path": image,
        "options_json": json.dumps({k: opts[k] for k in LETTERS}, ensure_ascii=False),
        "correct": correct[0],
        "explanation_md": q["explanation_md"],
        "review_note": review,
        "status": "needs_review" if review else "draft",
    }
    return row, warns


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=str(ROOT / "qbank.db"))
    ap.add_argument("--data-dir", default=str(ROOT / "data"), help="folder with chapter*_mcq.json and images/")
    ap.add_argument("--pattern", default="chapter*_mcq.json")
    ap.add_argument("--dry-run", action="store_true", help="validate only, write nothing")
    ap.add_argument("--skip-invalid", action="store_true", help="load valid questions even if some have errors")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    files = sorted(data_dir.glob(args.pattern))
    if not files:
        print(f"No files matching {args.pattern} in {data_dir}")
        return 1

    rows, errors, seen = [], [], set()
    for f in files:
        try:
            items = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as ex:
            errors.append(f"{f.name}: invalid JSON ({ex})")
            continue
        file_nums, n_ok = [], 0
        for d in items:
            tag = f"{f.name} Q{d.get('number', '?')}"
            try:
                row, warns = check_question(d, data_dir)
                key = (row["chapter"], row["number"])
                if key in seen:
                    raise ValueError("duplicate (chapter, number)")
                seen.add(key)
            except ValueError as ex:
                errors.append(f"{tag}: {ex}")
                continue
            rows.append(row)
            file_nums.append(row["number"])
            n_ok += 1
            for w in warns:
                print(f"  WARN  {tag}: {w}")
        gaps = sorted(set(range(1, max(file_nums) + 1)) - set(file_nums)) if file_nums else []
        print(f"{f.name}: {n_ok}/{len(items)} valid | missing numbers: {gaps or 'none'}")

    for e in errors:
        print(f"  ERROR {e}")

    if errors and not args.skip_invalid:
        print(f"\n{len(errors)} error(s). Nothing written. Fix the JSON, or use --skip-invalid.")
        return 1
    if args.dry_run:
        print(f"\nDry run: {len(rows)} valid questions, nothing written.")
        return 0

    con = sqlite3.connect(args.db)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text(encoding="utf-8"))  # no-op if tables already exist
    inserted = updated = 0
    with con:  # single transaction: commit on success, roll back on exception
        for row in rows:
            exists = con.execute(
                "SELECT 1 FROM questions WHERE chapter = ? AND number = ?", (row["chapter"], row["number"])
            ).fetchone()
            con.execute(UPSERT, row)
            updated += bool(exists)
            inserted += not exists

    print(f"\nLoaded into {args.db}: {inserted} inserted, {updated} updated.")
    print("Per chapter / status:")
    for ch, st, n in con.execute(
        "SELECT chapter, status, COUNT(*) FROM questions GROUP BY chapter, status ORDER BY chapter, status"
    ):
        print(f"  chapter {ch}: {n:>3} {st}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
