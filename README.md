<<<<<<< HEAD
# NMS_Project
=======
1. uv init
2. uv venv
3. .venv\Scripts\activate

#install dependencies 4. uv add fastapi uvicorn 5. uv add pydantic-settings python-dotenv pydantic[email]

#run the project with uvicorn server 6. uv run uvicorn app.main:app --reload
# stop running process : taskkill /f /im python.exe

#dependencied for db
Driver Purpose
asyncpg Runtime async DB
psycopg Alembic migrations 7. uv add sqlalchemy asyncpg psycopg[binary]

#pgadmin 8. pgadmin4/v4.16/windows

# password hashing

9. uv add passlib[argon2]

uv add alembic

uv run alembic init alembic


uv run alembic revision --autogenerate -m "create users table"

uv run alembic upgrade head


#jwt
uv add python-jose      ->   JWT encoding & decoding
>>>>>>> 587ef32 (initial commit)
