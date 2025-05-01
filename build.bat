@echo off
setlocal

REM --- Configuration ---
set APP_NAME=AutomationPanel-windows
set VENV_DIR=.venv
set MAIN_SCRIPT=app.py
set DIST_DIR=dist
set BUILD_DIR=build
set SPEC_FILE=%APP_NAME%.spec

echo ===================================
echo Building & Packaging Facebook Automation Panel
echo ===================================
echo.

REM --- Ensure we're at project root ---
if not exist "pyproject.toml" (
    echo ERROR: Run this from your project root!
    goto EndFailure
)

REM --- Activate or warn about venv ---
if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "%VENV_DIR%\Scripts\activate.bat"
) else (
    echo WARNING: No venv found. Using system Python.
)
echo.

REM --- Ensure uv (pyproject.toml manager) is installed ---
echo Checking for uv...
pip show uv > nul 2>&1
if errorlevel 1 (
    echo Installing uv...
    pip install uv
    if errorlevel 1 (
        echo ERROR: Could not install uv.
        goto EndFailure
    )
)
echo.

REM --- Sync project dependencies ---
echo Running uv sync...
uv sync
if errorlevel 1 (
    echo ERROR: uv sync failed.
    goto EndFailure
)
echo.

REM --- Ensure PyInstaller is installed ---
echo Checking for PyInstaller...
pip show pyinstaller > nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Could not install PyInstaller.
        goto EndFailure
    )
)
echo.

REM --- Clean previous build artifacts ---
echo Cleaning old dist/build/spec...
if exist "%DIST_DIR%\%APP_NAME%" rmdir /S /Q "%DIST_DIR%\%APP_NAME%"
if exist "%BUILD_DIR%"            rmdir /S /Q "%BUILD_DIR%"
if exist "%SPEC_FILE%"            del     "%SPEC_FILE%"
echo.

REM --- Run PyInstaller one-dir build ---
echo Running PyInstaller (--onedir)...
pyinstaller ^
  --noconsole ^
  --onedir ^
  --name "%APP_NAME%" ^
  --hidden-import="playwright_stealth" ^
  --hidden-import="patchright" ^
  --hidden-import="psutil" ^
  --hidden-import="tkinter" ^
  --hidden-import="customtkinter" ^
  %MAIN_SCRIPT%

if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    goto EndFailure
)
echo Build succeeded.
echo.

REM --- Generate the end‐user setup_and_run.bat inside dist ---
echo Writing setup_and_run.bat into %DIST_DIR%\%APP_NAME%...
(
  echo @echo off
  echo setlocal
  echo.
  echo REM — Activate or warn about venv —
  echo if exist "%%~dp0\%VENV_DIR%\Scripts\activate.bat" (^) 
  echo     call "%%~dp0\%VENV_DIR%\Scripts\activate.bat"
  echo ^) else (^
  echo     echo WARNING: No venv in distribution—using system Python.
  echo ^)
  echo.
  echo REM — Ensure uv is installed —
  echo pip show uv ^> nul 2^>^&1
  echo if errorlevel 1 (^
  echo     echo Installing uv...
  echo     pip install uv
  echo     if errorlevel 1 (^
  echo         echo ERROR: Could not install uv.
  echo         pause
  echo         exit /b 1
  echo     ^)
  echo ^)
  echo echo.
  echo REM — Sync dependencies —
  echo uv sync
  echo if errorlevel 1 (^
  echo     echo ERROR: uv sync failed.
  echo     pause
  echo     exit /b 1
  echo ^)
  echo echo.
  echo REM — Install Playwright browsers —
  echo python -m playwright install
  echo if errorlevel 1 (^
  echo     echo ERROR: Playwright install failed.
  echo     pause
  echo     exit /b 1
  echo ^)
  echo echo.
  echo echo Setup complete! Launch with:
  echo echo    start "" "%%~dp0\%APP_NAME%\%APP_NAME%.exe"
  echo pause
  echo endlocal
) > "%DIST_DIR%\%APP_NAME%\setup_and_run.bat"

if errorlevel 1 (
    echo WARNING: Failed to write setup script. Copy it manually from the template.
) else (
    echo setup_and_run.bat created successfully.
)
echo.

echo ===================================
echo ALL DONE!
echo Your distributable is at: %DIST_DIR%\%APP_NAME%
echo Tell your users to run: setup_and_run.bat
goto EndSuccess

:EndFailure
echo.
echo ********** BUILD FAILED **********
pause
exit /b 1

:EndSuccess
echo.
echo Press any key to finish.
pause > nul
exit /b 0
