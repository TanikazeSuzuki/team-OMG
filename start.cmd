@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 exit /b 1
if not exist ".venv\Scripts\python.exe" goto missing
.venv\Scripts\python.exe -c "import django"
if errorlevel 1 goto missing
echo Open http://127.0.0.1:8000/ in your browser.
echo Press Ctrl+C to stop the development server.
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
set "TEAM_OMG_EXIT=%ERRORLEVEL%"
popd
if not "%TEAM_OMG_EXIT%"=="0" pause
exit /b %TEAM_OMG_EXIT%
:missing
echo Run setup.cmd first. See README.md if setup fails.
popd
pause
exit /b 1
