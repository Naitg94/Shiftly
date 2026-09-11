import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional
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
    SourceReference,
)

logger = logging.getLogger("shiftly.db")

LOCAL_DB_PATH = os.path.join(os.path.dirname(__file__), "project_memory.db")


class ProjectNotFoundError(Exception):
    pass


class AnalysisNotFoundError(Exception):
    pass


class DatabaseOperationError(Exception):
    pass


def _init_local_db():
    """Initializes the local SQLite database schema if not already present."""
    conn = sqlite3.connect(LOCAL_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
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
    """)
    conn.commit()
    conn.close()


# Ensure local database schema is ready
_init_local_db()


class ProjectMemoryRepository:
    """
    Unified repository supporting Supabase PostgreSQL with seamless,
    deterministic local storage fallback for testing and offline development.
    """

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL.rstrip('/') if settings.SUPABASE_URL else ""
        self.supabase_key = settings.SUPABASE_ANON_KEY if settings.SUPABASE_ANON_KEY else ""
        self.is_supabase_configured = bool(self.supabase_url and self.supabase_key)
        if self.is_supabase_configured:
            logger.info("Project Memory initialized using Supabase PostgreSQL client.")
        else:
            logger.info("Project Memory initialized using local relational storage (test/dev fallback).")

    def _get_supabase_headers(self) -> dict:
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    # =========================================================================
    # PROJECT OPERATIONS
    # =========================================================================

    def create_project(self, name: str, description: Optional[str] = None) -> Project:
        project_id = str(uuid.uuid4())
        now_str = datetime.utcnow().isoformat() + "Z"

        if self.is_supabase_configured:
            try:
                url = f"{self.supabase_url}/rest/v1/projects"
                payload = {
                    "id": project_id,
                    "name": name,
                    "description": description,
                    "created_at": now_str,
                    "updated_at": now_str,
                }
                res = httpx.post(url, headers=self._get_supabase_headers(), json=payload, timeout=10.0)
                if res.status_code in (200, 201):
                    # Also mirror locally for cache resilience
                    self._save_project_locally(project_id, name, description, now_str)
                    return Project(
                        id=project_id,
                        name=name,
                        description=description,
                        created_at=now_str,
                        updated_at=now_str,
                        analyses_count=0,
                    )
                else:
                    logger.warning(f"Supabase write returned {res.status_code}: {res.text}")
            except Exception as e:
                logger.warning(f"Supabase write failed ({e}); recording in local storage.")

        return self._save_project_locally(project_id, name, description, now_str)

    def _save_project_locally(self, project_id: str, name: str, description: Optional[str], now_str: str) -> Project:
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "INSERT INTO projects (id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET name=excluded.name, description=excluded.description, updated_at=excluded.updated_at",
                (project_id, name, description, now_str, now_str),
            )
            conn.commit()
            return Project(
                id=project_id,
                name=name,
                description=description,
                created_at=now_str,
                updated_at=now_str,
                analyses_count=0,
            )
        except Exception as e:
            raise DatabaseOperationError(f"Failed to create project: {str(e)}") from e
        finally:
            conn.close()

    def list_projects(self) -> List[Project]:
        if self.is_supabase_configured:
            try:
                url = f"{self.supabase_url}/rest/v1/projects?select=*,analyses(count)&order=created_at.desc"
                res = httpx.get(url, headers=self._get_supabase_headers(), timeout=10.0)
                if res.status_code == 200:
                    projects_data = res.json()
                    projects: List[Project] = []
                    for row in projects_data:
                        count = row.get("analyses", [{}])[0].get("count", 0) if isinstance(row.get("analyses"), list) else 0
                        projects.append(
                            Project(
                                id=row["id"],
                                name=row["name"],
                                description=row.get("description"),
                                created_at=row["created_at"],
                                updated_at=row["updated_at"],
                                analyses_count=count,
                            )
                        )
                    return projects
                else:
                    logger.warning(f"Supabase read returned {res.status_code}: {res.text}")
            except Exception as e:
                logger.warning(f"Supabase read failed ({e}); falling back to local storage.")

        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, p.name, p.description, p.created_at, p.updated_at, COUNT(a.id) as count
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
                )
                for r in rows
            ]
        finally:
            conn.close()

    def get_project(self, project_id: str) -> Optional[Project]:
        if self.is_supabase_configured:
            try:
                url = f"{self.supabase_url}/rest/v1/projects?id=eq.{project_id}&select=*,analyses(count)"
                res = httpx.get(url, headers=self._get_supabase_headers(), timeout=10.0)
                if res.status_code == 200 and res.json():
                    row = res.json()[0]
                    count = row.get("analyses", [{}])[0].get("count", 0) if isinstance(row.get("analyses"), list) else 0
                    return Project(
                        id=row["id"],
                        name=row["name"],
                        description=row.get("description"),
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                        analyses_count=count,
                    )
            except Exception as e:
                logger.warning(f"Supabase get_project failed ({e}); reading local storage.")

        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, p.name, p.description, p.created_at, p.updated_at, COUNT(a.id) as count
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
            )
        finally:
            conn.close()

    # =========================================================================
    # ANALYSIS PERSISTENCE & RETRIEVAL
    # =========================================================================

    def save_analysis(self, project_id: str, result: ShiftlyAnalysisResult) -> StoredAnalysisSummary:
        project = self.get_project(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project with ID '{project_id}' does not exist.")

        analysis_id = result.id if result.id else str(uuid.uuid4())
        now_str = datetime.utcnow().isoformat() + "Z"

        # Determine primary source metadata
        source_type = "Chat Export"
        source_name = None
        for kp in result.keyPoints:
            if kp.source:
                source_type = kp.source.sourceType
                source_name = kp.source.sourceName
                break

        stats_json = result.stats.model_dump_json()

        # If Supabase is configured, write directly to Supabase
        if self.is_supabase_configured:
            try:
                headers = {**self._get_supabase_headers(), "Prefer": "resolution=merge-duplicates"}
                analysis_payload = {
                    "id": analysis_id,
                    "project_id": project_id,
                    "title": result.title,
                    "source_type": source_type,
                    "source_name": source_name,
                    "summary": result.summary,
                    "stats": stats_json,
                    "created_at": now_str,
                    "updated_at": now_str,
                }
                a_res = httpx.post(f"{self.supabase_url}/rest/v1/analyses", headers=headers, json=analysis_payload, timeout=10.0)
                if a_res.status_code in (200, 201):
                    # Delete any previous children for this analysis if re-saving
                    del_hdr = self._get_supabase_headers()
                    httpx.delete(f"{self.supabase_url}/rest/v1/key_points?analysis_id=eq.{analysis_id}", headers=del_hdr, timeout=10.0)
                    httpx.delete(f"{self.supabase_url}/rest/v1/action_items?analysis_id=eq.{analysis_id}", headers=del_hdr, timeout=10.0)
                    httpx.delete(f"{self.supabase_url}/rest/v1/decisions?analysis_id=eq.{analysis_id}", headers=del_hdr, timeout=10.0)
                    httpx.delete(f"{self.supabase_url}/rest/v1/important_dates?analysis_id=eq.{analysis_id}", headers=del_hdr, timeout=10.0)

                    # Batch insert Key Points
                    if result.keyPoints:
                        kp_records = [
                            {
                                "id": f"{analysis_id}_{kp.id}",
                                "analysis_id": analysis_id,
                                "content": kp.point,
                                "topic": kp.category,
                                "source_reference": kp.source.model_dump_json(),
                                "created_at": now_str,
                            }
                            for kp in result.keyPoints
                        ]
                        httpx.post(f"{self.supabase_url}/rest/v1/key_points", headers=headers, json=kp_records, timeout=10.0)

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
                                "source_reference": act.source.model_dump_json(),
                                "created_at": now_str,
                            }
                            for act in result.actions
                        ]
                        httpx.post(f"{self.supabase_url}/rest/v1/action_items", headers=headers, json=act_records, timeout=10.0)

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
                                "source_reference": dec.source.model_dump_json(),
                                "created_at": now_str,
                            }
                            for dec in result.decisions
                        ]
                        httpx.post(f"{self.supabase_url}/rest/v1/decisions", headers=headers, json=dec_records, timeout=10.0)

                    # Batch insert Important Dates
                    if result.importantDates:
                        dt_records = [
                            {
                                "id": f"{analysis_id}_{dt.id}",
                                "analysis_id": analysis_id,
                                "label": dt.title,
                                "date": dt.date,
                                "description": dt.significance,
                                "source_reference": dt.source.model_dump_json(),
                                "created_at": now_str,
                            }
                            for dt in result.importantDates
                        ]
                        httpx.post(f"{self.supabase_url}/rest/v1/important_dates", headers=headers, json=dt_records, timeout=10.0)

                    # Also mirror in local DB for fallback
                    self._save_analysis_locally(project_id, analysis_id, result, source_type, source_name, stats_json, now_str)

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
                    )
                else:
                    logger.warning(f"Supabase save_analysis failed with {a_res.status_code}: {a_res.text}")
            except Exception as e:
                logger.warning(f"Supabase save_analysis error ({e}); saving locally.")

        return self._save_analysis_locally(project_id, analysis_id, result, source_type, source_name, stats_json, now_str)

    def _save_analysis_locally(self, project_id: str, analysis_id: str, result: ShiftlyAnalysisResult, source_type: str, source_name: Optional[str], stats_json: str, now_str: str) -> StoredAnalysisSummary:
        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            # Transactional atomic save
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

            # Clear existing children if updating
            cursor.execute("DELETE FROM key_points WHERE analysis_id = ?", (analysis_id,))
            cursor.execute("DELETE FROM action_items WHERE analysis_id = ?", (analysis_id,))
            cursor.execute("DELETE FROM decisions WHERE analysis_id = ?", (analysis_id,))
            cursor.execute("DELETE FROM important_dates WHERE analysis_id = ?", (analysis_id,))

            # Save Key Points
            for kp in result.keyPoints:
                src_json = kp.source.model_dump_json()
                kp_row_id = f"{analysis_id}_{kp.id}"
                cursor.execute(
                    "INSERT INTO key_points (id, analysis_id, content, topic, source_reference, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (kp_row_id, analysis_id, kp.point, kp.category, src_json, now_str),
                )

            # Save Actions
            for act in result.actions:
                src_json = act.source.model_dump_json()
                act_row_id = f"{analysis_id}_{act.id}"
                cursor.execute(
                    "INSERT INTO action_items (id, analysis_id, content, responsible_person, due_date, status, priority, source_reference, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (act_row_id, analysis_id, act.action, act.responsiblePerson, act.deadline, "Pending", act.priority or "Normal", src_json, now_str),
                )

            # Save Decisions
            for dec in result.decisions:
                src_json = dec.source.model_dump_json()
                dec_row_id = f"{analysis_id}_{dec.id}"
                cursor.execute(
                    "INSERT INTO decisions (id, analysis_id, content, decision_type, approved_by, date, source_reference, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (dec_row_id, analysis_id, dec.decision, "Approval", dec.approvedBy, dec.date, src_json, now_str),
                )

            # Save Important Dates
            for dt in result.importantDates:
                src_json = dt.source.model_dump_json()
                dt_row_id = f"{analysis_id}_{dt.id}"
                cursor.execute(
                    "INSERT INTO important_dates (id, analysis_id, label, date, description, source_reference, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (dt_row_id, analysis_id, dt.title, dt.date, dt.significance, src_json, now_str),
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
            )
        except Exception as e:
            conn.rollback()
            raise DatabaseOperationError(f"Failed to save analysis to project memory: {str(e)}") from e
        finally:
            conn.close()

    def list_project_analyses(self, project_id: str) -> List[StoredAnalysisSummary]:
        project = self.get_project(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project '{project_id}' not found.")

        if self.is_supabase_configured:
            try:
                url = f"{self.supabase_url}/rest/v1/analyses?project_id=eq.{project_id}&select=*,key_points(count),action_items(count),decisions(count),important_dates(count)&order=created_at.desc"
                res = httpx.get(url, headers=self._get_supabase_headers(), timeout=10.0)
                if res.status_code == 200:
                    rows = res.json()
                    analyses: List[StoredAnalysisSummary] = []
                    for r in rows:
                        kp_c = r.get("key_points", [{}])[0].get("count", 0) if isinstance(r.get("key_points"), list) else 0
                        act_c = r.get("action_items", [{}])[0].get("count", 0) if isinstance(r.get("action_items"), list) else 0
                        dec_c = r.get("decisions", [{}])[0].get("count", 0) if isinstance(r.get("decisions"), list) else 0
                        dt_c = r.get("important_dates", [{}])[0].get("count", 0) if isinstance(r.get("important_dates"), list) else 0
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
                            )
                        )
                    return analyses
            except Exception as e:
                logger.warning(f"Supabase list_analyses error ({e}); falling back to local storage.")

        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    a.id, a.project_id, a.title, a.source_type, a.source_name, a.summary, a.created_at,
                    (SELECT COUNT(*) FROM key_points kp WHERE kp.analysis_id = a.id),
                    (SELECT COUNT(*) FROM action_items act WHERE act.analysis_id = a.id),
                    (SELECT COUNT(*) FROM decisions dec WHERE dec.analysis_id = a.id),
                    (SELECT COUNT(*) FROM important_dates dt WHERE dt.analysis_id = a.id)
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
                )
                for r in rows
            ]
        finally:
            conn.close()

    def get_analysis(self, project_id: str, analysis_id: str) -> Optional[ShiftlyAnalysisResult]:
        if self.is_supabase_configured:
            try:
                url = f"{self.supabase_url}/rest/v1/analyses?id=eq.{analysis_id}&project_id=eq.{project_id}&select=*,key_points(*),action_items(*),decisions(*),important_dates(*)"
                res = httpx.get(url, headers=self._get_supabase_headers(), timeout=10.0)
                if res.status_code == 200 and res.json():
                    r = res.json()[0]
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
                    )
            except Exception as e:
                logger.warning(f"Supabase get_analysis failed ({e}); checking local storage.")

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
            )
        finally:
            conn.close()

    # =========================================================================
    # DETERMINISTIC SEARCH
    # =========================================================================

    def search_project_memory(self, project_id: str, query: str) -> List[SearchResultItem]:
        clean_q = query.strip().lower()
        if not clean_q:
            return []

        # Try Supabase if configured
        if self.is_supabase_configured:
            try:
                results: List[SearchResultItem] = []
                headers = self._get_supabase_headers()
                # 1. Key points search
                kp_url = f"{self.supabase_url}/rest/v1/key_points?select=content,source_reference,created_at,analyses!inner(id,title,project_id)&analyses.project_id=eq.{project_id}&content=ilike.*{clean_q}*"
                res = httpx.get(kp_url, headers=headers, timeout=10.0)
                if res.status_code == 200:
                    for r in res.json():
                        src = SourceReference.model_validate_json(r["source_reference"]) if isinstance(r["source_reference"], str) else SourceReference.model_validate(r["source_reference"])
                        results.append(
                            SearchResultItem(
                                analysis_id=r["analyses"]["id"],
                                analysis_title=r["analyses"]["title"],
                                item_type="Key Point",
                                content=r["content"],
                                source_reference=src,
                                created_at=r["created_at"],
                            )
                        )
                # 2. Action items search
                act_url = f"{self.supabase_url}/rest/v1/action_items?select=content,responsible_person,source_reference,created_at,analyses!inner(id,title,project_id)&analyses.project_id=eq.{project_id}&content=ilike.*{clean_q}*"
                res = httpx.get(act_url, headers=headers, timeout=10.0)
                if res.status_code == 200:
                    for r in res.json():
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
                if results:
                    return results
            except Exception as e:
                logger.warning(f"Supabase search error ({e}); using local storage.")

        conn = sqlite3.connect(LOCAL_DB_PATH)
        try:
            cursor = conn.cursor()
            results: List[SearchResultItem] = []
            param = f"%{clean_q}%"

            # 1. Search in Key Points
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

            # 2. Search in Actions
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

            # 3. Search in Decisions
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

            # 4. Search in Important Dates
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
                        content=f"{r[2]} ({r[3]}) — {r[4]}",
                        source_reference=SourceReference.model_validate_json(r[5]),
                        created_at=r[6],
                    )
                )

            # 5. Search in Summary
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

            return results
        finally:
            conn.close()


# Singleton repository instance
memory_repo = ProjectMemoryRepository()

