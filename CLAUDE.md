# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flash Trainer is a Streamlit-based flashcard study app. It supports multiple flashcard sets (any CSV in `data/`), presents Q&A pairs in random order with spaced-repetition-lite logic, tracks session statistics, and offers a completion screen where users can restart with a subset filtered by score.

## Commands

```bash
pip install -r requirements.txt      # Install dependencies
python convert_docx_to_csv.py        # Re-generate CSV from the source DOCX
streamlit run app.py                  # Launch the app (opens in browser)
```

## Architecture

- **`convert_docx_to_csv.py`** — One-time script that parses `data/Flashcard questions Dutch history.docx` into `data/flashcards.csv` (columns: `section`, `question`, `answer`). Uses zipfile/xml parsing (no python-docx dependency at runtime).
- **`app.py`** — Single-file Streamlit app. All state (queue, stats, per-card ratings) lives in `st.session_state` — purely session-based, nothing persisted to disk. Supports multiple CSV sets via auto-discovery of `data/*.csv`.
- **`data/*.csv`** — Flashcard sets. Each CSV must have columns `section`, `question`, `answer`. The file name becomes the display name in the set picker.

## Key Design Decisions

- **Spaced repetition logic**: Rating 1-2 reinserts card 3-7 positions ahead; rating 3 reinserts 10-15 ahead; rating 4-5 defers to end-of-round pool. End-pool cards form a new round when the main queue is exhausted.
- **Section filtering**: Users select which sections (Mock, Multiple Choice by lecture, Essay by lecture) to study before starting.
- **Completion screen**: Shows full score breakdown per rating bucket. Users can restart with only cards from selected rating buckets (e.g. practise only Bad/Poor/Okay cards).
- **Per-card rating tracking**: `card_ratings` dict in session state maps each question to its last rating, enabling the restart-by-score filter.
- **Styling**: Custom CSS injected via `st.markdown(unsafe_allow_html=True)` for colored question/answer cards and stat boxes.
