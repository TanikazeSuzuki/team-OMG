@echo off
setlocal
if /i "%~1"=="--help" goto help
pushd "%~dp0"
if errorlevel 1 exit /b 1
set "TEAM_OMG_PY=.tools\python-3.13.15\tools\python.exe"
set "TEAM_OMG_VENV=.venv\Scripts\python.exe"
if exist "%TEAM_OMG_PY%" goto verify_python

echo [1/5] Downloading Python 3.13.15 from the official NuGet package...
powershell.exe -NoLogo -NoProfile -Command "$ErrorActionPreference='Stop'; New-Item -ItemType Directory -Path '.tools' -Force | Out-Null; Invoke-WebRequest -UseBasicParsing -Uri 'https://api.nuget.org/v3-flatcontainer/python/3.13.15/python.3.13.15.nupkg' -OutFile '.tools\python-3.13.15.zip.part'; Move-Item -LiteralPath '.tools\python-3.13.15.zip.part' -Destination '.tools\python-3.13.15.zip' -Force; Expand-Archive -LiteralPath '.tools\python-3.13.15.zip' -DestinationPath '.tools\python-3.13.15' -Force"
if errorlevel 1 goto failed

:verify_python
"%TEAM_OMG_PY%" -c "import sys, ssl, sqlite3, venv, ensurepip; assert sys.version_info[:3] == (3, 13, 15), sys.version; print(sys.version)"
if errorlevel 1 goto failed

echo [2/5] Preparing the project virtual environment...
if exist "%TEAM_OMG_VENV%" goto verify_venv
if exist ".venv" goto broken_venv
"%TEAM_OMG_PY%" -m venv .venv
if errorlevel 1 goto failed

:verify_venv
"%TEAM_OMG_VENV%" -c "import sys; assert sys.version_info[:3] == (3, 13, 15), sys.version; assert sys.prefix != sys.base_prefix"
if errorlevel 1 goto broken_venv
"%TEAM_OMG_VENV%" -m pip --version
if errorlevel 1 goto broken_venv

echo [3/5] Installing project dependencies...
"%TEAM_OMG_VENV%" -m pip install --disable-pip-version-check --no-cache-dir --index-url https://pypi.org/simple -r requirements.txt
if errorlevel 1 goto failed
"%TEAM_OMG_VENV%" -m pip check
if errorlevel 1 goto failed
"%TEAM_OMG_VENV%" -m pip freeze > .setup-installed.txt
if errorlevel 1 goto failed

echo [4/5] Applying the shared database migrations...
"%TEAM_OMG_VENV%" manage.py migrate --noinput
if errorlevel 1 goto failed

echo [5/5] Running Django system checks...
"%TEAM_OMG_VENV%" manage.py check
if errorlevel 1 goto failed
echo.
echo Setup completed. Run start.cmd to open the local development server.
echo Create your own admin account with:
echo   .venv\Scripts\python.exe manage.py createsuperuser
popd
if /i not "%~1"=="--no-pause" pause
exit /b 0

:broken_venv
echo.
echo The existing .venv is incomplete, has moved, or uses another Python version.
echo No project files or database were deleted. See README.md for recovery.
goto failed

:failed
echo.
echo Setup stopped. Read the error above and see README.md.
echo Do not remove db.sqlite3 or your source files.
popd
if /i not "%~1"=="--no-pause" pause
exit /b 1

:help
echo Usage: setup.cmd [--no-pause]
echo Installs local Python 3.13.15, creates .venv, installs Django,
echo applies migrations, and runs Django checks. Internet access is required.
echo Existing source files and the SQLite database are preserved.
echo The .tools directory must remain in this project after setup.
exit /b 0
