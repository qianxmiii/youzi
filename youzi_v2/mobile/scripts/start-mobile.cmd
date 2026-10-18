@echo off
setlocal
set "PYTHONIOENCODING=utf-8"
pushd "%~dp0..\..\.."
if errorlevel 1 exit /b 1
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m youzi_v2.mobile.backend %*
) else (
    python -m youzi_v2.mobile.backend %*
)
set "mobileExitCode=%errorlevel%"
popd
exit /b %mobileExitCode%
