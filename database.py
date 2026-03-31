import sqlite3
import uuid
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger("database")

DB_PATH = Path(__file__).parent / "data" / "parenting_plan.db"


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS lawyers (
            id TEXT PRIMARY KEY,
            firm_name TEXT NOT NULL,
            lawyer_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,
            lawyer_id TEXT NOT NULL,
            intake_token TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (lawyer_id) REFERENCES lawyers(id)
        );

        CREATE TABLE IF NOT EXISTS intake_responses (
            id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL UNIQUE,
            full_name TEXT,
            maiden_name TEXT,
            birth_date TEXT,
            city_state_born TEXT,
            drivers_license_last3 TEXT,
            ssn_last3 TEXT,
            address TEXT,
            city TEXT,
            county TEXT,
            state TEXT,
            zip TEXT,
            phone TEXT,
            email TEXT,
            employer TEXT,
            job_title TEXT,
            employer_address TEXT,
            employer_city_state_zip TEXT,
            gross_salary TEXT,
            length_of_employment TEXT,
            education TEXT,
            submitted_at TEXT,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS survey_responses (
            id TEXT PRIMARY KEY,
            client_id TEXT,
            selection TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized at %s", DB_PATH)


def create_lawyer(firm_name: str, lawyer_name: str, email: str = "", phone: str = "") -> dict:
    conn = get_db()
    lawyer_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO lawyers (id, firm_name, lawyer_name, email, phone, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (lawyer_id, firm_name, lawyer_name, email, phone, now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM lawyers WHERE id = ?", (lawyer_id,)).fetchone()
    conn.close()
    return dict(row)


def get_lawyer(lawyer_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM lawyers WHERE id = ?", (lawyer_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_lawyers() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM lawyers ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_client(lawyer_id: str) -> dict:
    conn = get_db()
    client_id = str(uuid.uuid4())
    intake_token = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO clients (id, lawyer_id, intake_token, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
        (client_id, lawyer_id, intake_token, now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    conn.close()
    return dict(row)


def get_client(client_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_client_by_token(token: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM clients WHERE intake_token = ?", (token,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_clients_for_lawyer(lawyer_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT c.*, ir.full_name, ir.email as client_email
           FROM clients c
           LEFT JOIN intake_responses ir ON ir.client_id = c.id
           WHERE c.lawyer_id = ?
           ORDER BY c.created_at DESC""",
        (lawyer_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_intake_response(client_id: str, data: dict) -> dict:
    conn = get_db()
    response_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO intake_responses
           (id, client_id, full_name, maiden_name, birth_date, city_state_born,
            drivers_license_last3, ssn_last3, address, city, county, state, zip,
            phone, email, employer, job_title, employer_address, employer_city_state_zip,
            gross_salary, length_of_employment, education, submitted_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            response_id, client_id,
            data.get("full_name", ""), data.get("maiden_name", ""),
            data.get("birth_date", ""), data.get("city_state_born", ""),
            data.get("drivers_license_last3", ""), data.get("ssn_last3", ""),
            data.get("address", ""), data.get("city", ""), data.get("county", ""),
            data.get("state", ""), data.get("zip", ""),
            data.get("phone", ""), data.get("email", ""),
            data.get("employer", ""), data.get("job_title", ""),
            data.get("employer_address", ""), data.get("employer_city_state_zip", ""),
            data.get("gross_salary", ""), data.get("length_of_employment", ""),
            data.get("education", ""), now,
        ),
    )
    conn.execute(
        "UPDATE clients SET status = 'completed', completed_at = ? WHERE id = ?",
        (now, client_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM intake_responses WHERE id = ?", (response_id,)).fetchone()
    conn.close()
    return dict(row)


def get_intake_response(client_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM intake_responses WHERE client_id = ?", (client_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_survey_response(client_id: str | None, selection: str) -> dict:
    conn = get_db()
    survey_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO survey_responses (id, client_id, selection, created_at) VALUES (?, ?, ?, ?)",
        (survey_id, client_id, selection, now),
    )
    conn.commit()
    conn.close()
    return {"id": survey_id, "selection": selection}


def get_survey_results() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT selection, COUNT(*) as count FROM survey_responses GROUP BY selection ORDER BY count DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
