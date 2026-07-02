from datetime import date, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Employee
from app.schemas import EmployeeFilters


def _years_before(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year - years)
    except ValueError:
        return d.replace(month=2, day=28, year=d.year - years)


def _birth_date_range_for_age(today: date, age: int) -> tuple[date, date]:
    return _years_before(today, age + 1) + timedelta(days=1), _years_before(today, age)


class EmployeeRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, employee_id: int) -> Employee | None:
        return await self._session.get(Employee, employee_id)

    async def list_employees(self, filters: EmployeeFilters) -> list[Employee]:
        stmt = select(Employee).order_by(Employee.last_name, Employee.first_name)
        today = date.today()

        if filters.genders:
            stmt = stmt.where(Employee.gender.in_(filters.genders))

        if filters.age_from is not None:
            stmt = stmt.where(Employee.birth_date <= _years_before(today, filters.age_from))
        if filters.age_to is not None:
            lower_bound, _ = _birth_date_range_for_age(today, filters.age_to)
            stmt = stmt.where(Employee.birth_date >= lower_bound)

        if filters.query:
            needle = filters.query.strip()
            like = f"%{needle}%"
            conditions = [
                Employee.last_name.ilike(like),
                Employee.first_name.ilike(like),
                Employee.middle_name.ilike(like),
                Employee.phone.ilike(like),
            ]
            if needle.isdigit():
                lower, upper = _birth_date_range_for_age(today, int(needle))
                conditions.append(Employee.birth_date.between(lower, upper))
            stmt = stmt.where(or_(*conditions))

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def add(self, employee: Employee) -> Employee:
        self._session.add(employee)
        await self._session.commit()
        await self._session.refresh(employee)
        return employee

    async def update(self, employee: Employee, changes: dict) -> Employee:
        for field, value in changes.items():
            setattr(employee, field, value)
        await self._session.commit()
        await self._session.refresh(employee)
        return employee

    async def delete(self, employee: Employee) -> None:
        await self._session.delete(employee)
        await self._session.commit()
