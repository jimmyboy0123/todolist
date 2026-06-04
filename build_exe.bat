@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ==========================================
echo   Todo List - Build Windows EXE
echo ==========================================
echo.

set "USE_PY=0"
python --version >nul 2>&1
if errorlevel 1 set "USE_PY=1"

if "%USE_PY%"=="1" (
    py -3 --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found.
        echo Install Python 3.10+ from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    py -3 --version
) else (
    python --version
)

set "VENV_DIR=%~dp0.venv_build"
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

"%VPY%" -m pip install -q -r requirements.txt pyinstaller
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
)

echo.
echo Building EXE, please wait 1-3 minutes...
"%VPY%" -m PyInstaller todo_list.spec --clean -y
if errorlevel 1 (
    echo [ERROR] PyInstaller failed.
    pause
    exit /b 1
)

if exist "dist\TodoList.exe" (
    copy /Y USER_README.txt dist\USER_README.txt >nul 2>&1
    echo.
    echo ==========================================
    echo   SUCCESS: dist\TodoList.exe
    echo ==========================================
    set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    if exist "%ISCC%" (
        echo Building installer...
        "%ISCC%" installer\TodoList.iss
        if exist "installer\output\TodoList-Setup.exe" (
            echo   Installer: installer\output\TodoList-Setup.exe
        )
    ) else (
        echo   Tip: Install Inno Setup 6 to build TodoList-Setup.exe
    )
) else (
    echo [ERROR] dist\TodoList.exe not found.
)

echo.
pause
endlocal
