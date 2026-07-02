from dataclasses import dataclass
from datetime import date

from app.models import Employee, Gender


@dataclass
class EmployeeFormInput:
    last_name: str
    first_name: str
    middle_name: str
    phone: str
    birth_date: str
    gender: str


@dataclass
class EmployeeFilters:
    query: str | None = None
    genders: list[Gender] | None = None
    age_from: int | None = None
    age_to: int | None = None
    page: int = 1


@dataclass
class PageResult:
    items: list[Employee]
    total: int
    page: int
    total_pages: int


@dataclass
class FormValidationResult:
    birth_date: date | None
    gender: Gender | None
    errors: dict[str, str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


@dataclass
class PhotoResult:
    data: bytes | None
    content_type: str | None
    error: str | None
