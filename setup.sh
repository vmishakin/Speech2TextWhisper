#!/bin/bash
set -e

echo "=== Speech2Text Whisper — Установка ==="
echo

# uv
if ! command -v uv &>/dev/null; then
    echo "Устанавливаю uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Добавляем uv в PATH текущей сессии
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
fi
echo "uv: $(uv --version)"

# tkinter (нужен отдельно при использовании Homebrew Python)
PYTHON_VERSION=$(python3 --version 2>/dev/null | grep -o '3\.[0-9]*' | head -1)
if command -v brew &>/dev/null; then
    echo "Устанавливаю python-tk@${PYTHON_VERSION} (tkinter для macOS)..."
    brew install "python-tk@${PYTHON_VERSION}" 2>/dev/null || true
fi

echo "Устанавливаю зависимости проекта..."
uv sync

echo
echo "=== Установка завершена! ==="
echo "Запустите ./run.sh чтобы открыть приложение."
