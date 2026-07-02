from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Employee, Gender
from app.repository import EmployeeRepository
from app.schemas import EmployeeFilters, EmployeeFormInput
from app.service import EmployeeService

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_employee_service(session: AsyncSession = Depends(get_db)) -> EmployeeService:
    return EmployeeService(EmployeeRepository(session))


def parse_genders(values: list[str]) -> list[Gender]:
    parsed = []
    for value in values:
        try:
            parsed.append(Gender(value))
        except ValueError:
            continue
    return parsed


def parse_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def form_context(errors: dict | None = None, values: dict | None = None, employee: Employee | None = None) -> dict:
    return {
        "errors": errors or {},
        "values": values or {},
        "employee": employee,
        "genders": Gender,
        "today": date.today().isoformat(),
    }


async def get_employee_or_404(employee_id: int, service: EmployeeService) -> Employee:
    employee = await service.get(employee_id)
    if not employee:
        raise HTTPException(status_code=404)
    return employee


@router.get("/")
async def registry(
    request: Request,
    q: str | None = None,
    gender: list[str] | None = Query(None),
    age_from: str | None = None,
    age_to: str | None = None,
    page: int = 1,
    service: EmployeeService = Depends(get_employee_service),
):
    genders = parse_genders(gender or [])
    result = await service.search(
        EmployeeFilters(
            query=q,
            genders=genders or None,
            age_from=parse_int(age_from),
            age_to=parse_int(age_to),
            page=page,
        )
    )
    return templates.TemplateResponse(
        request,
        "registry.html",
        {
            "employees": result.items,
            "total": result.total,
            "page": result.page,
            "total_pages": result.total_pages,
            "q": q or "",
            "selected_genders": {g.value for g in genders},
            "age_from": age_from or "",
            "age_to": age_to or "",
        },
    )


@router.get("/employees/{employee_id}/photo")
async def employee_photo(employee_id: int, service: EmployeeService = Depends(get_employee_service)):
    employee = await get_employee_or_404(employee_id, service)
    if not employee.photo:
        raise HTTPException(status_code=404)
    return Response(content=employee.photo, media_type=employee.photo_content_type or "image/jpeg")


@router.get("/employees/new")
async def new_employee_form(request: Request):
    return templates.TemplateResponse(request, "employee_form.html", form_context())


@router.get("/employees/{employee_id}/edit")
async def edit_employee_form(
    request: Request, employee_id: int, service: EmployeeService = Depends(get_employee_service)
):
    employee = await get_employee_or_404(employee_id, service)
    return templates.TemplateResponse(request, "employee_form.html", form_context(employee=employee))


@router.post("/employees/new")
async def create_employee(
    request: Request,
    last_name: str = Form(...),
    first_name: str = Form(...),
    middle_name: str = Form(""),
    phone: str = Form(""),
    birth_date: str = Form(...),
    gender: str = Form(""),
    photo: UploadFile | None = File(None),
    service: EmployeeService = Depends(get_employee_service),
):
    form = EmployeeFormInput(last_name, first_name, middle_name, phone, birth_date, gender)
    _, errors = await service.create(form, photo)
    if errors:
        return templates.TemplateResponse(
            request, "employee_form.html", form_context(errors=errors, values=asdict(form)), status_code=422
        )
    return RedirectResponse(url="/", status_code=303)


@router.post("/employees/{employee_id}/edit")
async def update_employee(
    request: Request,
    employee_id: int,
    last_name: str = Form(...),
    first_name: str = Form(...),
    middle_name: str = Form(""),
    phone: str = Form(""),
    birth_date: str = Form(...),
    gender: str = Form(""),
    photo: UploadFile | None = File(None),
    remove_photo: str = Form(""),
    service: EmployeeService = Depends(get_employee_service),
):
    employee = await get_employee_or_404(employee_id, service)
    form = EmployeeFormInput(last_name, first_name, middle_name, phone, birth_date, gender)
    errors = await service.update(employee, form, photo, remove_photo == "1")
    if errors:
        return templates.TemplateResponse(
            request,
            "employee_form.html",
            form_context(errors=errors, values=asdict(form), employee=employee),
            status_code=422,
        )
    return RedirectResponse(url="/", status_code=303)


@router.post("/employees/{employee_id}/delete")
async def delete_employee(employee_id: int, service: EmployeeService = Depends(get_employee_service)):
    employee = await get_employee_or_404(employee_id, service)
    await service.delete(employee)
    return RedirectResponse(url="/", status_code=303)
