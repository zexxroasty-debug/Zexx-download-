from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from functools import wraps
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "zexx-development-secret-change-this"
)

app.permanent_session_lifetime = timedelta(days=30)

DATABASE = "zexx.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            poster TEXT,
            drive_url TEXT NOT NULL
        )
    """)

    user = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        ("admin",)
    ).fetchone()

    if user is None:
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("admin", generate_password_hash("zexx123"))
        )


    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rating INTEGER NOT NULL,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return function(*args, **kwargs)

    return wrapper


@app.route("/")
def index():
    return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):
            session.permanent = remember
            session["user"] = username

            return redirect(url_for("home"))

        return render_template(
            "login.html",
            error="Incorrect username or password."
        )

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if len(username) < 3:
            return render_template(
                "register.html",
                error="Username must be at least 3 characters."
            )

        if len(password) < 6:
            return render_template(
                "register.html",
                error="Password must be at least 6 characters."
            )

        if password != confirm:
            return render_template(
                "register.html",
                error="Passwords do not match."
            )

        conn = get_db()

        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if existing:
            conn.close()

            return render_template(
                "register.html",
                error="That username already exists."
            )

        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, generate_password_hash(password))
        )

        conn.commit()
        conn.close()

        return redirect(url_for("login", created="1"))

    return render_template("register.html")


@app.route("/home")
def home():

    category = request.args.get("category", "All")

    conn = get_db()

    if category == "All":
        media = conn.execute(
            "SELECT * FROM media ORDER BY id DESC"
        ).fetchall()
    else:
        media = conn.execute(
            """
            SELECT * FROM media
            WHERE category = ?
            ORDER BY id DESC
            """,
            (category,)
        ).fetchall()

    conn.close()

    return render_template(
        "home.html",
        media=media,
        category=category,
        username=session["user"]
    )




@app.route("/details/<int:media_id>")
def details(media_id):

    conn = get_db()

    item = conn.execute(
        "SELECT * FROM media WHERE id = ?",
        (media_id,)
    ).fetchone()

    if item is None:
        conn.close()
        return "Content not found", 404

    related = conn.execute(
        """
        SELECT * FROM media
        WHERE category = ?
        ORDER BY id ASC
        """,
        (item["category"],)
    ).fetchall()

    conn.close()

    current_index = -1

    for index, media in enumerate(related):
        if media["id"] == item["id"]:
            current_index = index
            break

    previous_item = None
    next_item = None

    if current_index > 0:
        previous_item = related[current_index - 1]

    if current_index >= 0 and current_index < len(related) - 1:
        next_item = related[current_index + 1]

    return render_template(
        "details.html",
        item=item,
        previous_item=previous_item,
        next_item=next_item
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/add")
@login_required
def add_demo():

    conn = get_db()

    item = (
        "TOXIC",
        "Movies",
        "TOXIC movie information.",
        "/static/posters/toxic.jpg",
        "https://drive.google.com/uc?export=download&id=14K8t2enUYk9nzspfITJhFfmQ8pOSym0d"
    )

    conn.execute(
        """
        INSERT INTO media
        (title, category, description, poster, drive_url)
        VALUES (?, ?, ?, ?, ?)
        """,
        item
    )

    conn.commit()
    conn.close()

    return redirect(url_for("home"))


@app.route("/add-can-these-love")
@login_required
def add_can_these_love():

    conn = get_db()

    title = "Can These Love Be Threaten - Part 1"

    existing = conn.execute(
        "SELECT id FROM media WHERE title = ?",
        (title,)
    ).fetchone()

    if existing is None:
        item = (
            title,
            "Series",
            "Can These Love Be Threaten - Part 1.",
            "/static/posters/can-these-love-part-1.jpg",
            "https://drive.google.com/uc?export=download&id=1sXVGz3_EpUYWa0ihz7du-atYpG5tl3Rp"
        )

        conn.execute(
            """
            INSERT INTO media
            (title, category, description, poster, drive_url)
            VALUES (?, ?, ?, ?, ?)
            """,
            item
        )

        conn.commit()

    conn.close()

    return redirect(url_for("home"))


@app.route("/feedback", methods=["POST"])
def feedback():

    rating = request.form.get("rating", "0").strip()
    message = request.form.get("message", "").strip()

    try:
        rating = int(rating)
    except ValueError:
        rating = 0

    if rating < 1 or rating > 5:
        return redirect(url_for("home"))

    if len(message) > 1000:
        message = message[:1000]

    conn = get_db()

    conn.execute(
        """
        INSERT INTO feedback (rating, message)
        VALUES (?, ?)
        """,
        (rating, message)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("home", feedback="thanks"))



init_db()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )
