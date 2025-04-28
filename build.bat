@echo off
setlocal

REM --- Configuration ---
set APP_NAME=AutomationPanel-windows  REM Name without quotes
set VENV_DIR=.venv
set MAIN_SCRIPT=app.py
set DIST_DIR=dist
set BUILD_DIR=build
set SPEC_FILE=%APP_NAME%.spec
set USER_SETUP_SCRIPT=setup_and_run.bat

echo ===================================
echo Building Facebook Automation Panel (%APP_NAME% - Directory Mode)
echo ===================================
echo.

REM --- Check if running from project root ---
if not exist "pyproject.toml" (
    echo ERROR: This script must be run from the project root directory.
    goto EndFailure
)

REM --- Activate Virtual Environment (Recommended) ---
if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "%VENV_DIR%\Scripts\activate.bat"
) else (
    echo WARNING: Virtual environment '%VENV_DIR%' not found or not activated.
    echo          Attempting to build with system Python/packages.
    echo          It's HIGHLY recommended to create and activate the venv first:
    echo          python -m venv %VENV_DIR%
    echo          %VENV_DIR%\Scripts\activate
    echo          pip install -r requirements.txt (or uv sync)
    echo.
    pause
)

REM --- Check/Install PyInstaller ---
echo Checking for PyInstaller...
pip show pyinstaller > nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Attempting to install...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller. Check pip and internet connection.
        goto EndFailure
    )
    echo PyInstaller installed successfully.
) else (
    echo PyInstaller found.
)
echo.

REM --- Clean specific previous artifacts ---
echo Cleaning previous artifacts (if they exist)...
if exist "%DIST_DIR%\%APP_NAME%" rmdir /S /Q "%DIST_DIR%\%APP_NAME%"
if exist "%BUILD_DIR%" rmdir /S /Q "%BUILD_DIR%"
if exist "%SPEC_FILE%" del "%SPEC_FILE%"
echo Done cleaning.
echo.

REM --- Run PyInstaller using --onedir ---
echo Running PyInstaller (--onedir)...
REM Add quotes around APP_NAME when passing it as the --name argument
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
    echo ERROR: PyInstaller failed. Check the detailed output above.
    goto EndFailure
)
echo PyInstaller finished successfully.
echo.

REM --- Copy Setup Script for User ---
echo Checking for user setup script '%USER_SETUP_SCRIPT%'...
if not exist "%USER_SETUP_SCRIPT%" (
    echo WARNING: %USER_SETUP_SCRIPT% not found in project root!
    echo          The user needs this script to install Playwright browsers.
    echo          Please create it using the previously provided code.
) else (
    echo Copying %USER_SETUP_SCRIPT% to distribution folder...
    copy "%USER_SETUP_SCRIPT%" "%DIST_DIR%\%APP_NAME%\" > nul
    if errorlevel 1 (
       echo WARNING: Failed to copy %USER_SETUP_SCRIPT%. Please copy it manually into '%DIST_DIR%\%APP_NAME%'.
    ) else (
       echo %USER_SETUP_SCRIPT% copied successfully.
    )
)
echo.

REM --- Optional: Clean up build artifacts ---
REM Keep the build folder for potential debugging if needed
if exist "%BUILD_DIR%" (
    echo Cleaning up build directory...
    rmdir /S /Q "%BUILD_DIR%"
)
if exist "%SPEC_FILE%" (
    echo Cleaning up spec file...
     del "%SPEC_FILE%"
)
echo.

echo ===================================
echo Build Complete!
echo ===================================
echo The distributable application folder is: %DIST_DIR%\%APP_NAME%
echo Ensure '%USER_SETUP_SCRIPT%' is inside that folder for the user.
goto EndSuccess


:EndFailure
echo.
echo ********** BUILD FAILED **********
pause
exit /b 1

:EndSuccessa
echo.
echo Build finished. Press any key to exit.
pause > nul
exit /b 0

endlocal