
from flask import Flask, render_template, request, redirect, url_for, flash, session
import json, os, random, uuid
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_mail import Mail, Message

# ---------------- APP SETUP ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# ---------------- MAIL CONFIG ----------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = "echowipe@gmail.com"        # ✅ your gmail
app.config['MAIL_PASSWORD'] = "fcri sitd zmnw rpqn"   # ✅ gmail app password
app.config['MAIL_DEFAULT_SENDER'] = "echowipe@gmail.com"

mail = Mail(app)

# ---------------- PATHS ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from model_service import detect_voice

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DATABASE ----------------
USER_DB = os.path.join(BASE_DIR, "users.json")
otp_store = {}

def load_users():
    if os.path.exists(USER_DB):
        with open(USER_DB, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_DB, "w") as f:
        json.dump(users, f, indent=4)

# ---------------- HOME (LOGIN / SIGNUP) ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    users = load_users()
    otp_sent = False
    email_for_otp = ""

    # ---------- LOGIN ----------
    if request.method == "POST" and request.form.get("action") == "login":
        email = request.form.get("login_email")
        password = request.form.get("login_password")

        if email in users and check_password_hash(users[email]["password"], password):
            session["email"] = email
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password", "danger")

    # ---------- SIGNUP ----------
    if request.method == "POST" and request.form.get("action") == "signup":
        email = request.form.get("signup_email")
        otp_input = request.form.get("otp_code")

        # SEND OTP
        if not otp_input:
            first = request.form.get("first_name")
            last = request.form.get("last_name")
            password = request.form.get("signup_password")
            confirm = request.form.get("confirm_password")
            agree = request.form.get("agree")

            if not all([first, last, email, password, confirm, agree]):
                flash("All fields are required", "warning")

            elif password != confirm:
                flash("Passwords do not match", "danger")

            elif email in users:
                flash("User already exists", "danger")

            else:
                token = str(random.randint(100000, 999999))

                otp_store[email] = {
                    "otp": token,
                    "first": first,
                    "last": last,
                    "password": generate_password_hash(password)
                }

                msg = Message(
                    subject="Echowipe – Email Verification Code",
                    recipients=[email],
                    body=f"""
Hello,

Your Echowipe verification code is: {token}

This code is valid for 10 minutes.
Do not share it with anyone.

Regards,
Echowipe Team
"""
                )

                try:
                    mail.send(msg)
                    flash("Verification email sent!", "success")
                    otp_sent = True
                    email_for_otp = email
                except Exception as e:
                    flash("Email sending failed", "danger")

        # VERIFY OTP
        else:
            if email in otp_store and otp_input == otp_store[email]["otp"]:
                users[email] = {
                    "first": otp_store[email]["first"],
                    "last": otp_store[email]["last"],
                    "password": otp_store[email]["password"],
                    "created": datetime.now().strftime("%d-%m-%Y %H:%M")
                }
                save_users(users)
                otp_store.pop(email)

                session["email"] = email
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid OTP", "danger")
                otp_sent = True
                email_for_otp = email

    return render_template("index.html", otp_sent=otp_sent, email_for_otp=email_for_otp)

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "email" not in session:
        return redirect(url_for("index"))
    return render_template("dashboard.html")

# ---------------- DETECT ----------------
# ---------------- DETECT ----------------
@app.route("/detect", methods=["POST"])
def detect():
    if "audio" not in request.files:
        return render_template("dashboard.html", error="No file uploaded")

    file = request.files["audio"]
    if file.filename == "":
        return render_template("dashboard.html", error="Empty filename")

    filename = f"{uuid.uuid4().hex}.wav"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    try:
        fake, real, raw = detect_voice(file_path)
        result = {
            "fake": round(fake, 6),
            "real": round(real, 6),
            "label": "FAKE (AI GENERATED)" if fake > real else "REAL VOICE"
        }
    except Exception as e:
        return render_template("dashboard.html", error=str(e))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    return render_template("dashboard.html", result=result)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)

