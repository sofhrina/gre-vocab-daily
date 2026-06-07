import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from scheduler import schedule_new_word, schedule_review


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "gre_vocab.db"


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                list_name TEXT NOT NULL,
                word TEXT NOT NULL COLLATE NOCASE UNIQUE,
                phonetic TEXT DEFAULT '',
                meaning TEXT DEFAULT '',
                equivalents TEXT DEFAULT '',
                example TEXT DEFAULT '',
                source TEXT DEFAULT 'Imported CSV',
                level INTEGER NOT NULL DEFAULT 0,
                next_review_date TEXT NOT NULL,
                times_reviewed INTEGER NOT NULL DEFAULT 0,
                times_wrong INTEGER NOT NULL DEFAULT 0,
                date_added TEXT NOT NULL,
                last_reviewed TEXT,
                is_red_word INTEGER NOT NULL DEFAULT 0,
                notes TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS daily_log (
                date TEXT PRIMARY KEY,
                new_words_studied INTEGER NOT NULL DEFAULT 0,
                review_words_completed INTEGER NOT NULL DEFAULT 0,
                forgot_count INTEGER NOT NULL DEFAULT 0,
                vague_count INTEGER NOT NULL DEFAULT 0,
                remembered_count INTEGER NOT NULL DEFAULT 0,
                easy_count INTEGER NOT NULL DEFAULT 0,
                wrong_count INTEGER NOT NULL DEFAULT 0,
                accuracy REAL NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_words_due ON words(next_review_date);
            CREATE INDEX IF NOT EXISTS idx_words_list ON words(list_name);
            CREATE INDEX IF NOT EXISTS idx_words_level ON words(level);
            """
        )


def rows(query, params=()):
    with connect() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def row(query, params=()):
    result = rows(query, params)
    return result[0] if result else None


def execute(query, params=()):
    with connect() as conn:
        cursor = conn.execute(query, params)
        return cursor.rowcount


def list_names():
    return [item["list_name"] for item in rows("SELECT DISTINCT list_name FROM words ORDER BY list_name")]


def is_red_clause():
    return "(is_red_word = 1 OR times_wrong >= 2 OR (level <= 1 AND times_reviewed >= 2))"


def record_activity(kind: str, rating: str):
    today = date.today().isoformat()
    allowed = {"forgot", "vague", "remembered", "easy"}
    rating_column = f"{rating}_count" if rating in allowed else None
    with connect() as conn:
        conn.execute("INSERT OR IGNORE INTO daily_log(date) VALUES (?)", (today,))
        activity_col = "new_words_studied" if kind == "new" else "review_words_completed"
        conn.execute(f"UPDATE daily_log SET {activity_col} = {activity_col} + 1 WHERE date = ?", (today,))
        if rating_column:
            conn.execute(
                f"UPDATE daily_log SET {rating_column} = {rating_column} + 1 WHERE date = ?",
                (today,),
            )
        if rating in {"forgot", "dont_know"}:
            conn.execute("UPDATE daily_log SET wrong_count = wrong_count + 1 WHERE date = ?", (today,))
        conn.execute(
            """
            UPDATE daily_log
            SET accuracy = CASE
                WHEN new_words_studied + review_words_completed = 0 THEN 0
                ELSE ROUND(
                    100.0 * (new_words_studied + review_words_completed - wrong_count)
                    / (new_words_studied + review_words_completed), 1
                )
            END
            WHERE date = ?
            """,
            (today,),
        )


def apply_rating(word_id: int, kind: str, rating: str):
    word = row("SELECT * FROM words WHERE id = ?", (word_id,))
    if not word:
        return
    result = (
        schedule_new_word(word["level"], rating)
        if kind == "new"
        else schedule_review(word["level"], rating)
    )
    execute(
        """
        UPDATE words SET level = ?, next_review_date = ?, times_reviewed = times_reviewed + 1,
            times_wrong = times_wrong + ?, last_reviewed = ?,
            is_red_word = CASE WHEN ? THEN 1 ELSE is_red_word END
        WHERE id = ?
        """,
        (
            result["level"],
            result["next_review_date"],
            result["wrong_increment"],
            date.today().isoformat(),
            result["mark_red"],
            word_id,
        ),
    )
    record_activity(kind, rating)


def dashboard_stats():
    today = date.today().isoformat()
    stats = row(
        f"""
        SELECT COUNT(*) total_words,
            SUM(CASE WHEN next_review_date <= ? THEN 1 ELSE 0 END) due_today,
            SUM(CASE WHEN {is_red_clause()} THEN 1 ELSE 0 END) red_words,
            SUM(CASE WHEN level >= 4 THEN 1 ELSE 0 END) mastered_words
        FROM words
        """,
        (today,),
    )
    log = row("SELECT * FROM daily_log WHERE date = ?", (today,)) or {}
    return {**stats, **log}


def progress_by_list():
    return rows(
        """
        SELECT list_name, COUNT(*) total_words,
            SUM(CASE WHEN times_reviewed > 0 THEN 1 ELSE 0 END) studied_words,
            SUM(CASE WHEN level >= 4 THEN 1 ELSE 0 END) mastered_words,
            ROUND(100.0 * SUM(CASE WHEN times_reviewed > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) progress_pct
        FROM words GROUP BY list_name ORDER BY list_name
        """
    )
