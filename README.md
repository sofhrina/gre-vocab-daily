# GRE Vocab Daily

A local-first GRE vocabulary study app built with Python, Streamlit, and SQLite.
It supports new-word study, spaced repetition, red-word tracking, daily progress,
search and editing, and CSV exports.

Each user runs the app locally. There is no login, cloud backend, or public sharing
of study records.

## Features

- Study unseen words by vocabulary list
- Review due words with level-based spaced repetition
- Automatically identify difficult words from learning performance
- Track daily activity and accuracy
- Search, edit, and delete vocabulary entries
- Export words, difficult words, study logs, and a complete database backup

## Install And Run

Clone this repository, then open Terminal in the project directory:

```bash
git clone YOUR_REPOSITORY_URL
cd gre-vocab-daily
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501` if Streamlit does not open automatically.
The SQLite database is created at `data/gre_vocab.db`.

## Import Vocabulary

Open the **Import** page and upload a CSV. Required columns:

```text
list_name,word,phonetic,meaning,equivalents,example
```

Only `list_name` and `word` must contain values. Optional `source` and `notes`
columns are also supported. The importer additionally accepts `meaning_cn`,
`equivalent_words`, and `example_sentence` as alternate column names.

You can import `data/example_vocab.csv` to try the app. Duplicate English words
are skipped case-insensitively.

## Successive Relearning Schedule

The app combines active recall, immediate feedback, and expanding spaced retrieval.
New words that are vague or unknown remain due for another same-day recall attempt.
Only words already studied can appear on the Review page.

New-word ratings:

| Rating | New level | Next review |
|---|---:|---:|
| Know | At least stage 1 | 1 day |
| Vague | Stage 0 | Same day |
| Don't Know | Stage 0 | Same day |

Review ratings:

| Rating | Level change | Next review |
|---|---:|---:|
| Forgot | Return to stage 0 | 1 day |
| Vague | Move back one stage | 1 day |
| Remembered | Plus 1, maximum 7 | Interval for new stage |
| Easy | Plus 2, maximum 7 | Interval for new stage |

Intervals by stage: stages 0–1 = 1 day, stage 2 = 3 days, stage 3 = 7 days,
stage 4 = 14 days, stage 5 = 30 days, stage 6 = 60 days, and stage 7 = 120 days.

Statuses are derived automatically:

- **Unseen:** never studied
- **Learning:** stages 0–1
- **Reviewing:** stages 2–5
- **Mastered:** stages 6–7

Difficult words are detected from repeated mistakes, low review accuracy, or being
stuck in early learning stages. Users can separately star any important word.

## Data And Privacy

Vocabulary CSV files and the SQLite study database are excluded from Git by
default. This prevents personal progress and third-party vocabulary datasets from
being accidentally published.

To back up your progress privately, copy `data/gre_vocab.db` while the app is
closed, or use **Export → Download complete database backup**.

Database upgrades use additive migrations so existing vocabulary and progress are
preserved. Future features such as practice-error tracking should use separate
database tables rather than altering vocabulary history.

## Publishing Your Own Vocabulary

Only publish vocabulary datasets that you created, that are in the public domain,
or that you have permission to redistribute. The MIT license in this repository
applies to the software code, not to third-party vocabulary content imported by
users.

## License

The software code is available under the [MIT License](LICENSE).
