# Flash Trainer

A Streamlit-based flashcard study app for Dutch history exam preparation. It loads question-and-answer pairs from a CSV file, presents them in random order with spaced-repetition-style logic, and tracks your session statistics in real time.

## Features

- **Section filtering** — choose which sections (Mock exam, Multiple Choice by lecture, Essay by lecture) to study before starting a session.
- **Spaced repetition (lite)** — cards you rate poorly reappear soon; cards you know well are deferred to a later round.
- **Live statistics** — sidebar shows a running timer, review count, progress bar, average score, and rating distribution.
- **Multi-round sessions** — well-known cards form a new round once the current queue is exhausted, so you keep practising until everything sticks.
- **Multiple flashcard sets** — drop any number of CSV files into `data/` and pick which set to study from a dropdown.
- **Completion screen** — when a session ends you see a full score breakdown and can restart with only the cards you scored poorly on.

## Live App

Hosted on Streamlit Cloud: [flashtrainer.streamlit.app](https://flashtrainer.streamlit.app)

## Getting Started

### Prerequisites

- Python 3.10+

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

The app requires two secrets for authentication. Create `.streamlit/secrets.toml` (already gitignored):

```toml
[auth]
password = "your-password"
redirect_url = "https://your-redirect-url.com/"
```

On Streamlit Cloud, add the same values via **Manage app → Secrets** in the dashboard.

### Running the app

```bash
streamlit run app.py
```

This opens the app in your default browser.

## Project Structure

```
flash_trainer/
├── app.py                      # Main Streamlit application
├── convert_docx_to_csv.py      # Script to regenerate CSV from source DOCX
├── data/
│   ├── Flashcard questions Dutch history.docx   # Source document
│   └── flashcards.csv          # Runtime data (section, question, answer)
├── .streamlit/
│   └── secrets.toml            # Local secrets (gitignored)
├── requirements.txt
└── README.md
```

## How It Works

1. **Start screen** — select one or more sections and hit *Start Training*.
2. **Study loop** — a question card is shown; click *Show Answer* to reveal it, then rate yourself 1-5.
3. **Re-queuing logic**
   - Rating 1-2 (Bad/Poor): card is reinserted 3-7 positions ahead in the queue.
   - Rating 3 (Okay): card is reinserted 10-15 positions ahead.
   - Rating 4-5 (Good/Perfect): card moves to an end-of-round pool.
4. **New rounds** — when the queue runs out, end-pool cards are shuffled into a new round.
5. **Completion** — once no cards remain in either the queue or the pool, a summary screen is shown.

## Extending the App

### Adding or editing flashcards

Edit any CSV in `data/` directly, or add a new CSV file. Each CSV must have three columns:

| Column     | Description                                       |
|------------|---------------------------------------------------|
| `section`  | Grouping label shown in the section selector      |
| `question` | The question text                                 |
| `answer`   | The answer text (newlines within the field are OK) |

The app auto-discovers every `*.csv` file in `data/` and shows them in a dropdown. The file name (without extension) becomes the display name.

To regenerate the Dutch History CSV from the source DOCX:

```bash
python convert_docx_to_csv.py
```

### Adjusting spaced-repetition parameters

The re-insertion distances are defined in the `advance()` function in `app.py`. Change the `random.randint(...)` ranges to make cards reappear sooner or later.

### Styling

All custom CSS lives in the `st.markdown(...)` block near the top of `app.py`. Modify the `.question-card`, `.answer-card`, `.section-tag`, or `.stat-box` classes to change colours, fonts, or layout.
