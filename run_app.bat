@echo off
chcp 65001 > nul
set PYTHONIOENCODING=UTF-8
set VENV_DIR=venv

echo Checking and creating virtual environment...
if not exist %VENV_DIR% (
    python -m venv %VENV_DIR%
    echo Virtual environment '%VENV_DIR%' created.
) else (
    echo Virtual environment '%VENV_DIR%' already exists.
)

echo Activating virtual environment...
call %VENV_DIR%\Scripts\activate

echo Installing required packages...
pip install -r requirements.txt

echo Running Flask application...
python app.py
