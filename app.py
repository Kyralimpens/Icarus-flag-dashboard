"""Operations Check-in — live dashboard web service (FastAPI).
Per-user login (accounts). Health + churn queried live from the Icarus MariaDB.

Env vars (set in Railway):
  DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE  — read-only DB user recommended
  SESSION_SECRET   — long random string (signs the login cookie)
  USERS            — JSON: {"kyra": "<pbkdf2 hash>", ...}  (make hashes with gen_password.py)
  COOKIE_SECURE    — "true" (default) on Railway/HTTPS; "false" for local http testing
  CACHE_TTL_SECONDS (optional, default 600)
"""
import os, json, hmac, hashlib, base64, time
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse

import data, render

app = FastAPI(title="Operations Check-in")

SECRET = os.environ.get("SESSION_SECRET", "").encode() or os.urandom(32)
USERS = json.loads(os.environ.get("USERS", "{}"))
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() != "false"
COOKIE = "ops_session"
MAX_AGE = 60 * 60 * 12  # 12h


# ---- password hashing (stdlib pbkdf2) ----
def hash_password(pw, iterations=240000):
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def verify_password(pw, stored):
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


# ---- signed session cookie ----
def _sign(value):
    sig = hmac.new(SECRET, value.encode(), hashlib.sha256).hexdigest()
    return f"{value}.{sig}"


def _unsign(token):
    try:
        value, sig = token.rsplit(".", 1)
        expected = hmac.new(SECRET, value.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        user, ts = value.split("|")
        if time.time() - float(ts) > MAX_AGE:
            return None
        return user
    except Exception:
        return None


def current_user(request):
    tok = request.cookies.get(COOKIE)
    return _unsign(tok) if tok else None


LOGIN_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Sign in · Operations Check-in</title>
<style>
:root{{color-scheme:light dark}}
body{{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:#f5f6f9;color:#0a1024;margin:0;display:grid;place-items:center;min-height:100vh}}
@media(prefers-color-scheme:dark){{body{{background:#0a1024;color:#eef1f8}}.card{{background:#121a33!important;border-color:#26304f!important}}input{{background:#0a1024;color:#eef1f8;border-color:#26304f}}}}
.card{{background:#fff;border:1px solid #e2e5ee;border-radius:14px;padding:30px 28px;width:min(360px,90vw);box-shadow:0 8px 30px rgba(10,16,36,.12);border-top:5px solid #FD5E35}}
.b{{font-size:11px;font-weight:800;letter-spacing:.22em;color:#FD5E35}}
h1{{font-size:20px;margin:8px 0 18px}}
label{{font-size:12px;font-weight:600;color:#5a6480;display:block;margin:12px 0 5px}}
input{{width:100%;padding:10px 12px;border:1px solid #e2e5ee;border-radius:8px;font-size:15px}}
button{{margin-top:20px;width:100%;padding:11px;background:#001137;color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:650;cursor:pointer}}
button:hover{{background:#FD5E35}}
.err{{color:#D6432E;font-size:13px;margin-top:14px;{err_display}}}
</style></head><body><form class="card" method="post" action="/login">
<div class="b">ICARUS · OPERATIONS</div><h1>Sign in</h1>
<label>Username</label><input name="username" autofocus autocomplete="username">
<label>Password</label><input name="password" type="password" autocomplete="current-password">
<button type="submit">Sign in</button>
<div class="err">Incorrect username or password.</div>
</form></body></html>"""


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if current_user(request):
        return RedirectResponse("/", status_code=302)
    return LOGIN_HTML.format(err_display="display:none", )


@app.post("/login")
def login_submit(request: Request, username: str = Form(""), password: str = Form("")):
    stored = USERS.get(username.strip())
    if stored and verify_password(password, stored):
        token = _sign(f"{username.strip()}|{time.time():.0f}")
        resp = RedirectResponse("/", status_code=302)
        resp.set_cookie(COOKIE, token, max_age=MAX_AGE, httponly=True,
                        secure=COOKIE_SECURE, samesite="lax")
        return resp
    return HTMLResponse(LOGIN_HTML.format(err_display=""), status_code=401)


@app.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie(COOKIE)
    return resp


@app.get("/healthz", response_class=PlainTextResponse)
def healthz():
    return "ok"


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    try:
        payload = data.get_data()
    except Exception as e:
        return HTMLResponse(f"<pre>Could not load data from the database.\n{type(e).__name__}: {e}</pre>",
                            status_code=503)
    return render.render_page(payload, user=user)
