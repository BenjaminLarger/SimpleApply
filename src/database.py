import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel


class Application(BaseModel):
    id: Optional[int] = None
    company: str
    position: str
    matching_rate: float
    unmatched_skills: List[str]
    matched_skills: List[str]
    location: str
    job_offer_input: str
    application_cost: float
    language: str = "en"
    created_at: Optional[datetime] = None


class ApplicationDatabase:
    def __init__(self, db_path: str = "applications.db"):
        self.db_path = Path(db_path)
        self.init_database()

    def init_database(self):
        """Initialize the SQLite database and create tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    position TEXT NOT NULL,
                    matching_rate REAL NOT NULL,
                    unmatched_skills TEXT NOT NULL,
                    matched_skills TEXT NOT NULL,
                    location TEXT NOT NULL,
                    job_offer_input TEXT NOT NULL,
                    application_cost REAL NOT NULL DEFAULT 0.0,
                    language TEXT NOT NULL DEFAULT 'en',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Add application_cost column if it doesn't exist (for existing databases)
            try:
                conn.execute("ALTER TABLE applications ADD COLUMN application_cost REAL NOT NULL DEFAULT 0.0")
            except sqlite3.OperationalError:
                # Column already exists
                pass

            # Add language column if it doesn't exist (for existing databases)
            try:
                conn.execute("ALTER TABLE applications ADD COLUMN language TEXT NOT NULL DEFAULT 'en'")
            except sqlite3.OperationalError:
                # Column already exists
                pass

            conn.commit()

    def save_application(self, application: Application) -> int:
        """Save a new application to the database or overwrite if company and position match"""
        with sqlite3.connect(self.db_path) as conn:
            # First, check if an application with the same company and position exists
            cursor = conn.execute("""
                SELECT id FROM applications WHERE company = ? AND position = ?
            """, (application.company, application.position))
            existing = cursor.fetchone()

            if existing:
                # Update existing record
                cursor = conn.execute("""
                    UPDATE applications
                    SET matching_rate = ?, unmatched_skills = ?, matched_skills = ?,
                        location = ?, job_offer_input = ?, application_cost = ?, language = ?,
                        created_at = CURRENT_TIMESTAMP
                    WHERE company = ? AND position = ?
                """, (
                    application.matching_rate,
                    json.dumps(application.unmatched_skills),
                    json.dumps(application.matched_skills),
                    application.location,
                    application.job_offer_input,
                    application.application_cost,
                    application.language,
                    application.company,
                    application.position
                ))
                conn.commit()
                return existing[0]  # Return the existing ID
            else:
                # Insert new record
                cursor = conn.execute("""
                    INSERT INTO applications
                    (company, position, matching_rate, unmatched_skills, matched_skills, location, job_offer_input, application_cost, language)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    application.company,
                    application.position,
                    application.matching_rate,
                    json.dumps(application.unmatched_skills),
                    json.dumps(application.matched_skills),
                    application.location,
                    application.job_offer_input,
                    application.application_cost,
                    application.language
                ))
                conn.commit()
                return cursor.lastrowid

    def get_application(self, application_id: int) -> Optional[Application]:
        """Retrieve an application by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM applications WHERE id = ?
            """, (application_id,))
            row = cursor.fetchone()

            if row:
                row_dict = dict(row)
                return Application(
                    id=row_dict['id'],
                    company=row_dict['company'],
                    position=row_dict['position'],
                    matching_rate=row_dict['matching_rate'],
                    unmatched_skills=json.loads(row_dict['unmatched_skills']),
                    matched_skills=json.loads(row_dict['matched_skills']),
                    location=row_dict['location'],
                    job_offer_input=row_dict['job_offer_input'],
                    application_cost=row_dict['application_cost'],
                    language=row_dict.get('language', 'en'),
                    created_at=datetime.fromisoformat(row_dict['created_at'])
                )
            return None

    def get_all_applications(self) -> List[Application]:
        """Retrieve all applications from the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM applications ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()

            applications = []
            for row in rows:
                row_dict = dict(row)
                applications.append(Application(
                    id=row_dict['id'],
                    company=row_dict['company'],
                    position=row_dict['position'],
                    matching_rate=row_dict['matching_rate'],
                    unmatched_skills=json.loads(row_dict['unmatched_skills']),
                    matched_skills=json.loads(row_dict['matched_skills']),
                    location=row_dict['location'],
                    job_offer_input=row_dict['job_offer_input'],
                    application_cost=row_dict['application_cost'],
                    language=row_dict.get('language', 'en'),
                    created_at=datetime.fromisoformat(row_dict['created_at'])
                ))
            return applications

    def delete_application(self, application_id: int) -> bool:
        """Delete an application by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM applications WHERE id = ?
            """, (application_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_applications_by_company(self, company: str) -> List[Application]:
        """Get all applications for a specific company"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM applications WHERE company = ? ORDER BY created_at DESC
            """, (company,))
            rows = cursor.fetchall()

            applications = []
            for row in rows:
                row_dict = dict(row)
                applications.append(Application(
                    id=row_dict['id'],
                    company=row_dict['company'],
                    position=row_dict['position'],
                    matching_rate=row_dict['matching_rate'],
                    unmatched_skills=json.loads(row_dict['unmatched_skills']),
                    matched_skills=json.loads(row_dict['matched_skills']),
                    location=row_dict['location'],
                    job_offer_input=row_dict['job_offer_input'],
                    application_cost=row_dict['application_cost'],
                    language=row_dict.get('language', 'en'),
                    created_at=datetime.fromisoformat(row_dict['created_at'])
                ))
            return applications

    def get_total_cost(self) -> float:
        """Get total cost of all applications"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT SUM(application_cost) as total FROM applications")
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 0.0

    def get_cost_by_date_range(self, start_date: datetime, end_date: datetime) -> float:
        """Get total cost within a date range"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT SUM(application_cost) as total
                FROM applications
                WHERE created_at BETWEEN ? AND ?
            """, (start_date.isoformat(), end_date.isoformat()))
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 0.0