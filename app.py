from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = "zexx-change-this-secret-key"

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
            ("admin", "zexx123")
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

        conn = get_db()

        user = conn.execute(
            """
            SELECT * FROM users
            WHERE username = ? AND password = ?
            """,
            (username, password)
        ).fetchone()

        conn.close()

        if user:
            session["user"] = username
            return redirect(url_for("home"))

        return render_template(
            "login.html",
            error="Invalid username or password"
        )

    return render_template("login.html")


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


if __name__ == "__main__":

    init_db()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
