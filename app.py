"""Flash Trainer – A Streamlit flashcard study app for Dutch History."""

import glob
import os
import random
import time
import tomllib
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_config_path = Path(__file__).parent / "config.toml"
with open(_config_path, "rb") as _f:
    _config = tomllib.load(_f)

AUTH_PASSWORD = _config["auth"]["password"]
AUTH_REDIRECT_URL = _config["auth"]["redirect_url"]

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Flash Trainer", page_icon="📚", layout="centered")

# ---------------------------------------------------------------------------
# Custom CSS – clear, bold colours
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Question card */
    .question-card {
        background: #1a5276;
        color: #ffffff;
        padding: 2rem;
        border-radius: 1rem;
        font-size: 1.25rem;
        line-height: 1.6;
        margin-bottom: 1rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    /* Answer card */
    .answer-card {
        background: #0e6655;
        color: #ffffff;
        padding: 2rem;
        border-radius: 1rem;
        font-size: 1.15rem;
        line-height: 1.6;
        margin-bottom: 1rem;
        white-space: pre-line;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    /* Section tag */
    .section-tag {
        background: #f39c12;
        color: #000;
        padding: 0.25rem 0.75rem;
        border-radius: 0.5rem;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 0.75rem;
    }
    /* Stats metric */
    .stat-box {
        background: #2c3e50;
        color: #ecf0f1;
        padding: 1rem;
        border-radius: 0.75rem;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .stat-box h3 { margin: 0; font-size: 1.6rem; color: #f39c12; }
    .stat-box p  { margin: 0.25rem 0 0 0; font-size: 0.85rem; }
    /* Rating labels */
    .rating-labels {
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        color: #888;
        margin-top: -0.5rem;
        margin-bottom: 0.5rem;
    }
    /* Title styling */
    .main-title {
        text-align: center;
        color: #1a5276;
        margin-bottom: 0.5rem;
    }
    /* Completion card */
    .completion-card {
        background: #2c3e50;
        color: #ecf0f1;
        padding: 1.5rem;
        border-radius: 1rem;
        text-align: center;
        margin-bottom: 1rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .completion-card h2 { margin: 0 0 0.5rem 0; color: #27ae60; }
    .completion-card .big-number { font-size: 2.5rem; color: #f39c12; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Data loading – support multiple CSV files in data/
# ---------------------------------------------------------------------------
@st.cache_data
def discover_flashcard_sets() -> dict[str, str]:
    """Return {display_name: file_path} for each CSV in data/."""
    csv_files = sorted(glob.glob("data/*.csv"))
    sets = {}
    for path in csv_files:
        name = os.path.splitext(os.path.basename(path))[0]
        # Make the name human-readable
        display = name.replace("_", " ").replace("-", " ").title()
        sets[display] = path
    return sets


@st.cache_data
def load_flashcards(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


flashcard_sets = discover_flashcard_sets()

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
defaults = {
    "authenticated": False,
    "started": False,
    "queue": [],
    "end_pool": [],
    "current_idx": 0,
    "show_answer": False,
    "rated": False,
    "stats_reviews": 0,
    "stats_ratings": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
    "stats_seen": set(),
    "stats_total": 0,
    "start_time": None,
    "paused_elapsed": 0,  # seconds accumulated before pauses
    "round_number": 1,
    "finished": False,
    "round_finished": False,  # pause between rounds for summary
    "round_card_history": {},  # question -> [ratings] for current round
    "card_history": {},  # question -> [all ratings] across session
    "active_cards": [],  # snapshot of cards used in current session
    "selected_csv": None,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ---------------------------------------------------------------------------
# Helper: build / manage the queue
# ---------------------------------------------------------------------------
def build_queue_from_cards(cards: list[dict]):
    """Initialise a session from a pre-built list of card dicts."""
    random.shuffle(cards)
    st.session_state.queue = cards
    st.session_state.end_pool = []
    st.session_state.current_idx = 0
    st.session_state.show_answer = False
    st.session_state.rated = False
    st.session_state.stats_reviews = 0
    st.session_state.stats_ratings = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    st.session_state.stats_seen = set()
    st.session_state.stats_total = len(cards)
    st.session_state.start_time = time.time()
    st.session_state.paused_elapsed = 0
    st.session_state.round_number = 1
    st.session_state.finished = False
    st.session_state.round_finished = False
    st.session_state.round_card_history = {}
    st.session_state.card_history = {}
    st.session_state.active_cards = list(cards)
    st.session_state.started = True


def build_queue(df: pd.DataFrame, selected_sections: list[str]):
    cards = df[df["section"].isin(selected_sections)].to_dict("records")
    build_queue_from_cards(cards)


def start_next_round(cards: list[dict]):
    """Begin the next round with the given cards."""
    st.session_state.round_number += 1
    random.shuffle(cards)
    st.session_state.queue = cards
    st.session_state.end_pool = []
    st.session_state.current_idx = 0
    st.session_state.show_answer = False
    st.session_state.rated = False
    st.session_state.round_finished = False
    st.session_state.round_card_history = {}
    # Reset round counters and progress
    st.session_state.stats_reviews = 0
    st.session_state.stats_ratings = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    st.session_state.stats_seen = set()
    st.session_state.stats_total = len(cards)
    # Resume the clock
    st.session_state.start_time = time.time()


def current_card() -> dict | None:
    q = st.session_state.queue
    idx = st.session_state.current_idx
    if idx < len(q):
        return q[idx]
    return None


def advance(rating: int):
    card = current_card()
    if card is None:
        return

    q = st.session_state.queue
    idx = st.session_state.current_idx
    card_id = card["question"]

    # Update stats
    st.session_state.stats_reviews += 1
    st.session_state.stats_ratings[rating] += 1
    st.session_state.stats_seen.add(card_id)
    st.session_state.card_history.setdefault(card_id, []).append(rating)
    st.session_state.round_card_history.setdefault(card_id, []).append(rating)

    if rating <= 2:
        # Bad – reinsert 3-7 positions ahead
        insert_pos = idx + 1 + random.randint(3, min(7, max(3, len(q) - idx - 1)))
        insert_pos = min(insert_pos, len(q))
        q.insert(insert_pos, card)
    elif rating == 3:
        # Okay – reinsert 10-15 positions ahead
        insert_pos = idx + 1 + random.randint(10, min(15, max(10, len(q) - idx - 1)))
        insert_pos = min(insert_pos, len(q))
        q.insert(insert_pos, card)
    else:
        # Good/Perfect – goes to end-of-round pool
        st.session_state.end_pool.append(card)

    st.session_state.current_idx = idx + 1

    # Check if we've exhausted the current queue
    if st.session_state.current_idx >= len(q):
        # Pause the clock: accumulate elapsed time so far
        if st.session_state.start_time is not None:
            st.session_state.paused_elapsed += time.time() - st.session_state.start_time
            st.session_state.start_time = None
        if st.session_state.end_pool:
            # Pause for round summary instead of auto-advancing
            st.session_state.round_finished = True
        else:
            st.session_state.finished = True

    st.session_state.show_answer = False
    st.session_state.rated = False


# ---------------------------------------------------------------------------
# Sidebar – Statistics
# ---------------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.markdown("## Statistics")

        if st.session_state.start_time is not None or st.session_state.paused_elapsed > 0:
            import base64
            paused = st.session_state.paused_elapsed
            if st.session_state.start_time is not None:
                # Clock is running: JS counts live from a virtual start that
                # accounts for previously accumulated time
                virtual_start = time.time() - paused
                timer_html = f"""<!DOCTYPE html>
<html><body style="margin:0;font-family:sans-serif;overflow:hidden;">
<div style="background:#2c3e50;color:#ecf0f1;padding:1rem;
            border-radius:0.75rem;text-align:center;">
    <h3 id="t" style="margin:0;font-size:1.6rem;color:#f39c12;">00:00</h3>
    <p style="margin:0.25rem 0 0 0;font-size:0.85rem;">Time spent</p>
</div>
<script>
const s={virtual_start};
function u(){{const e=Math.floor(Date.now()/1000-s);
document.getElementById('t').textContent=
String(Math.floor(e/60)).padStart(2,'0')+':'+String(e%60).padStart(2,'0');}}
u();setInterval(u,1000);
</script></body></html>"""
            else:
                # Clock is paused: show static frozen time
                total_secs = int(paused)
                mm = str(total_secs // 60).zfill(2)
                ss = str(total_secs % 60).zfill(2)
                timer_html = f"""<!DOCTYPE html>
<html><body style="margin:0;font-family:sans-serif;overflow:hidden;">
<div style="background:#2c3e50;color:#ecf0f1;padding:1rem;
            border-radius:0.75rem;text-align:center;">
    <h3 style="margin:0;font-size:1.6rem;color:#f39c12;">{mm}:{ss}</h3>
    <p style="margin:0.25rem 0 0 0;font-size:0.85rem;">Time spent (paused)</p>
</div></body></html>"""
            b64 = base64.b64encode(timer_html.encode()).decode()
            st.markdown(
                f'<iframe src="data:text/html;base64,{b64}" '
                f'style="width:100%;height:80px;border:none;"></iframe>',
                unsafe_allow_html=True,
            )

        reviews = st.session_state.stats_reviews
        total = st.session_state.stats_total
        seen = len(st.session_state.stats_seen)

        st.markdown(
            f'<div class="stat-box"><h3>{reviews}</h3>'
            f"<p>Cards reviewed</p></div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div class="stat-box"><h3>{seen} / {total}</h3>'
            f"<p>Unique cards seen</p></div>",
            unsafe_allow_html=True,
        )

        if total > 0:
            remaining = len(st.session_state.queue) - st.session_state.current_idx
            pct_progress = max(0, (total - remaining) / total * 100)
            st.markdown(
                f'<p style="font-size:0.85rem;margin-bottom:0.25rem;">Progress</p>'
                f'<div style="background:transparent;border:1px solid #7f8c8d;'
                f'border-radius:0.75rem;height:20px;overflow:hidden;margin-bottom:0.75rem;">'
                f'<div style="width:{pct_progress}%;background:#27ae60;height:100%;'
                f'border-radius:0.75rem;transition:width 0.3s ease;"></div>'
                f"</div>",
                unsafe_allow_html=True,
            )

        # Rating distribution
        ratings = st.session_state.stats_ratings
        if reviews > 0:
            avg = sum(r * c for r, c in ratings.items()) / reviews
            st.markdown(
                f'<div class="stat-box"><h3>{avg:.1f}</h3>'
                f"<p>Average score</p></div>",
                unsafe_allow_html=True,
            )

            st.markdown("#### Rating Distribution")
            labels = {1: "Bad", 2: "Poor", 3: "Okay", 4: "Good", 5: "Perfect"}
            colors = {1: "#e74c3c", 2: "#e67e22", 3: "#f1c40f", 4: "#2ecc71", 5: "#27ae60"}
            for r in range(1, 6):
                count = ratings[r]
                pct = count / reviews * 100
                st.markdown(
                    f'<div style="display:flex;align-items:center;margin-bottom:4px;">'
                    f'<span style="width:60px;font-size:0.85rem;">{labels[r]}</span>'
                    f'<div style="flex:1;background:#ecf0f1;border-radius:4px;height:18px;margin:0 8px;">'
                    f'<div style="width:{pct}%;background:{colors[r]};height:100%;border-radius:4px;"></div>'
                    f"</div>"
                    f'<span style="font-size:0.85rem;width:30px;text-align:right;">{count}</span>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        st.markdown(f"**Round:** {st.session_state.round_number}")
        remaining = len(st.session_state.queue) - st.session_state.current_idx
        st.markdown(f"**Remaining in queue:** {remaining}")
        st.markdown(f"**End-of-round pool:** {len(st.session_state.end_pool)}")

        st.markdown("---")
        if st.button("Restart", use_container_width=True):
            for key in defaults:
                if key == "authenticated":
                    continue
                st.session_state[key] = (
                    defaults[key]
                    if not isinstance(defaults[key], (set, dict, list))
                    else type(defaults[key])(defaults[key])
                )
            st.rerun()


def reset_to_home():
    """Reset all state back to the home / set-selection screen."""
    for key in defaults:
        if key == "authenticated":
            continue
        st.session_state[key] = (
            defaults[key]
            if not isinstance(defaults[key], (set, dict, list))
            else type(defaults[key])(defaults[key])
        )


# ---------------------------------------------------------------------------
# Login gate
# ---------------------------------------------------------------------------
if not st.session_state.authenticated:
    st.markdown('<h1 class="main-title">Flash Trainer</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align:center;color:#7f8c8d;margin-bottom:2rem;">Enter the password to continue</p>',
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        pwd = st.text_input("Password", type="password", placeholder="Password")
        submitted = st.form_submit_button("Enter", use_container_width=True, type="primary")

    if submitted:
        if pwd == AUTH_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.markdown(
                f'<meta http-equiv="refresh" content="0; url={AUTH_REDIRECT_URL}">',
                unsafe_allow_html=True,
            )
            st.stop()

    st.stop()

# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------
st.markdown('<h1 class="main-title">Flash Trainer</h1>', unsafe_allow_html=True)
st.markdown(
    '<p style="text-align:center;color:#7f8c8d;">Flashcard Study Trainer</p>',
    unsafe_allow_html=True,
)

if not st.session_state.started:
    # ---- Flashcard set selector ----
    if len(flashcard_sets) == 0:
        st.error("No CSV files found in `data/`. Add at least one flashcard CSV.")
        st.stop()

    st.markdown("### Choose a flashcard set")
    set_names = list(flashcard_sets.keys())
    selected_set = st.selectbox(
        "Flashcard set",
        options=set_names,
        label_visibility="collapsed",
    )
    csv_path = flashcard_sets[selected_set]
    df = load_flashcards(csv_path)
    all_sections = sorted(df["section"].unique())

    # ---- Section selector ----
    st.markdown("### Select sections to study")
    section_counts = df["section"].value_counts().to_dict()
    short_names = {"Multiple Choice": "MC"}
    section_labels = [
        f"{short_names.get(s, s)} ({section_counts[s]})" for s in all_sections
    ]
    label_to_section = dict(zip(section_labels, all_sections))

    selected_labels = st.multiselect(
        "Sections",
        options=section_labels,
        default=section_labels,
        label_visibility="collapsed",
    )
    selected = [label_to_section[l] for l in selected_labels]

    if selected:
        count = len(df[df["section"].isin(selected)])
        st.info(f"{count} flashcards selected")

    if st.button(
        "Start Training",
        type="primary",
        use_container_width=True,
        disabled=not selected,
    ):
        st.session_state.selected_csv = csv_path
        build_queue(df, selected)
        st.rerun()

elif st.session_state.round_finished:
    # ---- Round summary screen ----
    render_sidebar()

    round_num = st.session_state.round_number
    round_history = st.session_state.round_card_history
    pool = st.session_state.end_pool
    round_seen = len(round_history)

    st.markdown(
        '<div class="completion-card">'
        f"<h2>Round {round_num} Complete!</h2>"
        f'<div class="big-number">{round_seen}</div>'
        "<p>unique cards this round</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    # Classify cards by their history this round:
    # "Struggled" = had at least one rating <= 3 before passing
    # "Aced" = only ever rated 4-5 (got it right first time)
    struggled_qs = set()
    aced_qs = set()
    for q, ratings_list in round_history.items():
        if any(r <= 3 for r in ratings_list):
            struggled_qs.add(q)
        else:
            aced_qs.add(q)


    if round_seen > 0:
        # Show attempts summary
        total_attempts = sum(len(rl) for rl in round_history.values())
        multi_attempt = sum(1 for rl in round_history.values() if len(rl) > 1)

        col1, col2, col3 = st.columns(3)
        col1.metric("Cards", round_seen)
        col2.metric("Total attempts", total_attempts)
        col3.metric("Needed retries", multi_attempt)

        st.markdown("#### Round Breakdown")
        aced_pct = len(aced_qs) / round_seen * 100
        struggled_pct = len(struggled_qs) / round_seen * 100
        st.markdown(
            f'<div style="display:flex;align-items:center;margin-bottom:6px;">'
            f'<span style="width:120px;font-size:0.95rem;font-weight:600;">Aced first try</span>'
            f'<div style="flex:1;background:#ecf0f1;border-radius:0.5rem;height:22px;margin:0 8px;">'
            f'<div style="width:{aced_pct}%;background:#27ae60;height:100%;'
            f'border-radius:0.5rem;min-width:{"2rem" if aced_qs else "0"};'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:0.75rem;color:#fff;font-weight:600;">'
            f"{len(aced_qs)}</div></div></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="display:flex;align-items:center;margin-bottom:6px;">'
            f'<span style="width:120px;font-size:0.95rem;font-weight:600;">Struggled</span>'
            f'<div style="flex:1;background:#ecf0f1;border-radius:0.5rem;height:22px;margin:0 8px;">'
            f'<div style="width:{struggled_pct}%;background:#e74c3c;height:100%;'
            f'border-radius:0.5rem;min-width:{"2rem" if struggled_qs else "0"};'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:0.75rem;color:#fff;font-weight:600;">'
            f"{len(struggled_qs)}</div></div></div>",
            unsafe_allow_html=True,
        )

    # Weak cards = struggled this round (from pool)
    weak_cards = [c for c in pool if c["question"] in struggled_qs]

    st.markdown("---")
    st.markdown(f"**{len(pool)}** cards ready for the next round.")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button(
            f"Continue all ({len(pool)})",
            type="primary",
            use_container_width=True,
        ):
            start_next_round(list(pool))
            st.rerun()
    with col_b:
        if st.button(
            f"Only weak cards ({len(weak_cards)})",
            use_container_width=True,
            disabled=(len(weak_cards) == 0),
        ):
            start_next_round(weak_cards)
            st.rerun()

    if st.button("Back to home", use_container_width=True):
        reset_to_home()
        st.rerun()

elif st.session_state.finished:
    # ---- Completed screen ----
    render_sidebar()
    st.balloons()

    reviews = st.session_state.stats_reviews
    ratings = st.session_state.stats_ratings
    round_history = st.session_state.round_card_history
    seen = len(st.session_state.stats_seen)

    st.markdown(
        '<div class="completion-card">'
        "<h2>Session Complete!</h2>"
        f'<div class="big-number">{seen}</div>'
        "<p>cards studied</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    # Score summary row
    if reviews > 0:
        avg = sum(r * c for r, c in ratings.items()) / reviews
        elapsed = int(st.session_state.paused_elapsed)
        minutes, seconds = divmod(elapsed, 60)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Reviews", reviews)
        col2.metric("Average Score", f"{avg:.1f} / 5")
        col3.metric("Time", f"{minutes}m {seconds:02d}s")

    # History-based breakdown
    if reviews > 0:
        struggled_qs = {q for q, rl in round_history.items() if any(r <= 3 for r in rl)}
        aced_qs = {q for q, rl in round_history.items() if all(r >= 4 for r in rl)}
        multi_attempt = sum(1 for rl in round_history.values() if len(rl) > 1)

        st.markdown("### Session Breakdown")
        col1, col2, col3 = st.columns(3)
        col1.metric("Aced first try", len(aced_qs))
        col2.metric("Struggled", len(struggled_qs))
        col3.metric("Needed retries", multi_attempt)

        aced_pct = len(aced_qs) / seen * 100 if seen > 0 else 0
        struggled_pct = len(struggled_qs) / seen * 100 if seen > 0 else 0
        st.markdown(
            f'<div style="display:flex;align-items:center;margin-bottom:6px;">'
            f'<span style="width:120px;font-size:0.95rem;font-weight:600;">Aced first try</span>'
            f'<div style="flex:1;background:#ecf0f1;border-radius:0.5rem;height:22px;margin:0 8px;">'
            f'<div style="width:{aced_pct}%;background:#27ae60;height:100%;'
            f'border-radius:0.5rem;min-width:{"2rem" if aced_qs else "0"};'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:0.75rem;color:#fff;font-weight:600;">'
            f"{len(aced_qs)}</div></div></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="display:flex;align-items:center;margin-bottom:6px;">'
            f'<span style="width:120px;font-size:0.95rem;font-weight:600;">Struggled</span>'
            f'<div style="flex:1;background:#ecf0f1;border-radius:0.5rem;height:22px;margin:0 8px;">'
            f'<div style="width:{struggled_pct}%;background:#e74c3c;height:100%;'
            f'border-radius:0.5rem;min-width:{"2rem" if struggled_qs else "0"};'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:0.75rem;color:#fff;font-weight:600;">'
            f"{len(struggled_qs)}</div></div></div>",
            unsafe_allow_html=True,
        )

        # Restart with weak cards
        weak_cards = [
            c for c in st.session_state.active_cards
            if c["question"] in struggled_qs
        ]

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(
                f"Restart weak cards ({len(weak_cards)})",
                type="primary",
                use_container_width=True,
                disabled=(len(weak_cards) == 0),
            ):
                build_queue_from_cards(weak_cards)
                st.rerun()
        with col_b:
            if st.button("Back to home", use_container_width=True):
                reset_to_home()
                st.rerun()
    else:
        if st.button("Back to home", use_container_width=True):
            reset_to_home()
            st.rerun()

else:
    # ---- Training mode ----
    render_sidebar()
    card = current_card()
    if card is None:
        st.warning("No cards available.")
    else:
        # Section tag
        st.markdown(
            f'<span class="section-tag">{card["section"]}</span>',
            unsafe_allow_html=True,
        )

        # Question
        st.markdown(
            f'<div class="question-card">{card["question"]}</div>',
            unsafe_allow_html=True,
        )

        # Show answer button / answer display
        if not st.session_state.show_answer:
            if st.button("Show Answer", type="primary", use_container_width=True):
                st.session_state.show_answer = True
                st.rerun()
        else:
            # Render answer (preserve newlines for multi-line answers)
            answer_html = card["answer"].replace("\n", "<br>")
            st.markdown(
                f'<div class="answer-card">{answer_html}</div>',
                unsafe_allow_html=True,
            )

            # Rating
            if not st.session_state.rated:
                st.markdown("**How well did you know this?**")
                st.markdown(
                    '<div class="rating-labels">'
                    "<span>Bad</span><span>Poor</span><span>Okay</span>"
                    "<span>Good</span><span>Perfect</span></div>",
                    unsafe_allow_html=True,
                )
                rating = st.slider(
                    "Rate your answer",
                    min_value=1,
                    max_value=5,
                    value=3,
                    label_visibility="collapsed",
                )

                if st.button(
                    "Submit & Next", type="primary", use_container_width=True
                ):
                    advance(rating)
                    st.rerun()
