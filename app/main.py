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
            grade_level INTEGER NOT NULL DEFAULT 5,
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
            grade_level INTEGER NOT NULL DEFAULT 5,
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

        CREATE TABLE IF NOT EXISTS learning_paths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            class_name TEXT NOT NULL DEFAULT '',
            grade_level INTEGER NOT NULL DEFAULT 5,
            subject TEXT NOT NULL DEFAULT 'mixed',
            active INTEGER NOT NULL DEFAULT 1,
            reward_coins INTEGER NOT NULL DEFAULT 500,
            created_by INTEGER,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY(created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS learning_path_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path_id INTEGER NOT NULL,
            step_order INTEGER NOT NULL DEFAULT 1,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            step_type TEXT NOT NULL DEFAULT 'practice',
            subject TEXT NOT NULL DEFAULT 'mixed',
            skill TEXT NOT NULL DEFAULT '',
            grade_level INTEGER NOT NULL DEFAULT 5,
            target_correct INTEGER NOT NULL DEFAULT 5,
            boss_required INTEGER NOT NULL DEFAULT 0,
            reward_coins INTEGER NOT NULL DEFAULT 100,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(path_id) REFERENCES learning_paths(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS learning_path_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            path_id INTEGER NOT NULL,
            step_id INTEGER NOT NULL,
            correct_count INTEGER NOT NULL DEFAULT 0,
            answered_count INTEGER NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0,
            reward_claimed INTEGER NOT NULL DEFAULT 0,
            started_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            completed_at INTEGER,
            UNIQUE(user_id, path_id, step_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(path_id) REFERENCES learning_paths(id) ON DELETE CASCADE,
            FOREIGN KEY(step_id) REFERENCES learning_path_steps(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS path_quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            class_name TEXT NOT NULL DEFAULT '',
            grade_level INTEGER NOT NULL DEFAULT 5,
            subject TEXT NOT NULL DEFAULT 'mixed',
            question_count INTEGER NOT NULL DEFAULT 10,
            pass_percent INTEGER NOT NULL DEFAULT 70,
            active INTEGER NOT NULL DEFAULT 1,
            created_by INTEGER,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY(path_id) REFERENCES learning_paths(id) ON DELETE CASCADE,
            FOREIGN KEY(created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS path_quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0,
            percent INTEGER NOT NULL DEFAULT 0,
            passed INTEGER NOT NULL DEFAULT 0,
            answers_json TEXT NOT NULL DEFAULT '[]',
            created_at INTEGER NOT NULL,
            FOREIGN KEY(quiz_id) REFERENCES path_quizzes(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id)
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
        if "grade_level" not in attempt_cols:
            conn.execute("ALTER TABLE attempts ADD COLUMN grade_level INTEGER NOT NULL DEFAULT 5")

        custom_cols = [r["name"] for r in conn.execute("PRAGMA table_info(custom_questions)").fetchall()]
        if "grade_level" not in custom_cols:
            conn.execute("ALTER TABLE custom_questions ADD COLUMN grade_level INTEGER NOT NULL DEFAULT 5")

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
    grade_level: int = Field(default=5, ge=5, le=7)
    text: str = Field(min_length=3, max_length=1000)
    answer: str = Field(min_length=1, max_length=300)
    hint: str = Field(default="", max_length=500)
    options: list[str] = Field(default_factory=list)
    active: bool = True


class QuestionUpdate(BaseModel):
    subject: Optional[str] = Field(default=None, min_length=2, max_length=40)
    skill: Optional[str] = Field(default=None, max_length=80)
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    grade_level: Optional[int] = Field(default=None, ge=5, le=7)
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


class LearningPathStepIn(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    description: str = Field(default="", max_length=500)
    step_type: str = Field(default="practice", max_length=40)
    subject: str = Field(default="mixed", max_length=40)
    skill: str = Field(default="", max_length=80)
    grade_level: int = Field(default=5, ge=5, le=7)
    target_correct: int = Field(default=5, ge=1, le=100)
    boss_required: bool = False
    reward_coins: int = Field(default=100, ge=0, le=5000)


class LearningPathCreate(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    description: str = Field(default="", max_length=800)
    class_name: str = Field(default="", max_length=80)
    grade_level: int = Field(default=5, ge=5, le=7)
    subject: str = Field(default="mixed", max_length=40)
    reward_coins: int = Field(default=500, ge=0, le=10000)
    active: bool = True
    steps: list[LearningPathStepIn] = Field(default_factory=list)


class LearningPathUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=140)
    description: Optional[str] = Field(default=None, max_length=800)
    class_name: Optional[str] = Field(default=None, max_length=80)
    grade_level: Optional[int] = Field(default=None, ge=5, le=7)
    subject: Optional[str] = Field(default=None, max_length=40)
    reward_coins: Optional[int] = Field(default=None, ge=0, le=10000)
    active: Optional[bool] = None
    steps: Optional[list[LearningPathStepIn]] = None


class LearningPathProgressIn(BaseModel):
    path_id: int
    step_id: int
    correct: bool = False
    answered: bool = True


class LearningPathClaimIn(BaseModel):
    path_id: int
    step_id: int


class PathQuizCreateIn(BaseModel):
    path_id: int
    title: Optional[str] = None
    description: str = ""
    question_count: int = Field(default=10, ge=3, le=40)
    pass_percent: int = Field(default=70, ge=0, le=100)
    active: bool = True


class PathQuizSubmitIn(BaseModel):
    quiz_id: int
    answers: list[dict] = Field(default_factory=list)


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
    grade_level: int = 5
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



@app.get("/api/me/skills")
def my_skill_summary(user=Depends(current_user)):
    with db() as conn:
        rows = conn.execute("""
            SELECT subject,
                   COALESCE(NULLIF(skill,''), 'almennt') AS skill,
                   grade_level,
                   COUNT(*) AS answered,
                   SUM(correct) AS correct
            FROM attempts
            WHERE user_id=?
            GROUP BY subject, COALESCE(NULLIF(skill,''), 'almennt'), grade_level
            ORDER BY grade_level, subject, skill
        """, (user["id"],)).fetchall()
        return [
            {
                "subject": r["subject"],
                "skill": r["skill"],
                "grade_level": r["grade_level"],
                "answered": r["answered"],
                "correct": r["correct"],
                "accuracy": round((r["correct"] / r["answered"]) * 100) if r["answered"] else 0
            }
            for r in rows
        ]

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
            INSERT INTO attempts(user_id, subject, skill, difficulty, grade_level, question, answer_given, correct_answer, correct, xp_gain, coin_gain, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            user["id"], data.subject, data.skill or "almennt", data.difficulty or 1, data.grade_level or 5,
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
            SELECT subject, COALESCE(NULLIF(skill,''), 'almennt') AS skill, grade_level, question, answer_given, correct_answer, correct, created_at
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
            SELECT id, subject, skill, difficulty, grade_level, text, answer, hint, options_json, active, created_at, updated_at
            FROM custom_questions
            WHERE active=1
            ORDER BY updated_at DESC
        """).fetchall()
        return [question_row_to_dict(r) for r in rows]


@app.get("/api/teacher/questions")
def teacher_list_questions(teacher=Depends(require_teacher)):
    with db() as conn:
        rows = conn.execute("""
            SELECT id, subject, skill, difficulty, grade_level, text, answer, hint, options_json, active, created_at, updated_at
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
            INSERT INTO custom_questions(subject, skill, difficulty, grade_level, text, answer, hint, options_json, active, created_by, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data.subject.strip(), data.skill.strip() or "almennt", data.difficulty, data.grade_level, data.text.strip(),
            data.answer.strip(), data.hint.strip(), json.dumps(options, ensure_ascii=False),
            1 if data.active else 0, teacher["id"], now(), now()
        ))
        row = conn.execute("SELECT id, subject, skill, difficulty, grade_level, text, answer, hint, options_json, active, created_at, updated_at FROM custom_questions WHERE id=?", (cur.lastrowid,)).fetchone()
        return question_row_to_dict(row)


@app.patch("/api/teacher/questions/{question_id}")
def teacher_update_question(question_id: int, data: QuestionUpdate, teacher=Depends(require_teacher)):
    allowed = {}
    for field in ["subject", "skill", "difficulty", "grade_level", "text", "answer", "hint"]:
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
            SELECT q.id, q.subject, q.skill, q.difficulty, q.grade_level, q.text, q.answer, q.hint, q.options_json, q.active, q.created_at, q.updated_at
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
              a.grade_level AS bekkjarstig,
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
    fields = ["grein","faerni","erfidleiki","bekkjarstig","spurning","svar_nemanda","rett_svar","rett","timi"]
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



def learning_step_row_to_dict(r):
    return {
        "id": r["id"],
        "step_order": r["step_order"],
        "title": r["title"],
        "description": r["description"],
        "step_type": r["step_type"],
        "subject": r["subject"],
        "skill": r["skill"],
        "grade_level": r["grade_level"],
        "target_correct": r["target_correct"],
        "boss_required": bool(r["boss_required"]),
        "reward_coins": r["reward_coins"],
    }


def learning_path_row_to_dict(conn, r, include_steps=True):
    d = dict(r)
    d["active"] = bool(d["active"])
    if include_steps:
        steps = conn.execute("""
            SELECT id, step_order, title, description, step_type, subject, skill, grade_level, target_correct, boss_required, reward_coins
            FROM learning_path_steps
            WHERE path_id=?
            ORDER BY step_order ASC, id ASC
        """, (r["id"],)).fetchall()
        d["steps"] = [learning_step_row_to_dict(s) for s in steps]
    return d


def replace_learning_steps(conn, path_id: int, steps: list[LearningPathStepIn]):
    conn.execute("DELETE FROM learning_path_steps WHERE path_id=?", (path_id,))
    for i, s in enumerate(steps, start=1):
        conn.execute("""
            INSERT INTO learning_path_steps(path_id, step_order, title, description, step_type, subject, skill, grade_level, target_correct, boss_required, reward_coins, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            path_id, i, s.title.strip(), s.description.strip(), s.step_type.strip() or "practice",
            s.subject.strip() or "mixed", s.skill.strip(), s.grade_level, s.target_correct,
            1 if s.boss_required else 0, s.reward_coins, now()
        ))


@app.get("/api/learning-paths")
def assigned_learning_paths(user=Depends(current_user)):
    class_name = user.get("class_name") or ""
    with db() as conn:
        rows = conn.execute("""
            SELECT id, title, description, class_name, grade_level, subject, active, reward_coins, created_at, updated_at
            FROM learning_paths
            WHERE active=1 AND (class_name='' OR class_name=?)
            ORDER BY updated_at DESC
        """, (class_name,)).fetchall()
        return [learning_path_row_to_dict(conn, r, include_steps=True) for r in rows]


@app.get("/api/teacher/learning-paths")
def teacher_list_learning_paths(teacher=Depends(require_teacher)):
    with db() as conn:
        rows = conn.execute("""
            SELECT id, title, description, class_name, grade_level, subject, active, reward_coins, created_at, updated_at
            FROM learning_paths
            ORDER BY updated_at DESC
        """).fetchall()
        return [learning_path_row_to_dict(conn, r, include_steps=True) for r in rows]


@app.post("/api/teacher/learning-paths")
def teacher_create_learning_path(data: LearningPathCreate, teacher=Depends(require_teacher)):
    with db() as conn:
        cur = conn.execute("""
            INSERT INTO learning_paths(title, description, class_name, grade_level, subject, active, reward_coins, created_by, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            data.title.strip(), data.description.strip(), data.class_name.strip(), data.grade_level,
            data.subject.strip() or "mixed", 1 if data.active else 0, data.reward_coins,
            teacher["id"], now(), now()
        ))
        path_id = cur.lastrowid
        steps = data.steps or [
            LearningPathStepIn(title="Æfing", description="Kláraðu fyrstu lotuna.", subject=data.subject, grade_level=data.grade_level, target_correct=5, reward_coins=100),
            LearningPathStepIn(title="Áskorun", description="Sýndu að þú náir færninni.", subject=data.subject, grade_level=data.grade_level, target_correct=8, reward_coins=150),
            LearningPathStepIn(title="Boss", description="Sigraðu lokabossinn.", step_type="boss", subject=data.subject, grade_level=data.grade_level, target_correct=5, boss_required=True, reward_coins=250),
        ]
        replace_learning_steps(conn, path_id, steps)
        row = conn.execute("""
            SELECT id, title, description, class_name, grade_level, subject, active, reward_coins, created_at, updated_at
            FROM learning_paths WHERE id=?
        """, (path_id,)).fetchone()
        return learning_path_row_to_dict(conn, row, include_steps=True)


@app.patch("/api/teacher/learning-paths/{path_id}")
def teacher_update_learning_path(path_id: int, data: LearningPathUpdate, teacher=Depends(require_teacher)):
    with db() as conn:
        exists = conn.execute("SELECT id FROM learning_paths WHERE id=?", (path_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Námsleið fannst ekki.")
        updates = {}
        for field in ["title", "description", "class_name", "grade_level", "subject", "reward_coins"]:
            value = getattr(data, field)
            if value is not None:
                updates[field] = value.strip() if isinstance(value, str) else value
        if data.active is not None:
            updates["active"] = 1 if data.active else 0
        updates["updated_at"] = now()
        sets = ", ".join([f"{k}=?" for k in updates])
        conn.execute(f"UPDATE learning_paths SET {sets} WHERE id=?", list(updates.values()) + [path_id])
        if data.steps is not None:
            replace_learning_steps(conn, path_id, data.steps)
    return {"ok": True}


@app.delete("/api/teacher/learning-paths/{path_id}")
def teacher_delete_learning_path(path_id: int, teacher=Depends(require_teacher)):
    with db() as conn:
        conn.execute("DELETE FROM learning_path_steps WHERE path_id=?", (path_id,))
        conn.execute("DELETE FROM learning_paths WHERE id=?", (path_id,))
    return {"ok": True}



def get_learning_step(conn, step_id: int):
    return conn.execute("""
        SELECT s.id, s.path_id, s.step_order, s.title, s.description, s.step_type, s.subject, s.skill, s.grade_level, s.target_correct, s.boss_required, s.reward_coins,
               p.title AS path_title, p.class_name, p.active
        FROM learning_path_steps s
        JOIN learning_paths p ON p.id = s.path_id
        WHERE s.id=?
    """, (step_id,)).fetchone()


def progress_row_to_dict(r):
    if not r:
        return None
    return {
        "path_id": r["path_id"],
        "step_id": r["step_id"],
        "correct_count": r["correct_count"],
        "answered_count": r["answered_count"],
        "completed": bool(r["completed"]),
        "reward_claimed": bool(r["reward_claimed"]),
        "started_at": r["started_at"],
        "updated_at": r["updated_at"],
        "completed_at": r["completed_at"],
    }


@app.get("/api/learning-path-progress")
def my_learning_path_progress(user=Depends(current_user)):
    with db() as conn:
        rows = conn.execute("""
            SELECT path_id, step_id, correct_count, answered_count, completed, reward_claimed, started_at, updated_at, completed_at
            FROM learning_path_progress
            WHERE user_id=?
        """, (user["id"],)).fetchall()
        return [progress_row_to_dict(r) for r in rows]


@app.post("/api/learning-path-progress/start")
def start_learning_path_step(data: LearningPathClaimIn, user=Depends(current_user)):
    with db() as conn:
        step = get_learning_step(conn, data.step_id)
        if not step or step["path_id"] != data.path_id:
            raise HTTPException(status_code=404, detail="Skref fannst ekki.")
        conn.execute("""
            INSERT OR IGNORE INTO learning_path_progress(user_id, path_id, step_id, correct_count, answered_count, completed, reward_claimed, started_at, updated_at)
            VALUES (?,?,?,?,0,0,0,0,?,?)
        """, (user["id"], data.path_id, data.step_id, now(), now()))
        row = conn.execute("""
            SELECT path_id, step_id, correct_count, answered_count, completed, reward_claimed, started_at, updated_at, completed_at
            FROM learning_path_progress
            WHERE user_id=? AND path_id=? AND step_id=?
        """, (user["id"], data.path_id, data.step_id)).fetchone()
        return progress_row_to_dict(row)


@app.post("/api/learning-path-progress/answer")
def update_learning_path_progress(data: LearningPathProgressIn, user=Depends(current_user)):
    with db() as conn:
        step = get_learning_step(conn, data.step_id)
        if not step or step["path_id"] != data.path_id:
            raise HTTPException(status_code=404, detail="Skref fannst ekki.")
        conn.execute("""
            INSERT OR IGNORE INTO learning_path_progress(user_id, path_id, step_id, correct_count, answered_count, completed, reward_claimed, started_at, updated_at)
            VALUES (?,?,?,?,0,0,0,0,?,?)
        """, (user["id"], data.path_id, data.step_id, now(), now()))
        row = conn.execute("""
            SELECT correct_count, answered_count, completed
            FROM learning_path_progress
            WHERE user_id=? AND path_id=? AND step_id=?
        """, (user["id"], data.path_id, data.step_id)).fetchone()
        new_correct = row["correct_count"] + (1 if data.correct else 0)
        new_answered = row["answered_count"] + (1 if data.answered else 0)
        completed = 1 if (new_correct >= step["target_correct"]) else row["completed"]
        completed_at = now() if completed and not row["completed"] else None
        if completed_at:
            conn.execute("""
                UPDATE learning_path_progress
                SET correct_count=?, answered_count=?, completed=1, updated_at=?, completed_at=?
                WHERE user_id=? AND path_id=? AND step_id=?
            """, (new_correct, new_answered, now(), completed_at, user["id"], data.path_id, data.step_id))
        else:
            conn.execute("""
                UPDATE learning_path_progress
                SET correct_count=?, answered_count=?, completed=?, updated_at=?
                WHERE user_id=? AND path_id=? AND step_id=?
            """, (new_correct, new_answered, completed, now(), user["id"], data.path_id, data.step_id))
        out = conn.execute("""
            SELECT path_id, step_id, correct_count, answered_count, completed, reward_claimed, started_at, updated_at, completed_at
            FROM learning_path_progress
            WHERE user_id=? AND path_id=? AND step_id=?
        """, (user["id"], data.path_id, data.step_id)).fetchone()
        return progress_row_to_dict(out)


@app.post("/api/learning-path-progress/claim")
def claim_learning_path_step_reward(data: LearningPathClaimIn, user=Depends(current_user)):
    with db() as conn:
        step = get_learning_step(conn, data.step_id)
        if not step or step["path_id"] != data.path_id:
            raise HTTPException(status_code=404, detail="Skref fannst ekki.")
        prog = conn.execute("""
            SELECT completed, reward_claimed
            FROM learning_path_progress
            WHERE user_id=? AND path_id=? AND step_id=?
        """, (user["id"], data.path_id, data.step_id)).fetchone()
        if not prog or not prog["completed"]:
            raise HTTPException(status_code=400, detail="Skrefi er ekki lokið.")
        if prog["reward_claimed"]:
            raise HTTPException(status_code=400, detail="Verðlaun hafa þegar verið sótt.")
        p = conn.execute("SELECT coins, xp FROM progress WHERE user_id=?", (user["id"],)).fetchone()
        if not p:
            conn.execute("INSERT INTO progress(user_id, updated_at) VALUES (?,?)", (user["id"], now()))
            p = conn.execute("SELECT coins, xp FROM progress WHERE user_id=?", (user["id"],)).fetchone()
        reward = step["reward_coins"]
        conn.execute("UPDATE progress SET coins=?, xp=?, updated_at=? WHERE user_id=?", (p["coins"] + reward, p["xp"] + max(20, reward // 2), now(), user["id"]))
        conn.execute("""
            UPDATE learning_path_progress SET reward_claimed=1, updated_at=?
            WHERE user_id=? AND path_id=? AND step_id=?
        """, (now(), user["id"], data.path_id, data.step_id))
        return {"ok": True, "coins": reward, "xp": max(20, reward // 2)}


@app.get("/api/teacher/learning-paths/{path_id}/progress")
def teacher_learning_path_progress(path_id: int, teacher=Depends(require_teacher)):
    with db() as conn:
        path = conn.execute("SELECT id, title, class_name FROM learning_paths WHERE id=?", (path_id,)).fetchone()
        if not path:
            raise HTTPException(status_code=404, detail="Námsleið fannst ekki.")
        rows = conn.execute("""
            SELECT u.id AS user_id, u.display_name, u.username, COALESCE(NULLIF(u.class_name,''), 'Óflokkað') AS class_name,
                   s.id AS step_id, s.title AS step_title, s.step_order, s.target_correct,
                   COALESCE(pr.correct_count,0) AS correct_count,
                   COALESCE(pr.answered_count,0) AS answered_count,
                   COALESCE(pr.completed,0) AS completed,
                   COALESCE(pr.reward_claimed,0) AS reward_claimed
            FROM users u
            JOIN learning_paths lp ON lp.id=?
            JOIN learning_path_steps s ON s.path_id=lp.id
            LEFT JOIN learning_path_progress pr ON pr.user_id=u.id AND pr.path_id=lp.id AND pr.step_id=s.id
            WHERE u.role='student' AND (lp.class_name='' OR COALESCE(NULLIF(u.class_name,''), 'Óflokkað')=lp.class_name)
            ORDER BY u.display_name COLLATE NOCASE, s.step_order
        """, (path_id,)).fetchall()
        return [dict(r) for r in rows]



def quiz_row_to_dict(r):
    return dict(r)


@app.post("/api/teacher/path-quizzes")
def teacher_create_path_quiz(data: PathQuizCreateIn, teacher=Depends(require_teacher)):
    with db() as conn:
        path = conn.execute("""
            SELECT id, title, description, class_name, grade_level, subject
            FROM learning_paths WHERE id=?
        """, (data.path_id,)).fetchone()
        if not path:
            raise HTTPException(status_code=404, detail="Námsleið fannst ekki.")
        title = data.title or f"Lokapróf - {path['title']}"
        cur = conn.execute("""
            INSERT INTO path_quizzes(path_id, title, description, class_name, grade_level, subject, question_count, pass_percent, active, created_by, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data.path_id, title.strip(), data.description.strip() or f"Lokapróf úr námsleið: {path['title']}",
            path["class_name"], path["grade_level"], path["subject"], data.question_count,
            data.pass_percent, 1 if data.active else 0, teacher["id"], now(), now()
        ))
        row = conn.execute("SELECT * FROM path_quizzes WHERE id=?", (cur.lastrowid,)).fetchone()
        return quiz_row_to_dict(row)


@app.get("/api/path-quizzes")
def assigned_path_quizzes(user=Depends(current_user)):
    class_name = user.get("class_name") or ""
    with db() as conn:
        rows = conn.execute("""
            SELECT * FROM path_quizzes
            WHERE active=1 AND (class_name='' OR class_name=?)
            ORDER BY updated_at DESC
        """, (class_name,)).fetchall()
        out = []
        for r in rows:
            d = quiz_row_to_dict(r)
            best = conn.execute("""
                SELECT MAX(percent) AS best_percent, COUNT(*) AS attempts
                FROM path_quiz_attempts
                WHERE quiz_id=? AND user_id=?
            """, (r["id"], user["id"])).fetchone()
            d["best_percent"] = best["best_percent"] if best and best["best_percent"] is not None else None
            d["attempts"] = best["attempts"] if best else 0
            out.append(d)
        return out


@app.get("/api/path-quizzes/{quiz_id}/questions")
def get_path_quiz_questions(quiz_id: int, user=Depends(current_user)):
    with db() as conn:
        quiz = conn.execute("SELECT * FROM path_quizzes WHERE id=? AND active=1", (quiz_id,)).fetchone()
        if not quiz:
            raise HTTPException(status_code=404, detail="Próf fannst ekki.")
        steps = conn.execute("""
            SELECT subject, skill, grade_level FROM learning_path_steps
            WHERE path_id=?
        """, (quiz["path_id"],)).fetchall()

    # Use static question bank as source for quiz questions
    bank_path = APP_DIR / "static" / "questions.json"
    data = json.loads(bank_path.read_text(encoding="utf-8"))
    all_q = data.get("questions", [])
    skills = {s["skill"] for s in steps if s["skill"]}
    subjects = {s["subject"] for s in steps if s["subject"] and s["subject"] != "mixed"}
    grade = quiz["grade_level"]

    pool = [
        q for q in all_q
        if int(q.get("grade_level", grade)) == int(grade)
        and (not subjects or q.get("subject") in subjects or quiz["subject"] == "mixed")
        and (not skills or q.get("skill") in skills or len(skills) < 2)
        and q.get("options")
    ]
    if len(pool) < quiz["question_count"]:
        pool = [
            q for q in all_q
            if int(q.get("grade_level", grade)) == int(grade)
            and (quiz["subject"] == "mixed" or q.get("subject") == quiz["subject"] or not quiz["subject"])
            and q.get("options")
        ]
    if len(pool) < quiz["question_count"]:
        pool = [q for q in all_q if q.get("options")]

    import random
    random.shuffle(pool)
    selected = pool[:quiz["question_count"]]
    # do not send hint only if you want exam mode stricter
    return [{
        "id": q["id"],
        "subject": q.get("subject"),
        "skill": q.get("skill", "almennt"),
        "grade_level": q.get("grade_level", grade),
        "text": q.get("text"),
        "options": q.get("options") or [],
    } for q in selected]


@app.post("/api/path-quizzes/submit")
def submit_path_quiz(data: PathQuizSubmitIn, user=Depends(current_user)):
    with db() as conn:
        quiz = conn.execute("SELECT * FROM path_quizzes WHERE id=? AND active=1", (data.quiz_id,)).fetchone()
        if not quiz:
            raise HTTPException(status_code=404, detail="Próf fannst ekki.")

    bank_path = APP_DIR / "static" / "questions.json"
    qdata = json.loads(bank_path.read_text(encoding="utf-8"))
    answer_map = {q["id"]: str(q.get("answer")) for q in qdata.get("questions", [])}
    detailed = []
    score = 0
    total = 0
    for a in data.answers:
        qid = str(a.get("id"))
        given = str(a.get("answer", ""))
        correct_answer = answer_map.get(qid)
        if correct_answer is None:
            continue
        correct = normalize_answer(given) == normalize_answer(correct_answer)
        score += 1 if correct else 0
        total += 1
        detailed.append({"id": qid, "answer": given, "correct_answer": correct_answer, "correct": correct})
    percent = round((score / total) * 100) if total else 0
    passed = 1 if percent >= quiz["pass_percent"] else 0
    with db() as conn:
        conn.execute("""
            INSERT INTO path_quiz_attempts(quiz_id, user_id, score, total, percent, passed, answers_json, created_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (data.quiz_id, user["id"], score, total, percent, passed, json.dumps(detailed, ensure_ascii=False), now()))
        # Reward pass once by adding small reward. Multiple passes still recorded.
        if passed:
            p = conn.execute("SELECT coins, xp FROM progress WHERE user_id=?", (user["id"],)).fetchone()
            if p:
                conn.execute("UPDATE progress SET coins=?, xp=?, updated_at=? WHERE user_id=?", (p["coins"] + 250, p["xp"] + 150, now(), user["id"]))
    return {"score": score, "total": total, "percent": percent, "passed": bool(passed), "answers": detailed}


@app.get("/api/teacher/path-quizzes")
def teacher_list_path_quizzes(teacher=Depends(require_teacher)):
    with db() as conn:
        rows = conn.execute("""
            SELECT q.*, lp.title AS path_title
            FROM path_quizzes q
            JOIN learning_paths lp ON lp.id=q.path_id
            ORDER BY q.updated_at DESC
        """).fetchall()
        return [dict(r) for r in rows]


@app.get("/api/teacher/path-quizzes/{quiz_id}/results")
def teacher_path_quiz_results(quiz_id: int, teacher=Depends(require_teacher)):
    with db() as conn:
        rows = conn.execute("""
            SELECT u.display_name, u.username, COALESCE(NULLIF(u.class_name,''), 'Óflokkað') AS class_name,
                   a.score, a.total, a.percent, a.passed, a.created_at
            FROM path_quiz_attempts a
            JOIN users u ON u.id=a.user_id
            WHERE a.quiz_id=?
            ORDER BY a.created_at DESC
        """, (quiz_id,)).fetchall()
        return [dict(r) for r in rows]


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
