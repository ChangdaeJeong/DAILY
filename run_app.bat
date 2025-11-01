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

echo Checking for existing Flask application on port 5000 and terminating if found...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000') do (
    if not "%%a"=="" (
        echo Terminating process with PID %%a
        taskkill /PID %%a /F
    )
)

echo Running Flask application in a new window...
python app.py
echo Flask application started. This batch file will now terminate.
exit
