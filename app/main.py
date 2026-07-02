from datetime import date, datetime

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import crud
from app.database import Base, engine, get_db
from app.models import Employee, Gender

MAX_PHOTO_SIZE = 200 * 1024  # 200 kB, per spec

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Реестр сотрудников")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def parse_genders(genders: list[str]) -> list[Gender]:
    result = []
    for g in genders:
        try:
            result.append(Gender(g))
        except ValueError:
            continue
    return result


def parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


@app.get("/")
def registry(
    request: Request,
    q: str | None = None,
    gender: list[str] | None = Query(None),
    age_from: str | None = None,
    age_to: str | None = None,
    page: int = 1,
    db: Session = Depends(get_db),
):
    genders = parse_genders(gender or [])
    employees, total, page, total_pages = crud.list_employees(
        db,
        query=q,
        genders=genders or None,
        age_from=parse_int(age_from),
        age_to=parse_int(age_to),
        page=page,
    )
    return templates.TemplateResponse(
        request,
        "registry.html",
        {
            "employees": employees,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "q": q or "",
            "selected_genders": {g.value for g in genders},
            "age_from": age_from or "",
            "age_to": age_to or "",
        },
    )


@app.get("/employees/{employee_id}/photo")
def employee_photo(employee_id: int, db: Session = Depends(get_db)):
    employee = crud.get_employee(db, employee_id)
    if not employee or not employee.photo:
        raise HTTPException(status_code=404)
    return Response(content=employee.photo, media_type=employee.photo_content_type or "image/jpeg")


def _form_context(errors: dict | None = None, values: dict | None = None, employee: Employee | None = None):
    return {
        "errors": errors or {},
        "values": values or {},
        "employee": employee,
        "genders": Gender,
        "today": date.today().isoformat(),
    }


@app.get("/employees/new")
def new_employee_form(request: Request):
    return templates.TemplateResponse(request, "employee_form.html", _form_context())


@app.get("/employees/{employee_id}/edit")
def edit_employee_form(request: Request, employee_id: int, db: Session = Depends(get_db)):
    employee = crud.get_employee(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "employee_form.html", _form_context(employee=employee))


async def _read_photo(photo: UploadFile | None) -> tuple[bytes | None, str | None, str | None]:
    """Returns (data, content_type, error)."""
    if photo is None or not photo.filename:
        return None, None, None
    if photo.content_type and not photo.content_type.startswith("image/"):
        return None, None, "Файл должен быть изображением."
    data = await photo.read()
    if len(data) > MAX_PHOTO_SIZE:
        return None, None, "Размер фото не должен превышать 200 кБ."
    if not data:
        return None, None, None
    return data, photo.content_type, None


def _validate_employee_form(
    last_name: str, first_name: str, birth_date: str, gender: str
) -> tuple[date | None, Gender | None, dict[str, str]]:
    errors: dict[str, str] = {}

    if not last_name.strip():
        errors["last_name"] = "Обязательное поле."
    if not first_name.strip():
        errors["first_name"] = "Обязательное поле."

    parsed_date = None
    if not birth_date:
        errors["birth_date"] = "Обязательное поле."
    else:
        try:
            parsed_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
            if parsed_date > date.today():
                errors["birth_date"] = "Дата рождения не может быть в будущем."
        except ValueError:
            errors["birth_date"] = "Некорректная дата."

    parsed_gender = None
    if not gender:
        errors["gender"] = "Обязательное поле."
    else:
        try:
            parsed_gender = Gender(gender)
        except ValueError:
            errors["gender"] = "Некорректное значение."

    return parsed_date, parsed_gender, errors


@app.post("/employees/new")
async def create_employee(
    request: Request,
    last_name: str = Form(...),
    first_name: str = Form(...),
    middle_name: str = Form(""),
    phone: str = Form(""),
    birth_date: str = Form(...),
    gender: str = Form(""),
    photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    values = {
        "last_name": last_name,
        "first_name": first_name,
        "middle_name": middle_name,
        "phone": phone,
        "birth_date": birth_date,
        "gender": gender,
    }
    parsed_date, parsed_gender, errors = _validate_employee_form(last_name, first_name, birth_date, gender)

    photo_data, photo_content_type, photo_error = await _read_photo(photo)
    if photo_error:
        errors["photo"] = photo_error

    if errors:
        return templates.TemplateResponse(
            request,
            "employee_form.html",
            _form_context(errors=errors, values=values),
            status_code=422,
        )

    crud.create_employee(
        db,
        last_name=last_name.strip(),
        first_name=first_name.strip(),
        middle_name=middle_name.strip() or None,
        phone=phone.strip() or None,
        birth_date=parsed_date,
        gender=parsed_gender,
        photo=photo_data,
        photo_content_type=photo_content_type,
    )
    return RedirectResponse(url="/", status_code=303)


@app.post("/employees/{employee_id}/edit")
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
    db: Session = Depends(get_db),
):
    employee = crud.get_employee(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404)

    values = {
        "last_name": last_name,
        "first_name": first_name,
        "middle_name": middle_name,
        "phone": phone,
        "birth_date": birth_date,
        "gender": gender,
    }
    parsed_date, parsed_gender, errors = _validate_employee_form(last_name, first_name, birth_date, gender)

    photo_data, photo_content_type, photo_error = await _read_photo(photo)
    if photo_error:
        errors["photo"] = photo_error

    if errors:
        return templates.TemplateResponse(
            request,
            "employee_form.html",
            _form_context(errors=errors, values=values, employee=employee),
            status_code=422,
        )

    update_fields = dict(
        last_name=last_name.strip(),
        first_name=first_name.strip(),
        middle_name=middle_name.strip() or None,
        phone=phone.strip() or None,
        birth_date=parsed_date,
        gender=parsed_gender,
    )
    if photo_data is not None:
        update_fields["photo"] = photo_data
        update_fields["photo_content_type"] = photo_content_type
    elif remove_photo == "1":
        employee.photo = None
        employee.photo_content_type = None

    crud.update_employee(db, employee, **update_fields)
    return RedirectResponse(url="/", status_code=303)


@app.post("/employees/{employee_id}/delete")
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = crud.get_employee(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404)
    crud.delete_employee(db, employee)
    return RedirectResponse(url="/", status_code=303)
