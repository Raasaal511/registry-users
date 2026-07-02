from sqlalchemy import or_
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

    if query:
        like = f"%{query}%"
        stmt = stmt.filter(
            or_(
                Employee.last_name.ilike(like),
                Employee.first_name.ilike(like),
                Employee.middle_name.ilike(like),
                Employee.phone.ilike(like),
            )
        )

    employees = stmt.order_by(Employee.last_name, Employee.first_name).all()

    if query and query.strip().isdigit():
        age_query = int(query.strip())
        text_matches = {e.id for e in employees}
        # widen with age-only matches from the gender-filtered set (ignore text filter)
        base_stmt = db.query(Employee)
        if genders:
            base_stmt = base_stmt.filter(Employee.gender.in_(genders))
        extra = [e for e in base_stmt.all() if e.age == age_query and e.id not in text_matches]
        employees = employees + extra
        employees.sort(key=lambda e: (e.last_name, e.first_name))

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
