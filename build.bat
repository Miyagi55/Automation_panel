@echo off
setlocal enabledelayedexpansion

REM ══════════════════════════════════════════════════════════════════════
REM  Configuration
REM ══════════════════════════════════════════════════════════════════════
set "APP_NAME=AutomationPanel-windows"
set "VENV_DIR=.venv"
set "MAIN_SCRIPT=app.py"
set "DIST_DIR=dist"
set "BUILD_DIR=build"
set "SPEC_FILE=%APP_NAME%.spec"

echo ===================================
echo Building ^& Packaging Facebook Automation Panel
echo ===================================
echo.

REM ══════════════════════════════════════════════════════════════════════
REM  Step 0: Ensure we're in repo root
REM ══════════════════════════════════════════════════════════════════════
if not exist "pyproject.toml" (
    echo ERROR: Run this from your project root!
    goto EndFailure
)

REM ══════════════════════════════════════════════════════════════════════
REM  Step 1: Create a venv seeded with pip
REM ══════════════════════════════════════════════════════════════════════
echo Ensuring virtual environment (uv venv --seed)...
uv venv --seed
if errorlevel 1 (
    echo ERROR: Failed to create/seed venv.
    goto EndFailure
)
echo Virtual environment ready at "%VENV_DIR%".
echo.

REM ══════════════════════════════════════════════════════════════════════
REM  Step 2: Prep venv executables
REM ══════════════════════════════════════════════════════════════════════
set "VENV_SCRIPTS=%~dp0%VENV_DIR%\Scripts"
set "PYTHON=%VENV_SCRIPTS%\python.exe"
set "PIP=%VENV_SCRIPTS%\pip.exe"

REM  Put venv Scripts first so pip.exe in venv is used
set "PATH=%VENV_SCRIPTS%;%PATH%"

echo Using Python: %PYTHON%
echo Using Pip   : %PIP%
echo.

REM ══════════════════════════════════════════════════════════════════════
REM  Step 3: Sync project deps into the venv (global uv CLI)
REM ══════════════════════════════════════════════════════════════════════
echo Running uv sync...
uv sync
if errorlevel 1 (
    echo ERROR: uv sync failed.
    goto EndFailure
)
echo Dependencies synchronized.
echo.

REM ══════════════════════════════════════════════════════════════════════
REM  Step 4: Install build tools (pip & PyInstaller) into the venv
REM ══════════════════════════════════════════════════════════════════════
echo Installing build tools into venv...
"%PIP%" install --upgrade pip pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install pip or PyInstaller in venv.
    goto EndFailure
)
echo Build tools installed.
echo.

REM ══════════════════════════════════════════════════════════════════════
REM  Step 5: Clean previous build artifacts
REM ══════════════════════════════════════════════════════════════════════
echo Cleaning old dist/build/spec...
if exist "%DIST_DIR%\%APP_NAME%" rmdir /S /Q "%DIST_DIR%\%APP_NAME%"
if exist "%BUILD_DIR%"            rmdir /S /Q "%BUILD_DIR%"
if exist "%SPEC_FILE%"            del     "%SPEC_FILE%"
echo.

REM ══════════════════════════════════════════════════════════════════════
REM  Step 6: Run PyInstaller from the venv
REM ══════════════════════════════════════════════════════════════════════
echo Running PyInstaller (--onedir)...
"%PYTHON%" -m PyInstaller ^
  --noconsole ^
  --onedir ^
  --name "%APP_NAME%" ^
  --hidden-import=playwright_stealth ^
  --hidden-import=patchright ^
  --hidden-import=psutil ^
  --hidden-import=tkinter ^
  --hidden-import=customtkinter ^
  %MAIN_SCRIPT%
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    goto EndFailure
)
echo Build succeeded.
echo.

REM ══════════════════════════════════════════════════════════════════════
REM  Step 7: Generate end-user setup_and_run.bat inside dist
REM ══════════════════════════════════════════════════════════════════════
echo Writing setup_and_run.bat into %DIST_DIR%\%APP_NAME%...
(
  echo @echo off
  echo setlocal
  echo rem ─ Activate venv if present ───────────────────────────────────
  echo if exist "^^%%~dp0%VENV_DIR%\Scripts\activate.bat^^" ^^( 
  echo     call "^^%%~dp0%VENV_DIR%\Scripts\activate.bat^^"
  echo ^^) else ^^( 
  echo     echo WARNING: No venv in distribution—using system Python.
  echo ^^)
  echo.
  echo rem ─ Ensure uv CLI is installed ─────────────────────────────────
  echo pip show uv ^^^> nul 2^^^>^^&1 ^^^|^^^| pip install uv
  echo.
  echo rem ─ Sync dependencies ────────────────────────────────────────────
  echo uv sync
  echo if errorlevel 1 ^^( 
  echo     echo ERROR: uv sync failed.
  echo     pause
  echo     exit /b 1
  echo ^^)
  echo.
  echo rem ─ Install Playwright browsers ─────────────────────────────────
  echo python -m playwright install --with-deps
  echo if errorlevel 1 ^^( 
  echo     echo ERROR: Playwright install failed.
  echo     pause
  echo     exit /b 1
  echo ^^)
  echo.
  echo echo Setup complete! Launching the app...
  echo start "" "^^%%~dp0%APP_NAME%\%APP_NAME%.exe^^"
  echo endlocal
) > "%DIST_DIR%\%APP_NAME%\setup_and_run.bat"

if errorlevel 1 (
    echo WARNING: Could not write setup script. Copy manually.
) else (
    echo setup_and_run.bat created successfully.
)
echo.

REM ══════════════════════════════════════════════════════════════════════
REM  Finish
REM ══════════════════════════════════════════════════════════════════════
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
