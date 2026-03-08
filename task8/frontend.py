"""
Spotify Flask Frontend
Serves the UI and proxies API calls to the backend on port 5000
"""
from flask import Flask, render_template, request, jsonify, session, redirect
import requests, os, secrets
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))

BACKEND = os.getenv("BACKEND_URL", "http://localhost:5000")

# ── Pages ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

# ── Auth pass-through ─────────────────────────────────────────────────────────

@app.route("/login")
def login():
    return redirect(f"{BACKEND}/auth/login")

@app.route("/auth/callback")
def callback():
    # Forward callback to backend, grab tokens, store in session
    code  = request.args.get("code")
    state = request.args.get("state")
    resp  = requests.get(f"{BACKEND}/auth/callback",
                         params={"code": code, "state": state},
                         cookies=request.cookies)
    if resp.ok:
        data = resp.json().get("data", {})
        session["access_token"]  = data.get("access_token")
        session["refresh_token"] = data.get("refresh_token")
        return redirect("/")
    return redirect("/?error=auth_failed")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})

# ── API proxy (all /api/* → backend) ─────────────────────────────────────────

@app.route("/api/<path:path>", methods=["GET","POST","PUT","DELETE"])
def proxy(path):
    token = session.get("access_token") or \
            request.headers.get("Authorization","").replace("Bearer ","")

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url    = f"{BACKEND}/{path}"
    kwargs = dict(headers=headers, params=request.args)
    if request.method in ("POST","PUT","DELETE"):
        kwargs["json"] = request.get_json(silent=True) or {}

    resp = requests.request(request.method, url, **kwargs)
    return (resp.content, resp.status_code,
            {"Content-Type": "application/json"})

if __name__ == "__main__":
    app.run(debug=True, port=8080)
