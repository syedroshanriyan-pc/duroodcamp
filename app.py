from flask import Flask, render_template, request, redirect, url_for, session
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=60),
)

bcrypt = Bcrypt(app)


MONGO_URI = os.getenv("MONGO_URI")
app.secret_key = os.getenv("SECRET_KEY")
# Cookie/session lifetime → 30 days
app.permanent_session_lifetime = timedelta(days=60)

client = MongoClient(MONGO_URI)
db = client["darood_2026"]
users = db["users"]
recitations = db["recitations"]

TARGET = 1501000
EVENT_DATE = datetime(2026, 8, 25, 17, 0, 0)


@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))

    total = recitations.aggregate([
        {"$group": {"_id": None, "sum": {"$sum": "$count"}}}
    ])
    total_count = 0
    for t in total:
        total_count = t["sum"]

    remaining = TARGET - total_count
    if remaining < 0:
        remaining = 0

    user_total = recitations.aggregate([
        {"$match": {"user": session["user"]}},
        {"$group": {"_id": None, "sum": {"$sum": "$count"}}}
    ])
    my_total = 0
    for u in user_total:
        my_total = u["sum"]

    progress = 0
    if TARGET > 0:
        progress = round((total_count / TARGET) * 100, 2)

    return render_template("index.html",
                           target=TARGET,
                           total=total_count,
                           remaining=remaining,
                           my_total=my_total,
                           event_date=EVENT_DATE.strftime("%Y-%m-%d %H:%M:%S"),
                           progress=progress)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        fullname = request.form["fullname"]
        mobile = request.form["mobile"]
        password = bcrypt.generate_password_hash(request.form["password"]).decode("utf-8")

        if users.find_one({"mobile": mobile}):
            return "Mobile number already registered!"

        users.insert_one({"fullname": fullname, "mobile": mobile, "password": password})
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        mobile = request.form["mobile"]
        password = request.form["password"]

        user = users.find_one({"mobile": mobile})
        if user and bcrypt.check_password_hash(user["password"], password):
            session.permanent = True  # Keep session active
            session["user"] = user["mobile"]
            session["fullname"] = user["fullname"]
            return redirect(url_for("home"))
        else:
            return "Invalid mobile or password!"

    # Auto-login if already logged in
    if "user" in session:
        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/add", methods=["POST"])
def add_recitation():
    if "user" not in session:
        return redirect(url_for("login"))

    try:
        count = int(request.form["count"])
    except ValueError:
        return "Invalid number entered!"

    recitations.insert_one({"user": session["user"], "count": count})
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
