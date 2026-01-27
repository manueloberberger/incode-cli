"""
Tests for the pdf module in src/pdf.py
"""
import pytest
import os
import sys
import tempfile
from datetime import datetime
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models import Duty


class TestExportToPdf:
    """Tests for export_to_pdf function."""

    @patch('src.pdf.console')
    def test_export_empty_list(self, mock_console):
        """Test exporting an empty duty list."""
        from src.pdf import export_to_pdf

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            filepath = f.name

        try:
            result = export_to_pdf([], filepath)
            assert result is True
            assert os.path.exists(filepath)
            assert os.path.getsize(filepath) > 0
        finally:
            os.unlink(filepath)

    @patch('src.pdf.console')
    def test_export_with_duty_objects(self, mock_console):
        """Test exporting Duty dataclass objects."""
        from src.pdf import export_to_pdf

        duties = [
            Duty(
                begin=datetime(2026, 1, 15, 8, 0),
                end=datetime(2026, 1, 15, 16, 0),
                location="Wien",
                vehicle="RTW 1",
                duty_type="Rettungsdienst",
                crew=["Max Mustermann", "Anna Schmidt"],
                comment=""
            ),
            Duty(
                begin=datetime(2026, 1, 16, 7, 0),
                end=datetime(2026, 1, 16, 19, 0),
                location="Graz",
                vehicle="KTW 2",
                duty_type="KTW",
                crew=["Hans Huber"],
                comment=""
            )
        ]

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            filepath = f.name

        try:
            result = export_to_pdf(duties, filepath, title_text="Test Dienstplan")
            assert result is True
            assert os.path.exists(filepath)
            assert os.path.getsize(filepath) > 1000  # PDF should have content
        finally:
            os.unlink(filepath)

    @patch('src.pdf.console')
    def test_export_with_dict_duties(self, mock_console):
        """Test exporting dict-based duties."""
        from src.pdf import export_to_pdf

        duties = [
            {
                'begin': datetime(2026, 2, 20, 7, 0),
                'end': datetime(2026, 2, 20, 19, 0),
                'vehicle': 'KTW 2',
                'crew': ['Hans Huber', 'Maria Maier']
            }
        ]

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            filepath = f.name

        try:
            result = export_to_pdf(duties, filepath)
            assert result is True
        finally:
            os.unlink(filepath)

    @patch('src.pdf.console')
    def test_export_with_string_dates(self, mock_console):
        """Test exporting duties with ISO string dates."""
        from src.pdf import export_to_pdf

        duties = [
            {
                'begin': '2026-03-10T08:00:00',
                'end': '2026-03-10T16:00:00',
                'vehicle': 'NEF',
                'crew': []
            }
        ]

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            filepath = f.name

        try:
            result = export_to_pdf(duties, filepath)
            assert result is True
        finally:
            os.unlink(filepath)

    @patch('src.pdf.console')
    def test_export_with_dict_crew(self, mock_console):
        """Test exporting duties with dict-based crew (daily plan format)."""
        from src.pdf import export_to_pdf

        duties = [
            {
                'begin': datetime(2026, 1, 20, 6, 0),
                'end': datetime(2026, 1, 20, 18, 0),
                'vehicle': 'RTW 3',
                'crew': {
                    'FAHRER': 'Max Mustermann',
                    'SANITAETER1': 'Anna Schmidt',
                    'SANITAETER2': 'Hans Huber'
                }
            }
        ]

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            filepath = f.name

        try:
            result = export_to_pdf(duties, filepath)
            assert result is True
        finally:
            os.unlink(filepath)

    @patch('src.pdf.console')
    def test_export_skips_invalid_entries(self, mock_console):
        """Test that invalid entries are skipped without failing."""
        from src.pdf import export_to_pdf

        duties = [
            {'begin': 'invalid', 'end': 'invalid'},  # Invalid dates
            {
                'begin': datetime(2026, 1, 1, 8, 0),
                'end': datetime(2026, 1, 1, 16, 0),
                'vehicle': 'Valid'
            }
        ]

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            filepath = f.name

        try:
            result = export_to_pdf(duties, filepath)
            assert result is True
        finally:
            os.unlink(filepath)


class TestExportAbsencesToPdf:
    """Tests for export_absences_to_pdf function."""

    @patch('src.pdf.console')
    def test_export_empty_absences(self, mock_console):
        """Test exporting an empty absence list."""
        from src.pdf import export_absences_to_pdf

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            filepath = f.name

        try:
            result = export_absences_to_pdf([], filepath)
            assert result is True
            assert os.path.exists(filepath)
        finally:
            os.unlink(filepath)

    @patch('src.pdf.console')
    def test_export_with_absences(self, mock_console):
        """Test exporting absences."""
        from src.pdf import export_absences_to_pdf

        absences = [
            {
                'begin': '2026-01-15T00:00:00',
                'end': '2026-01-17T00:00:00',
                'duty_type': 'Urlaub'
            },
            {
                'begin': '2026-02-01T08:00:00',
                'end': '2026-02-01T16:00:00',
                'duty_type': 'Zeitausgleich'
            }
        ]

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            filepath = f.name

        try:
            result = export_absences_to_pdf(absences, filepath, title_text="Mein Urlaub")
            assert result is True
            assert os.path.getsize(filepath) > 1000
        finally:
            os.unlink(filepath)

    @patch('src.pdf.console')
    def test_export_single_day_absence(self, mock_console):
        """Test exporting a single day absence."""
        from src.pdf import export_absences_to_pdf

        absences = [
            {
                'begin': '2026-03-10T00:00:00',
                'end': '2026-03-11T00:00:00',
                'duty_type': 'Urlaub'
            }
        ]

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            filepath = f.name

        try:
            result = export_absences_to_pdf(absences, filepath)
            assert result is True
        finally:
            os.unlink(filepath)

    @patch('src.pdf.console')
    def test_export_overnight_adjustment(self, mock_console):
        """Test that overnight shifts are adjusted correctly."""
        from src.pdf import export_absences_to_pdf

        absences = [
            {
                'begin': '2026-01-20T20:00:00',  # Starts at 20:00
                'end': '2026-01-21T08:00:00',
                'duty_type': 'Nachtdienst'
            }
        ]

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            filepath = f.name

        try:
            result = export_absences_to_pdf(absences, filepath)
            assert result is True
        finally:
            os.unlink(filepath)

    @patch('src.pdf.console')
    def test_export_skips_invalid_absences(self, mock_console):
        """Test that invalid absence entries are skipped."""
        from src.pdf import export_absences_to_pdf

        absences = [
            {'begin': 'invalid', 'end': 'invalid'},  # Invalid
            {
                'begin': '2026-01-15T00:00:00',
                'end': '2026-01-16T00:00:00',
                'duty_type': 'Valid'
            }
        ]

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            filepath = f.name

        try:
            result = export_absences_to_pdf(absences, filepath)
            assert result is True
        finally:
            os.unlink(filepath)
