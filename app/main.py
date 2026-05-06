from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path
import sqlite3, secrets, hashlib, os, json, time, io, csv
from typing import Optional, Any
from urllib.parse import urlparse

APP_DIR = Path(__file__).parent

# ---- Production configuration ----
# Local development uses SQLite by default.
# On Render, set DATA_DIR=/var/data and attach a persistent disk.
# DATABASE_URL is reserved for PostgreSQL migration; this v1.0 keeps the stable SQLite schema,
# but all secrets and deployment settings are now environment driven.
DATA_DIR = Path(os.environ.get("DATA_DIR", str(APP_DIR)))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "skola_royale.db"

SESSION_DAYS = int(os.environ.get("SESSION_DAYS", "14"))
APP_ENV = os.environ.get("APP_ENV", "development")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
TEACHER_USERNAME = os.environ.get("TEACHER_USERNAME", "kennari")
TEACHER_PASSWORD = os.environ.get("TEACHER_PASSWORD", "kennari123")
ALLOW_DEFAULT_TEACHER_PASSWORD = os.environ.get("ALLOW_DEFAULT_TEACHER_PASSWORD", "false").lower() == "true"

app = FastAPI(title="Skóla Royale API", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if APP_ENV == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/health")
def health():
    return {
        "ok": True,
        "app": "Skóla Royale",
        "version": "1.0.0",
        "env": APP_ENV,
        "database": "sqlite",
        "data_dir": str(DATA_DIR)
    }


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now() -> int:
    return int(time.time())


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 210_000)
    return f"pbkdf2_sha256${salt}${hashed.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt, _ = stored.split("$", 2)
        if algo != "pbkdf2_sha256":
            return False
        return secrets.compare_digest(hash_password(password, salt), stored)
    except Exception:
        return False


def init_db():
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('teacher','student')),
            password_hash TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            class_name TEXT NOT NULL DEFAULT '',
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS progress (
            user_id INTEGER PRIMARY KEY,
            level INTEGER NOT NULL DEFAULT 1,
            xp INTEGER NOT NULL DEFAULT 0,
            coins INTEGER NOT NULL DEFAULT 0,
            streak INTEGER NOT NULL DEFAULT 0,
            shields INTEGER NOT NULL DEFAULT 0,
            hints INTEGER NOT NULL DEFAULT 2,
            skips INTEGER NOT NULL DEFAULT 2,
            loot_boxes INTEGER NOT NULL DEFAULT 0,
            total_correct INTEGER NOT NULL DEFAULT 0,
            total_answered INTEGER NOT NULL DEFAULT 0,
            boss_wins INTEGER NOT NULL DEFAULT 0,
            zone TEXT NOT NULL DEFAULT 'mixed',
            owned_json TEXT NOT NULL DEFAULT '{}',
            achievements_json TEXT NOT NULL DEFAULT '{}',
            updated_at INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            skill TEXT NOT NULL DEFAULT 'almennt',
            difficulty INTEGER NOT NULL DEFAULT 1,
            question TEXT NOT NULL,
            answer_given TEXT,
            correct_answer TEXT,
            correct INTEGER NOT NULL,
            xp_gain INTEGER NOT NULL DEFAULT 0,
            coin_gain INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS custom_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            skill TEXT NOT NULL DEFAULT 'almennt',
            difficulty INTEGER NOT NULL DEFAULT 1,
            text TEXT NOT NULL,
            answer TEXT NOT NULL,
            hint TEXT NOT NULL DEFAULT '',
            options_json TEXT NOT NULL DEFAULT '[]',
            active INTEGER NOT NULL DEFAULT 1,
            created_by INTEGER,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY(created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS mission_packs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            class_name TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            created_by INTEGER,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY(created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS mission_pack_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pack_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            UNIQUE(pack_id, question_id),
            FOREIGN KEY(pack_id) REFERENCES mission_packs(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES custom_questions(id) ON DELETE CASCADE
        );
        """)

        # Lightweight migrations for older local databases
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "class_name" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN class_name TEXT NOT NULL DEFAULT ''")

        attempt_cols = [r["name"] for r in conn.execute("PRAGMA table_info(attempts)").fetchall()]
        if "skill" not in attempt_cols:
            conn.execute("ALTER TABLE attempts ADD COLUMN skill TEXT NOT NULL DEFAULT 'almennt'")
        if "difficulty" not in attempt_cols:
            conn.execute("ALTER TABLE attempts ADD COLUMN difficulty INTEGER NOT NULL DEFAULT 1")

        teacher = conn.execute("SELECT id FROM users WHERE role='teacher' LIMIT 1").fetchone()
        if not teacher:
            conn.execute(
                "INSERT INTO users(username, display_name, role, password_hash, active, class_name, created_at) VALUES (?,?,?,?,1,?,?)",
                (TEACHER_USERNAME, "Kennari", "teacher", hash_password(TEACHER_PASSWORD), "", now())
            )


@app.on_event("startup")
def startup():
    if APP_ENV == "production":
        if SECRET_KEY == "dev-only-change-me":
            raise RuntimeError("SECRET_KEY must be set in production.")
        if TEACHER_PASSWORD == "kennari123" and not ALLOW_DEFAULT_TEACHER_PASSWORD:
            raise RuntimeError("Change TEACHER_PASSWORD before running in production.")
    init_db()


@app.get("/")
def index():
    return FileResponse(APP_DIR / "static" / "index.html")


class LoginIn(BaseModel):
    username: str
    password: str


class StudentCreate(BaseModel):
    username: str = Field(min_length=2, max_length=40)
    display_name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=4, max_length=80)
    class_name: str = Field(default="", max_length=80)


class BulkStudentCreate(BaseModel):
    students: list[StudentCreate]


class PasswordResetIn(BaseModel):
    password: str = Field(min_length=4, max_length=80)


class QuestionCreate(BaseModel):
    subject: str = Field(min_length=2, max_length=40)
    skill: str = Field(default="almennt", max_length=80)
    difficulty: int = Field(default=1, ge=1, le=5)
    text: str = Field(min_length=3, max_length=1000)
    answer: str = Field(min_length=1, max_length=300)
    hint: str = Field(default="", max_length=500)
    options: list[str] = Field(default_factory=list)
    active: bool = True


class QuestionUpdate(BaseModel):
    subject: Optional[str] = Field(default=None, min_length=2, max_length=40)
    skill: Optional[str] = Field(default=None, max_length=80)
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    text: Optional[str] = Field(default=None, min_length=3, max_length=1000)
    answer: Optional[str] = Field(default=None, min_length=1, max_length=300)
    hint: Optional[str] = Field(default=None, max_length=500)
    options: Optional[list[str]] = None
    active: Optional[bool] = None


class MissionPackCreate(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)
    class_name: str = Field(default="", max_length=80)
    question_ids: list[int] = Field(default_factory=list)
    active: bool = True


class MissionPackUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    class_name: Optional[str] = Field(default=None, max_length=80)
    question_ids: Optional[list[int]] = None
    active: Optional[bool] = None


class ProgressIn(BaseModel):
    level: int = 1
    xp: int = 0
    coins: int = 0
    streak: int = 0
    shields: int = 0
    hints: int = 2
    skips: int = 2
    loot_boxes: int = 0
    total_correct: int = 0
    total_answered: int = 0
    boss_wins: int = 0
    zone: str = "mixed"
    owned: dict[str, Any] = {}
    achievements: dict[str, Any] = {}


class AttemptIn(BaseModel):
    subject: str
    skill: str = "almennt"
    difficulty: int = 1
    question: str
    answer_given: Optional[str] = ""
    correct_answer: Optional[str] = ""
    correct: bool
    xp_gain: int = 0
    coin_gain: int = 0


def create_default_progress(conn, user_id: int):
    existing = conn.execute("SELECT user_id FROM progress WHERE user_id=?", (user_id,)).fetchone()
    if not existing:
        conn.execute("INSERT INTO progress(user_id, updated_at) VALUES (?,?)", (user_id, now()))


def current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Ekki innskráð/ur.")
    token = authorization.replace("Bearer ", "", 1).strip()
    with db() as conn:
        row = conn.execute("""
            SELECT u.* FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token=? AND s.expires_at>? AND u.active=1
        """, (token, now())).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Innskráning rann út eða er ógild.")
        return dict(row)


def require_teacher(user=Depends(current_user)):
    if user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Aðeins kennari hefur aðgang.")
    return user


@app.post("/api/login")
def login(data: LoginIn):
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE username=? AND active=1", (data.username.strip(),)).fetchone()
        if not user or not verify_password(data.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Rangt notandanafn eða lykilorð.")
        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO sessions(token, user_id, created_at, expires_at) VALUES (?,?,?,?)",
            (token, user["id"], now(), now() + SESSION_DAYS * 24 * 60 * 60)
        )
        create_default_progress(conn, user["id"])
        return {"token": token, "user": {"username": user["username"], "display_name": user["display_name"], "role": user["role"], "class_name": user["class_name"]}}


@app.post("/api/logout")
def logout(authorization: Optional[str] = Header(None)):
    token = authorization.replace("Bearer ", "", 1).strip() if authorization else ""
    with db() as conn:
        conn.execute("DELETE FROM sessions WHERE token=?", (token,))
    return {"ok": True}


@app.get("/api/me")
def me(user=Depends(current_user)):
    return {"id": user["id"], "username": user["username"], "display_name": user["display_name"], "role": user["role"], "class_name": user["class_name"]}


@app.get("/api/progress")
def get_progress(user=Depends(current_user)):
    with db() as conn:
        create_default_progress(conn, user["id"])
        p = conn.execute("SELECT * FROM progress WHERE user_id=?", (user["id"],)).fetchone()
        result = dict(p)
        result["owned"] = json.loads(result.pop("owned_json") or "{}")
        result["achievements"] = json.loads(result.pop("achievements_json") or "{}")
        return result


@app.post("/api/progress")
def save_progress(data: ProgressIn, user=Depends(current_user)):
    with db() as conn:
        create_default_progress(conn, user["id"])
        conn.execute("""
            UPDATE progress SET
              level=?, xp=?, coins=?, streak=?, shields=?, hints=?, skips=?, loot_boxes=?,
              total_correct=?, total_answered=?, boss_wins=?, zone=?,
              owned_json=?, achievements_json=?, updated_at=?
            WHERE user_id=?
        """, (
            data.level, data.xp, data.coins, data.streak, data.shields, data.hints, data.skips, data.loot_boxes,
            data.total_correct, data.total_answered, data.boss_wins, data.zone,
            json.dumps(data.owned, ensure_ascii=False), json.dumps(data.achievements, ensure_ascii=False),
            now(), user["id"]
        ))
    return {"ok": True}


@app.post("/api/attempts")
def log_attempt(data: AttemptIn, user=Depends(current_user)):
    with db() as conn:
        conn.execute("""
            INSERT INTO attempts(user_id, subject, skill, difficulty, question, answer_given, correct_answer, correct, xp_gain, coin_gain, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            user["id"], data.subject, data.skill or "almennt", data.difficulty or 1,
            data.question, data.answer_given, data.correct_answer, 1 if data.correct else 0,
            data.xp_gain, data.coin_gain, now()
        ))
    return {"ok": True}


@app.post("/api/teacher/students")
def create_student(data: StudentCreate, teacher=Depends(require_teacher)):
    username = data.username.strip().lower()
    with db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users(username, display_name, role, password_hash, active, class_name, created_at) VALUES (?,?,?,?,1,?,?)",
                (username, data.display_name.strip(), "student", hash_password(data.password), data.class_name.strip(), now())
            )
            create_default_progress(conn, cur.lastrowid)
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Þetta notandanafn er nú þegar til.")
    return {"ok": True, "username": username}


@app.get("/api/teacher/students")
def list_students(teacher=Depends(require_teacher)):
    with db() as conn:
        rows = conn.execute("""
            SELECT
              u.id, u.username, u.display_name, u.active, u.class_name, u.created_at,
              p.level, p.xp, p.coins, p.streak, p.total_correct, p.total_answered, p.updated_at,
              COALESCE(SUM(CASE WHEN a.created_at > strftime('%s','now','-7 days') THEN 1 ELSE 0 END), 0) AS attempts_7d,
              COALESCE(SUM(CASE WHEN a.created_at > strftime('%s','now','-7 days') AND a.correct=1 THEN 1 ELSE 0 END), 0) AS correct_7d
            FROM users u
            LEFT JOIN progress p ON p.user_id = u.id
            LEFT JOIN attempts a ON a.user_id = u.id
            WHERE u.role='student'
            GROUP BY u.id
            ORDER BY u.display_name COLLATE NOCASE
        """).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            answered = d.get("total_answered") or 0
            d["accuracy"] = round((d.get("total_correct") or 0) / answered * 100) if answered else 0
            attempts_7d = d.get("attempts_7d") or 0
            d["accuracy_7d"] = round((d.get("correct_7d") or 0) / attempts_7d * 100) if attempts_7d else 0
            out.append(d)
        return out



@app.post("/api/teacher/students/bulk")
def create_students_bulk(data: BulkStudentCreate, teacher=Depends(require_teacher)):
    created = []
    errors = []
    with db() as conn:
        for s in data.students:
            username = s.username.strip().lower()
            try:
                cur = conn.execute(
                    "INSERT INTO users(username, display_name, role, password_hash, active, class_name, created_at) VALUES (?,?,?,?,1,?,?)",
                    (username, s.display_name.strip(), "student", hash_password(s.password), s.class_name.strip(), now())
                )
                create_default_progress(conn, cur.lastrowid)
                created.append(username)
            except sqlite3.IntegrityError:
                errors.append({"username": username, "error": "Notandanafn er nú þegar til."})
    return {"ok": True, "created": created, "errors": errors}


@app.post("/api/teacher/students/{student_id}/reset-password")
def reset_student_password(student_id: int, data: PasswordResetIn, teacher=Depends(require_teacher)):
    with db() as conn:
        row = conn.execute("SELECT id FROM users WHERE id=? AND role='student'", (student_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Nemandi fannst ekki.")
        conn.execute("UPDATE users SET password_hash=? WHERE id=? AND role='student'", (hash_password(data.password), student_id))
    return {"ok": True}


@app.get("/api/teacher/classes")
def list_classes(teacher=Depends(require_teacher)):
    with db() as conn:
        rows = conn.execute("""
            SELECT COALESCE(NULLIF(class_name,''), 'Óflokkað') AS class_name, COUNT(*) AS students
            FROM users
            WHERE role='student'
            GROUP BY COALESCE(NULLIF(class_name,''), 'Óflokkað')
            ORDER BY class_name COLLATE NOCASE
        """).fetchall()
        return [dict(r) for r in rows]


@app.get("/api/teacher/students/{student_id}/detail")
def student_detail(student_id: int, teacher=Depends(require_teacher)):
    with db() as conn:
        u = conn.execute("""
            SELECT u.id, u.username, u.display_name, u.class_name, u.active,
                   p.level, p.xp, p.coins, p.streak, p.total_correct, p.total_answered, p.updated_at
            FROM users u
            LEFT JOIN progress p ON p.user_id = u.id
            WHERE u.id=? AND u.role='student'
        """, (student_id,)).fetchone()
        if not u:
            raise HTTPException(status_code=404, detail="Nemandi fannst ekki.")
        subjects = conn.execute("""
            SELECT subject, COUNT(*) AS answered, SUM(correct) AS correct
            FROM attempts
            WHERE user_id=?
            GROUP BY subject
            ORDER BY subject
        """, (student_id,)).fetchall()
        skills = conn.execute("""
            SELECT subject, COALESCE(NULLIF(skill,''), 'almennt') AS skill, COUNT(*) AS answered, SUM(correct) AS correct
            FROM attempts
            WHERE user_id=?
            GROUP BY subject, COALESCE(NULLIF(skill,''), 'almennt')
            ORDER BY subject, skill
        """, (student_id,)).fetchall()
        recent = conn.execute("""
            SELECT subject, COALESCE(NULLIF(skill,''), 'almennt') AS skill, question, answer_given, correct_answer, correct, created_at
            FROM attempts
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT 20
        """, (student_id,)).fetchall()
        detail = dict(u)
        detail["accuracy"] = round((detail.get("total_correct") or 0) / (detail.get("total_answered") or 1) * 100) if detail.get("total_answered") else 0
        detail["subjects"] = [
            {"subject": r["subject"], "answered": r["answered"], "correct": r["correct"], "accuracy": round((r["correct"] / r["answered"]) * 100) if r["answered"] else 0}
            for r in subjects
        ]
        detail["skills"] = [
            {"subject": r["subject"], "skill": r["skill"], "answered": r["answered"], "correct": r["correct"], "accuracy": round((r["correct"] / r["answered"]) * 100) if r["answered"] else 0}
            for r in skills
        ]
        detail["recent_attempts"] = [dict(r) for r in recent]
        return detail


@app.patch("/api/teacher/students/{student_id}/class")
def update_student_class(student_id: int, class_name: str, teacher=Depends(require_teacher)):
    with db() as conn:
        conn.execute("UPDATE users SET class_name=? WHERE id=? AND role='student'", (class_name.strip(), student_id))
    return {"ok": True}



def question_row_to_dict(r):
    d = dict(r)
    try:
        d["options"] = json.loads(d.pop("options_json") or "[]")
    except Exception:
        d["options"] = []
    d["id"] = f"custom-{d['id']}"
    return d


@app.get("/api/questions")
def list_public_questions(user=Depends(current_user)):
    """Questions added by the teacher. Students load these automatically."""
    with db() as conn:
        rows = conn.execute("""
            SELECT id, subject, skill, difficulty, text, answer, hint, options_json, active, created_at, updated_at
            FROM custom_questions
            WHERE active=1
            ORDER BY updated_at DESC
        """).fetchall()
        return [question_row_to_dict(r) for r in rows]


@app.get("/api/teacher/questions")
def teacher_list_questions(teacher=Depends(require_teacher)):
    with db() as conn:
        rows = conn.execute("""
            SELECT id, subject, skill, difficulty, text, answer, hint, options_json, active, created_at, updated_at
            FROM custom_questions
            ORDER BY updated_at DESC
        """).fetchall()
        return [question_row_to_dict(r) for r in rows]


@app.post("/api/teacher/questions")
def teacher_create_question(data: QuestionCreate, teacher=Depends(require_teacher)):
    options = [str(x).strip() for x in data.options if str(x).strip()]
    if options and data.answer not in options:
        options = [data.answer] + options
    with db() as conn:
        cur = conn.execute("""
            INSERT INTO custom_questions(subject, skill, difficulty, text, answer, hint, options_json, active, created_by, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data.subject.strip(), data.skill.strip() or "almennt", data.difficulty, data.text.strip(),
            data.answer.strip(), data.hint.strip(), json.dumps(options, ensure_ascii=False),
            1 if data.active else 0, teacher["id"], now(), now()
        ))
        row = conn.execute("SELECT id, subject, skill, difficulty, text, answer, hint, options_json, active, created_at, updated_at FROM custom_questions WHERE id=?", (cur.lastrowid,)).fetchone()
        return question_row_to_dict(row)


@app.patch("/api/teacher/questions/{question_id}")
def teacher_update_question(question_id: int, data: QuestionUpdate, teacher=Depends(require_teacher)):
    allowed = {}
    for field in ["subject", "skill", "difficulty", "text", "answer", "hint"]:
        value = getattr(data, field)
        if value is not None:
            allowed[field] = value.strip() if isinstance(value, str) else value
    if data.options is not None:
        opts = [str(x).strip() for x in data.options if str(x).strip()]
        allowed["options_json"] = json.dumps(opts, ensure_ascii=False)
    if data.active is not None:
        allowed["active"] = 1 if data.active else 0
    if not allowed:
        return {"ok": True}
    allowed["updated_at"] = now()
    sets = ", ".join([f"{k}=?" for k in allowed])
    values = list(allowed.values()) + [question_id]
    with db() as conn:
        row = conn.execute("SELECT id FROM custom_questions WHERE id=?", (question_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Spurning fannst ekki.")
        conn.execute(f"UPDATE custom_questions SET {sets} WHERE id=?", values)
    return {"ok": True}


@app.delete("/api/teacher/questions/{question_id}")
def teacher_delete_question(question_id: int, teacher=Depends(require_teacher)):
    with db() as conn:
        conn.execute("DELETE FROM custom_questions WHERE id=?", (question_id,))
    return {"ok": True}



@app.get("/api/teacher/skill-summary")
def skill_summary(class_name: Optional[str] = None, teacher=Depends(require_teacher)):
    with db() as conn:
        params = []
        where = "WHERE u.role='student'"
        if class_name:
            where += " AND COALESCE(NULLIF(u.class_name,''), 'Óflokkað')=?"
            params.append(class_name)
        rows = conn.execute(f"""
            SELECT
                a.subject,
                COALESCE(NULLIF(a.skill,''), 'almennt') AS skill,
                COUNT(*) AS answered,
                SUM(a.correct) AS correct,
                COUNT(DISTINCT a.user_id) AS students
            FROM attempts a
            JOIN users u ON u.id = a.user_id
            {where}
            GROUP BY a.subject, COALESCE(NULLIF(a.skill,''), 'almennt')
            HAVING answered > 0
            ORDER BY subject, skill
        """, params).fetchall()
        out = []
        for r in rows:
            answered = r["answered"] or 0
            correct = r["correct"] or 0
            out.append({
                "subject": r["subject"],
                "skill": r["skill"],
                "answered": answered,
                "correct": correct,
                "students": r["students"],
                "accuracy": round((correct / answered) * 100) if answered else 0
            })
        return out


@app.get("/api/teacher/skill-needs")
def skill_needs(class_name: Optional[str] = None, min_answers: int = 3, teacher=Depends(require_teacher)):
    with db() as conn:
        params = []
        where = "WHERE u.role='student'"
        if class_name:
            where += " AND COALESCE(NULLIF(u.class_name,''), 'Óflokkað')=?"
            params.append(class_name)
        rows = conn.execute(f"""
            SELECT
                a.subject,
                COALESCE(NULLIF(a.skill,''), 'almennt') AS skill,
                COUNT(*) AS answered,
                SUM(a.correct) AS correct,
                COUNT(DISTINCT a.user_id) AS students
            FROM attempts a
            JOIN users u ON u.id = a.user_id
            {where}
            GROUP BY a.subject, COALESCE(NULLIF(a.skill,''), 'almennt')
            HAVING answered >= ?
            ORDER BY (CAST(SUM(a.correct) AS REAL) / COUNT(*)) ASC, answered DESC
            LIMIT 12
        """, params + [min_answers]).fetchall()
        return [
            {
                "subject": r["subject"],
                "skill": r["skill"],
                "answered": r["answered"],
                "correct": r["correct"],
                "students": r["students"],
                "accuracy": round((r["correct"] / r["answered"]) * 100) if r["answered"] else 0
            }
            for r in rows
        ]


@app.get("/api/teacher/students/{student_id}/skills")
def student_skill_summary(student_id: int, teacher=Depends(require_teacher)):
    with db() as conn:
        u = conn.execute("SELECT id FROM users WHERE id=? AND role='student'", (student_id,)).fetchone()
        if not u:
            raise HTTPException(status_code=404, detail="Nemandi fannst ekki.")
        rows = conn.execute("""
            SELECT
                subject,
                COALESCE(NULLIF(skill,''), 'almennt') AS skill,
                COUNT(*) AS answered,
                SUM(correct) AS correct
            FROM attempts
            WHERE user_id=?
            GROUP BY subject, COALESCE(NULLIF(skill,''), 'almennt')
            ORDER BY subject, skill
        """, (student_id,)).fetchall()
        return [
            {
                "subject": r["subject"],
                "skill": r["skill"],
                "answered": r["answered"],
                "correct": r["correct"],
                "accuracy": round((r["correct"] / r["answered"]) * 100) if r["answered"] else 0
            }
            for r in rows
        ]



def pack_row_to_dict(conn, pack_row, include_questions: bool = True):
    pack = dict(pack_row)
    pack["id"] = int(pack["id"])
    if include_questions:
        qrows = conn.execute("""
            SELECT q.id, q.subject, q.skill, q.difficulty, q.text, q.answer, q.hint, q.options_json, q.active, q.created_at, q.updated_at
            FROM mission_pack_questions pq
            JOIN custom_questions q ON q.id = pq.question_id
            WHERE pq.pack_id=?
            ORDER BY pq.id
        """, (pack["id"],)).fetchall()
        pack["questions"] = [question_row_to_dict(q) for q in qrows]
    else:
        count = conn.execute("SELECT COUNT(*) AS c FROM mission_pack_questions WHERE pack_id=?", (pack["id"],)).fetchone()["c"]
        pack["question_count"] = count
    return pack


@app.get("/api/assigned-packs")
def assigned_packs(user=Depends(current_user)):
    """Active mission packs for the logged-in student/teacher."""
    class_name = user.get("class_name") or ""
    with db() as conn:
        rows = conn.execute("""
            SELECT id, title, description, class_name, active, created_at, updated_at
            FROM mission_packs
            WHERE active=1 AND (class_name='' OR class_name=?)
            ORDER BY updated_at DESC
        """, (class_name,)).fetchall()
        packs = []
        for r in rows:
            pack = pack_row_to_dict(conn, r, include_questions=True)
            pack["questions"] = [q for q in pack["questions"] if q.get("active")]
            if pack["questions"]:
                packs.append(pack)
        return packs


@app.get("/api/teacher/packs")
def teacher_list_packs(teacher=Depends(require_teacher)):
    with db() as conn:
        rows = conn.execute("""
            SELECT id, title, description, class_name, active, created_at, updated_at
            FROM mission_packs
            ORDER BY updated_at DESC
        """).fetchall()
        return [pack_row_to_dict(conn, r, include_questions=True) for r in rows]


@app.post("/api/teacher/packs")
def teacher_create_pack(data: MissionPackCreate, teacher=Depends(require_teacher)):
    clean_ids = sorted(set(int(x) for x in data.question_ids if int(x) > 0))
    with db() as conn:
        cur = conn.execute("""
            INSERT INTO mission_packs(title, description, class_name, active, created_by, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?)
        """, (
            data.title.strip(), data.description.strip(), data.class_name.strip(),
            1 if data.active else 0, teacher["id"], now(), now()
        ))
        pack_id = cur.lastrowid
        for qid in clean_ids:
            exists = conn.execute("SELECT id FROM custom_questions WHERE id=?", (qid,)).fetchone()
            if exists:
                conn.execute("INSERT OR IGNORE INTO mission_pack_questions(pack_id, question_id, created_at) VALUES (?,?,?)", (pack_id, qid, now()))
        row = conn.execute("SELECT id, title, description, class_name, active, created_at, updated_at FROM mission_packs WHERE id=?", (pack_id,)).fetchone()
        return pack_row_to_dict(conn, row, include_questions=True)


@app.patch("/api/teacher/packs/{pack_id}")
def teacher_update_pack(pack_id: int, data: MissionPackUpdate, teacher=Depends(require_teacher)):
    with db() as conn:
        row = conn.execute("SELECT id FROM mission_packs WHERE id=?", (pack_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Verkefnapakki fannst ekki.")

        updates = {}
        if data.title is not None:
            updates["title"] = data.title.strip()
        if data.description is not None:
            updates["description"] = data.description.strip()
        if data.class_name is not None:
            updates["class_name"] = data.class_name.strip()
        if data.active is not None:
            updates["active"] = 1 if data.active else 0
        updates["updated_at"] = now()

        sets = ", ".join([f"{k}=?" for k in updates])
        conn.execute(f"UPDATE mission_packs SET {sets} WHERE id=?", list(updates.values()) + [pack_id])

        if data.question_ids is not None:
            clean_ids = sorted(set(int(x) for x in data.question_ids if int(x) > 0))
            conn.execute("DELETE FROM mission_pack_questions WHERE pack_id=?", (pack_id,))
            for qid in clean_ids:
                exists = conn.execute("SELECT id FROM custom_questions WHERE id=?", (qid,)).fetchone()
                if exists:
                    conn.execute("INSERT OR IGNORE INTO mission_pack_questions(pack_id, question_id, created_at) VALUES (?,?,?)", (pack_id, qid, now()))
    return {"ok": True}


@app.delete("/api/teacher/packs/{pack_id}")
def teacher_delete_pack(pack_id: int, teacher=Depends(require_teacher)):
    with db() as conn:
        conn.execute("DELETE FROM mission_pack_questions WHERE pack_id=?", (pack_id,))
        conn.execute("DELETE FROM mission_packs WHERE id=?", (pack_id,))
    return {"ok": True}



def csv_response(filename: str, rows: list[dict], fieldnames: list[str]):
    output = io.StringIO()
    output.write("\ufeff")  # Excel-friendly UTF-8 BOM
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/api/teacher/reports/class.csv")
def export_class_csv(class_name: Optional[str] = None, teacher=Depends(require_teacher)):
    params = []
    where = "WHERE u.role='student'"
    label = "allir"
    if class_name:
        where += " AND COALESCE(NULLIF(u.class_name,''), 'Óflokkað')=?"
        params.append(class_name)
        label = class_name.replace(" ", "_")
    with db() as conn:
        rows = conn.execute(f"""
            SELECT
              u.display_name AS nemandi,
              u.username AS notandanafn,
              COALESCE(NULLIF(u.class_name,''), 'Óflokkað') AS bekkur,
              u.active AS virkur,
              COALESCE(p.level,1) AS level,
              COALESCE(p.xp,0) AS xp,
              COALESCE(p.coins,0) AS coins,
              COALESCE(p.streak,0) AS streak,
              COALESCE(p.total_correct,0) AS rett,
              COALESCE(p.total_answered,0) AS svarad,
              COALESCE(p.updated_at,0) AS sidast_virkur
            FROM users u
            LEFT JOIN progress p ON p.user_id = u.id
            {where}
            ORDER BY bekkur COLLATE NOCASE, nemandi COLLATE NOCASE
        """, params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["nakvaemni_pr"] = round((d["rett"] / d["svarad"]) * 100) if d["svarad"] else 0
            out.append(d)
    fields = ["nemandi","notandanafn","bekkur","virkur","level","xp","coins","streak","rett","svarad","nakvaemni_pr","sidast_virkur"]
    return csv_response(f"skola_royale_bekkjarskyrsla_{label}.csv", out, fields)


@app.get("/api/teacher/reports/skills.csv")
def export_skills_csv(class_name: Optional[str] = None, teacher=Depends(require_teacher)):
    params = []
    where = "WHERE u.role='student'"
    label = "allir"
    if class_name:
        where += " AND COALESCE(NULLIF(u.class_name,''), 'Óflokkað')=?"
        params.append(class_name)
        label = class_name.replace(" ", "_")
    with db() as conn:
        rows = conn.execute(f"""
            SELECT
              u.display_name AS nemandi,
              u.username AS notandanafn,
              COALESCE(NULLIF(u.class_name,''), 'Óflokkað') AS bekkur,
              a.subject AS grein,
              COALESCE(NULLIF(a.skill,''), 'almennt') AS faerni,
              COUNT(*) AS svarad,
              SUM(a.correct) AS rett
            FROM attempts a
            JOIN users u ON u.id = a.user_id
            {where}
            GROUP BY u.id, a.subject, COALESCE(NULLIF(a.skill,''), 'almennt')
            ORDER BY bekkur COLLATE NOCASE, nemandi COLLATE NOCASE, grein, faerni
        """, params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["nakvaemni_pr"] = round((d["rett"] / d["svarad"]) * 100) if d["svarad"] else 0
            out.append(d)
    fields = ["nemandi","notandanafn","bekkur","grein","faerni","rett","svarad","nakvaemni_pr"]
    return csv_response(f"skola_royale_faerniskyrsla_{label}.csv", out, fields)


@app.get("/api/teacher/reports/student/{student_id}.csv")
def export_student_csv(student_id: int, teacher=Depends(require_teacher)):
    with db() as conn:
        user = conn.execute("SELECT username, display_name, COALESCE(NULLIF(class_name,''), 'Óflokkað') AS class_name FROM users WHERE id=? AND role='student'", (student_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Nemandi fannst ekki.")
        rows = conn.execute("""
            SELECT
              a.subject AS grein,
              COALESCE(NULLIF(a.skill,''), 'almennt') AS faerni,
              a.difficulty AS erfidleiki,
              a.question AS spurning,
              a.answer_given AS svar_nemanda,
              a.correct_answer AS rett_svar,
              a.correct AS rett,
              a.created_at AS timi
            FROM attempts a
            WHERE a.user_id=?
            ORDER BY a.created_at DESC
        """, (student_id,)).fetchall()
        out = [dict(r) for r in rows]
    safe = user["username"].replace(" ", "_")
    fields = ["grein","faerni","erfidleiki","spurning","svar_nemanda","rett_svar","rett","timi"]
    return csv_response(f"skola_royale_nemandi_{safe}.csv", out, fields)


@app.get("/api/teacher/support-needs")
def support_needs(class_name: Optional[str] = None, max_accuracy: int = 65, min_answers: int = 3, teacher=Depends(require_teacher)):
    params = []
    where = "WHERE u.role='student'"
    if class_name:
        where += " AND COALESCE(NULLIF(u.class_name,''), 'Óflokkað')=?"
        params.append(class_name)
    with db() as conn:
        rows = conn.execute(f"""
            SELECT
              u.id AS student_id,
              u.display_name AS nemandi,
              u.username AS notandanafn,
              COALESCE(NULLIF(u.class_name,''), 'Óflokkað') AS bekkur,
              a.subject AS grein,
              COALESCE(NULLIF(a.skill,''), 'almennt') AS faerni,
              COUNT(*) AS svarad,
              SUM(a.correct) AS rett
            FROM attempts a
            JOIN users u ON u.id = a.user_id
            {where}
            GROUP BY u.id, a.subject, COALESCE(NULLIF(a.skill,''), 'almennt')
            HAVING svarad >= ?
            ORDER BY (CAST(SUM(a.correct) AS REAL) / COUNT(*)) ASC, svarad DESC
            LIMIT 50
        """, params + [min_answers]).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["nakvaemni"] = round((d["rett"] / d["svarad"]) * 100) if d["svarad"] else 0
            if d["nakvaemni"] <= max_accuracy:
                out.append(d)
        return out


@app.get("/api/teacher/subject-summary")
def subject_summary(teacher=Depends(require_teacher)):
    with db() as conn:
        rows = conn.execute("""
            SELECT subject, COUNT(*) AS answered, SUM(correct) AS correct
            FROM attempts
            GROUP BY subject
            ORDER BY subject
        """).fetchall()
        return [
            {"subject": r["subject"], "answered": r["answered"], "correct": r["correct"], "accuracy": round((r["correct"] / r["answered"]) * 100) if r["answered"] else 0}
            for r in rows
        ]


@app.patch("/api/teacher/students/{student_id}/active")
def set_active(student_id: int, active: bool, teacher=Depends(require_teacher)):
    with db() as conn:
        conn.execute("UPDATE users SET active=? WHERE id=? AND role='student'", (1 if active else 0, student_id))
    return {"ok": True}
