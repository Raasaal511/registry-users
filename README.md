# Реестр сотрудников

Веб-модуль учёта сотрудников: список с поиском/фильтрами/пагинацией, создание,
редактирование и удаление карточки сотрудника, загрузка фото.

Реализовано по макету ТЗ (`01_test_python.pdf`): страница реестра и страница
создания/редактирования сотрудника используют одну и ту же форму.

## Стек

- Python 3.12, FastAPI (async), Uvicorn
- SQLAlchemy 2.0 async (SQLite/aiosqlite по умолчанию, PostgreSQL/asyncpg через `DATABASE_URL`)
- Jinja2 для серверного рендеринга HTML
- Tailwind CSS (через CDN, без сборки)
- Немного ванильного JavaScript (проверка размера фото на клиенте, подтверждение удаления)
- pytest для тестов

## Архитектура

Слоистая структура: HTTP-слой не обращается к БД напрямую, вся работа с
данными и бизнес-правила вынесены из роутов.

```
app/
  main.py         FastAPI-приложение, lifespan, роутер
  routes.py       HTTP-эндпоинты (тонкие, делегируют в EmployeeService)
  service.py      EmployeeService — бизнес-логика: пагинация, create/update/delete, вызов валидаторов
  repository.py   EmployeeRepository — один SQL-запрос со всеми фильтрами (пол, возраст с/по, текстовый поиск по ФИО/телефону/возрасту)
  validators.py   EmployeeFormValidator, validate_photo — валидация формы и фото
  schemas.py      DTO: EmployeeFormInput, EmployeeFilters, PageResult, FormValidationResult
  models.py       SQLAlchemy-модель Employee
  database.py     async engine/session, инициализация БД
templates/
  base.html, registry.html (страница 1 — реестр), employee_form.html (страница 2 — форма)
static/
  css/, js/, img/
tests/
  test_app.py     тесты на FastAPI TestClient
```

Роут вызывает `EmployeeService`, сервис — `EmployeeRepository` для чтения/записи
и `validators` для проверки формы; наружу утечек SQL или деталей запросов нет.

## Функционал

- Реестр сотрудников: таблица (№, фото, ФИО, возраст, телефон, пол, действия), пагинация.
- Поиск по ФИО, возрасту и телефону + фильтр по полу и диапазону возраста.
- Пол подсвечивается цветом (муж — синий, жен — розовый).
- Фото сотрудника увеличивается при наведении мыши; при отсутствии фото — плейсхолдер.
- Создание сотрудника: обязательные поля — фамилия, имя, дата рождения, пол;
  отчество, телефон и фото — необязательны.
- Редактирование выполняется в той же форме создания.
- Удаление — с подтверждением (диалог confirm).
- Загрузка фото — ограничение 200 кБ (проверка на клиенте и на сервере).
- «Сохранить» — сохраняет и возвращает в реестр; «Отмена» — возвращает без сохранения.

## Запуск локально

Требуется Python 3.11+.

```bash
git clone https://github.com/Raasaal511/registry-users.git
cd registry-users

python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt

uvicorn app.main:app --reload
```

Приложение будет доступно на http://127.0.0.1:8000

По умолчанию используется SQLite-файл `employees.db`, который создаётся
автоматически при первом запуске — устанавливать отдельную БД не нужно.

### Использование PostgreSQL (опционально)

```bash
export DATABASE_URL=postgresql://user:password@localhost:5432/registry_users
uvicorn app.main:app --reload
```

Обычная строка подключения (`postgresql://...` или `postgres://...`) подойдёт
без изменений — приложение само подставляет асинхронный драйвер `asyncpg`.

## Тесты

```bash
pip install -r requirements-dev.txt
pytest
```

## Деплой

В репозитории есть `render.yaml` и `Procfile` для деплоя на [Render.com](https://render.com)
(или любой другой PaaS, поддерживающий `Procfile`, например Railway):

1. Создать новый Web Service на Render, подключить GitHub-репозиторий.
2. Render подхватит `render.yaml` автоматически (build: `pip install -r requirements.txt`,
   start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`).
3. По умолчанию используется SQLite — этого достаточно для демонстрации.
   Для устойчивого хранения данных между деплоями можно подключить бесплатную
   PostgreSQL (Render Postgres / Neon / Supabase) через переменную окружения `DATABASE_URL`.

Примечание: на бесплатных тарифах диск обычно эфемерный (сбрасывается при
передеплое/пересборке), поэтому данные в SQLite между деплоями не сохраняются —
для демонстрации функционала это не критично.

## Демо

- Репозиторий: https://github.com/Raasaal511/registry-users
- Демо-версия: <ссылка на хостинг>
