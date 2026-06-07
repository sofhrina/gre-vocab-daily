import csv
import io
from datetime import date

from db import connect


ALIASES = {
    "list_name": ("list_name",),
    "word": ("word",),
    "phonetic": ("phonetic",),
    "meaning": ("meaning", "meaning_cn"),
    "equivalents": ("equivalents", "equivalent_words"),
    "example": ("example", "example_sentence"),
    "source": ("source",),
    "notes": ("notes",),
}


def value_for(raw, field):
    for candidate in ALIASES[field]:
        if candidate in raw and raw[candidate] is not None:
            return raw[candidate].strip()
    return ""


def import_csv(file_or_bytes):
    if hasattr(file_or_bytes, "read"):
        content = file_or_bytes.read()
    else:
        content = file_or_bytes
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(content))
    required = {"list_name", "word"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise ValueError("CSV must contain list_name and word columns.")

    imported = duplicates = skipped_blank = 0
    today = date.today().isoformat()
    with connect() as conn:
        for raw in reader:
            word = value_for(raw, "word")
            if not word:
                skipped_blank += 1
                continue
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO words (
                    list_name, word, phonetic, meaning, equivalents, example, source,
                    level, next_review_date, times_reviewed, times_wrong, date_added,
                    is_red_word, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, 0, 0, ?, 0, ?)
                """,
                (
                    value_for(raw, "list_name"),
                    word,
                    value_for(raw, "phonetic"),
                    value_for(raw, "meaning"),
                    value_for(raw, "equivalents"),
                    value_for(raw, "example"),
                    value_for(raw, "source") or "Imported CSV",
                    today,
                    today,
                    value_for(raw, "notes"),
                ),
            )
            if cursor.rowcount:
                imported += 1
            else:
                duplicates += 1
    return {"imported": imported, "duplicates": duplicates, "skipped_blank": skipped_blank}
