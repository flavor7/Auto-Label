@echo off
setlocal

set ENV_NAME=inspecsafe-label
if not "%~1"=="" set ENV_NAME=%~1

for %%I in ("%~dp0..") do set STACK_ROOT=%%~fI
for %%I in ("%STACK_ROOT%\..") do set PROJECT_ROOT=%%~fI
set DATA_ROOT=%PROJECT_ROOT%\datasets\InspecSafe-V1\DATA_PATH

if not exist "%DATA_ROOT%" (
  echo [ERROR] DATA_ROOT not found: %DATA_ROOT%
  echo Expected dataset path: %PROJECT_ROOT%\datasets\InspecSafe-V1\DATA_PATH
  exit /b 1
)

echo [INFO] ENV_NAME=%ENV_NAME%
echo [INFO] STACK_ROOT=%STACK_ROOT%
echo [INFO] DATA_ROOT=%DATA_ROOT%

start "InspecSafe Static Server" cmd /k "cd /d %STACK_ROOT% && conda run -n %ENV_NAME% python scripts\run_static_server_with_cors.py --root %DATA_ROOT% --host 127.0.0.1 --port 9000 --allow-origin http://127.0.0.1:8080"

start "Label Studio" cmd /k "set LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED=true && set LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT=%PROJECT_ROOT% && set NO_PROXY=localhost,127.0.0.1 && conda run -n %ENV_NAME% label-studio --host 127.0.0.1 --port 8080"

echo [OK] Started two windows:
echo   1) InspecSafe Static Server on http://127.0.0.1:9000
echo   2) Label Studio on http://127.0.0.1:8080
echo.
echo Keep both windows running while annotating.

endlocal
