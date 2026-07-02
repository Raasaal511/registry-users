from datetime import date, datetime

from fastapi import UploadFile

from app.models import Gender
from app.schemas import EmployeeFormInput, FormValidationResult, PhotoResult

MAX_PHOTO_SIZE = 200 * 1024


class EmployeeFormValidator:
    @staticmethod
    def validate(form: EmployeeFormInput) -> FormValidationResult:
        errors: dict[str, str] = {}

        if not form.last_name.strip():
            errors["last_name"] = "Обязательное поле."
        if not form.first_name.strip():
            errors["first_name"] = "Обязательное поле."

        parsed_date = EmployeeFormValidator._parse_birth_date(form.birth_date, errors)
        parsed_gender = EmployeeFormValidator._parse_gender(form.gender, errors)

        return FormValidationResult(birth_date=parsed_date, gender=parsed_gender, errors=errors)

    @staticmethod
    def _parse_birth_date(raw: str, errors: dict[str, str]) -> date | None:
        if not raw:
            errors["birth_date"] = "Обязательное поле."
            return None
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            errors["birth_date"] = "Некорректная дата."
            return None
        if parsed > date.today():
            errors["birth_date"] = "Дата рождения не может быть в будущем."
        return parsed

    @staticmethod
    def _parse_gender(raw: str, errors: dict[str, str]) -> Gender | None:
        if not raw:
            errors["gender"] = "Обязательное поле."
            return None
        try:
            return Gender(raw)
        except ValueError:
            errors["gender"] = "Некорректное значение."
            return None


async def validate_photo(photo: UploadFile | None) -> PhotoResult:
    if photo is None or not photo.filename:
        return PhotoResult(None, None, None)
    if photo.content_type and not photo.content_type.startswith("image/"):
        return PhotoResult(None, None, "Файл должен быть изображением.")

    data = await photo.read()
    if len(data) > MAX_PHOTO_SIZE:
        return PhotoResult(None, None, "Размер фото не должен превышать 200 кБ.")
    if not data:
        return PhotoResult(None, None, None)
    return PhotoResult(data, photo.content_type, None)
