from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

@dataclass
class Duty:
    begin: datetime
    end: datetime
    vehicle: Optional[str] = None
    location: Optional[str] = None
    duty_type: Optional[str] = None
    crew: List[str] = field(default_factory=list)
    # Extra fields for flexibility
    comment: Optional[str] = None
    
    @property
    def duration_hours(self) -> float:
        return (self.end - self.begin).total_seconds() / 3600

@dataclass
class StaffMember:
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
        return self.name

@dataclass
class Absence:
    begin: datetime
    end: datetime
    reason: str
    is_vacation: bool = False
    status_text: Optional[str] = None # e.g. "(Beantragt)"
