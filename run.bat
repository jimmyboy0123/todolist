@echo off

setlocal EnableExtensions

cd /d "%~dp0"

if exist "dist\TodoList.exe" (
    echo Starting TodoList desktop app...
    start "" "%~dp0dist\TodoList.exe"
    exit /b 0
)

set "USE_PY=0"

python --version >nul 2>&1

if errorlevel 1 set "USE_PY=1"



if "%USE_PY%"=="1" (

    py -3 --version >nul 2>&1

    if errorlevel 1 (

        echo [ERROR] Python not found.

        pause

        exit /b 1

    )

)



set "VENV_DIR=%~dp0.venv"

set "VPY=%VENV_DIR%\Scripts\python.exe"



if not exist "%VPY%" (

    echo Creating virtual environment...

    if "%USE_PY%"=="0" (python -m venv "%VENV_DIR%") else (py -3 -m venv "%VENV_DIR%")

    if errorlevel 1 (

        echo [ERROR] Failed to create venv.

        pause

        exit /b 1

    )

)



"%VPY%" -m pip install -q -r requirements.txt

if errorlevel 1 (

    echo [ERROR] pip install failed.

    pause

    exit /b 1

)



echo.

echo   Todo List - http://127.0.0.1:5050

echo.



"%VPY%" run.py --host 0.0.0.0 --port 5050

pause

endlocal


