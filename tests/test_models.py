"""
Tests for the data models in src/models.py
"""
import pytest
from datetime import datetime, timedelta

from src.models import Duty, StaffMember, Absence


class TestDuty:
    """Tests for the Duty dataclass."""

    def test_duty_creation(self):
        """Test creating a Duty with required fields."""
        begin = datetime(2024, 1, 15, 8, 0)
        end = datetime(2024, 1, 15, 16, 0)

        duty = Duty(begin=begin, end=end)

        assert duty.begin == begin
        assert duty.end == end
        assert duty.vehicle is None
        assert duty.location is None
        assert duty.duty_type is None
        assert duty.crew == []
        assert duty.comment is None

    def test_duty_with_all_fields(self):
        """Test creating a Duty with all fields."""
        begin = datetime(2024, 1, 15, 8, 0)
        end = datetime(2024, 1, 15, 16, 0)
        crew = ["Max Mustermann", "Erika Musterfrau"]

        duty = Duty(
            begin=begin,
            end=end,
            vehicle="RTW 1",
            location="Ort A",
            duty_type="Tagdienst",
            crew=crew,
            comment="Testkommentar"
        )

        assert duty.vehicle == "RTW 1"
        assert duty.location == "Ort A"
        assert duty.duty_type == "Tagdienst"
        assert duty.crew == crew
        assert duty.comment == "Testkommentar"

    def test_duty_duration_hours(self):
        """Test the duration_hours property."""
        begin = datetime(2024, 1, 15, 8, 0)
        end = datetime(2024, 1, 15, 16, 0)  # 8 hours

        duty = Duty(begin=begin, end=end)

        assert duty.duration_hours == 8.0

    def test_duty_duration_hours_with_minutes(self):
        """Test duration_hours with partial hours."""
        begin = datetime(2024, 1, 15, 8, 0)
        end = datetime(2024, 1, 15, 14, 30)  # 6.5 hours

        duty = Duty(begin=begin, end=end)

        assert duty.duration_hours == 6.5

    def test_duty_duration_overnight(self):
        """Test duration_hours for overnight shifts."""
        begin = datetime(2024, 1, 15, 20, 0)
        end = datetime(2024, 1, 16, 8, 0)  # 12 hours

        duty = Duty(begin=begin, end=end)

        assert duty.duration_hours == 12.0

    def test_duty_crew_default_empty_list(self):
        """Test that crew defaults to empty list."""
        duty1 = Duty(begin=datetime.now(), end=datetime.now())
        duty2 = Duty(begin=datetime.now(), end=datetime.now())

        # Ensure they don't share the same list instance
        duty1.crew.append("Test")
        assert "Test" not in duty2.crew


class TestStaffMember:
    """Tests for the StaffMember dataclass."""

    def test_staff_member_creation(self):
        """Test creating a StaffMember with minimal fields."""
        member = StaffMember(name="Max Mustermann")

        assert member.name == "Max Mustermann"
        assert member.personalnummer is None
        assert member.email is None
        assert member.score == 0
        assert member.raw_data == {}

    def test_staff_member_with_all_fields(self):
        """Test creating a StaffMember with all fields."""
        member = StaffMember(
            name="Max Mustermann",
            personalnummer="12345",
            email="max@example.com",
            email_privat="max.privat@example.com",
            phone="+43 1 234567",
            phone_privat="+43 699 1234567",
            mobile="+43 660 1234567",
            role="Rettungssanitäter",
            score=100,
            raw_data={"extra": "data"}
        )

        assert member.name == "Max Mustermann"
        assert member.personalnummer == "12345"
        assert member.email == "max@example.com"
        assert member.email_privat == "max.privat@example.com"
        assert member.phone == "+43 1 234567"
        assert member.phone_privat == "+43 699 1234567"
        assert member.mobile == "+43 660 1234567"
        assert member.role == "Rettungssanitäter"
        assert member.score == 100
        assert member.raw_data == {"extra": "data"}

    def test_staff_member_display_name(self):
        """Test the display_name property."""
        member = StaffMember(name="Max Mustermann")

        assert member.display_name == "Max Mustermann"

    def test_staff_member_raw_data_default(self):
        """Test that raw_data defaults to empty dict."""
        member1 = StaffMember(name="Test 1")
        member2 = StaffMember(name="Test 2")

        # Ensure they don't share the same dict instance
        member1.raw_data["key"] = "value"
        assert "key" not in member2.raw_data


class TestAbsence:
    """Tests for the Absence dataclass."""

    def test_absence_creation(self):
        """Test creating an Absence with required fields."""
        begin = datetime(2024, 1, 15)
        end = datetime(2024, 1, 20)

        absence = Absence(begin=begin, end=end, reason="Urlaub")

        assert absence.begin == begin
        assert absence.end == end
        assert absence.reason == "Urlaub"
        assert absence.is_vacation is False
        assert absence.status_text is None

    def test_absence_vacation(self):
        """Test creating a vacation absence."""
        absence = Absence(
            begin=datetime(2024, 1, 15),
            end=datetime(2024, 1, 20),
            reason="Urlaub",
            is_vacation=True,
            status_text="(Genehmigt)"
        )

        assert absence.is_vacation is True
        assert absence.status_text == "(Genehmigt)"

    def test_absence_sick_leave(self):
        """Test creating a sick leave absence."""
        absence = Absence(
            begin=datetime(2024, 1, 15),
            end=datetime(2024, 1, 16),
            reason="Krankenstand",
            is_vacation=False
        )

        assert absence.reason == "Krankenstand"
        assert absence.is_vacation is False
