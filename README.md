# GRE Vocab Daily

A local-first GRE vocabulary study app built with Python, Streamlit, and SQLite.
It supports new-word study, spaced repetition, red-word tracking, daily progress,
search and editing, and CSV exports.

Each user runs the app locally. There is no login, cloud backend, or public sharing
of study records.

## Features

- Study unseen words by vocabulary list
- Review due words with level-based spaced repetition
- Automatically identify difficult red words
- Track daily activity and accuracy
- Search, edit, and delete vocabulary entries
- Export words, red words, and study logs to CSV

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

## Spaced Repetition

New-word ratings:

| Rating | New level | Next review |
|---|---:|---:|
| Know | At least 2 | 4 days |
| Vague | At least 1 | 2 days |
| Don't Know | 0 | 1 day |

Review ratings:

| Rating | Level change | Next review |
|---|---:|---:|
| Forgot | Minus 1, minimum 0 | 1 day |
| Vague | No change | 2 days |
| Remembered | Plus 1, maximum 5 | Interval for new level |
| Easy | Plus 2, maximum 5 | Interval for new level |

Intervals by level: level 0 = 1 day, level 1 = 2 days, level 2 = 4 days,
level 3 = 7 days, level 4 = 15 days, and level 5 = 30 days.

## Data And Privacy

Vocabulary CSV files and the SQLite study database are excluded from Git by
default. This prevents personal progress and third-party vocabulary datasets from
being accidentally published.

To back up your progress privately, copy `data/gre_vocab.db` while the app is
closed.

## Publishing Your Own Vocabulary

Only publish vocabulary datasets that you created, that are in the public domain,
or that you have permission to redistribute. The MIT license in this repository
applies to the software code, not to third-party vocabulary content imported by
users.

## License

The software code is available under the [MIT License](LICENSE).
