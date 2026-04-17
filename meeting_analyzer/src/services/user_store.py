import hashlib
import hmac
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4


DEFAULT_DB_PATH = "src/storage/meetings.db"
DEFAULT_TOKEN_TTL_DAYS = 30
DEFAULT_DEMO_PASSWORD = "demo1234"
DEFAULT_COMPANY_CODE = "COMPANY"

DEFAULT_SEED_USERS = [
    {
        "name": "Ahmet Yilmaz",
        "email": "ahmet.yilmaz@company.com",
        "avatar": "https://i.pravatar.cc/150?img=12",
        "role": "manager",
        "department": "Urun Gelistirme",
    },
    {
        "name": "Zeynep Kara",
        "email": "zeynep.kara@company.com",
        "avatar": "https://i.pravatar.cc/150?img=45",
        "role": "member",
        "department": "Tasarim",
    },
    {
        "name": "Mehmet Demir",
        "email": "mehmet.demir@company.com",
        "avatar": "https://i.pravatar.cc/150?img=33",
        "role": "member",
        "department": "Muhendislik",
    },
    {
        "name": "Ayse Sahin",
        "email": "ayse.sahin@company.com",
        "avatar": "https://i.pravatar.cc/150?img=47",
        "role": "admin",
        "department": "Operasyon",
    },
    {
        "name": "Can Ozturk",
        "email": "can.ozturk@company.com",
        "avatar": "https://i.pravatar.cc/150?img=15",
        "role": "member",
        "department": "Muhendislik",
    },
    {
        "name": "Elif Arslan",
        "email": "elif.arslan@company.com",
        "avatar": "https://i.pravatar.cc/150?img=23",
        "role": "member",
        "department": "Pazarlama",
    },
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _normalize_company_code(company_code: Optional[str]) -> Optional[str]:
    if not company_code:
        return None
    cleaned = "".join(ch for ch in company_code.strip().upper() if ch.isalnum() or ch in {"-", "_"})
    return cleaned or None


def _hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    active_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        active_salt.encode("utf-8"),
        120_000,
    )
    return active_salt, digest.hex()


def _verify_password(password: str, *, salt: str, password_hash: str) -> bool:
    _, digest = _hash_password(password, salt=salt)
    return hmac.compare_digest(digest, password_hash)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class UserStore:
    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()
        self.seed_default_data()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS companies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    company_code TEXT NOT NULL UNIQUE,
                    domain TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    company_id TEXT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    avatar TEXT,
                    role TEXT NOT NULL,
                    department TEXT NOT NULL,
                    account_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS auth_tokens (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    last_used_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )

    def _serialize_user(self, row: sqlite3.Row) -> Dict[str, Any]:
        company_id = row["company_id"]
        company_code = row["company_code"] if "company_code" in row.keys() else None
        company_name = row["company_name"] if "company_name" in row.keys() else None
        return {
            "id": row["id"],
            "name": row["name"],
            "email": row["email"],
            "avatar": row["avatar"],
            "role": row["role"],
            "department": row["department"],
            "company_id": company_id,
            "company_code": company_code,
            "company_name": company_name,
            "account_type": row["account_type"],
            "status": row["status"],
        }

    def _fetch_user_row(self, connection: sqlite3.Connection, *, user_id: Optional[str] = None, email: Optional[str] = None) -> Optional[sqlite3.Row]:
        if user_id:
            return connection.execute(
                """
                SELECT users.*, companies.company_code, companies.name AS company_name
                FROM users
                LEFT JOIN companies ON companies.id = users.company_id
                WHERE users.id = ?
                """,
                (user_id,),
            ).fetchone()
        if email:
            return connection.execute(
                """
                SELECT users.*, companies.company_code, companies.name AS company_name
                FROM users
                LEFT JOIN companies ON companies.id = users.company_id
                WHERE users.email = ?
                """,
                (_normalize_email(email),),
            ).fetchone()
        return None

    def _get_or_create_company(
        self,
        connection: sqlite3.Connection,
        *,
        company_code: str,
        company_name: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> sqlite3.Row:
        normalized_code = _normalize_company_code(company_code)
        if normalized_code is None:
            raise ValueError("company_code required")

        row = connection.execute(
            "SELECT * FROM companies WHERE company_code = ?",
            (normalized_code,),
        ).fetchone()
        if row is not None:
            return row

        company_id = f"cmp-{uuid4().hex[:8]}"
        now = _utc_now_iso()
        connection.execute(
            """
            INSERT INTO companies (id, name, company_code, domain, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                company_id,
                (company_name or normalized_code).strip() or normalized_code,
                normalized_code,
                domain,
                now,
                now,
            ),
        )
        row = connection.execute(
            "SELECT * FROM companies WHERE id = ?",
            (company_id,),
        ).fetchone()
        assert row is not None
        return row

    def seed_default_data(self) -> None:
        with self._lock, self._connect() as connection:
            company = self._get_or_create_company(
                connection,
                company_code=DEFAULT_COMPANY_CODE,
                company_name="Demo Company",
                domain="company.com",
            )
            for user in DEFAULT_SEED_USERS:
                email = _normalize_email(user["email"])
                existing = connection.execute(
                    "SELECT id FROM users WHERE email = ?",
                    (email,),
                ).fetchone()
                if existing is not None:
                    continue

                salt, password_hash = _hash_password(DEFAULT_DEMO_PASSWORD)
                now = _utc_now_iso()
                connection.execute(
                    """
                    INSERT INTO users (
                        id, company_id, name, email, password_salt, password_hash,
                        avatar, role, department, account_type, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"usr-{uuid4().hex[:8]}",
                        company["id"],
                        user["name"],
                        email,
                        salt,
                        password_hash,
                        user["avatar"],
                        user["role"],
                        user["department"],
                        "company_member",
                        "active",
                        now,
                        now,
                    ),
                )

    def register_user(
        self,
        *,
        name: str,
        email: str,
        password: str,
        department: Optional[str] = None,
        role: Optional[str] = None,
        avatar: Optional[str] = None,
        company_code: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_name = name.strip()
        normalized_email = _normalize_email(email)
        if not normalized_name:
            raise ValueError("name required")
        if not normalized_email:
            raise ValueError("email required")
        if len(password) < 8:
            raise ValueError("password must be at least 8 characters")

        with self._lock, self._connect() as connection:
            existing = self._fetch_user_row(connection, email=normalized_email)
            if existing is not None:
                raise ValueError("email already registered")

            company_row = None
            account_type = "independent"
            resolved_role = role or "member"

            normalized_company_code = _normalize_company_code(company_code)
            if normalized_company_code:
                company_row = self._get_or_create_company(
                    connection,
                    company_code=normalized_company_code,
                    company_name=company_name,
                    domain=normalized_email.split("@", 1)[1] if "@" in normalized_email else None,
                )
                account_type = "company_member"
                member_count = connection.execute(
                    "SELECT COUNT(*) FROM users WHERE company_id = ?",
                    (company_row["id"],),
                ).fetchone()[0]
                if member_count == 0 and role is None:
                    resolved_role = "manager"

            salt, password_hash = _hash_password(password)
            user_id = f"usr-{uuid4().hex[:8]}"
            now = _utc_now_iso()
            connection.execute(
                """
                INSERT INTO users (
                    id, company_id, name, email, password_salt, password_hash,
                    avatar, role, department, account_type, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    company_row["id"] if company_row else None,
                    normalized_name,
                    normalized_email,
                    salt,
                    password_hash,
                    avatar,
                    resolved_role if resolved_role in {"admin", "manager", "member"} else "member",
                    (department or "Genel").strip() or "Genel",
                    account_type,
                    "active",
                    now,
                    now,
                ),
            )
            row = self._fetch_user_row(connection, user_id=user_id)
            assert row is not None
            return self._serialize_user(row)

    def authenticate_user(self, *, email: str, password: str) -> Optional[Dict[str, Any]]:
        normalized_email = _normalize_email(email)
        with self._lock, self._connect() as connection:
            row = self._fetch_user_row(connection, email=normalized_email)
            if row is None:
                return None
            if row["status"] != "active":
                return None
            if not _verify_password(
                password,
                salt=row["password_salt"],
                password_hash=row["password_hash"],
            ):
                return None
            return self._serialize_user(row)

    def create_auth_token(self, user_id: str, *, ttl_days: int = DEFAULT_TOKEN_TTL_DAYS) -> str:
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        now = _utc_now()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO auth_tokens (id, user_id, token_hash, created_at, last_used_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    f"tok-{uuid4().hex[:8]}",
                    user_id,
                    token_hash,
                    now.isoformat(),
                    now.isoformat(),
                    (now + timedelta(days=ttl_days)).isoformat(),
                ),
            )
        return raw_token

    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        token_hash = _hash_token(token)
        now = _utc_now()
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    users.*,
                    companies.company_code,
                    companies.name AS company_name,
                    auth_tokens.id AS auth_token_id,
                    auth_tokens.expires_at
                FROM auth_tokens
                JOIN users ON users.id = auth_tokens.user_id
                LEFT JOIN companies ON companies.id = users.company_id
                WHERE auth_tokens.token_hash = ?
                """,
                (token_hash,),
            ).fetchone()
            if row is None:
                return None
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at <= now:
                connection.execute(
                    "DELETE FROM auth_tokens WHERE id = ?",
                    (row["auth_token_id"],),
                )
                return None
            connection.execute(
                "UPDATE auth_tokens SET last_used_at = ? WHERE id = ?",
                (now.isoformat(), row["auth_token_id"]),
            )
            return self._serialize_user(row)

    def list_company_members(self, company_id: Optional[str], *, query: Optional[str] = None) -> List[Dict[str, Any]]:
        if not company_id:
            return []

        sql = """
            SELECT users.*, companies.company_code, companies.name AS company_name
            FROM users
            LEFT JOIN companies ON companies.id = users.company_id
            WHERE users.company_id = ? AND users.status = 'active'
        """
        params: List[Any] = [company_id]

        if query:
            token = f"%{query.strip().lower()}%"
            sql += " AND (LOWER(users.name) LIKE ? OR LOWER(users.email) LIKE ? OR LOWER(users.department) LIKE ?)"
            params.extend([token, token, token])

        sql += " ORDER BY users.name ASC"

        with self._lock, self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
            return [self._serialize_user(row) for row in rows]


user_store = UserStore()
