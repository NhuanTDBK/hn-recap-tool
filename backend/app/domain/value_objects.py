"""Domain value objects - Immutable objects without identity.

Using Pydantic for pragmatic validation and immutability.
Value objects represent concepts defined by their attributes rather than identity.
"""

from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import ClassVar
import re


class Email(BaseModel):
    """Email address value object with validation.

    Attributes:
        address: The email address string
    """
    address: EmailStr

    model_config = {"frozen": True}  # Immutable

    def __str__(self) -> str:
        """Return the email address as string."""
        return str(self.address)

    @property
    def domain(self) -> str:
        """Extract domain from email address."""
        return str(self.address).split('@')[1]


class Password(BaseModel):
    """Password value object with validation rules.

    Attributes:
        value: The plain text password (should be hashed before storage)
    """
    value: str = Field(min_length=8, max_length=128)

    model_config = {"frozen": True}  # Immutable

    def __str__(self) -> str:
        """Return masked password for display."""
        return "********"


class DateRange(BaseModel):
    """Date range value object for filtering digests.

    Attributes:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    start_date: str
    end_date: str

    DATE_PATTERN: ClassVar[re.Pattern] = re.compile(r'^\d{4}-\d{2}-\d{2}$')

    model_config = {"frozen": True}  # Immutable

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date format is YYYY-MM-DD."""
        if not cls.DATE_PATTERN.match(v):
            raise ValueError(f"Invalid date format: {v}. Must be YYYY-MM-DD")
        return v

    def model_post_init(self, __context) -> None:
        """Validate date range after initialization."""
        if self.start_date > self.end_date:
            raise ValueError(
                f"Start date {self.start_date} must be before or equal to end date {self.end_date}"
            )

    def contains(self, date: str) -> bool:
        """Check if a date falls within this range."""
        return self.start_date <= date <= self.end_date

    def days_count(self) -> int:
        """Calculate number of days in the range."""
        from datetime import datetime
        start = datetime.strptime(self.start_date, '%Y-%m-%d')
        end = datetime.strptime(self.end_date, '%Y-%m-%d')
        return (end - start).days + 1
