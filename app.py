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

    conn.commit()
    conn.close()


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return function(*args, **kwargs)

    return wrapper


@app.route("/", methods=["GET", "POST"])
def login():

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
@login_required
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


init_db()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )
