import asyncio
import os
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_employees.db"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

client = TestClient(app)


async def _reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(autouse=True)
def clean_db():
    asyncio.run(_reset_db())
    yield
    asyncio.run(_reset_db())


def birth_date_for_age(age: int) -> str:
    today = date.today()
    return today.replace(year=today.year - age).isoformat()


def create_sample_employee(**overrides):
    data = {
        "last_name": "Иванов",
        "first_name": "Петр",
        "middle_name": "Петрович",
        "phone": "+79254455667",
        "birth_date": "2000-05-20",
        "gender": "male",
    }
    data.update(overrides)
    return client.post("/employees/new", data=data, follow_redirects=False)


def test_registry_page_loads_empty():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Сотрудники не найдены" in resp.text


def test_create_employee_success_redirects_to_registry():
    resp = create_sample_employee()
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"

    resp = client.get("/")
    assert "Иванов Петр Петрович" in resp.text
    assert "Муж." in resp.text


def test_create_employee_missing_required_field_shows_error():
    resp = create_sample_employee(last_name="")
    assert resp.status_code == 422
    assert "Обязательное поле" in resp.text


def test_create_employee_future_birth_date_rejected():
    resp = create_sample_employee(birth_date="2999-01-01")
    assert resp.status_code == 422


def test_edit_employee_updates_fields():
    create_sample_employee()
    resp = client.get("/")
    assert "Иванов" in resp.text

    edit_page = client.get("/employees/1/edit")
    assert edit_page.status_code == 200
    assert 'value="Иванов"' in edit_page.text

    resp = client.post(
        "/employees/1/edit",
        data={
            "last_name": "Сидоров",
            "first_name": "Петр",
            "middle_name": "Петрович",
            "phone": "+79254455667",
            "birth_date": "2000-05-20",
            "gender": "male",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303

    resp = client.get("/")
    assert "Сидоров Петр Петрович" in resp.text
    assert "Иванов Петр Петрович" not in resp.text


def test_delete_employee_removes_from_registry():
    create_sample_employee()
    resp = client.post("/employees/1/delete", follow_redirects=False)
    assert resp.status_code == 303

    resp = client.get("/")
    assert "Сотрудники не найдены" in resp.text


def test_search_by_last_name():
    create_sample_employee(last_name="Иванов", first_name="Петр")
    create_sample_employee(last_name="Петров", first_name="Олег")

    resp = client.get("/", params={"q": "Иванов"})
    assert "Иванов Петр" in resp.text
    assert "Петров Олег" not in resp.text


def test_filter_by_gender():
    create_sample_employee(last_name="Иванов", gender="male")
    create_sample_employee(last_name="Петрова", gender="female")

    resp = client.get("/", params={"gender": "female"})
    assert "Петрова" in resp.text
    assert "Иванов" not in resp.text


def test_filter_by_age_range():
    create_sample_employee(last_name="Молодой", birth_date=birth_date_for_age(20))
    create_sample_employee(last_name="Средний", birth_date=birth_date_for_age(30))
    create_sample_employee(last_name="Старший", birth_date=birth_date_for_age(50))

    resp = client.get("/", params={"age_from": 25, "age_to": 35})
    assert "Средний" in resp.text
    assert "Молодой" not in resp.text
    assert "Старший" not in resp.text


def test_search_by_exact_age():
    create_sample_employee(
        last_name="Иванов", first_name="Виктор", middle_name="", phone="+79001112233", birth_date=birth_date_for_age(25)
    )
    create_sample_employee(
        last_name="Кузнецов", first_name="Олег", middle_name="", phone="+79004445566", birth_date=birth_date_for_age(40)
    )

    resp = client.get("/", params={"q": "25"})
    assert "Иванов Виктор" in resp.text
    assert "Кузнецов Олег" not in resp.text


def test_gender_age_and_text_filters_combine_in_one_query():
    create_sample_employee(last_name="Смирнова", first_name="Анна", gender="female", birth_date=birth_date_for_age(28))
    create_sample_employee(last_name="Смирнов", first_name="Антон", gender="male", birth_date=birth_date_for_age(28))
    create_sample_employee(last_name="Орлова", first_name="Ольга", gender="female", birth_date=birth_date_for_age(60))

    resp = client.get("/", params={"q": "Смирн", "gender": "female", "age_from": 20, "age_to": 30})
    assert "Смирнова Анна" in resp.text
    assert "Смирнов Антон" not in resp.text
    assert "Орлова" not in resp.text


def test_photo_upload_rejects_oversized_file():
    big_content = b"0" * (200 * 1024 + 1)
    resp = client.post(
        "/employees/new",
        data={
            "last_name": "Иванов",
            "first_name": "Петр",
            "birth_date": "2000-05-20",
            "gender": "male",
        },
        files={"photo": ("photo.jpg", big_content, "image/jpeg")},
        follow_redirects=False,
    )
    assert resp.status_code == 422
    assert "200 к" in resp.text
