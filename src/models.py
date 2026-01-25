"""
Data models for incode-cli.

This module defines the core data structures used throughout the application
for representing duties, staff members, and absences.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class Duty:
    """
    Represents a duty/shift assignment.
    
    Attributes:
        begin: Start datetime of the duty.
        end: End datetime of the duty.
        vehicle: Vehicle identifier (e.g., 'RTW 1', 'KTW 2').
        location: Station or location name.
        duty_type: Type of duty (e.g., 'Tagdienst', 'Nachtdienst').
        crew: List of crew member names assigned to this duty.
        comment: Optional additional notes or comments.
    """
    begin: datetime
    end: datetime
    vehicle: Optional[str] = None
    location: Optional[str] = None
    duty_type: Optional[str] = None
    crew: List[str] = field(default_factory=list)
    comment: Optional[str] = None
    
    @property
    def duration_hours(self) -> float:
        """Calculate the duration of the duty in hours."""
        return (self.end - self.begin).total_seconds() / 3600


@dataclass
class StaffMember:
    """
    Represents a staff member / colleague.
    
    Attributes:
        name: Full name of the staff member.
        personalnummer: Employee ID number.
        email: Work email address.
        email_privat: Private email address.
        phone: Work phone number.
        phone_privat: Private phone number.
        mobile: Mobile phone number.
        role: Role or position (e.g., 'Rettungssanitäter', 'Notfallsanitäter').
        score: Search relevance score for sorting results.
        raw_data: Original API response data for additional fields.
    """
    name: str
    personalnummer: Optional[str] = None
    email: Optional[str] = None
    email_privat: Optional[str] = None
    phone: Optional[str] = None
    phone_privat: Optional[str] = None
    mobile: Optional[str] = None
    role: Optional[str] = None
    score: int = 0
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def display_name(self) -> str:
        """Return the display name for this staff member."""
        return self.name


@dataclass
class Absence:
    """
    Represents an absence period (vacation, sick leave, etc.).
    
    Attributes:
        begin: Start datetime of the absence.
        end: End datetime of the absence.
        reason: Type/reason for absence (e.g., 'Urlaub', 'Krank').
        is_vacation: Whether this is a vacation/holiday absence.
        status_text: Approval status text (e.g., '(Beantragt)', '(Genehmigt)').
    """
    begin: datetime
    end: datetime
    reason: str
    is_vacation: bool = False
    status_text: Optional[str] = None
