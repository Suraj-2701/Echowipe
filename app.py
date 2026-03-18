from flask import Flask, render_template, request, redirect, url_for, flash, session
import json, os, random, uuid
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_mail import Mail, Message

from reportlab.platypus import SimpleDocTemplate, Table
from reportlab.lib.pagesizes import letter
import io
from flask import send_file

import csv
from flask import Response
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify  # Added jsonify


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

# ---------------History Path------------
HISTORY_DB = os.path.join(BASE_DIR, "history.json")

def load_history():
    if os.path.exists(HISTORY_DB):
        with open(HISTORY_DB,"r") as f:
            return json.load(f)
    return []

def save_history(data):
    with open(HISTORY_DB,"w") as f:
        json.dump(data,f,indent=4)

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
            return redirect(url_for("splash"))
        else:
         flash("Invalid email or password", "danger")
         return redirect(url_for("index"))
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

        
            if not first or not last or not email or not password or not confirm:
                flash("All fields are required", "warning")
                return redirect(url_for("index"))

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

This code is valid for 5 minutes.
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
                return redirect(url_for("splash"))
            else:
                flash("Invalid OTP", "danger")
                otp_sent = True
                email_for_otp = email

    return render_template("index.html", otp_sent=otp_sent, email_for_otp=email_for_otp)
@app.route("/resend-otp", methods=["GET", "POST"])
def resend_otp():
    email = request.args.get("email")
    
    # If the user is submitting the OTP code from this URL
    if request.method == "POST":
        # Redirect the POST request back to the main index logic 
        # so you don't have to duplicate the verification code.
        return index() 

    # Handle the GET request (actually resending the email)
    if email in otp_store:
        token = otp_store[email]["otp"]
        
        msg = Message(
             subject="Echowipe – Email Verification Code",
                    recipients=[email],
                    body=f"""
Hello,

Your Echowipe verification code is: {token}

This code is valid for 5 minutes.
Do not share it with anyone.

Regards,
Echowipe Team
"""
        )
        
        try:
            mail.send(msg)
            flash("A new OTP has been sent!", "success")
        except Exception:
            flash("Failed to resend email.", "danger")
    else:
        flash("Session expired. Please sign up again.", "warning")
        return redirect(url_for("index"))
    
    # Re-render index with flags to keep the OTP form visible
    return render_template("index.html", otp_sent=True, email_for_otp=email)

# --- UNAUTHENTICATED FORGOT PASSWORD (REQUEST OTP) ---
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    # If the user submits their email to get an OTP
    if request.method == "POST":
        email = request.form.get("reset_email")
        users = load_users()

        # Check if email exists in database
        if email not in users:
            flash("Email not found in our system.", "danger")
            return redirect(url_for("forgot_password"))

        # Generate and store OTP
        token = str(random.randint(100000, 999999))
        otp_store[email] = {"otp": token}

        # Send Email
        msg = Message(
            subject="Echowipe – Password Reset Code",
            recipients=[email],
            body=f"Your code to reset your Echowipe password is: {token}\n\nIf you did not request this, please ignore this email."
        )
        
        try:
            mail.send(msg)
            flash("OTP sent to your email!", "success")
            # Store email temporarily in session to use in the next step
            session["reset_email"] = email 
            return redirect(url_for("reset_password"))
        except Exception as e:
            flash("Failed to send email. Check your mail configuration.", "danger")
            return redirect(url_for("forgot_password"))

    # Show the email entry form
    return render_template("forgot_password.html")


# --- UNAUTHENTICATED RESET PASSWORD (VERIFY OTP & NEW PASS) ---
@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    # Get the email from the temporary session
    email = session.get("reset_email")
    if not email:
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        otp_input = request.form.get("otp_code")
        new_pass = request.form.get("new_password")
        confirm_pass = request.form.get("confirm_password")

        # Check if passwords match
        if new_pass != confirm_pass:
            flash("New passwords do not match.", "danger")
            return redirect(url_for("reset_password"))

        # Verify OTP
        if email in otp_store and otp_input == otp_store[email]["otp"]:
            users = load_users()
            # Update password
            users[email]["password"] = generate_password_hash(new_pass)
            save_users(users)
            
            # Clean up
            otp_store.pop(email)
            session.pop("reset_email", None) 
            
            flash("Password reset successfully! You can now log in.", "success")
            return redirect(url_for("index")) # Send back to login page
        else:
            flash("Invalid OTP code.", "danger")
            return redirect(url_for("reset_password"))

    # Show the OTP and New Password form
    return render_template("reset_password.html", email=email)

#---------Terms and Condition-----------
@app.route("/terms")
def terms():
 return render_template("terms.html")

 # ---------------- SPLASH SCREEN ----------------
@app.route("/splash")
def splash():
    if "email" not in session:
        return redirect(url_for("index"))
    return render_template("splash.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "email" not in session:
        return redirect(url_for("index"))
    
    # Load all users and get data for the logged-in session
    users = load_users()
    user_email = session["email"]
    user_data = users.get(user_email)

    # Pass the user data and email to the dashboard template
    return render_template("dashboard.html", user=user_data, email=user_email)

    

# ---------------- DETECT ----------------
@app.route("/detect", methods=["POST"])
def detect():

    if "email" not in session:
        return redirect(url_for("index"))

    users = load_users()
    user_email = session["email"]
    user_data = users.get(user_email)

    if "audio" not in request.files:
        return render_template(
            "dashboard.html",
            error="No file uploaded",
            user=user_data,
            email=user_email
        )

    file = request.files["audio"]

    if file.filename == "":
        return render_template(
            "dashboard.html",
            error="Empty filename",
            user=user_data,
            email=user_email
        )

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
        return render_template(
            "dashboard.html",
            error=str(e),
            user=user_data,
            email=user_email
        )

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    history = load_history()

    history.append({
        "email": user_email,
        "file": file.filename,
        "label": result["label"],
        "fake": result["fake"],
        "real": result["real"],
        "time": datetime.now().strftime("%d-%m-%Y %H:%M")
    })

    save_history(history)

    return render_template(
        "dashboard.html",
        result=result,
        user=user_data,
        email=user_email
    )
#---------------- HISTORY -------------
#---------------- HISTORY -------------
@app.route("/history")
def history():

    if "email" not in session:
        return redirect(url_for("index"))

    user_email = session["email"]
    data = load_history()
    
    # Filter history for only the currently logged-in user
    user_history = [scan for scan in data if scan.get("email") == user_email]
    user_history.reverse()

    users = load_users()
    user_data = users.get(user_email)

    return render_template(
        "history.html",
        scans=user_history,  # Pass the filtered list here
        user=user_data,
        email=user_email
    )
# --- Export csv and pdf-----
@app.route("/export-csv")
def export_csv():
    if "email" not in session:
        return redirect(url_for("index"))

    user_email = session["email"]
    data = load_history()
    
    # Filter for the current user
    user_history = [scan for scan in data if scan.get("email") == user_email]

    def generate():
        yield "File,Result,Fake Score,Real Score,Date\n"
        for row in user_history:
            yield f"{row['file']},{row['label']},{row['fake']},{row['real']},{row['time']}\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition":"attachment;filename=echowipe_history.csv"}
    )


@app.route("/export-pdf")
def export_pdf():
    if "email" not in session:
        return redirect(url_for("index"))

    user_email = session["email"]
    data = load_history()
    
    # Filter for the current user
    user_history = [scan for scan in data if scan.get("email") == user_email]

    buffer = io.BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=letter)

    table_data = [["File","Result","Fake Score","Real Score","Date"]]

    for row in user_history:
        table_data.append([
            row["file"],
            row["label"],
            row["fake"],
            row["real"],
            row["time"]
        ])

    table = Table(table_data)
    pdf.build([table])
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="echowipe_history.pdf",
        mimetype="application/pdf"
    )

@app.context_processor
def inject_user():

    if "email" in session:
        users = load_users()
        email = session["email"]
        user = users.get(email)

        return dict(user=user, email=email)

    return dict(user=None, email=None)
    
# ---------------- HELP & SUPPORT ----------------
@app.route("/help")
def help():
    if "email" not in session:
        return redirect(url_for("index"))
    
    users = load_users()
    user_data = users.get(session["email"])
    
    # We pass 'user' so the HTML can do {{ user.first }}
    return render_template("help.html", user=user_data, email=session["email"])

# --- FORGOT PASSWORD (SEND OTP) ---
@app.route("/forgot-password-otp")
def forgot_password_otp():
    if "email" not in session:
        return redirect(url_for("index"))
    
    users = load_users()
    email = session["email"]
    user_data = users.get(email) # नॅव्हबारसाठी डेटा मिळवा
    
    token = str(random.randint(100000, 999999))
    otp_store[email] = {"otp": token}

    msg = Message(
        subject="Echowipe – Password Reset Code",
        recipients=[email],
        body=f"Your code to reset your Echowipe password is: {token}\n\nIf you did not request this, please secure your account."
    )
    
    try:
        mail.send(msg)
        flash("OTP sent to your email!", "success")
        # बदल: इथे user=user_data आणि email=email पाठवा जेणेकरून नॅव्हबार दिसेल
        return render_template("verify_forgot_otp.html", user=user_data, email=email)
    except Exception as e:
        flash("Failed to send email.", "danger")
        return redirect(url_for("change_password"))

# --- VERIFY FORGOT OTP ---
@app.route("/verify-reset-otp", methods=["POST"])
def verify_reset_otp():
    if "email" not in session:
        return redirect(url_for("index"))
        
    users = load_users()
    email = session.get("email")
    user_data = users.get(email) # नॅव्हबारसाठी डेटा मिळवा
    
    otp_input = request.form.get("otp_code")
    new_pass = request.form.get("new_password")

    if email in otp_store and otp_input == otp_store[email]["otp"]:
        users[email]["password"] = generate_password_hash(new_pass)
        save_users(users)
        otp_store.pop(email)
        flash("Password reset successfully!", "success")
        return redirect(url_for("dashboard"))
    else:
        flash("Invalid OTP code.", "danger")
        # बदल: एरर आल्यावर पुन्हा डेटा पाठवावा लागतो जेणेकरून नॅव्हबार टिकून राहील
        return render_template("verify_forgot_otp.html", user=user_data, email=email)
    
  # ---- change password ------  
@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    if "email" not in session:
        return redirect(url_for("index"))

    users = load_users()
    email = session["email"]
    user_data = users.get(email)

    if request.method == "POST":
        old_pass = request.form.get("old_password")
        new_pass = request.form.get("new_password")
        confirm_pass = request.form.get("confirm_password")

        if not check_password_hash(user_data["password"], old_pass):
            flash("Current password is incorrect", "danger")
        elif new_pass != confirm_pass:
            flash("New passwords do not match", "danger")
        else:
            user_data["password"] = generate_password_hash(new_pass)
            users[email] = user_data
            save_users(users)
            flash("Password updated successfully!", "success")
            return redirect(url_for("dashboard"))

    # IMPORTANT: Ensure this matches your filename: change_password.html
    return render_template("change_password.html", user=user_data, email=email)

# ---- Profile ------
@app.route('/profile')
def profile():
    if "email" not in session:
        return redirect(url_for("index"))
    
    users = load_users()
    user_email = session["email"]
    user_data = users.get(user_email)

    if not user_data:
        return redirect(url_for("index"))

    # Pass the user dictionary to the template
    return render_template("profile.html", user=user_data, email=user_email)

# ---- Edit Profile ------
@app.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    if "email" not in session:
        return redirect(url_for("index"))

    users = load_users()
    email = session["email"]
    user_data = users.get(email)

    if request.method == "POST":
        new_first = request.form.get("first_name")
        new_last = request.form.get("last_name")

        if not new_first or not new_last:
            flash("Names cannot be empty", "danger")
        else:
            # Update the data
            users[email]["first"] = new_first
            users[email]["last"] = new_last
            save_users(users)
            
            flash("Profile updated successfully!", "success")
            return redirect(url_for("dashboard"))

    return render_template("edit_profile.html", user=user_data, email=email)


@app.route('/api')
def api_docs():
    return render_template('api_docs.html') 

@app.route('/how-it-works')
def how_it_works():
    return render_template('how_it_works.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    # If you want to restrict this to logged-in users only:
    if "email" not in session:
        return redirect(url_for("index"))
    
    users = load_users()
    user_data = users.get(session["email"])
    return render_template('contact.html', user=user_data, email=session["email"])

@app.route('/contact-submit', methods=['POST'])
def contact_submit():
    # 1. Collect Data
    new_entry = {
        "name": request.form.get('name'),
        "email": request.form.get('email'),
        "subject": request.form.get('subject'),
        "message": request.form.get('message'),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # 2. Save to JSON
    file_path = 'messages.json'
    data = []
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []

    data.append(new_entry)
    
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

    # 3. Return JSON response (No redirect!)
    return jsonify({"status": "success", "message": "Saved successfully"})

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=20000, debug=True)

