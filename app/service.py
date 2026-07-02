from fastapi import UploadFile

from app.models import Employee
from app.repository import EmployeeRepository
from app.schemas import EmployeeFilters, EmployeeFormInput, PageResult
from app.validators import EmployeeFormValidator, validate_photo

PAGE_SIZE = 10


class EmployeeService:
    def __init__(self, repository: EmployeeRepository):
        self._repository = repository

    async def get(self, employee_id: int) -> Employee | None:
        return await self._repository.get_by_id(employee_id)

    async def search(self, filters: EmployeeFilters) -> PageResult:
        employees = await self._repository.list_employees(filters)
        return self._paginate(employees, filters.page)

    async def create(self, form: EmployeeFormInput, photo: UploadFile | None) -> tuple[Employee | None, dict[str, str]]:
        validation = EmployeeFormValidator.validate(form)
        photo_result = await validate_photo(photo)
        errors = dict(validation.errors)
        if photo_result.error:
            errors["photo"] = photo_result.error
        if errors:
            return None, errors

        employee = Employee(
            last_name=form.last_name.strip(),
            first_name=form.first_name.strip(),
            middle_name=form.middle_name.strip() or None,
            phone=form.phone.strip() or None,
            birth_date=validation.birth_date,
            gender=validation.gender,
            photo=photo_result.data,
            photo_content_type=photo_result.content_type,
        )
        return await self._repository.add(employee), {}

    async def update(
        self, employee: Employee, form: EmployeeFormInput, photo: UploadFile | None, remove_photo: bool
    ) -> dict[str, str]:
        validation = EmployeeFormValidator.validate(form)
        photo_result = await validate_photo(photo)
        errors = dict(validation.errors)
        if photo_result.error:
            errors["photo"] = photo_result.error
        if errors:
            return errors

        changes = {
            "last_name": form.last_name.strip(),
            "first_name": form.first_name.strip(),
            "middle_name": form.middle_name.strip() or None,
            "phone": form.phone.strip() or None,
            "birth_date": validation.birth_date,
            "gender": validation.gender,
        }
        if photo_result.data is not None:
            changes["photo"] = photo_result.data
            changes["photo_content_type"] = photo_result.content_type
        elif remove_photo:
            changes["photo"] = None
            changes["photo_content_type"] = None

        await self._repository.update(employee, changes)
        return {}

    async def delete(self, employee: Employee) -> None:
        await self._repository.delete(employee)

    @staticmethod
    def _paginate(employees: list[Employee], page: int) -> PageResult:
        total = len(employees)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(1, min(page, total_pages))
        start = (page - 1) * PAGE_SIZE
        return PageResult(items=employees[start : start + PAGE_SIZE], total=total, page=page, total_pages=total_pages)
