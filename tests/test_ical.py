"""
Tests for the ical module in src/ical.py
"""
import pytest
import os
import sys
import tempfile
from datetime import datetime
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models import Duty


class TestExportToIcs:
    """Tests for export_to_ics function."""

    @patch('src.ical.console')
    def test_export_empty_list(self, mock_console):
        """Test exporting an empty duty list."""
        from src.ical import export_to_ics

        with tempfile.NamedTemporaryFile(suffix='.ics', delete=False) as f:
            filepath = f.name

        try:
            result = export_to_ics([], filepath)
            assert result is True
            assert os.path.exists(filepath)

            # Check file contains basic calendar structure
            with open(filepath, 'rb') as f:
                content = f.read().decode('utf-8')
            assert 'BEGIN:VCALENDAR' in content
            assert 'END:VCALENDAR' in content
        finally:
            os.unlink(filepath)

    @patch('src.ical.console')
    def test_export_with_duty_objects(self, mock_console):
        """Test exporting Duty dataclass objects."""
        from src.ical import export_to_ics

        duties = [
            Duty(
                begin=datetime(2026, 1, 15, 8, 0),
                end=datetime(2026, 1, 15, 16, 0),
                location="Wien",
                vehicle="RTW 1",
                duty_type="Rettungsdienst",
                crew=["Max Mustermann", "Anna Schmidt"],
                comment=""
            )
        ]

        with tempfile.NamedTemporaryFile(suffix='.ics', delete=False) as f:
            filepath = f.name

        try:
            result = export_to_ics(duties, filepath)
            assert result is True

            with open(filepath, 'rb') as f:
                content = f.read().decode('utf-8')

            assert 'BEGIN:VEVENT' in content
            assert 'RTW 1' in content
            assert 'Wien' in content
            assert 'Max Mustermann' in content
        finally:
            os.unlink(filepath)

    @patch('src.ical.console')
    def test_export_with_dict_duties(self, mock_console):
        """Test exporting dict-based duties."""
        from src.ical import export_to_ics

        duties = [
            {
                'begin': datetime(2026, 2, 20, 7, 0),
                'end': datetime(2026, 2, 20, 19, 0),
                'location': 'Graz',
                'vehicle': 'KTW 2',
                'duty_type': 'KTW Dienst',
                'crew': ['Hans Huber']
            }
        ]

        with tempfile.NamedTemporaryFile(suffix='.ics', delete=False) as f:
            filepath = f.name

        try:
            result = export_to_ics(duties, filepath)
            assert result is True

            with open(filepath, 'rb') as f:
                content = f.read().decode('utf-8')

            assert 'KTW 2' in content
            assert 'Graz' in content
        finally:
            os.unlink(filepath)

    @patch('src.ical.console')
    def test_export_with_string_dates(self, mock_console):
        """Test exporting duties with ISO string dates."""
        from src.ical import export_to_ics

        duties = [
            {
                'begin': '2026-03-10T08:00:00',
                'end': '2026-03-10T16:00:00',
                'vehicle': 'NEF',
                'location': 'Linz'
            }
        ]

        with tempfile.NamedTemporaryFile(suffix='.ics', delete=False) as f:
            filepath = f.name

        try:
            result = export_to_ics(duties, filepath)
            assert result is True

            with open(filepath, 'rb') as f:
                content = f.read().decode('utf-8')

            assert 'NEF' in content
        finally:
            os.unlink(filepath)

    @patch('src.ical.console')
    def test_export_skips_invalid_entries(self, mock_console):
        """Test that invalid entries are skipped without failing."""
        from src.ical import export_to_ics

        duties = [
            {'begin': None, 'end': None},  # Invalid - no dates
            {
                'begin': datetime(2026, 1, 1, 8, 0),
                'end': datetime(2026, 1, 1, 16, 0),
                'vehicle': 'Valid Entry'
            }
        ]

        with tempfile.NamedTemporaryFile(suffix='.ics', delete=False) as f:
            filepath = f.name

        try:
            result = export_to_ics(duties, filepath)
            assert result is True

            with open(filepath, 'rb') as f:
                content = f.read().decode('utf-8')

            # Only valid entry should be exported
            assert content.count('BEGIN:VEVENT') == 1
            assert 'Valid Entry' in content
        finally:
            os.unlink(filepath)

    @patch('src.ical.console')
    def test_export_file_write_error(self, mock_console):
        """Test handling of file write errors."""
        from src.ical import export_to_ics

        duties = [
            {
                'begin': datetime(2026, 1, 1, 8, 0),
                'end': datetime(2026, 1, 1, 16, 0),
                'vehicle': 'Test'
            }
        ]

        # Try to write to an invalid path
        result = export_to_ics(duties, '/nonexistent/path/file.ics')
        assert result is False


def test_calendar_identity_timezone_and_cancellations(tmp_path):
    from dataclasses import replace
    from icalendar import Calendar
    from src.ical import export_to_ics
    duty = Duty(datetime(2026, 10, 25, 7), datetime(2026, 10, 25, 19),
                vehicle='RTW', location='A', source_id='stable-1', source_scope='account-a')
    path = tmp_path / 'duties.ics'
    with patch('src.ical.console'):
        assert export_to_ics([duty, replace(duty), replace(duty, source_id='cancelled', is_cancelled=True)], str(path))
        original = Calendar.from_ical(path.read_bytes()).walk('VEVENT')
        assert len(original) == 1
        assert original[0].decoded('dtstamp').utcoffset().total_seconds() == 0
        assert original[0].decoded('dtstart').hour == 7
        assert original[0].decoded('dtstart').tzinfo is not None
        assert export_to_ics([replace(duty, begin=datetime(2026, 10, 25, 8), vehicle='KTW')], str(path))
        updated = Calendar.from_ical(path.read_bytes()).walk('VEVENT')
    assert original[0]['UID'] == updated[0]['UID']


def test_calendar_legacy_simultaneous_distinct_duties(tmp_path):
    from dataclasses import replace
    from icalendar import Calendar
    from src.ical import export_to_ics
    first = Duty(datetime(2026, 10, 20, 8), datetime(2026, 10, 20, 16), vehicle='RTW', location='A')
    second = replace(first, end=datetime(2026, 10, 20, 12), location='B')
    path = tmp_path / 'duties.ics'
    with patch('src.ical.console'):
        assert export_to_ics([first, second], str(path))
    events = Calendar.from_ical(path.read_bytes()).walk('VEVENT')
    assert len({str(event['UID']) for event in events}) == 2
