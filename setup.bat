@echo off
echo === Speech2Text Whisper - Setup ===
echo.

echo Installing Visual C++ Redistributable (required for PyTorch)...
powershell -ExecutionPolicy ByPass -c "Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vc_redist.x64.exe' -OutFile 'vc_redist.x64.exe'"
vc_redist.x64.exe /install /quiet /norestart
del vc_redist.x64.exe
echo Visual C++ Redistributable installed.
echo.

where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing uv...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    if %errorlevel% neq 0 (
        echo ERROR: failed to install uv.
        pause
        exit /b 1
    )
    echo.
    echo uv installed. Please run setup.bat again.
    pause
    exit /b 0
) else (
    echo uv is already installed.
)

echo.
echo Installing dependencies (this may take a few minutes)...
uv sync
if %errorlevel% neq 0 (
    echo ERROR: failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo === Done! Run run.bat to start the app. ===
pause
