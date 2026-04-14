import os
import hashlib
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

        if not username or not password:
            return "All fields required"

        password = hashlib.sha256(password.encode()).hexdigest()

        if users_collection.find_one({"username": username}):
            return "User already exists"

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
            return "All fields required"

        password = hashlib.sha256(password.encode()).hexdigest()

        user = users_collection.find_one({
            "username": username,
            "password": password
        })

        if user:
            session["user"] = username
            return redirect("/dashboard")
        else:
            return "Invalid Login"

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

        # Save user if not exists
        user = users_collection.find_one({"username": email})
        if not user:
            users_collection.insert_one({
                "username": email,
                "password": ""
            })

        session["user"] = email
        return redirect("/dashboard")

    except Exception as e:
        return f"❌ Google OAuth Failed: {str(e)}"

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html")

# ---------------- CALCULATOR ----------------
@app.route("/calculator")
def calculator():
    if "user" not in session:
        return redirect("/login")
    return render_template("calculator.html")

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
    from waitress import serve
    print("🚀 Server running at http://0.0.0.0:5000")
    serve(app, host="0.0.0.0", port=5000)