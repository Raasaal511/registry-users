from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Employee, Gender


class EmployeeRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, employee_id: int) -> Employee | None:
        return await self._session.get(Employee, employee_id)

    async def list_by_gender(self, genders: list[Gender] | None) -> list[Employee]:
        stmt = select(Employee).order_by(Employee.last_name, Employee.first_name)
        if genders:
            stmt = stmt.where(Employee.gender.in_(genders))
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
