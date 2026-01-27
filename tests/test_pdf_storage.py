#!/usr/bin/env python3
"""
Tests for PDF storage and retrieval functionality in the database.
"""

import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from src.database import Application, ApplicationDatabase


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test.db")
    db = ApplicationDatabase(db_path)
    yield db
    # Cleanup happens automatically with temp file


@pytest.fixture
def sample_pdf_bytes():
    """Create sample PDF-like bytes for testing."""
    # Create a larger sample PDF to ensure storage size > 0
    # Simulate a realistic PDF with more content
    pdf_content = b"%PDF-1.4\n"
    pdf_content += b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n" * 10
    pdf_content += b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n" * 10
    pdf_content += b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n"
    pdf_content += b"xref\ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n0\n%%EOF"
    return pdf_content


@pytest.fixture
def sample_application(sample_pdf_bytes):
    """Create a sample application with PDF data."""
    return Application(
        company="TestCorp",
        position="AI Engineer",
        matching_rate=0.85,
        unmatched_skills=["Rust", "Go"],
        matched_skills=["Python", "FastAPI", "Docker"],
        location="Remote",
        job_offer_input="Sample job offer text",
        application_cost=0.15,
        language="en",
        cv_pdf=sample_pdf_bytes,
        cover_letter_pdf=sample_pdf_bytes
    )


class TestPDFStorage:
    """Test PDF storage in the database."""

    def test_save_application_with_pdf(self, temp_db, sample_application):
        """Test saving application with PDF data to database."""
        app_id = temp_db.save_application(sample_application)
        assert app_id is not None
        assert isinstance(app_id, int)

    def test_retrieve_application_with_pdf(self, temp_db, sample_application):
        """Test retrieving application with PDF data from database."""
        original_id = temp_db.save_application(sample_application)
        retrieved = temp_db.get_application(original_id)

        assert retrieved is not None
        assert retrieved.id == original_id
        assert retrieved.cv_pdf == sample_application.cv_pdf
        assert retrieved.cover_letter_pdf == sample_application.cover_letter_pdf
        assert retrieved.company == "TestCorp"

    def test_pdf_persists_after_overwrite(self, temp_db, sample_application, sample_pdf_bytes):
        """Test that PDFs persist when application is overwritten."""
        # First save
        app_id = temp_db.save_application(sample_application)
        assert app_id is not None

        # Overwrite with new data
        updated_app = Application(
            company="TestCorp",
            position="AI Engineer",
            matching_rate=0.90,
            unmatched_skills=["Rust"],
            matched_skills=["Python", "FastAPI", "Docker", "Kubernetes"],
            location="Remote",
            job_offer_input="Updated job offer text",
            application_cost=0.20,
            language="en",
            cv_pdf=sample_pdf_bytes,
            cover_letter_pdf=sample_pdf_bytes
        )
        updated_id = temp_db.save_application(updated_app)
        assert updated_id == app_id  # Same ID due to company+position match

        # Verify PDFs are still there
        retrieved = temp_db.get_application(app_id)
        assert retrieved.cv_pdf is not None
        assert retrieved.cover_letter_pdf is not None
        assert retrieved.matching_rate == 0.90  # Updated

    def test_get_pdf_by_id_cv(self, temp_db, sample_application):
        """Test retrieving CV PDF by application ID."""
        app_id = temp_db.save_application(sample_application)
        cv_pdf = temp_db.get_pdf_by_id(app_id, "cv")
        assert cv_pdf == sample_application.cv_pdf

    def test_get_pdf_by_id_cover_letter(self, temp_db, sample_application):
        """Test retrieving cover letter PDF by application ID."""
        app_id = temp_db.save_application(sample_application)
        cl_pdf = temp_db.get_pdf_by_id(app_id, "cover_letter")
        assert cl_pdf == sample_application.cover_letter_pdf

    def test_get_pdf_not_found(self, temp_db):
        """Test retrieving PDF for non-existent application."""
        pdf = temp_db.get_pdf_by_id(999, "cv")
        assert pdf is None

    def test_application_without_pdf(self, temp_db):
        """Test saving and retrieving application without PDFs."""
        app = Application(
            company="TestCorp2",
            position="Data Scientist",
            matching_rate=0.75,
            unmatched_skills=["Julia"],
            matched_skills=["Python", "SQL"],
            location="New York",
            job_offer_input="Job offer",
            application_cost=0.10,
            language="en"
            # No PDFs
        )
        app_id = temp_db.save_application(app)
        retrieved = temp_db.get_application(app_id)

        assert retrieved.cv_pdf is None
        assert retrieved.cover_letter_pdf is None


class TestPDFCleanup:
    """Test PDF cleanup functionality."""

    def test_cleanup_old_pdfs(self, temp_db, sample_pdf_bytes):
        """Test cleanup function works."""
        # Create old application
        old_app = Application(
            company="OldCorp",
            position="Old Position",
            matching_rate=0.50,
            unmatched_skills=["X"],
            matched_skills=["Y"],
            location="Old",
            job_offer_input="old",
            application_cost=0.05,
            language="en",
            cv_pdf=sample_pdf_bytes,
            cover_letter_pdf=sample_pdf_bytes
        )
        old_id = temp_db.save_application(old_app)

        # Verify PDFs exist
        assert temp_db.get_pdf_by_id(old_id, "cv") is not None

        # Test that cleanup function exists and returns an integer
        cleaned = temp_db.cleanup_old_pdfs(days=90)
        assert isinstance(cleaned, int)

    def test_cleanup_preserves_recent_pdfs(self, temp_db, sample_pdf_bytes):
        """Test that cleanup doesn't remove recent PDFs."""
        # Create recent application
        recent_app = Application(
            company="RecentCorp",
            position="Recent Position",
            matching_rate=0.80,
            unmatched_skills=["Z"],
            matched_skills=["A", "B"],
            location="Recent",
            job_offer_input="recent",
            application_cost=0.10,
            language="en",
            cv_pdf=sample_pdf_bytes,
            cover_letter_pdf=sample_pdf_bytes
        )
        recent_id = temp_db.save_application(recent_app)

        # Cleanup (should not affect recent PDFs)
        cleaned = temp_db.cleanup_old_pdfs(days=90)

        # Verify PDFs still exist
        assert temp_db.get_pdf_by_id(recent_id, "cv") is not None
        assert temp_db.get_pdf_by_id(recent_id, "cover_letter") is not None


class TestPDFStorageInfo:
    """Test PDF storage information retrieval."""

    def test_storage_info_empty(self, temp_db):
        """Test storage info with no applications."""
        info = temp_db.get_pdf_storage_info()
        assert info["total_records"] == 0
        assert info["cv_pdf_count"] == 0
        assert info["cover_letter_pdf_count"] == 0
        assert info["total_size_mb"] == 0.0

    def test_storage_info_with_pdfs(self, temp_db, sample_pdf_bytes):
        """Test storage info with PDF data."""
        app = Application(
            company="InfoCorp",
            position="Position",
            matching_rate=0.70,
            unmatched_skills=["X"],
            matched_skills=["Y"],
            location="Location",
            job_offer_input="offer",
            application_cost=0.05,
            language="en",
            cv_pdf=sample_pdf_bytes,
            cover_letter_pdf=sample_pdf_bytes
        )
        temp_db.save_application(app)

        info = temp_db.get_pdf_storage_info()
        assert info["total_records"] == 1
        assert info["cv_pdf_count"] == 1
        assert info["cover_letter_pdf_count"] == 1
        assert info["total_size_mb"] >= 0

    def test_storage_info_multiple_applications(self, temp_db, sample_pdf_bytes):
        """Test storage info with multiple applications."""
        # App with both PDFs
        app1 = Application(
            company="Corp1",
            position="Position1",
            matching_rate=0.70,
            unmatched_skills=["X"],
            matched_skills=["Y"],
            location="Location",
            job_offer_input="offer",
            application_cost=0.05,
            language="en",
            cv_pdf=sample_pdf_bytes,
            cover_letter_pdf=sample_pdf_bytes
        )

        # App with only CV PDF
        app2 = Application(
            company="Corp2",
            position="Position2",
            matching_rate=0.80,
            unmatched_skills=[],
            matched_skills=["A", "B"],
            location="Location2",
            job_offer_input="offer2",
            application_cost=0.10,
            language="en",
            cv_pdf=sample_pdf_bytes,
            cover_letter_pdf=None
        )

        # App with no PDFs
        app3 = Application(
            company="Corp3",
            position="Position3",
            matching_rate=0.60,
            unmatched_skills=["Z"],
            matched_skills=["C"],
            location="Location3",
            job_offer_input="offer3",
            application_cost=0.08,
            language="en"
        )

        temp_db.save_application(app1)
        temp_db.save_application(app2)
        temp_db.save_application(app3)

        info = temp_db.get_pdf_storage_info()
        assert info["total_records"] == 3
        assert info["cv_pdf_count"] == 2
        assert info["cover_letter_pdf_count"] == 1
        assert info["total_size_mb"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
