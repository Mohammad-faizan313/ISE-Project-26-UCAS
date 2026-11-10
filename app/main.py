"""A4 coursework prototype: booking, check-in, queue ticket and staff call.

This application uses synthetic demo identities and SQLite. It is not suitable
for production or clinical use. See README.md and docs/a4/ for limitations.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterator

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"
DEMO_PATIENT_PASSWORD = "PatientDemo!2026"
DEMO_RECEPTION_PASSWORD = "ReceptionDemo!2026"
SESSION_HOURS = 8
PBKDF2_ITERATIONS = 260_000
# Queue sessions are grouped by the clinic's local calendar day in China.
CLINIC_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Shanghai")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc_iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_aware(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def password_record(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, expected_hex: str) -> bool:
    _, actual = password_record(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(actual, expected_hex)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class AppointmentInput(BaseModel):
    clinic_code: str = Field(min_length=2, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")
    window_start: str
    window_end: str

    @field_validator("window_start", "window_end")
    @classmethod
    def valid_time(cls, value: str) -> str:
        parse_aware(value)
        return value

    @field_validator("window_end")
    @classmethod
    def positive_window(cls, value: str, info):
        start = info.data.get("window_start")
        if start and parse_aware(start) >= parse_aware(value):
            raise ValueError("window_end must be later than window_start")
        return value


class UserContext(dict):
    """Typed-by-convention user context returned by the auth dependency."""


@contextmanager
def connect(db_path: str) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
    finally:
        conn.close()


def initialise_database(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('patient','receptionist'))
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL REFERENCES users(id),
                clinic_code TEXT NOT NULL,
                window_start TEXT NOT NULL,
                window_end TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('CONFIRMED','CHECKED_IN','CANCELLED','NO_SHOW','COMPLETED')),
                created_at TEXT NOT NULL,
                checked_in_at TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                CHECK(window_start < window_end)
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                appointment_id INTEGER NOT NULL UNIQUE REFERENCES appointments(id),
                clinic_code TEXT NOT NULL,
                service_date TEXT NOT NULL,
                queue_number TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('WAITING','CALLED')),
                issued_at TEXT NOT NULL,
                called_at TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                UNIQUE(clinic_code, service_date, queue_number)
            );
            CREATE TABLE IF NOT EXISTS idempotency (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                idem_key TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, idem_key)
            );
            CREATE INDEX IF NOT EXISTS idx_tickets_queue
              ON tickets(clinic_code, service_date, state, issued_at);
            """
        )
        for username, password, role in (
            ("patient", DEMO_PATIENT_PASSWORD, "patient"),
            ("reception", DEMO_RECEPTION_PASSWORD, "receptionist"),
        ):
            existing = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
            if existing is None:
                salt, digest = password_record(password)
                conn.execute(
                    "INSERT INTO users(username,password_salt,password_hash,role) VALUES(?,?,?,?)",
                    (username, salt, digest, role),
                )


def create_app(db_path: str | None = None, clock: Callable[[], datetime] = utc_now) -> FastAPI:
    resolved_db = db_path or os.environ.get("ISE_A4_DB", str(ROOT / "clinic_demo.sqlite3"))
    initialise_database(resolved_db)
    app = FastAPI(title="Clinic Appointment A4 Prototype", version="1.0.0")
    app.state.db_path = resolved_db
    app.state.clock = clock

    def current_user(authorization: str | None = Header(default=None)) -> UserContext:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Authentication required")
        raw_token = authorization.removeprefix("Bearer ").strip()
        if not raw_token:
            raise HTTPException(status_code=401, detail="Authentication required")
        with connect(app.state.db_path) as conn:
            row = conn.execute(
                """SELECT u.id,u.username,u.role,s.expires_at
                   FROM sessions s JOIN users u ON u.id=s.user_id
                   WHERE s.token_hash=?""",
                (token_digest(raw_token),),
            ).fetchone()
        if row is None or parse_aware(row["expires_at"]) <= app.state.clock():
            raise HTTPException(status_code=401, detail="Session is invalid or expired")
        return UserContext(id=row["id"], username=row["username"], role=row["role"])

    def require_role(user: UserContext, role: str) -> None:
        if user["role"] != role:
            raise HTTPException(status_code=403, detail="This action is not permitted for this role")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "clinic-appointment-a4"}

    @app.post("/api/login")
    def login(payload: LoginInput):
        with connect(app.state.db_path) as conn:
            row = conn.execute("SELECT * FROM users WHERE username=?", (payload.username,)).fetchone()
            if row is None or not verify_password(payload.password, row["password_salt"], row["password_hash"]):
                raise HTTPException(status_code=401, detail="Invalid username or password")
            token = secrets.token_urlsafe(32)
            expires = app.state.clock() + timedelta(hours=SESSION_HOURS)
            conn.execute(
                "INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)",
                (token_digest(token), row["id"], as_utc_iso(expires)),
            )
        return {"access_token": token, "token_type": "bearer", "expires_at": as_utc_iso(expires),
                "user": {"id": row["id"], "username": row["username"], "role": row["role"]}}

    @app.post("/api/appointments", status_code=201)
    def create_appointment(payload: AppointmentInput, user: UserContext = Depends(current_user)):
        require_role(user, "patient")
        start = parse_aware(payload.window_start)
        end = parse_aware(payload.window_end)
        now = app.state.clock().astimezone(timezone.utc)
        if start <= now:
            raise HTTPException(status_code=422, detail="Appointment window must start in the future")
        with connect(app.state.db_path) as conn:
            cur = conn.execute(
                """INSERT INTO appointments(patient_id,clinic_code,window_start,window_end,state,created_at)
                   VALUES(?,?,?,?,?,?)""",
                (user["id"], payload.clinic_code.upper(), as_utc_iso(start), as_utc_iso(end), "CONFIRMED", as_utc_iso(now)),
            )
            appointment_id = cur.lastrowid
            row = conn.execute("SELECT * FROM appointments WHERE id=?", (appointment_id,)).fetchone()
        return appointment_json(row)

    def appointment_json(row: sqlite3.Row) -> dict:
        return {"id": row["id"], "patient_id": row["patient_id"], "clinic_code": row["clinic_code"],
                "window_start": row["window_start"], "window_end": row["window_end"], "state": row["state"],
                "created_at": row["created_at"], "checked_in_at": row["checked_in_at"], "version": row["version"]}

    def ticket_json(row: sqlite3.Row) -> dict:
        return {"id": row["id"], "appointment_id": row["appointment_id"], "clinic_code": row["clinic_code"],
                "service_date": row["service_date"], "queue_number": row["queue_number"], "state": row["state"],
                "issued_at": row["issued_at"], "called_at": row["called_at"], "version": row["version"]}

    @app.get("/api/appointments/{appointment_id}")
    def get_appointment(appointment_id: int, user: UserContext = Depends(current_user)):
        with connect(app.state.db_path) as conn:
            row = conn.execute("SELECT * FROM appointments WHERE id=?", (appointment_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Appointment not found")
        if user["role"] != "receptionist" and row["patient_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Appointment belongs to another patient")
        return appointment_json(row)

    @app.post("/api/appointments/{appointment_id}/check-in")
    def check_in(
        appointment_id: int,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        user: UserContext = Depends(current_user),
    ):
        require_role(user, "patient")
        if not idempotency_key or len(idempotency_key) > 100:
            raise HTTPException(status_code=422, detail="A valid Idempotency-Key header is required")
        now = app.state.clock().astimezone(timezone.utc)
        with connect(app.state.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            replay = conn.execute(
                "SELECT response_json FROM idempotency WHERE user_id=? AND idem_key=?",
                (user["id"], idempotency_key),
            ).fetchone()
            if replay is not None:
                replayed_response = json.loads(replay["response_json"])
                if replayed_response.get("appointment", {}).get("id") != appointment_id:
                    conn.rollback()
                    raise HTTPException(status_code=409, detail="Idempotency-Key was already used for another appointment")
                conn.commit()
                return replayed_response
            appointment = conn.execute("SELECT * FROM appointments WHERE id=?", (appointment_id,)).fetchone()
            if appointment is None:
                conn.rollback()
                raise HTTPException(status_code=404, detail="Appointment not found")
            if appointment["patient_id"] != user["id"]:
                conn.rollback()
                raise HTTPException(status_code=403, detail="Appointment belongs to another patient")
            if appointment["state"] != "CONFIRMED":
                conn.rollback()
                raise HTTPException(status_code=409, detail="Appointment is not in CONFIRMED state")
            start, end = parse_aware(appointment["window_start"]), parse_aware(appointment["window_end"])
            if not (start <= now < end):
                conn.rollback()
                raise HTTPException(status_code=409, detail="Check-in is available only inside the arrival window")
            changed = conn.execute(
                "UPDATE appointments SET state='CHECKED_IN',checked_in_at=?,version=version+1 WHERE id=? AND state='CONFIRMED'",
                (as_utc_iso(now), appointment_id),
            ).rowcount
            if changed != 1:
                conn.rollback()
                raise HTTPException(status_code=409, detail="Appointment changed; refresh and retry")
            service_date = now.astimezone(CLINIC_TIMEZONE).date().isoformat()
            count = conn.execute(
                "SELECT COUNT(*) AS n FROM tickets WHERE clinic_code=? AND service_date=?",
                (appointment["clinic_code"], service_date),
            ).fetchone()["n"]
            queue_number = f"Q{count + 1:03d}"
            cur = conn.execute(
                """INSERT INTO tickets(appointment_id,clinic_code,service_date,queue_number,state,issued_at)
                   VALUES(?,?,?,?,?,?)""",
                (appointment_id, appointment["clinic_code"], service_date, queue_number, "WAITING", as_utc_iso(now)),
            )
            ticket = conn.execute("SELECT * FROM tickets WHERE id=?", (cur.lastrowid,)).fetchone()
            response = {"appointment": {"id": appointment_id, "state": "CHECKED_IN", "checked_in_at": as_utc_iso(now)},
                        "ticket": ticket_json(ticket)}
            conn.execute(
                "INSERT INTO idempotency(user_id,idem_key,response_json,created_at) VALUES(?,?,?,?)",
                (user["id"], idempotency_key, json.dumps(response), as_utc_iso(now)),
            )
            conn.commit()
        return response

    @app.get("/api/staff/queue")
    def staff_queue(clinic_code: str, user: UserContext = Depends(current_user)):
        require_role(user, "receptionist")
        today = app.state.clock().astimezone(CLINIC_TIMEZONE).date().isoformat()
        with connect(app.state.db_path) as conn:
            rows = conn.execute(
                """SELECT * FROM tickets WHERE clinic_code=? AND service_date=? AND state IN ('WAITING','CALLED')
                   ORDER BY issued_at,id""",
                (clinic_code.upper(), today),
            ).fetchall()
        return {"clinic_code": clinic_code.upper(), "service_date": today, "tickets": [ticket_json(r) for r in rows]}

    @app.post("/api/staff/tickets/{ticket_id}/call")
    def call_ticket(
        ticket_id: int,
        if_match: str | None = Header(default=None, alias="If-Match"),
        user: UserContext = Depends(current_user),
    ):
        require_role(user, "receptionist")
        if if_match is None:
            raise HTTPException(status_code=428, detail="If-Match version is required")
        try:
            expected_version = int(if_match.strip().strip('"'))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="If-Match must be an integer version") from exc
        now = as_utc_iso(app.state.clock())
        with connect(app.state.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            ticket = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
            if ticket is None:
                conn.rollback()
                raise HTTPException(status_code=404, detail="Ticket not found")
            if ticket["version"] != expected_version:
                conn.rollback()
                raise HTTPException(status_code=412, detail="Ticket version is stale; refresh the queue")
            changed = conn.execute(
                "UPDATE tickets SET state='CALLED',called_at=?,version=version+1 WHERE id=? AND state='WAITING' AND version=?",
                (now, ticket_id, expected_version),
            ).rowcount
            if changed != 1:
                conn.rollback()
                raise HTTPException(status_code=409, detail="Ticket is not WAITING")
            updated = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
            conn.commit()
        return ticket_json(updated)

    @app.exception_handler(sqlite3.IntegrityError)
    async def integrity_error_handler(request: Request, exc: sqlite3.IntegrityError):
        return JSONResponse(status_code=409, content={"detail": "The requested change conflicts with existing data"})

    return app


app = create_app()
