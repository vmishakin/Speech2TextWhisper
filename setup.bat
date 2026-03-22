@echo off
chcp 65001 >nul
echo === Speech2Text Whisper — Установка ===
echo.

:: Проверить, установлен ли уже uv
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo Устанавливаю uv...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    if %errorlevel% neq 0 (
        echo ОШИБКА: не удалось установить uv.
        pause
        exit /b 1
    )
    echo.
    echo uv установлен. Перезапустите setup.bat ещё раз.
    echo (нужно перезапустить, чтобы uv появился в PATH)
    pause
    exit /b 0
) else (
    echo uv уже установлен.
)

echo.
echo Устанавливаю зависимости проекта (может занять несколько минут)...
uv sync
if %errorlevel% neq 0 (
    echo ОШИБКА: не удалось установить зависимости.
    pause
    exit /b 1
)

echo.
echo === Установка завершена! ===
echo Запустите run.bat чтобы открыть приложение.
pause
