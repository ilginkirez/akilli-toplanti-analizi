import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MeetingStore:
    def __init__(self, db_path: str = "src/storage/meetings.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS meetings (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    scheduled_start TEXT NOT NULL,
                    scheduled_end TEXT NOT NULL,
                    status TEXT NOT NULL,
                    organizer_name TEXT NOT NULL,
                    organizer_email TEXT NOT NULL,
                    organizer_role TEXT,
                    organizer_department TEXT,
                    organizer_avatar TEXT,
                    session_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS meeting_participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meeting_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT,
                    role TEXT,
                    department TEXT,
                    avatar TEXT,
                    response_status TEXT NOT NULL DEFAULT 'pending',
                    position INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS meeting_agenda_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meeting_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    duration INTEGER NOT NULL,
                    completed INTEGER NOT NULL DEFAULT 0,
                    position INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
                );
                """
            )

    def _generate_meeting_id(self) -> str:
        return f"m-{uuid4().hex[:8]}"

    def _fetch_participants(self, connection: sqlite3.Connection, meeting_id: str) -> List[Dict[str, Any]]:
        rows = connection.execute(
            """
            SELECT name, email, role, department, avatar, response_status, position
            FROM meeting_participants
            WHERE meeting_id = ?
            ORDER BY position ASC, id ASC
            """,
            (meeting_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _fetch_agenda(self, connection: sqlite3.Connection, meeting_id: str) -> List[Dict[str, Any]]:
        rows = connection.execute(
            """
            SELECT id, title, duration, completed, position
            FROM meeting_agenda_items
            WHERE meeting_id = ?
            ORDER BY position ASC, id ASC
            """,
            (meeting_id,),
        ).fetchall()
        agenda: List[Dict[str, Any]] = []
        for row in rows:
            agenda.append(
                {
                    "id": f"agenda-{row['id']}",
                    "title": row["title"],
                    "duration": row["duration"],
                    "completed": bool(row["completed"]),
                    "position": row["position"],
                }
            )
        return agenda

    def _row_to_meeting(self, connection: sqlite3.Connection, row: sqlite3.Row) -> Dict[str, Any]:
        meeting_id = row["id"]
        return {
            "id": meeting_id,
            "title": row["title"],
            "description": row["description"],
            "scheduled_start": row["scheduled_start"],
            "scheduled_end": row["scheduled_end"],
            "status": row["status"],
            "session_id": row["session_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "organizer": {
                "name": row["organizer_name"],
                "email": row["organizer_email"],
                "role": row["organizer_role"] or "member",
                "department": row["organizer_department"] or "Genel",
                "avatar": row["organizer_avatar"],
            },
            "participants": self._fetch_participants(connection, meeting_id),
            "agenda": self._fetch_agenda(connection, meeting_id),
        }

    def create_meeting(
        self,
        *,
        title: str,
        description: Optional[str],
        scheduled_start: str,
        scheduled_end: str,
        organizer: Dict[str, Any],
        participants: List[Dict[str, Any]],
        agenda: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        meeting_id = self._generate_meeting_id()
        now = _utc_now_iso()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO meetings (
                    id, title, description, scheduled_start, scheduled_end, status,
                    organizer_name, organizer_email, organizer_role, organizer_department,
                    organizer_avatar, session_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meeting_id,
                    title,
                    description,
                    scheduled_start,
                    scheduled_end,
                    "upcoming",
                    organizer.get("name") or "Unknown",
                    organizer.get("email") or "",
                    organizer.get("role"),
                    organizer.get("department"),
                    organizer.get("avatar"),
                    None,
                    now,
                    now,
                ),
            )

            for index, participant in enumerate(participants):
                connection.execute(
                    """
                    INSERT INTO meeting_participants (
                        meeting_id, name, email, role, department, avatar, response_status, position
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        meeting_id,
                        participant.get("name") or "Unknown",
                        participant.get("email"),
                        participant.get("role"),
                        participant.get("department"),
                        participant.get("avatar"),
                        participant.get("response_status") or "pending",
                        index,
                    ),
                )

            for index, item in enumerate(agenda):
                connection.execute(
                    """
                    INSERT INTO meeting_agenda_items (
                        meeting_id, title, duration, completed, position
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        meeting_id,
                        item.get("title") or "",
                        int(item.get("duration") or 0),
                        1 if item.get("completed") else 0,
                        index,
                    ),
                )

            row = connection.execute(
                "SELECT * FROM meetings WHERE id = ?",
                (meeting_id,),
            ).fetchone()
            assert row is not None
            return self._row_to_meeting(connection, row)

    def list_meetings(self, status: Optional[str] = None, query: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM meetings"
        clauses: List[str] = []
        params: List[Any] = []

        if status:
            clauses.append("status = ?")
            params.append(status)

        if query:
            clauses.append("(LOWER(title) LIKE ? OR LOWER(COALESCE(description, '')) LIKE ?)")
            token = f"%{query.strip().lower()}%"
            params.extend([token, token])

        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY scheduled_start DESC, created_at DESC"

        with self._lock, self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
            return [self._row_to_meeting(connection, row) for row in rows]

    def get_meeting(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM meetings WHERE id = ?",
                (meeting_id,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_meeting(connection, row)

    def update_session_link(self, meeting_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, self._connect() as connection:
            now = _utc_now_iso()
            connection.execute(
                """
                UPDATE meetings
                SET session_id = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (session_id, "in-progress", now, meeting_id),
            )
            row = connection.execute(
                "SELECT * FROM meetings WHERE id = ?",
                (meeting_id,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_meeting(connection, row)

    def update_status(self, meeting_id: str, status: str) -> Optional[Dict[str, Any]]:
        with self._lock, self._connect() as connection:
            now = _utc_now_iso()
            connection.execute(
                """
                UPDATE meetings
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, now, meeting_id),
            )
            row = connection.execute(
                "SELECT * FROM meetings WHERE id = ?",
                (meeting_id,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_meeting(connection, row)

    def get_by_session_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM meetings WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_meeting(connection, row)


meeting_store = MeetingStore()
