import csv
import io
from datetime import date
from pathlib import Path

import streamlit as st

import db
from importer import import_csv


BASE_DIR = Path(__file__).resolve().parent
EXAMPLE_CSV = BASE_DIR / "data" / "example_vocab.csv"

st.set_page_config(page_title="GRE Vocab Daily", page_icon="G", layout="wide")
st.markdown(
    """
    <style>
    .word-card {text-align:center; padding:2rem 1rem 1rem}
    .word-card h1 {font-size:4rem; margin-bottom:.2rem}
    .phonetic {font-size:1.25rem; color:#777}
    .answer {font-size:1.15rem; padding:1rem 1.5rem; border-left:4px solid #ff4b4b;
             background:rgba(128,128,128,.08); margin:1rem 0}
    div[data-testid="stMetric"] {border:1px solid rgba(128,128,128,.25); padding:12px; border-radius:8px}
    </style>
    """,
    unsafe_allow_html=True,
)
db.init_db()


def csv_bytes(items):
    if not items:
        return b""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=items[0].keys())
    writer.writeheader()
    writer.writerows(items)
    return output.getvalue().encode("utf-8-sig")


def show_word_card(word, include_notes=False):
    if st.session_state.get("answer_word_id") != word["id"]:
        st.session_state.answer_shown = False
        st.session_state.answer_word_id = word["id"]
    st.markdown(
        f'<div class="word-card"><h1>{word["word"]}</h1>'
        f'<div class="phonetic">{word["phonetic"] or ""}</div></div>',
        unsafe_allow_html=True,
    )
    if st.session_state.get("answer_shown", False):
        parts = [f"**Meaning:** {word['meaning'] or '—'}"]
        if word["equivalents"]:
            parts.append(f"**Equivalents:** {word['equivalents']}")
        if word["example"]:
            parts.append(f"**Example:** {word['example']}")
        if include_notes and word["notes"]:
            parts.append(f"**Notes:** {word['notes']}")
        with st.container(border=True):
            for part in parts:
                st.markdown(part)
        return True
    if st.button("Show Answer", type="primary", width="stretch"):
        st.session_state.answer_shown = True
        st.rerun()
    return False


def rate_buttons(word_id, kind, ratings):
    columns = st.columns(len(ratings))
    for col, (label, rating) in zip(columns, ratings):
        if col.button(label, width="stretch", key=f"{kind}_{word_id}_{rating}"):
            db.apply_rating(word_id, kind, rating)
            st.session_state.answer_shown = False
            st.rerun()


def dashboard_page():
    st.title("GRE Vocab Daily")
    st.caption(f"Today: {date.today().isoformat()}")
    stats = db.dashboard_stats()
    metrics = [
        ("Total words", stats.get("total_words", 0)),
        ("Due today", stats.get("due_today", 0)),
        ("New studied today", stats.get("new_words_studied", 0)),
        ("Reviews today", stats.get("review_words_completed", 0)),
        ("Accuracy today", f"{stats.get('accuracy', 0)}%"),
        ("Red words", stats.get("red_words", 0)),
        ("Mastered (level ≥ 4)", stats.get("mastered_words", 0)),
    ]
    cols = st.columns(4)
    for index, (label, value) in enumerate(metrics):
        cols[index % 4].metric(label, value or 0)

    st.subheader("Progress by list")
    progress = db.progress_by_list()
    st.dataframe(progress, width="stretch", hide_index=True)
    st.subheader("Daily study log")
    logs = db.rows("SELECT * FROM daily_log ORDER BY date DESC LIMIT 60")
    st.dataframe(logs, width="stretch", hide_index=True)


def import_page():
    st.title("Import Vocabulary")
    st.write("Duplicates are skipped using the English word as a case-insensitive unique key.")
    uploaded = st.file_uploader("Choose a vocabulary CSV", type="csv")
    if uploaded and st.button("Import uploaded CSV", type="primary"):
        try:
            result = import_csv(uploaded)
            st.success(
                f"Imported {result['imported']} words. Skipped {result['duplicates']} duplicates"
                f" and {result['skipped_blank']} blank rows."
            )
        except ValueError as exc:
            st.error(str(exc))
    if EXAMPLE_CSV.exists() and st.button("Import example vocabulary CSV"):
        result = import_csv(EXAMPLE_CSV.read_bytes())
        st.success(
            f"Imported {result['imported']} words. Skipped {result['duplicates']} duplicates"
            f" and {result['skipped_blank']} blank rows."
        )


def new_words_page():
    st.title("Study New Words")
    names = db.list_names()
    if not names:
        st.info("Import the vocabulary CSV first.")
        return
    selected = st.selectbox("List", names)
    remaining = db.row(
        "SELECT COUNT(*) count FROM words WHERE list_name = ? AND times_reviewed = 0",
        (selected,),
    )["count"]
    st.caption(f"{remaining} unseen words remaining in this list")
    word = db.row(
        "SELECT * FROM words WHERE list_name = ? AND times_reviewed = 0 ORDER BY id LIMIT 1",
        (selected,),
    )
    if not word:
        st.success("You have studied every new word in this list.")
        return
    if show_word_card(word):
        rate_buttons(
            word["id"],
            "new",
            [("Don’t Know", "dont_know"), ("Vague", "vague"), ("Know", "know")],
        )


def review_page():
    st.title("Review Due Words")
    today = date.today().isoformat()
    due = db.row("SELECT COUNT(*) count FROM words WHERE next_review_date <= ?", (today,))["count"]
    st.caption(f"{due} words due")
    word = db.row(
        "SELECT * FROM words WHERE next_review_date <= ? ORDER BY next_review_date, times_reviewed DESC, id LIMIT 1",
        (today,),
    )
    if not word:
        st.success("All caught up for today.")
        return
    if show_word_card(word, include_notes=True):
        rate_buttons(
            word["id"],
            "review",
            [("Forgot", "forgot"), ("Vague", "vague"), ("Remembered", "remembered"), ("Easy", "easy")],
        )


def red_words_page():
    st.title("Red Words")
    names = ["All lists"] + db.list_names()
    left, right = st.columns(2)
    selected = left.selectbox("List", names, key="red_list")
    search = right.text_input("Search word or meaning", key="red_search")
    conditions = [db.is_red_clause()]
    params = []
    if selected != "All lists":
        conditions.append("list_name = ?")
        params.append(selected)
    if search:
        conditions.append("(word LIKE ? OR meaning LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    where = " AND ".join(conditions)
    red_words = db.rows(f"SELECT * FROM words WHERE {where} ORDER BY times_wrong DESC, word", params)
    st.caption(f"{len(red_words)} red words match the current filters")
    st.download_button(
        "Export filtered red words CSV",
        csv_bytes(red_words),
        "red_words.csv",
        "text/csv",
        disabled=not red_words,
    )
    if not red_words:
        st.info("No red words match.")
        return

    selected_id = st.selectbox(
        "Choose a red word to review",
        [item["id"] for item in red_words],
        format_func=lambda word_id: next(
            f"{item['word']} · L{item['level']} · wrong {item['times_wrong']}"
            for item in red_words
            if item["id"] == word_id
        ),
    )
    word = next(item for item in red_words if item["id"] == selected_id)
    if st.button("Remove manual red mark"):
        db.execute("UPDATE words SET is_red_word = 0 WHERE id = ?", (word["id"],))
        st.success("Manual red mark removed. Rule-based red status may still apply.")
        st.rerun()
    if show_word_card(word, include_notes=True):
        rate_buttons(
            word["id"],
            "review",
            [("Forgot", "forgot"), ("Vague", "vague"), ("Remembered", "remembered"), ("Easy", "easy")],
        )


def search_edit_page():
    st.title("Search & Edit")
    names = ["All lists"] + db.list_names()
    c1, c2, c3 = st.columns(3)
    search_word = c1.text_input("English word")
    search_meaning = c2.text_input("Chinese meaning")
    selected_list = c3.selectbox("List", names)
    c4, c5 = st.columns(2)
    selected_level = c4.selectbox("Level", ["All", 0, 1, 2, 3, 4, 5])
    red_only = c5.checkbox("Red words only")

    conditions, params = ["1 = 1"], []
    if search_word:
        conditions.append("word LIKE ?")
        params.append(f"%{search_word}%")
    if search_meaning:
        conditions.append("meaning LIKE ?")
        params.append(f"%{search_meaning}%")
    if selected_list != "All lists":
        conditions.append("list_name = ?")
        params.append(selected_list)
    if selected_level != "All":
        conditions.append("level = ?")
        params.append(selected_level)
    if red_only:
        conditions.append(db.is_red_clause())
    results = db.rows(
        f"SELECT * FROM words WHERE {' AND '.join(conditions)} ORDER BY word LIMIT 500",
        params,
    )
    st.caption(f"{len(results)} results shown (maximum 500)")
    if not results:
        return
    selected_id = st.selectbox(
        "Select entry",
        [item["id"] for item in results],
        format_func=lambda word_id: next(
            f"{item['word']} · {item['list_name']} · L{item['level']}"
            for item in results
            if item["id"] == word_id
        ),
    )
    item = next(item for item in results if item["id"] == selected_id)
    with st.form(f"edit_{selected_id}"):
        st.subheader(item["word"])
        meaning = st.text_area("Meaning", item["meaning"])
        equivalents = st.text_area("Equivalents", item["equivalents"])
        example = st.text_area("Example", item["example"])
        notes = st.text_area("Notes", item["notes"])
        is_red = st.checkbox("Manual red mark", bool(item["is_red_word"]))
        if st.form_submit_button("Save changes", type="primary"):
            db.execute(
                """
                UPDATE words SET meaning = ?, equivalents = ?, example = ?, notes = ?, is_red_word = ?
                WHERE id = ?
                """,
                (meaning, equivalents, example, notes, int(is_red), selected_id),
            )
            st.success("Entry updated.")
            st.rerun()
    confirm = st.checkbox("I understand this permanently deletes the selected entry.")
    if st.button("Delete entry", disabled=not confirm):
        db.execute("DELETE FROM words WHERE id = ?", (selected_id,))
        st.success("Entry deleted.")
        st.rerun()


def export_page():
    st.title("Export Data")
    st.write("Exports include a UTF-8 BOM so Chinese text opens cleanly in Excel.")
    all_words = db.rows("SELECT * FROM words ORDER BY list_name, id")
    red_words = db.rows(f"SELECT * FROM words WHERE {db.is_red_clause()} ORDER BY list_name, word")
    logs = db.rows("SELECT * FROM daily_log ORDER BY date")
    st.download_button("Download all words CSV", csv_bytes(all_words), "gre_vocab_all_words.csv", "text/csv")
    st.download_button("Download red words CSV", csv_bytes(red_words), "gre_vocab_red_words.csv", "text/csv")
    st.download_button("Download daily study log CSV", csv_bytes(logs), "gre_vocab_daily_log.csv", "text/csv")


PAGES = {
    "Dashboard": dashboard_page,
    "Import": import_page,
    "New Words": new_words_page,
    "Review": review_page,
    "Red Words": red_words_page,
    "Search & Edit": search_edit_page,
    "Export": export_page,
}

with st.sidebar:
    st.header("GRE Vocab Daily")
    page = st.radio("Navigate", list(PAGES), label_visibility="collapsed")
    st.divider()
    st.caption("Private local study app")

if "answer_shown" not in st.session_state:
    st.session_state.answer_shown = False
PAGES[page]()
