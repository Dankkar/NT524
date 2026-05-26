import os
from datetime import datetime, timezone

import psycopg
from flask import Flask, redirect, render_template, request, session, url_for


DATABASE_URL = os.environ["DATABASE_URL"]
TRUST_PROXY_HEADERS = os.getenv("APP_TRUST_PROXY_HEADERS", "true").lower() == "true"
DEV_LOGIN_ENABLED = os.getenv("APP_DEV_LOGIN_ENABLED", "false").lower() == "true"

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SESSION_SECRET", "change-me")


def db_connect():
    return psycopg.connect(DATABASE_URL)


def init_db():
    with db_connect() as conn:
        conn.execute(
            """
            create table if not exists app_users (
                id bigserial primary key,
                email text not null unique,
                display_name text not null,
                provider_subject text,
                created_at timestamptz not null default now(),
                last_seen_at timestamptz not null default now()
            )
            """
        )
        conn.execute(
            """
            create table if not exists notes (
                id bigserial primary key,
                user_id bigint not null references app_users(id) on delete cascade,
                body text not null,
                created_at timestamptz not null default now()
            )
            """
        )


def first_header(*names):
    for name in names:
        value = request.headers.get(name)
        if value:
            return value.strip()
    return None


def identity_from_proxy():
    if not TRUST_PROXY_HEADERS:
        return None
    email = first_header("X-Auth-Request-Email", "X-Forwarded-Email", "X-Forwarded-User")
    subject = first_header("X-Auth-Request-User", "X-Forwarded-Preferred-Username")
    name = first_header("X-Auth-Request-Preferred-Username", "X-Forwarded-User")
    if not email:
        return None
    return {"email": email.lower(), "display_name": name or email, "provider_subject": subject}


def identity_from_dev_session():
    email = session.get("dev_email")
    if not email:
        return None
    return {
        "email": email.lower(),
        "display_name": session.get("dev_name") or email,
        "provider_subject": "dev-login",
    }


def current_identity():
    return identity_from_proxy() or identity_from_dev_session()


def upsert_user(identity):
    with db_connect() as conn:
        row = conn.execute(
            """
            insert into app_users (email, display_name, provider_subject, last_seen_at)
            values (%s, %s, %s, %s)
            on conflict (email) do update set
                display_name = excluded.display_name,
                provider_subject = coalesce(excluded.provider_subject, app_users.provider_subject),
                last_seen_at = excluded.last_seen_at
            returning id, email, display_name, provider_subject, created_at, last_seen_at
            """,
            (
                identity["email"],
                identity["display_name"],
                identity.get("provider_subject"),
                datetime.now(timezone.utc),
            ),
        ).fetchone()
    return {
        "id": row[0],
        "email": row[1],
        "display_name": row[2],
        "provider_subject": row[3],
        "created_at": row[4],
        "last_seen_at": row[5],
    }


def require_user():
    identity = current_identity()
    if not identity:
        return None
    return upsert_user(identity)


@app.before_request
def ensure_schema():
    if not getattr(app, "_schema_ready", False):
        init_db()
        app._schema_ready = True


@app.get("/healthz")
def healthz():
    with db_connect() as conn:
        conn.execute("select 1")
    return {"status": "ok"}


@app.get("/")
def index():
    user = require_user()
    if not user:
        return redirect(url_for("login"))
    with db_connect() as conn:
        notes = conn.execute(
            """
            select body, created_at
            from notes
            where user_id = %s
            order by created_at desc
            limit 20
            """,
            (user["id"],),
        ).fetchall()
    return render_template("index.html", user=user, notes=notes)


@app.route("/login", methods=["GET", "POST"])
def login():
    if identity_from_proxy():
        return redirect(url_for("index"))
    if not DEV_LOGIN_ENABLED:
        return render_template("login.html", dev_login_enabled=False)
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        name = request.form.get("name", "").strip()
        if email:
            session["dev_email"] = email
            session["dev_name"] = name or email
            return redirect(url_for("index"))
    return render_template("login.html", dev_login_enabled=True)


@app.post("/notes")
def create_note():
    user = require_user()
    if not user:
        return redirect(url_for("login"))
    body = request.form.get("body", "").strip()
    if body:
        with db_connect() as conn:
            conn.execute("insert into notes (user_id, body) values (%s, %s)", (user["id"], body[:500]))
    return redirect(url_for("index"))


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
