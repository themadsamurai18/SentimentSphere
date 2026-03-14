from datetime import date
from functools import wraps
import json
import random
import os
import sqlite3

from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from textblob import TextBlob
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
app.config["DATABASE"] = "database.db"


EMOTION_COLOR_MAP = {
    "happy": {"bg1": "#fbbf24", "bg2": "#fb923c", "accent": "#b45309"},
    "calm": {"bg1": "#34d399", "bg2": "#10b981", "accent": "#047857"},
    "sad": {"bg1": "#1d4ed8", "bg2": "#1e3a8a", "accent": "#93c5fd"},
    "angry": {"bg1": "#ef4444", "bg2": "#7f1d1d", "accent": "#fee2e2"},
    "anxious": {"bg1": "#a855f7", "bg2": "#6b21a8", "accent": "#e9d5ff"},
    "neutral": {"bg1": "#0ea5e9", "bg2": "#0f766e", "accent": "#cffafe"},
    "focused": {"bg1": "#06b6d4", "bg2": "#0e7490", "accent": "#cffafe"},
    "excited": {"bg1": "#ec4899", "bg2": "#be185d", "accent": "#fce7f3"},
    "tired": {"bg1": "#9ca3af", "bg2": "#4b5563", "accent": "#e5e7eb"},
}

MOOD_BANK = {
    "Positive": {
        "emoji": "\U0001F60A",
        "quotes": [
            "Great things are built one good day at a time.",
            "Your energy is your superpower. Use it wisely.",
            "Joy grows when shared. Keep shining.",
        ],
        "activities": [
            "Take a gratitude walk and note five beautiful things.",
            "Call a friend and celebrate one success together.",
            "Start a passion project for 20 focused minutes.",
        ],
        "music": [
            "Happy lo-fi and chill upbeat beats playlist.",
            "Acoustic sunshine playlist with light vocals.",
            "Feel-good indie pop mix for momentum.",
        ],
        "tips": [
            "Do your hardest task first while motivation is high.",
            "Batch similar tasks to keep your flow state.",
            "Turn on a 25-minute timer and sprint.",
        ],
        "merch": [
            "Mindfulness Journal",
            "Mood Tracker Notebook",
            "Productivity Planner",
        ],
        "challenges": [
            "Share one thank-you message with someone.",
            "Spend 15 minutes building your personal project.",
            "Write 5 wins from this week.",
        ],
    },
    "Neutral": {
        "emoji": "\U0001F610",
        "quotes": [
            "Steady is powerful. Keep moving.",
            "Calm minds make strong choices.",
            "Progress is often quiet before it is loud.",
        ],
        "activities": [
            "Try a 5-minute breathing cycle (inhale 4, exhale 6).",
            "Write a short priority list of only three items.",
            "Do light stretching and reset your posture.",
        ],
        "music": [
            "Ambient rain + piano for gentle focus.",
            "Soft instrumental coffeehouse mix.",
            "Minimal chill electronic background flow.",
        ],
        "tips": [
            "Choose one tiny win and complete it now.",
            "Reduce distractions: one tab, one task.",
            "Use a checklist to convert thoughts into action.",
        ],
        "merch": [
            "Calm Breathing Cards",
            "Productivity Planner",
            "Emotional Wellness Stickers",
        ],
        "challenges": [
            "Take a 10-minute mindful walk.",
            "Clear your desk before your next task.",
            "Complete one delayed task today.",
        ],
    },
    "Negative": {
        "emoji": "\U0001F61E",
        "quotes": [
            "This moment is hard, but it is not forever.",
            "You are allowed to pause and breathe.",
            "Healing starts with one gentle step.",
        ],
        "activities": [
            "Write three things you can control today.",
            "Take a short walk without your phone.",
            "Do a body scan and release shoulder tension.",
        ],
        "music": [
            "Soft instrumental healing playlist.",
            "Nature sounds with low-tempo piano.",
            "Guided calm mix for emotional reset.",
        ],
        "tips": [
            "Break work into 10-minute chunks.",
            "Ask for help early, not after burnout.",
            "Do the smallest next step only.",
        ],
        "merch": [
            "Mindfulness Journal",
            "Calm Breathing Cards",
            "Emotional Wellness Stickers",
        ],
        "challenges": [
            "Do 6 deep breaths before opening social media.",
            "Write one compassionate sentence to yourself.",
            "Drink water and sit in sunlight for 5 minutes.",
        ],
    },
}

PRODUCT_CATALOG = [
    {
        "name": "Mindfulness Journal",
        "price": 14,
        "tag": "calm",
        "desc": "Guided pages for emotional reflection and clarity.",
        "image": "mindfulness_journal.svg",
    },
    {
        "name": "Mood Tracker Notebook",
        "price": 16,
        "tag": "focused",
        "desc": "Track emotional patterns and daily growth.",
        "image": "mood_tracker_notebook.svg",
    },
    {
        "name": "Calm Breathing Cards",
        "price": 10,
        "tag": "anxious",
        "desc": "Pocket cards with quick breathing routines.",
        "image": "calm_breathing_cards.svg",
    },
    {
        "name": "Productivity Planner",
        "price": 18,
        "tag": "happy",
        "desc": "Weekly planning pages to convert energy into results.",
        "image": "productivity_planner.svg",
    },
    {
        "name": "Emotional Wellness Stickers",
        "price": 8,
        "tag": "excited",
        "desc": "Visual stickers to track your feelings and wins.",
        "image": "wellness_stickers.svg",
    },
]

PERSONALITY_PROFILES = [
    "Vision Builder",
    "Strategic Thinker",
    "Creative Explorer",
    "Analytical Architect",
    "Calm Optimizer",
    "Emotional Connector",
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _has_column(db, table_name, column_name):
    rows = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row["name"] == column_name for row in rows)


def init_db():
    db = get_db()

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS mood_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            entry_text TEXT NOT NULL,
            primary_mood TEXT NOT NULL,
            emotion TEXT NOT NULL,
            polarity REAL NOT NULL,
            mood_score INTEGER NOT NULL,
            stress INTEGER NOT NULL,
            happiness INTEGER NOT NULL,
            energy INTEGER NOT NULL,
            focus INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS game_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER DEFAULT 10,
            accuracy REAL DEFAULT 0,
            reaction_ms REAL DEFAULT 0,
            tendency TEXT DEFAULT 'balanced',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )

    for column, sql in [
        ("total_questions", "ALTER TABLE game_results ADD COLUMN total_questions INTEGER DEFAULT 10"),
        ("accuracy", "ALTER TABLE game_results ADD COLUMN accuracy REAL DEFAULT 0"),
        ("reaction_ms", "ALTER TABLE game_results ADD COLUMN reaction_ms REAL DEFAULT 0"),
        ("tendency", "ALTER TABLE game_results ADD COLUMN tendency TEXT DEFAULT 'balanced'"),
    ]:
        if not _has_column(db, "game_results", column):
            db.execute(sql)

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS personality_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            profile TEXT NOT NULL,
            trait_summary TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )

    for column, sql in [
        ("profile", "ALTER TABLE personality_results ADD COLUMN profile TEXT DEFAULT 'Creative Explorer'"),
        ("trait_summary", "ALTER TABLE personality_results ADD COLUMN trait_summary TEXT DEFAULT '{}'"),
    ]:
        if not _has_column(db, "personality_results", column):
            db.execute(sql)

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS shop_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            status TEXT DEFAULT 'In Cart',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'Open',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS presence (
            user_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            challenge_date TEXT NOT NULL,
            challenge_text TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, challenge_date)
        )
        """
    )

    db.commit()


def login_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return route_function(*args, **kwargs)

    return wrapper


def clamp(n, lo=0, hi=100):
    return max(lo, min(hi, int(round(n))))


def detect_primary_mood(polarity):
    if polarity > 0.1:
        return "Positive"
    if polarity < -0.1:
        return "Negative"
    return "Neutral"


def detect_emotion(text, polarity):
    t = text.lower()

    keyword_map = {
        "angry": ["angry", "furious", "rage", "mad"],
        "anxious": ["anxious", "worried", "panic", "nervous", "overthinking"],
        "sad": ["sad", "down", "depressed", "lonely", "hurt"],
        "calm": ["calm", "peaceful", "relaxed", "steady"],
        "focused": ["focus", "productive", "disciplined", "clarity"],
        "excited": ["excited", "thrilled", "pumped", "energetic"],
        "tired": ["tired", "exhausted", "sleepy", "fatigue", "drained"],
        "happy": ["happy", "grateful", "joy", "great", "good"],
    }

    for emotion, keys in keyword_map.items():
        if any(k in t for k in keys):
            return emotion

    if polarity >= 0.45:
        return "happy"
    if polarity <= -0.45:
        return "sad"
    return "neutral"


def build_random_guidance(primary_mood):
    bank = MOOD_BANK[primary_mood]
    return {
        "emoji": bank["emoji"],
        "quote": random.choice(bank["quotes"]),
        "activity": random.choice(bank["activities"]),
        "music": random.choice(bank["music"]),
        "tip": random.choice(bank["tips"]),
        "merchandise": random.sample(bank["merch"], k=2),
    }


def compute_visual_metrics(polarity, emotion):
    mood_score = clamp(((polarity + 1) / 2) * 100)
    stress = clamp(100 - mood_score)
    happiness = clamp(mood_score)
    energy = clamp(50 + polarity * 35)
    focus = clamp(52 + polarity * 28)

    if emotion in ("anxious", "angry"):
        stress = clamp(stress + 22)
        focus = clamp(focus - 14)
    if emotion == "tired":
        energy = clamp(energy - 25)
    if emotion in ("focused", "calm"):
        focus = clamp(focus + 18)
        stress = clamp(stress - 14)

    return {
        "mood_score": mood_score,
        "stress": stress,
        "happiness": happiness,
        "energy": energy,
        "focus": focus,
    }


def analyze_mood(text):
    polarity = TextBlob(text).sentiment.polarity
    primary_mood = detect_primary_mood(polarity)
    emotion = detect_emotion(text, polarity)
    guidance = build_random_guidance(primary_mood)
    metrics = compute_visual_metrics(polarity, emotion)
    serious = primary_mood == "Negative" and metrics["stress"] >= 75
    return primary_mood, emotion, polarity, guidance, metrics, serious


def update_presence():
    if "user_id" not in session:
        return
    db = get_db()
    db.execute(
        """
        INSERT INTO presence (user_id, username, last_seen)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            last_seen = CURRENT_TIMESTAMP
        """,
        (session["user_id"], session["username"]),
    )
    db.commit()


def get_last_user_emotion(user_id):
    db = get_db()
    row = db.execute(
        "SELECT emotion FROM mood_logs WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    return row["emotion"] if row else "neutral"


def get_or_create_daily_challenge(user_id):
    db = get_db()
    today = date.today().isoformat()
    row = db.execute(
        """
        SELECT id, challenge_text, completed
        FROM daily_challenges
        WHERE user_id = ? AND challenge_date = ?
        """,
        (user_id, today),
    ).fetchone()

    if row:
        return {"id": row["id"], "text": row["challenge_text"], "completed": bool(row["completed"])}

    emotion = get_last_user_emotion(user_id)
    mood = "Neutral"
    if emotion in ("happy", "excited", "focused"):
        mood = "Positive"
    if emotion in ("sad", "angry", "anxious", "tired"):
        mood = "Negative"

    challenge = random.choice(MOOD_BANK[mood]["challenges"])
    db.execute(
        "INSERT INTO daily_challenges (user_id, challenge_date, challenge_text, completed) VALUES (?, ?, ?, 0)",
        (user_id, today, challenge),
    )
    db.commit()

    return {"id": None, "text": challenge, "completed": False}


def get_today_community_stats():
    db = get_db()
    row = db.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN primary_mood = 'Positive' THEN 1 ELSE 0 END) AS positive_count,
            SUM(CASE WHEN primary_mood = 'Neutral' THEN 1 ELSE 0 END) AS neutral_count,
            SUM(CASE WHEN primary_mood = 'Negative' THEN 1 ELSE 0 END) AS negative_count
        FROM mood_logs
        WHERE date(created_at) = date('now', 'localtime')
        """
    ).fetchone()

    total = row["total"] or 0
    positive = row["positive_count"] or 0
    neutral = row["neutral_count"] or 0
    negative = row["negative_count"] or 0

    most_row = db.execute(
        """
        SELECT emotion, COUNT(*) AS c
        FROM mood_logs
        WHERE date(created_at) = date('now', 'localtime')
        GROUP BY emotion
        ORDER BY c DESC
        LIMIT 1
        """
    ).fetchone()

    if total == 0:
        return {
            "total": 0,
            "positive_pct": 0,
            "neutral_pct": 0,
            "negative_pct": 0,
            "most_common_emotion": "No data yet",
        }

    return {
        "total": total,
        "positive_pct": round((positive / total) * 100, 1),
        "neutral_pct": round((neutral / total) * 100, 1),
        "negative_pct": round((negative / total) * 100, 1),
        "most_common_emotion": most_row["emotion"].title() if most_row else "Neutral",
    }


def build_game_question_bank(size=240):
    base = [
        ("calm", "blue"),
        ("happy", "yellow"),
        ("sad", "deep blue"),
        ("angry", "red"),
        ("anxious", "purple"),
        ("focused", "cyan"),
        ("excited", "pink"),
        ("tired", "gray"),
        ("hopeful", "green"),
        ("confident", "orange"),
        ("stressed", "maroon"),
        ("relaxed", "teal"),
    ]
    all_colors = ["blue", "yellow", "gray", "green", "purple", "red", "cyan", "pink", "orange", "deep blue", "teal", "maroon"]

    bank = []
    prompts = [
        "Which color best matches this feeling",
        "Choose the strongest color association for",
        "What color do most people associate with",
        "Pick the best emotional color for",
    ]

    for i in range(size):
        emotion, correct = base[i % len(base)]
        prompt = prompts[i % len(prompts)]
        options = [correct]
        distractors = [c for c in all_colors if c != correct]
        random.shuffle(distractors)
        options.extend(distractors[:5])
        random.shuffle(options)

        bank.append(
            {
                "id": i + 1,
                "emotion": emotion,
                "question": f"{prompt}: {emotion}?",
                "correct_color": correct,
                "options": options,
            }
        )

    return bank


def build_personality_question_bank(size=1000):
    traits = [
        "creativity",
        "empathy",
        "logic",
        "ambition",
        "leadership",
        "discipline",
        "emotional_stability",
    ]

    stems = [
        "I enjoy solving uncertain problems",
        "I naturally understand how people feel",
        "I prefer making decisions from evidence",
        "I set difficult goals and pursue them",
        "I take initiative in team settings",
        "I follow routines even when unmotivated",
        "I stay calm under pressure",
        "I adapt quickly when plans change",
        "I can explain complex ideas clearly",
        "I balance speed with quality",
        "I seek feedback to improve",
        "I handle setbacks constructively",
        "I create new ideas often",
        "I prioritize fairness in decisions",
        "I break big tasks into steps",
        "I keep focus for long periods",
    ]

    contexts = [
        "during work",
        "in personal projects",
        "when collaborating",
        "in stressful situations",
        "when learning something new",
        "during deadlines",
        "in unfamiliar environments",
        "while planning for the future",
    ]

    bank = []
    idx = 1
    while len(bank) < size:
        for stem in stems:
            for context in contexts:
                trait = traits[(idx - 1) % len(traits)]
                bank.append(
                    {
                        "id": idx,
                        "trait": trait,
                        "text": f"{stem} {context}.",
                        "reverse": (idx % 4 == 0),
                    }
                )
                idx += 1
                if len(bank) >= size:
                    break
            if len(bank) >= size:
                break
    return bank


def choose_profile(traits):
    c = traits["creativity"]
    e = traits["empathy"]
    l = traits["logic"]
    a = traits["ambition"]
    lead = traits["leadership"]
    d = traits["discipline"]
    s = traits["emotional_stability"]

    if c >= 3.8 and a >= 3.6:
        return "Vision Builder"
    if l >= 3.8 and lead >= 3.4:
        return "Strategic Thinker"
    if c >= 3.9 and e >= 3.2:
        return "Creative Explorer"
    if l >= 4.0 and d >= 3.8:
        return "Analytical Architect"
    if s >= 3.8 and d >= 3.5:
        return "Calm Optimizer"
    if e >= 3.8:
        return "Emotional Connector"
    return random.choice(PERSONALITY_PROFILES)


def get_insights_payload(user_id):
    db = get_db()

    distribution = {"Positive": 0, "Neutral": 0, "Negative": 0}
    for row in db.execute(
        "SELECT primary_mood, COUNT(*) AS c FROM mood_logs WHERE user_id = ? GROUP BY primary_mood",
        (user_id,),
    ).fetchall():
        distribution[row["primary_mood"]] = row["c"]

    trend_rows = db.execute(
        """
        SELECT date(created_at) AS day, ROUND(AVG(polarity), 3) AS avg_polarity
        FROM mood_logs
        WHERE user_id = ?
        GROUP BY date(created_at)
        ORDER BY day ASC
        LIMIT 30
        """,
        (user_id,),
    ).fetchall()

    game_row = db.execute(
        """
        SELECT
            ROUND(AVG(score), 2) AS avg_score,
            COALESCE(MAX(score), 0) AS max_score,
            COUNT(*) AS games_played
        FROM game_results
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    radar_rows = db.execute(
        """
        SELECT
            ROUND(AVG(stress), 2) AS stress,
            ROUND(AVG(happiness), 2) AS happiness,
            ROUND(AVG(focus), 2) AS focus,
            ROUND(AVG(energy), 2) AS energy
        FROM mood_logs
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    calm_count = db.execute(
        "SELECT COUNT(*) AS c FROM mood_logs WHERE user_id = ? AND emotion = 'calm'",
        (user_id,),
    ).fetchone()["c"]
    anxious_count = db.execute(
        "SELECT COUNT(*) AS c FROM mood_logs WHERE user_id = ? AND emotion = 'anxious'",
        (user_id,),
    ).fetchone()["c"]

    total_logs = sum(distribution.values()) or 1

    calm_score = clamp((calm_count / total_logs) * 100 if total_logs else 0)
    anxiety_score = clamp((anxious_count / total_logs) * 100 + (radar_rows["stress"] or 0) * 0.4)
    motivation = clamp(((radar_rows["energy"] or 0) + (radar_rows["focus"] or 0)) / 2)

    latest_profile_row = db.execute(
        "SELECT profile FROM personality_results WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()

    completed_challenges = db.execute(
        "SELECT COUNT(*) AS c FROM daily_challenges WHERE user_id = ? AND completed = 1",
        (user_id,),
    ).fetchone()["c"]

    return {
        "distribution": distribution,
        "trend": {
            "labels": [r["day"] for r in trend_rows],
            "values": [r["avg_polarity"] for r in trend_rows],
        },
        "game": {
            "average": game_row["avg_score"] or 0,
            "highest": game_row["max_score"] or 0,
            "played": game_row["games_played"] or 0,
        },
        "radar": {
            "calm": calm_score,
            "stress": int(radar_rows["stress"] or 0),
            "focus": int(radar_rows["focus"] or 0),
            "happiness": int(radar_rows["happiness"] or 0),
            "motivation": motivation,
            "anxiety": anxiety_score,
        },
        "latest_profile": latest_profile_row["profile"] if latest_profile_row else "Not tested yet",
        "completed_challenges": completed_challenges,
    }


@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect(url_for("signup"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return redirect(url_for("signup"))

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            db.commit()
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "error")
            return redirect(url_for("signup"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        db = get_db()
        user = db.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["game_done"] = False
            update_presence()
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    update_presence()
    result = None

    if request.method == "POST":
        entry_text = request.form.get("entry_text", "").strip()

        if not entry_text:
            flash("Please write something first.", "error")
            return redirect(url_for("dashboard"))

        primary_mood, emotion, polarity, guidance, metrics, serious = analyze_mood(entry_text)

        db = get_db()
        db.execute(
            """
            INSERT INTO mood_logs (user_id, entry_text, primary_mood, emotion, polarity, mood_score, stress, happiness, energy, focus)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                entry_text,
                primary_mood,
                emotion,
                polarity,
                metrics["mood_score"],
                metrics["stress"],
                metrics["happiness"],
                metrics["energy"],
                metrics["focus"],
            ),
        )
        db.commit()

        result = {
            "mood": primary_mood,
            "emotion": emotion,
            "polarity": round(polarity, 2),
            "serious": serious,
            "theme": emotion if emotion in EMOTION_COLOR_MAP else "neutral",
            **guidance,
            **metrics,
        }
        flash("Mood analyzed with visual dashboard insights.", "success")

    return render_template(
        "dashboard.html",
        username=session["username"],
        result=result,
        community_stats=get_today_community_stats(),
        challenge=get_or_create_daily_challenge(session["user_id"]),
        current_theme=(result["theme"] if result else "neutral"),
    )


@app.route("/challenge/complete", methods=["POST"])
@login_required
def challenge_complete():
    db = get_db()
    db.execute(
        """
        UPDATE daily_challenges
        SET completed = 1
        WHERE user_id = ? AND challenge_date = ?
        """,
        (session["user_id"], date.today().isoformat()),
    )
    db.commit()
    flash("Daily challenge marked complete. Great work!", "success")
    return redirect(url_for("dashboard"))


@app.route("/history")
@login_required
def history():
    update_presence()
    db = get_db()
    entries = db.execute(
        """
        SELECT entry_text, primary_mood, emotion, polarity, created_at
        FROM mood_logs
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (session["user_id"],),
    ).fetchall()

    counts = {"Positive": 0, "Neutral": 0, "Negative": 0}
    for entry in entries:
        if entry["primary_mood"] in counts:
            counts[entry["primary_mood"]] += 1

    return render_template("history.html", entries=entries, mood_counts=counts)


@app.route("/game")
@login_required
def game():
    update_presence()
    return render_template("game.html")


@app.route("/game/questions")
@login_required
def game_questions():
    bank = build_game_question_bank(240)
    random.shuffle(bank)
    selected = bank[:10]

    for q in selected:
        random.shuffle(q["options"])

    session["game_answer_key"] = {str(q["id"]): q["correct_color"] for q in selected}
    return jsonify({"questions": selected})


@app.route("/game/submit", methods=["POST"])
@login_required
def game_submit():
    payload = request.json or {}
    score = int(payload.get("score", 0))
    total_questions = int(payload.get("total_questions", 10))
    accuracy = float(payload.get("accuracy", 0))
    reaction_ms = float(payload.get("reaction_ms", 0))
    tendency = str(payload.get("tendency", "balanced"))

    db = get_db()
    db.execute(
        """
        INSERT INTO game_results (user_id, score, total_questions, accuracy, reaction_ms, tendency)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (session["user_id"], score, total_questions, accuracy, reaction_ms, tendency),
    )
    db.commit()

    session["game_done"] = True
    return jsonify({"ok": True})


@app.route("/personality", methods=["GET", "POST"])
@login_required
def personality():
    update_presence()

    if not session.get("game_done"):
        flash("Play the mood game first to unlock personality test.", "error")
        return redirect(url_for("game"))

    bank = build_personality_question_bank(1000)

    if request.method == "GET":
        selected = random.sample(bank, 10)
        session["personality_questions"] = selected
        return render_template("personality.html", result=None, questions=selected)

    selected = session.get("personality_questions")
    if not selected:
        selected = random.sample(bank, 10)

    traits = {
        "creativity": [],
        "empathy": [],
        "logic": [],
        "ambition": [],
        "leadership": [],
        "discipline": [],
        "emotional_stability": [],
    }

    for q in selected:
        raw = request.form.get(f"q_{q['id']}", "3")
        value = int(raw) if raw.isdigit() else 3
        if q.get("reverse"):
            value = 6 - value
        traits[q["trait"]].append(value)

    trait_scores = {
        trait: round(sum(vals) / len(vals), 2) if vals else 3.0
        for trait, vals in traits.items()
    }

    profile = choose_profile(trait_scores)

    db = get_db()
    db.execute(
        "INSERT INTO personality_results (user_id, profile, trait_summary) VALUES (?, ?, ?)",
        (session["user_id"], profile, json.dumps(trait_scores)),
    )
    db.commit()

    result = {
        "name": profile,
        "description": "Prediction generated from creativity, empathy, logic, ambition, leadership, discipline, and emotional stability.",
        "advice": "Use this profile as a direction guide, then refine it through daily habits.",
    }

    return render_template(
        "personality.html",
        result=result,
        personality_code=profile,
        trait_scores=trait_scores,
        questions=[],
    )


@app.route("/shop")
@login_required
def shop():
    update_presence()
    emotion = get_last_user_emotion(session["user_id"])
    recommended = [p for p in PRODUCT_CATALOG if p["tag"] == emotion]
    if not recommended:
        recommended = PRODUCT_CATALOG[:2]

    db = get_db()
    cart = db.execute(
        "SELECT product_name, price, status, created_at FROM shop_orders WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],),
    ).fetchall()

    return render_template(
        "shop.html",
        user_mood=emotion,
        recommended=recommended,
        others=PRODUCT_CATALOG,
        cart=cart,
    )


@app.route("/shop/order", methods=["POST"])
@login_required
def shop_order():
    product_name = request.form.get("product_name", "").strip()
    price = float(request.form.get("price", 0))
    if not product_name:
        flash("Product could not be added.", "error")
        return redirect(url_for("shop"))

    db = get_db()
    db.execute(
        "INSERT INTO shop_orders (user_id, product_name, price, status) VALUES (?, ?, ?, 'In Cart')",
        (session["user_id"], product_name, price),
    )
    db.commit()

    flash(f"Added '{product_name}' to cart.", "success")
    return redirect(url_for("shop"))


@app.route("/support", methods=["POST"])
@login_required
def support():
    reason = request.form.get("reason", "Need support").strip() or "Need support"
    db = get_db()
    db.execute(
        "INSERT INTO support_tickets (user_id, reason) VALUES (?, ?)",
        (session["user_id"], reason),
    )
    db.commit()

    flash("Support team request submitted. You are not alone.", "success")
    return redirect(url_for("dashboard"))


@app.route("/support-center")
@login_required
def support_center():
    update_presence()
    db = get_db()
    my_tickets = db.execute(
        "SELECT reason, status, created_at FROM support_tickets WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],),
    ).fetchall()

    return render_template("support_center.html", tickets=my_tickets)


@app.route("/insights")
@login_required
def insights():
    update_presence()
    payload = get_insights_payload(session["user_id"])
    return render_template("insights.html", insights=payload, insights_json=json.dumps(payload))


@app.route("/api/community")
@login_required
def api_community():
    update_presence()
    return jsonify(get_today_community_stats())


@app.route("/heartbeat", methods=["POST"])
@login_required
def heartbeat():
    update_presence()
    return jsonify({"ok": True})


if __name__ == "__main__":
    with app.app_context():
        init_db()
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
