import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import httpx
from app.core.config import settings
from app.db.models import Project, StoredAnalysisSummary, SearchResultItem
from app.models.schemas import (
    ShiftlyAnalysisResult,
    AnalysisStats,
    KeyPointItem,
    ActionItem,
    DecisionItem,
    ImportantDateItem,
    PendingDecisionItem,
    SourceReference,
)
from app.services.chunking_service import merge_analysis_results

import tempfile

import concurrent.futures

logger = logging.getLogger("shiftly.db")

# Isolated SQLite path for automated unit tests only. Production uses Supabase PostgreSQL.
LOCAL_DB_PATH = os.getenv("SQLITE_DB_PATH") or os.path.join(tempfile.gettempdir(), "shiftly_test_project_memory.db")


class DatabaseConfigurationError(Exception):
    """Raised when required database configuration (e.g. Supabase credentials) is missing in runtime."""
    pass


class ProjectNotFoundError(Exception):
    pass


class AnalysisNotFoundError(Exception):
    pass


class DatabaseOperationError(Exception):
    """Raised when a database operation fails."""
    pass


class DatabaseTimeoutError(DatabaseOperationError):
    """Raised when a database operation times out."""
    pass


class DatabaseConnectionError(DatabaseOperationError):
    """Raised when connecting to the database fails."""
    pass


def _init_local_db(clear: bool = False):
    """Initializes the local SQLite database schema for isolated automated tests."""
    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()

    if clear:
        conn.execute("PRAGMA foreign_keys = OFF")
        for tbl in ["pending_decisions", "important_dates", "decisions", "action_items", "key_points", "analyses", "projects"]:
            cursor.execute(f"DROP TABLE IF EXISTS {tbl}")

    conn.execute("PRAGMA foreign_keys = ON")

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        user_id TEXT
    );


    CREATE TABLE IF NOT EXISTS analyses (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        source_type TEXT,
        source_name TEXT,
        summary TEXT NOT NULL,
        stats TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS key_points (
        id TEXT PRIMARY KEY,
        analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        topic TEXT,
        source_reference TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS action_items (
        id TEXT PRIMARY KEY,
        analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        responsible_person TEXT,
        due_date TEXT,
        status TEXT DEFAULT 'Pending',
        priority TEXT DEFAULT 'Normal',
        source_reference TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS decisions (
        id TEXT PRIMARY KEY,
        analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        decision_type TEXT DEFAULT 'Approval',
        approved_by TEXT,
        date TEXT,
        source_reference TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS important_dates (
        id TEXT PRIMARY KEY,
        analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
        label TEXT NOT NULL,
        date TEXT NOT NULL,
        description TEXT,
        source_reference TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS pending_decisions (
        id TEXT PRIMARY KEY,
        analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        source_reference TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    cursor.execute("PRAGMA table_info(projects)")
    cols = [r[1] for r in cursor.fetchall()]
    if "user_id" not in cols:
        cursor.execute("ALTER TABLE projects ADD COLUMN user_id TEXT")
    conn.commit()
    conn.close()


class ProjectMemoryRepository:
    """
    Project Memory Repository.
    Production / Runtime: Uses Supabase PostgreSQL PostgREST as the Single Source of Truth.
    Automated Testing: SQLite is available ONLY when explicitly activated for isolated tests.
    Zero split-brain: When Supabase is configured, local SQLite is NEVER read from or written to.
    """

    def __init__(self, use_sqlite_for_tests: Optional[bool] = None):
        if use_sqlite_for_tests is not None:
            self.use_sqlite_for_tests = use_sqlite_for_tests
        else:
            self.use_sqlite_for_tests = os.getenv("TEST_USE_SQLITE", "false").lower() == "true"
        self._http_client = httpx.Client(
            timeout=10.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )
        self._reload_config()

    def _client(self) -> httpx.Client:
        if not hasattr(self, "_http_client") or self._http_client.is_closed:
            self._http_client = httpx.Client(
                timeout=10.0,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
            )
        return self._http_client

    def _reload_config(self):
        self.supabase_url = (settings.SUPABASE_URL or os.getenv("SUPABASE_URL", "")).rstrip('/')
        self.supabase_key = (
            getattr(settings, "SUPABASE_PUBLISHABLE_KEY", None)
            or os.getenv("SUPABASE_PUBLISHABLE_KEY")
            or settings.SUPABASE_ANON_KEY
            or os.getenv("SUPABASE_ANON_KEY", "")
        )
        self.is_supabase_configured = bool(self.supabase_url and self.supabase_key)

    def _get_supabase_headers(self, user_token: Optional[str] = None) -> dict:
        auth_bearer = user_token if (user_token and not user_token.startswith("test-token")) else self.supabase_key
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {auth_bearer}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    @property
    def _active_sqlite_mode(self) -> bool:
        if settings.ENVIRONMENT == "production":
            return False
        return self.use_sqlite_for_tests or os.getenv("TEST_USE_SQLITE", "false").lower() == "true"

    def _ensure_configured(self):
        self._reload_config()
        if self._active_sqlite_mode:
            return
        if not self.is_supabase_configured:
            raise DatabaseConfigurationError(
                "Supabase configuration is missing. Project Memory requires SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in backend/.env."
            )

    # =========================================================================
    # PROJECT OPERATIONS
    # =========================================================================

    def create_project(self, name: str, description: Optional[str] = None, user_id: Optional[str] = None, user_token: Optional[str] = None) -> Project:
        self._ensure_configured()
        project_id = str(uuid.uuid4())
        now_str = datetime.utcnow().isoformat() + "Z"

        if not self._active_sqlite_mode:
            url = f"{self.supabase_url}/rest/v1/projects"
            payload = {
                "id": project_id,
                "name": name,
                "description": description,
                "created_at": now_str,
                "updated_at": now_str,
            }
            if user_id:
                payload["user_id"] = user_id
            try:
                res = self._client().post(url, headers=self._get_supabase_headers(user_token), json=payload, timeout=10.0)
                if res.status_code in (200, 201):
                    return Project(
                        id=project_id,
                        name=name,
                        description=description,
                        created_at=now_str,
                        updated_at=now_str,
                        analyses_count=0,
                        user_id=user_id,
                    )
                raise DatabaseOperationError(f"Supabase create_project failed (HTTP {res.status_code}): {res.text}")
            except httpx.TimeoutException as te:
                raise DatabaseTimeoutError("Database operation timed out. Please try again.") from te
            except httpx.RequestError as e:
                raise DatabaseConnectionError(f"Network error connecting to Supabase: {str(e)}") from e

        return self._save_project_locally(project_id, name, description, now_str, user_id)

    def _save_project_locally(self, project_id: str, name: str, description: Optional[str], now_str: str, user_id: Optional[str] = None) -> Project:
        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "INSERT INTO projects (id, name, description, created_at, updated_at, user_id) VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET name=excluded.name, description=excluded.description, updated_at=excluded.updated_at, user_id=excluded.user_id",
                (project_id, name, description, now_str, now_str, user_id),
            )
            conn.commit()
            return Project(
                id=project_id,
                name=name,
                description=description,
                created_at=now_str,
                updated_at=now_str,
                analyses_count=0,
                user_id=user_id,
            )
        except Exception as e:
            raise DatabaseOperationError(f"Failed to create project in test DB: {str(e)}") from e
        finally:
            conn.close()

    def list_projects(self, user_id: Optional[str] = None, user_token: Optional[str] = None) -> List[Project]:
        self._ensure_configured()

        if not self._active_sqlite_mode:
            url = f"{self.supabase_url}/rest/v1/projects?select=*,analyses(count)&order=created_at.desc"
            if user_id:
                url = f"{self.supabase_url}/rest/v1/projects?user_id=eq.{user_id}&select=*,analyses(count)&order=created_at.desc"
            try:
                res = self._client().get(url, headers=self._get_supabase_headers(user_token), timeout=10.0)
                if res.status_code == 200:
                    projects_data = res.json()
                    projects: List[Project] = []
                    for row in projects_data:
                        count = row.get("analyses", [{}])[0].get("count", 0) if isinstance(row.get("analyses"), list) and row.get("analyses") else 0
                        projects.append(
                            Project(
                                id=row["id"],
                                name=row["name"],
                                description=row.get("description"),
                                created_at=row["created_at"],
                                updated_at=row["updated_at"],
                                analyses_count=count,
                                user_id=row.get("user_id"),
                            )
                        )
                    return projects
                raise DatabaseOperationError(f"Supabase list_projects failed (HTTP {res.status_code}): {res.text}")
            except httpx.TimeoutException as te:
                raise DatabaseTimeoutError("Database operation timed out. Please try again.") from te
            except httpx.RequestError as e:
                raise DatabaseConnectionError(f"Network error connecting to Supabase: {str(e)}") from e

        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("""
                    SELECT p.id, p.name, p.description, p.created_at, p.updated_at, COUNT(a.id) as count, p.user_id
                    FROM projects p
                    LEFT JOIN analyses a ON p.id = a.project_id
                    WHERE p.user_id = ?
                    GROUP BY p.id
                    ORDER BY p.created_at DESC
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT p.id, p.name, p.description, p.created_at, p.updated_at, COUNT(a.id) as count, p.user_id
                    FROM projects p
                    LEFT JOIN analyses a ON p.id = a.project_id
                    GROUP BY p.id
                    ORDER BY p.created_at DESC
                """)
            rows = cursor.fetchall()
            return [
                Project(
                    id=r[0],
                    name=r[1],
                    description=r[2],
                    created_at=r[3],
                    updated_at=r[4],
                    analyses_count=r[5],
                    user_id=r[6] if len(r) > 6 else None,
                )
                for r in rows
            ]
        finally:
            conn.close()

    def get_project(self, project_id: str, user_id: Optional[str] = None, user_token: Optional[str] = None) -> Optional[Project]:
        self._ensure_configured()

        if not self._active_sqlite_mode:
            url = f"{self.supabase_url}/rest/v1/projects?id=eq.{project_id}&select=*,analyses(count)"
            if user_id:
                url = f"{self.supabase_url}/rest/v1/projects?id=eq.{project_id}&user_id=eq.{user_id}&select=*,analyses(count)"
            try:
                res = self._client().get(url, headers=self._get_supabase_headers(user_token), timeout=10.0)
                if res.status_code == 200:
                    rows = res.json()
                    if not rows:
                        return None
                    row = rows[0]
                    count = row.get("analyses", [{}])[0].get("count", 0) if isinstance(row.get("analyses"), list) and row.get("analyses") else 0
                    return Project(
                        id=row["id"],
                        name=row["name"],
                        description=row.get("description"),
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                        analyses_count=count,
                        user_id=row.get("user_id"),
                    )
                raise DatabaseOperationError(f"Supabase get_project failed (HTTP {res.status_code}): {res.text}")
            except httpx.TimeoutException as te:
                raise DatabaseTimeoutError("Database operation timed out. Please try again.") from te
            except httpx.RequestError as e:
                raise DatabaseConnectionError(f"Network error connecting to Supabase: {str(e)}") from e

        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("""
                    SELECT p.id, p.name, p.description, p.created_at, p.updated_at, COUNT(a.id) as count, p.user_id
                    FROM projects p
                    LEFT JOIN analyses a ON p.id = a.project_id
                    WHERE p.id = ? AND p.user_id = ?
                    GROUP BY p.id
                """, (project_id, user_id))
            else:
                cursor.execute("""
                    SELECT p.id, p.name, p.description, p.created_at, p.updated_at, COUNT(a.id) as count, p.user_id
                    FROM projects p
                    LEFT JOIN analyses a ON p.id = a.project_id
                    WHERE p.id = ?
                    GROUP BY p.id
                """, (project_id,))
            r = cursor.fetchone()
            if not r:
                return None
            return Project(
                id=r[0],
                name=r[1],
                description=r[2],
                created_at=r[3],
                updated_at=r[4],
                analyses_count=r[5],
                user_id=r[6] if len(r) > 6 else None,
            )
        finally:
            conn.close()

    def delete_project(self, project_id: str, user_id: Optional[str] = None, user_token: Optional[str] = None) -> bool:
        self._ensure_configured()
        project = self.get_project(project_id, user_id=user_id, user_token=user_token)
        if not project:
            raise ProjectNotFoundError(f"Project '{project_id}' not found.")

        if not self._active_sqlite_mode:
            url = f"{self.supabase_url}/rest/v1/projects?id=eq.{project_id}"
            if user_id:
                url = f"{self.supabase_url}/rest/v1/projects?id=eq.{project_id}&user_id=eq.{user_id}"
            try:
                res = self._client().delete(url, headers=self._get_supabase_headers(user_token), timeout=10.0)
                if res.status_code in (200, 204):
                    return True
                raise DatabaseOperationError(f"Supabase delete_project failed (HTTP {res.status_code}): {res.text}")
            except httpx.TimeoutException as te:
                raise DatabaseTimeoutError("Database operation timed out. Please try again.") from te
            except httpx.RequestError as e:
                raise DatabaseConnectionError(f"Network error connecting to Supabase: {str(e)}") from e

        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            if user_id:
                conn.execute("DELETE FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id))
            else:
                conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    def update_project_name(self, project_id: str, name: str, user_id: Optional[str] = None, user_token: Optional[str] = None) -> Project:
        """
        Updates an existing project's name in-place without altering its ID, attached analyses, or intelligence.
        Enforces project ownership and avoids unnecessary database writes if the name is unchanged.
        """
        self._ensure_configured()
        project = self.get_project(project_id, user_id=user_id, user_token=user_token)
        if not project:
            raise ProjectNotFoundError(f"Project '{project_id}' not found.")

        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Project name cannot be empty or whitespace only.")

        if project.name == clean_name:
            return project

        now_str = datetime.utcnow().isoformat() + "Z"

        if not self._active_sqlite_mode:
            url = f"{self.supabase_url}/rest/v1/projects?id=eq.{project_id}"
            if user_id:
                url = f"{self.supabase_url}/rest/v1/projects?id=eq.{project_id}&user_id=eq.{user_id}"
            try:
                headers = {**self._get_supabase_headers(user_token), "Prefer": "return=representation"}
                res = self._client().patch(url, headers=headers, json={"name": clean_name, "updated_at": now_str}, timeout=10.0)
                if res.status_code in (200, 204):
                    return Project(
                        id=project.id,
                        name=clean_name,
                        description=project.description,
                        created_at=project.created_at,
                        updated_at=now_str,
                        analyses_count=project.analyses_count,
                        user_id=project.user_id,
                    )
                raise DatabaseOperationError(f"Supabase update_project_name failed (HTTP {res.status_code}): {res.text}")
            except httpx.TimeoutException as te:
                raise DatabaseTimeoutError("Database operation timed out. Please try again.") from te
            except httpx.RequestError as e:
                raise DatabaseConnectionError(f"Network error connecting to Supabase: {str(e)}") from e

        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    "UPDATE projects SET name = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                    (clean_name, now_str, project_id, user_id),
                )
            else:
                cursor.execute(
                    "UPDATE projects SET name = ?, updated_at = ? WHERE id = ?",
                    (clean_name, now_str, project_id),
                )
            conn.commit()
            return Project(
                id=project.id,
                name=clean_name,
                description=project.description,
                created_at=project.created_at,
                updated_at=now_str,
                analyses_count=project.analyses_count,
                user_id=project.user_id,
            )
        finally:
            conn.close()

    def delete_analysis(self, project_id: str, analysis_id: str, user_id: Optional[str] = None, user_token: Optional[str] = None) -> bool:
        self._ensure_configured()
        project = self.get_project(project_id, user_id=user_id, user_token=user_token)
        if not project:
            raise ProjectNotFoundError(f"Project '{project_id}' not found.")

        if not self._active_sqlite_mode:
            chk_url = f"{self.supabase_url}/rest/v1/analyses?id=eq.{analysis_id}&project_id=eq.{project_id}&select=id"
            try:
                chk_res = self._client().get(chk_url, headers=self._get_supabase_headers(user_token), timeout=10.0)
                if chk_res.status_code != 200 or not chk_res.json():
                    raise AnalysisNotFoundError(f"Analysis '{analysis_id}' not found in project '{project_id}'.")

                del_url = f"{self.supabase_url}/rest/v1/analyses?id=eq.{analysis_id}&project_id=eq.{project_id}"
                res = self._client().delete(del_url, headers=self._get_supabase_headers(user_token), timeout=10.0)
                if res.status_code in (200, 204):
                    return True
                raise DatabaseOperationError(f"Supabase delete_analysis failed (HTTP {res.status_code}): {res.text}")
            except httpx.TimeoutException as te:
                raise DatabaseTimeoutError("Database operation timed out. Please try again.") from te
            except httpx.RequestError as e:
                raise DatabaseConnectionError(f"Network error connecting to Supabase: {str(e)}") from e

        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM analyses WHERE id = ? AND project_id = ?", (analysis_id, project_id))
            if not cursor.fetchone():
                raise AnalysisNotFoundError(f"Analysis '{analysis_id}' not found in project '{project_id}'.")
            cursor.execute("DELETE FROM analyses WHERE id = ? AND project_id = ?", (analysis_id, project_id))
            conn.commit()
            return True
        finally:
            conn.close()

    def update_analysis_title(self, project_id: str, analysis_id: str, title: str, user_id: Optional[str] = None, user_token: Optional[str] = None) -> StoredAnalysisSummary:
        """
        Updates an existing analysis title in-place without altering its ID, parent project,
        or any child intelligence records (key points, actions, decisions, dates, pending decisions).
        Enforces project ownership and avoids unnecessary database writes if the title is unchanged.
        """
        self._ensure_configured()
        project = self.get_project(project_id, user_id=user_id, user_token=user_token)
        if not project:
            raise ProjectNotFoundError(f"Project '{project_id}' not found.")

        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Analysis title cannot be empty or whitespace only.")

        analysis = self.get_analysis(project_id, analysis_id, user_id=user_id, user_token=user_token)
        if not analysis:
            raise AnalysisNotFoundError(f"Analysis '{analysis_id}' not found in project '{project_id}'.")

        if analysis.title == clean_title:
            summaries = self.list_project_analyses(project_id, user_id=user_id, user_token=user_token)
            for s in summaries:
                if s.id == analysis_id:
                    return s
            return StoredAnalysisSummary(
                id=analysis_id,
                project_id=project_id,
                title=clean_title,
                summary=analysis.summary,
                created_at=analysis.analyzedAt,
                key_points_count=len(analysis.keyPoints),
                actions_count=len(analysis.actions),
                decisions_count=len(analysis.decisions),
                important_dates_count=len(analysis.importantDates),
                pending_decisions_count=len(analysis.pendingDecisions),
            )

        now_str = datetime.utcnow().isoformat() + "Z"

        if not self._active_sqlite_mode:
            url = f"{self.supabase_url}/rest/v1/analyses?id=eq.{analysis_id}&project_id=eq.{project_id}"
            try:
                headers = {**self._get_supabase_headers(user_token), "Prefer": "return=representation"}
                res = self._client().patch(url, headers=headers, json={"title": clean_title, "updated_at": now_str}, timeout=10.0)
                if res.status_code in (200, 204):
                    return StoredAnalysisSummary(
                        id=analysis_id,
                        project_id=project_id,
                        title=clean_title,
                        summary=analysis.summary,
                        created_at=analysis.analyzedAt,
                        key_points_count=len(analysis.keyPoints),
                        actions_count=len(analysis.actions),
                        decisions_count=len(analysis.decisions),
                        important_dates_count=len(analysis.importantDates),
                        pending_decisions_count=len(analysis.pendingDecisions),
                    )
                raise DatabaseOperationError(f"Supabase update_analysis_title failed (HTTP {res.status_code}): {res.text}")
            except httpx.TimeoutException as te:
                raise DatabaseTimeoutError("Database operation timed out. Please try again.") from te
            except httpx.RequestError as e:
                raise DatabaseConnectionError(f"Network error connecting to Supabase: {str(e)}") from e

        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE analyses SET title = ?, updated_at = ? WHERE id = ? AND project_id = ?",
                (clean_title, now_str, analysis_id, project_id),
            )
            conn.commit()
            return StoredAnalysisSummary(
                id=analysis_id,
                project_id=project_id,
                title=clean_title,
                summary=analysis.summary,
                created_at=analysis.analyzedAt,
                key_points_count=len(analysis.keyPoints),
                actions_count=len(analysis.actions),
                decisions_count=len(analysis.decisions),
                important_dates_count=len(analysis.importantDates),
                pending_decisions_count=len(analysis.pendingDecisions),
            )
        finally:
            conn.close()

    # =========================================================================
    # ANALYSIS PERSISTENCE & RETRIEVAL
    # =========================================================================

    def save_analysis(self, project_id: str, result: ShiftlyAnalysisResult, user_id: Optional[str] = None, user_token: Optional[str] = None) -> StoredAnalysisSummary:
        self._ensure_configured()
        project = self.get_project(project_id, user_id=user_id, user_token=user_token)
        if not project:
            raise ProjectNotFoundError(f"Project with ID '{project_id}' does not exist.")

        analysis_id = result.id if result.id else str(uuid.uuid4())
        now_str = datetime.utcnow().isoformat() + "Z"

        source_type = "Chat Export"
        source_name = None
        for kp in result.keyPoints:
            if kp.source:
                source_type = kp.source.sourceType
                source_name = kp.source.sourceName
                break

        if not self._active_sqlite_mode:
            try:
                headers = {**self._get_supabase_headers(user_token), "Prefer": "resolution=merge-duplicates"}
                analysis_payload = {
                    "id": analysis_id,
                    "project_id": project_id,
                    "title": result.title,
                    "source_type": source_type,
                    "source_name": source_name,
                    "summary": result.summary,
                    "stats": result.stats.model_dump(),
                    "created_at": now_str,
                    "updated_at": now_str,
                }
                a_res = self._client().post(f"{self.supabase_url}/rest/v1/analyses", headers=headers, json=analysis_payload, timeout=10.0)
                if a_res.status_code not in (200, 201):
                    raise DatabaseOperationError(f"Supabase save_analysis failed (HTTP {a_res.status_code}): {a_res.text}")

                # Delete previous children if overwriting
                del_hdr = self._get_supabase_headers(user_token)
                self._client().delete(f"{self.supabase_url}/rest/v1/key_points?analysis_id=eq.{analysis_id}", headers=del_hdr, timeout=10.0)
                self._client().delete(f"{self.supabase_url}/rest/v1/action_items?analysis_id=eq.{analysis_id}", headers=del_hdr, timeout=10.0)
                self._client().delete(f"{self.supabase_url}/rest/v1/decisions?analysis_id=eq.{analysis_id}", headers=del_hdr, timeout=10.0)
                self._client().delete(f"{self.supabase_url}/rest/v1/important_dates?analysis_id=eq.{analysis_id}", headers=del_hdr, timeout=10.0)
                self._client().delete(f"{self.supabase_url}/rest/v1/pending_decisions?analysis_id=eq.{analysis_id}", headers=del_hdr, timeout=10.0)

                # Batch insert Key Points
                if result.keyPoints:
                    kp_records = [
                        {
                            "id": f"{analysis_id}_{kp.id}",
                            "analysis_id": analysis_id,
                            "content": kp.point,
                            "topic": kp.category,
                            "source_reference": kp.source.model_dump(),
                            "created_at": now_str,
                        }
                        for kp in result.keyPoints
                    ]
                    kp_res = self._client().post(f"{self.supabase_url}/rest/v1/key_points", headers=headers, json=kp_records, timeout=10.0)
                    if kp_res.status_code not in (200, 201):
                        raise DatabaseOperationError(f"Supabase save key_points failed (HTTP {kp_res.status_code}): {kp_res.text}")

                # Batch insert Action Items
                if result.actions:
                    act_records = [
                        {
                            "id": f"{analysis_id}_{act.id}",
                            "analysis_id": analysis_id,
                            "content": act.action,
                            "responsible_person": act.responsiblePerson,
                            "due_date": act.deadline,
                            "status": "Pending",
                            "priority": act.priority or "Normal",
                            "source_reference": act.source.model_dump(),
                            "created_at": now_str,
                        }
                        for act in result.actions
                    ]
                    act_res = self._client().post(f"{self.supabase_url}/rest/v1/action_items", headers=headers, json=act_records, timeout=10.0)
                    if act_res.status_code not in (200, 201):
                        raise DatabaseOperationError(f"Supabase save action_items failed (HTTP {act_res.status_code}): {act_res.text}")

                # Batch insert Decisions
                if result.decisions:
                    dec_records = [
                        {
                            "id": f"{analysis_id}_{dec.id}",
                            "analysis_id": analysis_id,
                            "content": dec.decision,
                            "decision_type": "Approval",
                            "approved_by": dec.approvedBy,
                            "date": dec.date,
                            "source_reference": dec.source.model_dump(),
                            "created_at": now_str,
                        }
                        for dec in result.decisions
                    ]
                    dec_res = self._client().post(f"{self.supabase_url}/rest/v1/decisions", headers=headers, json=dec_records, timeout=10.0)
                    if dec_res.status_code not in (200, 201):
                        raise DatabaseOperationError(f"Supabase save decisions failed (HTTP {dec_res.status_code}): {dec_res.text}")

                # Batch insert Important Dates
                if result.importantDates:
                    dt_records = [
                        {
                            "id": f"{analysis_id}_{dt.id}",
                            "analysis_id": analysis_id,
                            "label": dt.title,
                            "date": dt.date,
                            "description": dt.significance,
                            "source_reference": dt.source.model_dump(),
                            "created_at": now_str,
                        }
                        for dt in result.importantDates
                    ]
                    dt_res = self._client().post(f"{self.supabase_url}/rest/v1/important_dates", headers=headers, json=dt_records, timeout=10.0)
                    if dt_res.status_code not in (200, 201):
                        raise DatabaseOperationError(f"Supabase save important_dates failed (HTTP {dt_res.status_code}): {dt_res.text}")

                # Batch insert Pending Decisions
                if result.pendingDecisions:
                    pd_records = [
                        {
                            "id": f"{analysis_id}_{pd.id}",
                            "analysis_id": analysis_id,
                            "content": pd.decision,
                            "status": pd.status or "Pending",
                            "source_reference": pd.source.model_dump(),
                            "created_at": now_str,
                        }
                        for pd in result.pendingDecisions
                    ]
                    pd_res = self._client().post(f"{self.supabase_url}/rest/v1/pending_decisions", headers=headers, json=pd_records, timeout=10.0)
                    if pd_res.status_code not in (200, 201):
                        raise DatabaseOperationError(f"Supabase save pending_decisions failed (HTTP {pd_res.status_code}): {pd_res.text}")

                return StoredAnalysisSummary(
                    id=analysis_id,
                    project_id=project_id,
                    title=result.title,
                    source_type=source_type,
                    source_name=source_name,
                    summary=result.summary,
                    created_at=now_str,
                    key_points_count=len(result.keyPoints),
                    actions_count=len(result.actions),
                    decisions_count=len(result.decisions),
                    important_dates_count=len(result.importantDates),
                    pending_decisions_count=len(result.pendingDecisions),
                )
            except httpx.TimeoutException as te:
                raise DatabaseTimeoutError("Database operation timed out. Please try again.") from te
            except httpx.RequestError as e:
                raise DatabaseConnectionError(f"Network error connecting to Supabase: {str(e)}") from e

        # Test SQLite path
        stats_json = result.stats.model_dump_json()
        return self._save_analysis_locally(project_id, analysis_id, result, source_type, source_name, stats_json, now_str)

    def _save_analysis_locally(self, project_id: str, analysis_id: str, result: ShiftlyAnalysisResult, source_type: str, source_name: Optional[str], stats_json: str, now_str: str) -> StoredAnalysisSummary:
        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO analyses (id, project_id, title, source_type, source_name, summary, stats, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    project_id=excluded.project_id,
                    title=excluded.title,
                    summary=excluded.summary,
                    stats=excluded.stats,
                    updated_at=excluded.updated_at
            """, (analysis_id, project_id, result.title, source_type, source_name, result.summary, stats_json, now_str, now_str))

            cursor.execute("DELETE FROM key_points WHERE analysis_id = ?", (analysis_id,))
            cursor.execute("DELETE FROM action_items WHERE analysis_id = ?", (analysis_id,))
            cursor.execute("DELETE FROM decisions WHERE analysis_id = ?", (analysis_id,))
            cursor.execute("DELETE FROM important_dates WHERE analysis_id = ?", (analysis_id,))
            cursor.execute("DELETE FROM pending_decisions WHERE analysis_id = ?", (analysis_id,))

            for kp in result.keyPoints:
                src_json = kp.source.model_dump_json()
                kp_row_id = f"{analysis_id}_{kp.id}"
                cursor.execute(
                    "INSERT INTO key_points (id, analysis_id, content, topic, source_reference, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (kp_row_id, analysis_id, kp.point, kp.category, src_json, now_str),
                )

            for act in result.actions:
                src_json = act.source.model_dump_json()
                act_row_id = f"{analysis_id}_{act.id}"
                cursor.execute(
                    "INSERT INTO action_items (id, analysis_id, content, responsible_person, due_date, status, priority, source_reference, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (act_row_id, analysis_id, act.action, act.responsiblePerson, act.deadline, "Pending", act.priority or "Normal", src_json, now_str),
                )

            for dec in result.decisions:
                src_json = dec.source.model_dump_json()
                dec_row_id = f"{analysis_id}_{dec.id}"
                cursor.execute(
                    "INSERT INTO decisions (id, analysis_id, content, decision_type, approved_by, date, source_reference, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (dec_row_id, analysis_id, dec.decision, "Approval", dec.approvedBy, dec.date, src_json, now_str),
                )

            for dt in result.importantDates:
                src_json = dt.source.model_dump_json()
                dt_row_id = f"{analysis_id}_{dt.id}"
                cursor.execute(
                    "INSERT INTO important_dates (id, analysis_id, label, date, description, source_reference, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (dt_row_id, analysis_id, dt.title, dt.date, dt.significance, src_json, now_str),
                )

            for pd in result.pendingDecisions:
                src_json = pd.source.model_dump_json()
                pd_row_id = f"{analysis_id}_{pd.id}"
                cursor.execute(
                    "INSERT INTO pending_decisions (id, analysis_id, content, status, source_reference, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (pd_row_id, analysis_id, pd.decision, pd.status or "Pending", src_json, now_str),
                )

            conn.commit()
            return StoredAnalysisSummary(
                id=analysis_id,
                project_id=project_id,
                title=result.title,
                source_type=source_type,
                source_name=source_name,
                summary=result.summary,
                created_at=now_str,
                key_points_count=len(result.keyPoints),
                actions_count=len(result.actions),
                decisions_count=len(result.decisions),
                important_dates_count=len(result.importantDates),
                pending_decisions_count=len(result.pendingDecisions),
            )
        except Exception as e:
            conn.rollback()
            raise DatabaseOperationError(f"Failed to save analysis to test DB: {str(e)}") from e
        finally:
            conn.close()

    def list_project_analyses(self, project_id: str, user_id: Optional[str] = None, user_token: Optional[str] = None) -> List[StoredAnalysisSummary]:
        self._ensure_configured()
        project = self.get_project(project_id, user_id=user_id, user_token=user_token)
        if not project:
            raise ProjectNotFoundError(f"Project '{project_id}' not found.")

        if not self._active_sqlite_mode:
            url = f"{self.supabase_url}/rest/v1/analyses?project_id=eq.{project_id}&select=*,key_points(count),action_items(count),decisions(count),important_dates(count),pending_decisions(count)&order=created_at.desc"
            try:
                res = self._client().get(url, headers=self._get_supabase_headers(user_token), timeout=10.0)
                if res.status_code == 200:
                    rows = res.json()
                    analyses: List[StoredAnalysisSummary] = []
                    for r in rows:
                        kp_c = r.get("key_points", [{}])[0].get("count", 0) if isinstance(r.get("key_points"), list) and r.get("key_points") else 0
                        act_c = r.get("action_items", [{}])[0].get("count", 0) if isinstance(r.get("action_items"), list) and r.get("action_items") else 0
                        dec_c = r.get("decisions", [{}])[0].get("count", 0) if isinstance(r.get("decisions"), list) and r.get("decisions") else 0
                        dt_c = r.get("important_dates", [{}])[0].get("count", 0) if isinstance(r.get("important_dates"), list) and r.get("important_dates") else 0
                        pd_c = r.get("pending_decisions", [{}])[0].get("count", 0) if isinstance(r.get("pending_decisions"), list) and r.get("pending_decisions") else 0
                        analyses.append(
                            StoredAnalysisSummary(
                                id=r["id"],
                                project_id=r["project_id"],
                                title=r["title"],
                                source_type=r.get("source_type"),
                                source_name=r.get("source_name"),
                                summary=r["summary"],
                                created_at=r["created_at"],
                                key_points_count=kp_c,
                                actions_count=act_c,
                                decisions_count=dec_c,
                                important_dates_count=dt_c,
                                pending_decisions_count=pd_c,
                            )
                        )
                    return analyses
                raise DatabaseOperationError(f"Supabase list_project_analyses failed (HTTP {res.status_code}): {res.text}")
            except httpx.TimeoutException as te:
                raise DatabaseTimeoutError("Database operation timed out. Please try again.") from te
            except httpx.RequestError as e:
                raise DatabaseConnectionError(f"Network error connecting to Supabase: {str(e)}") from e

        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    a.id, a.project_id, a.title, a.source_type, a.source_name, a.summary, a.created_at,
                    (SELECT COUNT(*) FROM key_points kp WHERE kp.analysis_id = a.id),
                    (SELECT COUNT(*) FROM action_items act WHERE act.analysis_id = a.id),
                    (SELECT COUNT(*) FROM decisions dec WHERE dec.analysis_id = a.id),
                    (SELECT COUNT(*) FROM important_dates dt WHERE dt.analysis_id = a.id),
                    (SELECT COUNT(*) FROM pending_decisions pd WHERE pd.analysis_id = a.id)
                FROM analyses a
                WHERE a.project_id = ?
                ORDER BY a.created_at DESC
            """, (project_id,))
            rows = cursor.fetchall()
            return [
                StoredAnalysisSummary(
                    id=r[0],
                    project_id=r[1],
                    title=r[2],
                    source_type=r[3],
                    source_name=r[4],
                    summary=r[5],
                    created_at=r[6],
                    key_points_count=r[7],
                    actions_count=r[8],
                    decisions_count=r[9],
                    important_dates_count=r[10],
                    pending_decisions_count=r[11],
                )
                for r in rows
            ]
        finally:
            conn.close()

    def get_analysis(self, project_id: str, analysis_id: str, user_id: Optional[str] = None, user_token: Optional[str] = None) -> Optional[ShiftlyAnalysisResult]:
        self._ensure_configured()
        project = self.get_project(project_id, user_id=user_id, user_token=user_token)
        if not project:
            return None

        if not self._active_sqlite_mode:
            url = f"{self.supabase_url}/rest/v1/analyses?id=eq.{analysis_id}&project_id=eq.{project_id}&select=*,key_points(*),action_items(*),decisions(*),important_dates(*),pending_decisions(*)"
            try:
                res = self._client().get(url, headers=self._get_supabase_headers(user_token), timeout=10.0)
                if res.status_code == 200:
                    rows = res.json()
                    if not rows:
                        return None
                    r = rows[0]
                    stats = AnalysisStats.model_validate_json(r["stats"]) if isinstance(r["stats"], str) else AnalysisStats.model_validate(r["stats"])
                    prefix = f"{analysis_id}_"
                    key_points = [
                        KeyPointItem(
                            id=k["id"][len(prefix):] if k["id"].startswith(prefix) else k["id"],
                            point=k["content"],
                            category=k.get("topic"),
                            source=SourceReference.model_validate_json(k["source_reference"]) if isinstance(k["source_reference"], str) else SourceReference.model_validate(k["source_reference"]),
                        )
                        for k in r.get("key_points", [])
                    ]
                    actions = [
                        ActionItem(
                            id=a["id"][len(prefix):] if a["id"].startswith(prefix) else a["id"],
                            action=a["content"],
                            responsiblePerson=a.get("responsible_person") or "Unassigned",
                            deadline=a.get("due_date"),
                            priority=a.get("priority") or "Normal",
                            source=SourceReference.model_validate_json(a["source_reference"]) if isinstance(a["source_reference"], str) else SourceReference.model_validate(a["source_reference"]),
                        )
                        for a in r.get("action_items", [])
                    ]
                    decisions = [
                        DecisionItem(
                            id=d["id"][len(prefix):] if d["id"].startswith(prefix) else d["id"],
                            decision=d["content"],
                            approvedBy=d.get("approved_by") or "Unknown",
                            date=d.get("date"),
                            source=SourceReference.model_validate_json(d["source_reference"]) if isinstance(d["source_reference"], str) else SourceReference.model_validate(d["source_reference"]),
                        )
                        for d in r.get("decisions", [])
                    ]
                    important_dates = [
                        ImportantDateItem(
                            id=dt["id"][len(prefix):] if dt["id"].startswith(prefix) else dt["id"],
                            title=dt["label"],
                            date=dt["date"],
                            significance=dt.get("description") or "",
                            source=SourceReference.model_validate_json(dt["source_reference"]) if isinstance(dt["source_reference"], str) else SourceReference.model_validate(dt["source_reference"]),
                        )
                        for dt in r.get("important_dates", [])
                    ]
                    pending_decisions = [
                        PendingDecisionItem(
                            id=pd["id"][len(prefix):] if pd["id"].startswith(prefix) else pd["id"],
                            decision=pd["content"],
                            status=pd.get("status") or "Pending",
                            source=SourceReference.model_validate_json(pd["source_reference"]) if isinstance(pd["source_reference"], str) else SourceReference.model_validate(pd["source_reference"]),
                        )
                        for pd in r.get("pending_decisions", [])
                    ]
                    return ShiftlyAnalysisResult(
                        id=r["id"],
                        title=r["title"],
                        analyzedAt=r["created_at"],
                        stats=stats,
                        summary=r["summary"],
                        keyPoints=key_points,
                        actions=actions,
                        decisions=decisions,
                        importantDates=important_dates,
                        pendingDecisions=pending_decisions,
                    )
                raise DatabaseOperationError(f"Supabase get_analysis failed (HTTP {res.status_code}): {res.text}")
            except httpx.TimeoutException as te:
                raise DatabaseTimeoutError("Database operation timed out. Please try again.") from te
            except httpx.RequestError as e:
                raise DatabaseConnectionError(f"Network error connecting to Supabase: {str(e)}") from e

        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, summary, stats, created_at FROM analyses WHERE id = ? AND project_id = ?", (analysis_id, project_id))
            row = cursor.fetchone()
            if not row:
                return None

            aid, title, summary, stats_raw, created_at = row
            stats = AnalysisStats.model_validate_json(stats_raw)
            prefix = f"{analysis_id}_"

            cursor.execute("SELECT id, content, topic, source_reference FROM key_points WHERE analysis_id = ?", (analysis_id,))
            kp_rows = cursor.fetchall()
            key_points = [
                KeyPointItem(
                    id=k[0][len(prefix):] if k[0].startswith(prefix) else k[0],
                    point=k[1],
                    category=k[2],
                    source=SourceReference.model_validate_json(k[3]),
                )
                for k in kp_rows
            ]

            cursor.execute("SELECT id, content, responsible_person, due_date, priority, source_reference FROM action_items WHERE analysis_id = ?", (analysis_id,))
            act_rows = cursor.fetchall()
            actions = [
                ActionItem(
                    id=a[0][len(prefix):] if a[0].startswith(prefix) else a[0],
                    action=a[1],
                    responsiblePerson=a[2] or "Unassigned",
                    deadline=a[3],
                    priority=a[4] or "Normal",
                    source=SourceReference.model_validate_json(a[5]),
                )
                for a in act_rows
            ]

            cursor.execute("SELECT id, content, approved_by, date, source_reference FROM decisions WHERE analysis_id = ?", (analysis_id,))
            dec_rows = cursor.fetchall()
            decisions = [
                DecisionItem(
                    id=d[0][len(prefix):] if d[0].startswith(prefix) else d[0],
                    decision=d[1],
                    approvedBy=d[2] or "Unknown",
                    date=d[3],
                    source=SourceReference.model_validate_json(d[4]),
                )
                for d in dec_rows
            ]

            cursor.execute("SELECT id, label, date, description, source_reference FROM important_dates WHERE analysis_id = ?", (analysis_id,))
            dt_rows = cursor.fetchall()
            important_dates = [
                ImportantDateItem(
                    id=t[0][len(prefix):] if t[0].startswith(prefix) else t[0],
                    title=t[1],
                    date=t[2],
                    significance=t[3] or "",
                    source=SourceReference.model_validate_json(t[4]),
                )
                for t in dt_rows
            ]

            cursor.execute("SELECT id, content, status, source_reference FROM pending_decisions WHERE analysis_id = ?", (analysis_id,))
            pd_rows = cursor.fetchall()
            pending_decisions = [
                PendingDecisionItem(
                    id=p[0][len(prefix):] if p[0].startswith(prefix) else p[0],
                    decision=p[1],
                    status=p[2] or "Pending",
                    source=SourceReference.model_validate_json(p[3]),
                )
                for p in pd_rows
            ]

            return ShiftlyAnalysisResult(
                id=aid,
                title=title,
                analyzedAt=created_at,
                stats=stats,
                summary=summary,
                keyPoints=key_points,
                actions=actions,
                decisions=decisions,
                importantDates=important_dates,
                pendingDecisions=pending_decisions,
            )
        finally:
            conn.close()

    # =========================================================================
    # DETERMINISTIC SEARCH
    # =========================================================================

    def search_project_memory(self, project_id: str, query: str, user_id: Optional[str] = None, user_token: Optional[str] = None) -> List[SearchResultItem]:
        self._ensure_configured()
        project = self.get_project(project_id, user_id=user_id, user_token=user_token)
        if not project:
            raise ProjectNotFoundError(f"Project '{project_id}' not found.")
        clean_q = query.strip().lower()
        if not clean_q:
            return []

        if not self._active_sqlite_mode:
            results: List[SearchResultItem] = []
            headers = self._get_supabase_headers(user_token)

            urls = [
                ("Key Point", f"{self.supabase_url}/rest/v1/key_points?select=content,source_reference,created_at,analyses!inner(id,title,project_id)&analyses.project_id=eq.{project_id}&content=ilike.*{clean_q}*"),
                ("Action", f"{self.supabase_url}/rest/v1/action_items?select=content,responsible_person,source_reference,created_at,analyses!inner(id,title,project_id)&analyses.project_id=eq.{project_id}&or=(content.ilike.*{clean_q}*,responsible_person.ilike.*{clean_q}*)"),
                ("Decision", f"{self.supabase_url}/rest/v1/decisions?select=content,approved_by,source_reference,created_at,analyses!inner(id,title,project_id)&analyses.project_id=eq.{project_id}&or=(content.ilike.*{clean_q}*,approved_by.ilike.*{clean_q}*)"),
                ("Date", f"{self.supabase_url}/rest/v1/important_dates?select=label,date,description,source_reference,created_at,analyses!inner(id,title,project_id)&analyses.project_id=eq.{project_id}&or=(label.ilike.*{clean_q}*,date.ilike.*{clean_q}*,description.ilike.*{clean_q}*)"),
                ("Summary", f"{self.supabase_url}/rest/v1/analyses?select=id,title,summary,created_at&project_id=eq.{project_id}&summary=ilike.*{clean_q}*"),
                ("Pending Decision", f"{self.supabase_url}/rest/v1/pending_decisions?select=content,source_reference,created_at,analyses!inner(id,title,project_id)&analyses.project_id=eq.{project_id}&content=ilike.*{clean_q}*"),
            ]

            def fetch_sub_search(item_type, url):
                res = self._client().get(url, headers=headers, timeout=10.0)
                if res.status_code == 200:
                    return item_type, res.json()
                return item_type, []

            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                    futures = [executor.submit(fetch_sub_search, item_type, url) for item_type, url in urls]
                    for f in concurrent.futures.as_completed(futures):
                        item_type, data = f.result()
                        for r in data:
                            if item_type == "Summary":
                                results.append(
                                    SearchResultItem(
                                        analysis_id=r["id"],
                                        analysis_title=r["title"],
                                        item_type="Summary",
                                        content=r["summary"],
                                        source_reference=None,
                                        created_at=r["created_at"],
                                    )
                                )
                            elif item_type == "Action":
                                src = SourceReference.model_validate_json(r["source_reference"]) if isinstance(r["source_reference"], str) else SourceReference.model_validate(r["source_reference"])
                                results.append(
                                    SearchResultItem(
                                        analysis_id=r["analyses"]["id"],
                                        analysis_title=r["analyses"]["title"],
                                        item_type="Action",
                                        content=f"{r['content']} ({r['responsible_person']})" if r.get('responsible_person') else r['content'],
                                        source_reference=src,
                                        created_at=r["created_at"],
                                    )
                                )
                            elif item_type == "Date":
                                src = SourceReference.model_validate_json(r["source_reference"]) if isinstance(r["source_reference"], str) else SourceReference.model_validate(r["source_reference"])
                                results.append(
                                    SearchResultItem(
                                        analysis_id=r["analyses"]["id"],
                                        analysis_title=r["analyses"]["title"],
                                        item_type="Date",
                                        content=f"{r['label']} ({r['date']}) — {r['description']}",
                                        source_reference=src,
                                        created_at=r["created_at"],
                                    )
                                )
                            else:
                                src = SourceReference.model_validate_json(r["source_reference"]) if isinstance(r["source_reference"], str) else SourceReference.model_validate(r["source_reference"])
                                results.append(
                                    SearchResultItem(
                                        analysis_id=r["analyses"]["id"],
                                        analysis_title=r["analyses"]["title"],
                                        item_type=item_type,
                                        content=r["content"],
                                        source_reference=src,
                                        created_at=r["created_at"],
                                    )
                                )

                return results
            except httpx.TimeoutException as te:
                raise DatabaseTimeoutError("Database operation timed out. Please try again.") from te
            except httpx.RequestError as e:
                raise DatabaseConnectionError(f"Network error connecting to Supabase: {str(e)}") from e

        # Test SQLite path
        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            cursor = conn.cursor()
            results: List[SearchResultItem] = []
            param = f"%{clean_q}%"

            cursor.execute("""
                SELECT a.id, a.title, kp.content, kp.source_reference, kp.created_at
                FROM key_points kp
                JOIN analyses a ON a.id = kp.analysis_id
                WHERE a.project_id = ? AND (LOWER(kp.content) LIKE ? OR LOWER(COALESCE(kp.topic, '')) LIKE ?)
                ORDER BY kp.created_at DESC
            """, (project_id, param, param))
            for r in cursor.fetchall():
                results.append(
                    SearchResultItem(
                        analysis_id=r[0],
                        analysis_title=r[1],
                        item_type="Key Point",
                        content=r[2],
                        source_reference=SourceReference.model_validate_json(r[3]),
                        created_at=r[4],
                    )
                )

            cursor.execute("""
                SELECT a.id, a.title, act.content, act.responsible_person, act.source_reference, act.created_at
                FROM action_items act
                JOIN analyses a ON a.id = act.analysis_id
                WHERE a.project_id = ? AND (LOWER(act.content) LIKE ? OR LOWER(COALESCE(act.responsible_person, '')) LIKE ?)
                ORDER BY act.created_at DESC
            """, (project_id, param, param))
            for r in cursor.fetchall():
                content_display = f"{r[2]} ({r[3]})" if r[3] else r[2]
                results.append(
                    SearchResultItem(
                        analysis_id=r[0],
                        analysis_title=r[1],
                        item_type="Action",
                        content=content_display,
                        source_reference=SourceReference.model_validate_json(r[4]),
                        created_at=r[5],
                    )
                )

            cursor.execute("""
                SELECT a.id, a.title, dec.content, dec.approved_by, dec.source_reference, dec.created_at
                FROM decisions dec
                JOIN analyses a ON a.id = dec.analysis_id
                WHERE a.project_id = ? AND (LOWER(dec.content) LIKE ? OR LOWER(COALESCE(dec.approved_by, '')) LIKE ?)
                ORDER BY dec.created_at DESC
            """, (project_id, param, param))
            for r in cursor.fetchall():
                results.append(
                    SearchResultItem(
                        analysis_id=r[0],
                        analysis_title=r[1],
                        item_type="Decision",
                        content=r[2],
                        source_reference=SourceReference.model_validate_json(r[4]),
                        created_at=r[5],
                    )
                )

            cursor.execute("""
                SELECT a.id, a.title, dt.label, dt.date, dt.description, dt.source_reference, dt.created_at
                FROM important_dates dt
                JOIN analyses a ON a.id = dt.analysis_id
                WHERE a.project_id = ? AND (LOWER(dt.label) LIKE ? OR LOWER(dt.date) LIKE ? OR LOWER(COALESCE(dt.description, '')) LIKE ?)
                ORDER BY dt.created_at DESC
            """, (project_id, param, param, param))
            for r in cursor.fetchall():
                results.append(
                    SearchResultItem(
                        analysis_id=r[0],
                        analysis_title=r[1],
                        item_type="Date",
                        content=f"{r[2]} ({r[3]})" if r[3] else r[2],
                        details=r[4],
                        source_reference=SourceReference.model_validate_json(r[5]),
                        created_at=r[6],
                    )
                )

            cursor.execute("""
                SELECT a.id, a.title, a.summary, a.created_at
                FROM analyses a
                WHERE a.project_id = ? AND LOWER(a.summary) LIKE ?
                ORDER BY a.created_at DESC
            """, (project_id, param))
            for r in cursor.fetchall():
                results.append(
                    SearchResultItem(
                        analysis_id=r[0],
                        analysis_title=r[1],
                        item_type="Summary",
                        content=r[2],
                        source_reference=None,
                        created_at=r[3],
                    )
                )

            cursor.execute("""
                SELECT a.id, a.title, pd.content, pd.source_reference, pd.created_at
                FROM pending_decisions pd
                JOIN analyses a ON a.id = pd.analysis_id
                WHERE a.project_id = ? AND LOWER(pd.content) LIKE ?
                ORDER BY pd.created_at DESC
            """, (project_id, param))
            for r in cursor.fetchall():
                results.append(
                    SearchResultItem(
                        analysis_id=r[0],
                        analysis_title=r[1],
                        item_type="Pending Decision",
                        content=r[2],
                        source_reference=SourceReference.model_validate_json(r[3]),
                        created_at=r[4],
                    )
                )

            return results
        finally:
            conn.close()

    def get_user_storage_stats(self, user_id: str, user_token: Optional[str] = None, storage_limit_bytes: Optional[int] = None) -> Dict[str, Any]:
        """Calculates real storage and usage statistics for an authenticated user."""
        self._ensure_configured()

        if not self._active_sqlite_mode:
            url = f"{self.supabase_url}/rest/v1/projects?user_id=eq.{user_id}&select=id,analyses(id,summary,title,key_points(id,content),action_items(id,content),decisions(id,content),important_dates(id,label,description),pending_decisions(id,content))"
            try:
                res = self._client().get(url, headers=self._get_supabase_headers(user_token), timeout=10.0)
                if res.status_code == 200:
                    data = res.json()
                    projects_count = len(data)
                    analyses_count = 0
                    key_points_count = 0
                    action_items_count = 0
                    decisions_count = 0
                    important_dates_count = 0
                    pending_decisions_count = 0
                    text_bytes = 0

                    for proj in data:
                        analyses = proj.get("analyses", [])
                        analyses_count += len(analyses)
                        for a in analyses:
                            text_bytes += len(a.get("summary", "") or "") + len(a.get("title", "") or "")
                            kps = a.get("key_points", [])
                            key_points_count += len(kps)
                            for kp in kps:
                                text_bytes += len(kp.get("content", "") or "")
                            acts = a.get("action_items", [])
                            action_items_count += len(acts)
                            for act in acts:
                                text_bytes += len(act.get("content", "") or "")
                            decs = a.get("decisions", [])
                            decisions_count += len(decs)
                            for dec in decs:
                                text_bytes += len(dec.get("content", "") or "")
                            dts = a.get("important_dates", [])
                            important_dates_count += len(dts)
                            for dt in dts:
                                text_bytes += len(dt.get("label", "") or "") + len(dt.get("description", "") or "")
                            pds = a.get("pending_decisions", [])
                            pending_decisions_count += len(pds)
                            for pd in pds:
                                text_bytes += len(pd.get("content", "") or "")

                    total_records = projects_count + analyses_count + key_points_count + action_items_count + decisions_count + important_dates_count + pending_decisions_count
                    used_bytes = text_bytes + (total_records * 256)
                    effective_limit = storage_limit_bytes if storage_limit_bytes is not None else 104857600

                    return {
                        "projects_count": projects_count,
                        "analyses_count": analyses_count,
                        "key_points_count": key_points_count,
                        "action_items_count": action_items_count,
                        "decisions_count": decisions_count,
                        "important_dates_count": important_dates_count,
                        "pending_decisions_count": pending_decisions_count,
                        "total_chars_processed": text_bytes,
                        "used_storage_bytes": used_bytes,
                        "limit_storage_bytes": effective_limit,
                    }
                raise DatabaseOperationError(f"Supabase get_user_storage_stats failed (HTTP {res.status_code}): {res.text}")
            except httpx.TimeoutException as te:
                raise DatabaseTimeoutError("Database operation timed out. Please try again.") from te
            except httpx.RequestError as e:
                raise DatabaseConnectionError(f"Network error connecting to Supabase: {str(e)}") from e

        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM projects WHERE user_id = ?", (user_id,))
            projects_count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(LENGTH(a.summary) + LENGTH(a.title)), 0)
                FROM analyses a
                JOIN projects p ON a.project_id = p.id
                WHERE p.user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            analyses_count = row[0]
            analyses_bytes = row[1]

            cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(LENGTH(kp.content)), 0)
                FROM key_points kp
                JOIN analyses a ON kp.analysis_id = a.id
                JOIN projects p ON a.project_id = p.id
                WHERE p.user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            key_points_count = row[0]
            kp_bytes = row[1]

            cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(LENGTH(act.content)), 0)
                FROM action_items act
                JOIN analyses a ON act.analysis_id = a.id
                JOIN projects p ON a.project_id = p.id
                WHERE p.user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            action_items_count = row[0]
            action_bytes = row[1]

            cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(LENGTH(dec.content)), 0)
                FROM decisions dec
                JOIN analyses a ON dec.analysis_id = a.id
                JOIN projects p ON a.project_id = p.id
                WHERE p.user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            decisions_count = row[0]
            decision_bytes = row[1]

            cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(LENGTH(dt.label) + LENGTH(COALESCE(dt.description, ''))), 0)
                FROM important_dates dt
                JOIN analyses a ON dt.analysis_id = a.id
                JOIN projects p ON a.project_id = p.id
                WHERE p.user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            important_dates_count = row[0]
            dates_bytes = row[1]

            cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(LENGTH(pd.content)), 0)
                FROM pending_decisions pd
                JOIN analyses a ON pd.analysis_id = a.id
                JOIN projects p ON a.project_id = p.id
                WHERE p.user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            pending_decisions_count = row[0]
            pending_bytes = row[1]

            raw_chars = analyses_bytes + kp_bytes + action_bytes + decision_bytes + dates_bytes + pending_bytes
            total_records = projects_count + analyses_count + key_points_count + action_items_count + decisions_count + important_dates_count + pending_decisions_count
            used_storage_bytes = raw_chars + (total_records * 256)
            effective_limit = storage_limit_bytes if storage_limit_bytes is not None else 104857600

            return {
                "projects_count": projects_count,
                "analyses_count": analyses_count,
                "key_points_count": key_points_count,
                "action_items_count": action_items_count,
                "decisions_count": decisions_count,
                "important_dates_count": important_dates_count,
                "pending_decisions_count": pending_decisions_count,
                "total_chars_processed": raw_chars,
                "used_storage_bytes": used_storage_bytes,
                "limit_storage_bytes": effective_limit,
            }
        finally:
            conn.close()

    def get_all_project_analyses(self, project_id: str, user_id: Optional[str] = None, user_token: Optional[str] = None) -> List[ShiftlyAnalysisResult]:
        """Fetches all analyses and their child records for a project in a single batched query to eliminate N+1 latency."""
        self._ensure_configured()

        if not self._active_sqlite_mode:
            url = f"{self.supabase_url}/rest/v1/analyses?project_id=eq.{project_id}&select=*,key_points(*),action_items(*),decisions(*),important_dates(*),pending_decisions(*)"
            try:
                res = self._client().get(url, headers=self._get_supabase_headers(user_token), timeout=10.0)
                if res.status_code == 200:
                    rows = res.json()
                    analyses: List[ShiftlyAnalysisResult] = []
                    for r in rows:
                        stats = AnalysisStats.model_validate_json(r["stats"]) if isinstance(r["stats"], str) else AnalysisStats.model_validate(r["stats"])
                        prefix = f"{r['id']}_"
                        key_points = [
                            KeyPointItem(
                                id=k["id"][len(prefix):] if k["id"].startswith(prefix) else k["id"],
                                point=k["content"],
                                category=k.get("topic"),
                                source=SourceReference.model_validate_json(k["source_reference"]) if isinstance(k["source_reference"], str) else SourceReference.model_validate(k["source_reference"]),
                            )
                            for k in r.get("key_points", [])
                        ]
                        actions = [
                            ActionItem(
                                id=a["id"][len(prefix):] if a["id"].startswith(prefix) else a["id"],
                                action=a["content"],
                                responsiblePerson=a.get("responsible_person") or "Unassigned",
                                deadline=a.get("due_date"),
                                priority=a.get("priority") or "Normal",
                                source=SourceReference.model_validate_json(a["source_reference"]) if isinstance(a["source_reference"], str) else SourceReference.model_validate(a["source_reference"]),
                            )
                            for a in r.get("action_items", [])
                        ]
                        decisions = [
                            DecisionItem(
                                id=d["id"][len(prefix):] if d["id"].startswith(prefix) else d["id"],
                                decision=d["content"],
                                approvedBy=d.get("approved_by") or "Unknown",
                                date=d.get("date"),
                                source=SourceReference.model_validate_json(d["source_reference"]) if isinstance(d["source_reference"], str) else SourceReference.model_validate(d["source_reference"]),
                            )
                            for d in r.get("decisions", [])
                        ]
                        important_dates = [
                            ImportantDateItem(
                                id=dt["id"][len(prefix):] if dt["id"].startswith(prefix) else dt["id"],
                                title=dt["label"],
                                date=dt["date"],
                                significance=dt.get("description") or "",
                                source=SourceReference.model_validate_json(dt["source_reference"]) if isinstance(dt["source_reference"], str) else SourceReference.model_validate(dt["source_reference"]),
                            )
                            for dt in r.get("important_dates", [])
                        ]
                        pending_decisions = [
                            PendingDecisionItem(
                                id=pd["id"][len(prefix):] if pd["id"].startswith(prefix) else pd["id"],
                                decision=pd["content"],
                                status=pd.get("status") or "Pending",
                                source=SourceReference.model_validate_json(pd["source_reference"]) if isinstance(pd["source_reference"], str) else SourceReference.model_validate(pd["source_reference"]),
                            )
                            for pd in r.get("pending_decisions", [])
                        ]
                        analyses.append(ShiftlyAnalysisResult(
                            id=r["id"],
                            title=r["title"],
                            analyzedAt=r["created_at"],
                            stats=stats,
                            summary=r["summary"],
                            keyPoints=key_points,
                            actions=actions,
                            decisions=decisions,
                            importantDates=important_dates,
                            pendingDecisions=pending_decisions,
                        ))
                    return analyses
                raise DatabaseOperationError(f"Supabase get_all_project_analyses failed (HTTP {res.status_code}): {res.text}")
            except httpx.TimeoutException as te:
                raise DatabaseTimeoutError("Database operation timed out. Please try again.") from te
            except httpx.RequestError as e:
                raise DatabaseConnectionError(f"Network error connecting to Supabase: {str(e)}") from e

        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, summary, stats, created_at FROM analyses WHERE project_id = ? ORDER BY created_at DESC", (project_id,))
            a_rows = cursor.fetchall()
            if not a_rows:
                return []

            analyses = []
            for row in a_rows:
                aid, title, summary, stats_raw, created_at = row
                stats = AnalysisStats.model_validate_json(stats_raw)
                prefix = f"{aid}_"

                cursor.execute("SELECT id, content, topic, source_reference FROM key_points WHERE analysis_id = ?", (aid,))
                key_points = [
                    KeyPointItem(
                        id=k[0][len(prefix):] if k[0].startswith(prefix) else k[0],
                        point=k[1],
                        category=k[2],
                        source=SourceReference.model_validate_json(k[3]),
                    )
                    for k in cursor.fetchall()
                ]

                cursor.execute("SELECT id, content, responsible_person, due_date, priority, source_reference FROM action_items WHERE analysis_id = ?", (aid,))
                actions = [
                    ActionItem(
                        id=a[0][len(prefix):] if a[0].startswith(prefix) else a[0],
                        action=a[1],
                        responsiblePerson=a[2] or "Unassigned",
                        deadline=a[3],
                        priority=a[4] or "Normal",
                        source=SourceReference.model_validate_json(a[5]),
                    )
                    for a in cursor.fetchall()
                ]

                cursor.execute("SELECT id, content, approved_by, date, source_reference FROM decisions WHERE analysis_id = ?", (aid,))
                decisions = [
                    DecisionItem(
                        id=d[0][len(prefix):] if d[0].startswith(prefix) else d[0],
                        decision=d[1],
                        approvedBy=d[2] or "Unknown",
                        date=d[3],
                        source=SourceReference.model_validate_json(d[4]),
                    )
                    for d in cursor.fetchall()
                ]

                cursor.execute("SELECT id, label, date, description, source_reference FROM important_dates WHERE analysis_id = ?", (aid,))
                important_dates = [
                    ImportantDateItem(
                        id=t[0][len(prefix):] if t[0].startswith(prefix) else t[0],
                        title=t[1],
                        date=t[2],
                        significance=t[3] or "",
                        source=SourceReference.model_validate_json(t[4]),
                    )
                    for t in cursor.fetchall()
                ]

                cursor.execute("SELECT id, content, status, source_reference FROM pending_decisions WHERE analysis_id = ?", (aid,))
                pending_decisions = [
                    PendingDecisionItem(
                        id=p[0][len(prefix):] if p[0].startswith(prefix) else p[0],
                        decision=p[1],
                        status=p[2] or "Pending",
                        source=SourceReference.model_validate_json(p[3]),
                    )
                    for p in cursor.fetchall()
                ]

                analyses.append(ShiftlyAnalysisResult(
                    id=aid,
                    title=title,
                    analyzedAt=created_at,
                    stats=stats,
                    summary=summary,
                    keyPoints=key_points,
                    actions=actions,
                    decisions=decisions,
                    importantDates=important_dates,
                    pendingDecisions=pending_decisions,
                ))
            return analyses
        finally:
            conn.close()

    def get_project_aggregated_intelligence(self, project_id: str, user_id: Optional[str] = None, user_token: Optional[str] = None) -> ShiftlyAnalysisResult:
        """
        Aggregates actual intelligence from all analyses belonging to a project,
        preserving Shiftly's deduplication and merge behavior.
        Optimized to eliminate N+1 queries.
        """
        self._ensure_configured()
        project = self.get_project(project_id, user_id=user_id, user_token=user_token)
        if not project:
            raise ProjectNotFoundError(f"Project '{project_id}' not found.")

        full_analyses = self.get_all_project_analyses(project_id, user_id=user_id, user_token=user_token)
        if not full_analyses:
            return ShiftlyAnalysisResult(
                id=f"agg-{project_id}",
                title=f"{project.name} — Project Intelligence",
                analyzedAt=datetime.utcnow().strftime("%B %d, %Y • %I:%M %p"),
                stats=AnalysisStats(),
                summary="",
                keyPoints=[],
                actions=[],
                decisions=[],
                importantDates=[],
                pendingDecisions=[],
            )

        merged = merge_analysis_results(full_analyses)
        merged.id = f"agg-{project_id}"
        merged.title = f"{project.name} — Project Intelligence"
        return merged

    def count_user_projects(self, user_id: str, user_token: Optional[str] = None) -> int:
        """Counts the total number of projects owned by user_id."""
        self._ensure_configured()
        if not self._active_sqlite_mode:
            url = f"{self.supabase_url}/rest/v1/projects?user_id=eq.{user_id}&select=id"
            try:
                headers = {**self._get_supabase_headers(user_token), "Prefer": "count=exact"}
                res = self._client().get(url, headers=headers, timeout=10.0)
                if res.status_code == 200:
                    content_range = res.headers.get("content-range")
                    if content_range and "/" in content_range:
                        total_str = content_range.split("/")[-1]
                        if total_str != "*":
                            return int(total_str)
                    return len(res.json())
                raise DatabaseOperationError(f"Supabase count_user_projects failed (HTTP {res.status_code}): {res.text}")
            except httpx.TimeoutException as te:
                raise DatabaseTimeoutError("Database operation timed out.") from te
            except httpx.RequestError as e:
                raise DatabaseConnectionError(f"Network error connecting to Supabase: {str(e)}") from e

        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM projects WHERE user_id = ?", (user_id,))
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def count_user_analyses_in_month(self, user_id: str, year: int, month: int, user_token: Optional[str] = None) -> int:
        """Counts the total analyses created by user_id within a calendar month."""
        self._ensure_configured()
        start_iso = f"{year:04d}-{month:02d}-01T00:00:00Z"
        if month == 12:
            end_iso = f"{year + 1:04d}-01-01T00:00:00Z"
        else:
            end_iso = f"{year:04d}-{month + 1:02d}-01T00:00:00Z"

        if not self._active_sqlite_mode:
            # Query projects owned by user, then count analyses
            url = f"{self.supabase_url}/rest/v1/projects?user_id=eq.{user_id}&select=id,analyses(id,created_at)&analyses.created_at=gte.{start_iso}&analyses.created_at=lt.{end_iso}"
            try:
                headers = self._get_supabase_headers(user_token)
                res = self._client().get(url, headers=headers, timeout=10.0)
                if res.status_code == 200:
                    total_count = 0
                    for p in res.json():
                        total_count += len(p.get("analyses", []))
                    return total_count
                raise DatabaseOperationError(f"Supabase count_user_analyses_in_month failed (HTTP {res.status_code}): {res.text}")
            except httpx.TimeoutException as te:
                raise DatabaseTimeoutError("Database operation timed out.") from te
            except httpx.RequestError as e:
                raise DatabaseConnectionError(f"Network error connecting to Supabase: {str(e)}") from e

        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM analyses a
                JOIN projects p ON a.project_id = p.id
                WHERE p.user_id = ? AND a.created_at >= ? AND a.created_at < ?
            """, (user_id, start_iso, end_iso))
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def delete_user_data(self, user_id: str, user_token: Optional[str] = None) -> bool:
        """Deletes all projects and cascading project memory entities owned by user_id."""
        self._ensure_configured()

        if not self._active_sqlite_mode:
            url = f"{self.supabase_url}/rest/v1/projects?user_id=eq.{user_id}"
            try:
                res = self._client().delete(url, headers=self._get_supabase_headers(user_token), timeout=10.0)
                if res.status_code in (200, 204):
                    return True
                raise DatabaseOperationError(f"Supabase delete_user_data failed (HTTP {res.status_code}): {res.text}")
            except httpx.TimeoutException as te:
                raise DatabaseTimeoutError("Database operation timed out. Please try again.") from te
            except httpx.RequestError as e:
                raise DatabaseConnectionError(f"Network error connecting to Supabase: {str(e)}") from e

        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("DELETE FROM projects WHERE user_id = ?", (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()


# Singleton repository instance
memory_repo = ProjectMemoryRepository()
