@echo off
setlocal

for %%P in (8080 9000) do (
  for /f "tokens=5" %%A in ('netstat -ano ^| findstr /r /c:":%%P .*LISTENING"') do (
    echo [INFO] Stopping process %%A on port %%P
    taskkill /PID %%A /F >nul 2>&1
  )
)

echo [OK] Requested stop for services on ports 8080 and 9000.
endlocal
