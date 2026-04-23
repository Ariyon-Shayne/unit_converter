import os
import time
import hashlib
from datetime import timedelta
from flask import Flask, render_template, request, redirect, session, url_for
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from pymongo import MongoClient

# ---------------- LOAD ENV ----------------
load_dotenv()
os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)

# IMPORTANT: strong & stable secret key
app.secret_key = "my_super_secret_key_12ṇ3456"

# ---------------- SESSION CONFIGURATION ----------------
# Force users to log in again after 5 minutes of inactivity
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)

@app.before_request
def make_session_permanent():
    session.permanent = True
    
    # Absolute 5-minute timeout enforcement
    if "login_time" in session:
        if time.time() - session["login_time"] > 300:
            session.pop("user", None)
            session.pop("login_time", None)
            return redirect("/login")

# ---------------- MONGODB ----------------
mongo_uri = os.getenv("MONGO_URI")
if not mongo_uri:
    raise ValueError("❌ MONGO_URI missing in .env")

client = MongoClient(mongo_uri)
db = client["mydatabase"]
users_collection = db["users"]

# ---------------- GOOGLE OAUTH ----------------
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# ---------------- HOME ----------------
@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if "user" in session:
        return redirect("/dashboard")
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not username or not password or not confirm_password:
            return render_template("register.html", error="All fields required")

        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match")

        if len(password) < 4:
            return render_template("register.html", error="Password must be at least 4 characters long")

        password = hashlib.sha256(password.encode()).hexdigest()

        if users_collection.find_one({"username": username}):
            return render_template("register.html", error="Username already exists")

        users_collection.insert_one({
            "username": username,
            "password": password
        })

        return redirect("/login")

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect("/dashboard")
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return render_template("login.html", error="All fields required")

        password = hashlib.sha256(password.encode()).hexdigest()

        user = users_collection.find_one({
            "username": username,
            "password": password
        })

        if user:
            session["user"] = username
            session["login_time"] = time.time()
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Invalid Username or Password")

    return render_template("login.html")

# ---------------- GOOGLE LOGIN ----------------
@app.route("/login/google")
def login_google():
    if "user" in session:
        return redirect("/dashboard")
    if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_CLIENT_SECRET"):
        return "❌ Google credentials missing in .env"

    redirect_uri = url_for('authorize', _external=True)
    
    return google.authorize_redirect(redirect_uri, prompt='select_account')

# ---------------- GOOGLE CALLBACK ----------------
@app.route("/authorize")
def authorize():
    try:
        # Get token
        token = google.authorize_access_token()

        # Look for userinfo in token, or fetch explicitly with token
        user_info = token.get('userinfo')
        if not user_info:
            resp = google.get('https://openidconnect.googleapis.com/v1/userinfo', token=token)
            user_info = resp.json()

        email = user_info.get('email')

        if not email:
            return "Google login failed: Email not found", 400

        # Save user if not exists based on email (or old fallback)
        user = users_collection.find_one({"$or": [{"email": email}, {"username": email}]})
        
        if not user:
            # First time logging in with this Google account, ask for a username!
            session["temp_google_email"] = email
            return redirect("/set_username")

        # Automatically log them in with the username found in the DB (or fallback to email)
        session["user"] = user.get("username", email)
        session["login_time"] = time.time()
        return redirect("/dashboard")

    except Exception as e:
        return f"❌ Google OAuth Failed: {str(e)}"

# ---------------- SET USERNAME (GOOGLE AUTH) ----------------
@app.route("/set_username", methods=["GET", "POST"])
def set_username():
    if "temp_google_email" not in session:
        return redirect("/login")

    if request.method == "POST":
        username = request.form.get("username")
        
        if not username:
            return render_template("set_username.html", error="Username is required")
            
        if users_collection.find_one({"username": username}):
            return render_template("set_username.html", error="Username already exists")

        # Save the structured user in MongoDB
        email = session["temp_google_email"]
        users_collection.insert_one({
            "username": username,
            "email": email,
            "password": ""  # Handled by Google Identity
        })

        # Clear the setup session logic and log them strictly in
        session.pop("temp_google_email", None)
        session["user"] = username
        session["login_time"] = time.time()
        return redirect("/dashboard")

    return render_template("set_username.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html", username=session.get("user"))

# ---------------- CALCULATOR ----------------
@app.route("/calculator")
def calculator():
    if "user" not in session:
        return redirect("/login")
    return render_template("calculator.html")

# ---------------- TIC-TAC-TOE (OX GAME) ----------------
@app.route("/oxgame")
def oxgame():
    if "user" not in session:
        return redirect("/login")
    return render_template("oxgame.html")

# ---------------- CONVERTER ----------------
@app.route("/converter", methods=["GET", "POST"])
def converter():
    if "user" not in session:
        return redirect("/login")

    result = None
    input_value = ""
    conversion_type = ""

    if request.method == "POST":
        try:
            input_value = request.form.get("value", "")
            conversion_type = request.form.get("conversion", "")
            
            value = float(input_value)

            if conversion_type == "km_m":
                result = value * 1000
            elif conversion_type == "m_km":
                result = value / 1000
            elif conversion_type == "kg_g":
                result = value * 1000
            elif conversion_type == "g_kg":
                result = value / 1000
            elif conversion_type == "c_f":
                result = (value * 9/5) + 32
            elif conversion_type == "f_c":
                result = (value - 32) * 5/9

        except:
            result = "Invalid input"

    return render_template("converter.html", result=result, value=input_value, conversion=conversion_type)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

# ---------------- RUN ----------------
if __name__ == "__main__":
    import sys
    from waitress import serve

    # default port
    port = 5000

    # if you pass a port in terminal → use it
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    print(f"🚀 Server running at: http://127.0.0.1:{port}")
    serve(app, host="0.0.0.0", port=port)