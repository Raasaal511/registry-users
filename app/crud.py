from sqlalchemy.orm import Session

from app.models import Employee, Gender

PAGE_SIZE = 10


def get_employee(db: Session, employee_id: int) -> Employee | None:
    return db.get(Employee, employee_id)


def list_employees(
    db: Session,
    query: str | None = None,
    genders: list[Gender] | None = None,
    age_from: int | None = None,
    age_to: int | None = None,
    page: int = 1,
):
    stmt = db.query(Employee)

    if genders:
        stmt = stmt.filter(Employee.gender.in_(genders))

    employees = stmt.order_by(Employee.last_name, Employee.first_name).all()

    # Age is derived from birth_date, not a DB column, and SQLite/PostgreSQL
    # disagree on date arithmetic, so text/age search is matched in Python
    # for one consistent, portable behaviour across both databases.
    if query:
        needle = query.strip().lower()
        employees = [
            e
            for e in employees
            if needle in e.last_name.lower()
            or needle in e.first_name.lower()
            or needle in (e.middle_name or "").lower()
            or needle in (e.phone or "").lower()
            or needle in str(e.age)
        ]

    if age_from is not None:
        employees = [e for e in employees if e.age >= age_from]
    if age_to is not None:
        employees = [e for e in employees if e.age <= age_to]

    total = len(employees)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    page_items = employees[start : start + PAGE_SIZE]

    return page_items, total, page, total_pages


def create_employee(db: Session, **fields) -> Employee:
    employee = Employee(**fields)
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def update_employee(db: Session, employee: Employee, **fields) -> Employee:
    for key, value in fields.items():
        if key in ("photo", "photo_content_type") and value is None:
            continue
        setattr(employee, key, value)
    db.commit()
    db.refresh(employee)
    return employee


def delete_employee(db: Session, employee: Employee) -> None:
    db.delete(employee)
    db.commit()
