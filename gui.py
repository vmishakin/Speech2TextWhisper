#!/usr/bin/env python3
"""
Speech2Text Whisper — графический интерфейс.
Запуск: python gui.py  (или run.bat / run.sh)
"""

import json
import queue
import threading
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext
from pathlib import Path

# transcriber импортируется лениво внутри _worker(),
# чтобы не задерживать появление окна (torch грузится ~10-15с)

# ── Настройки по умолчанию ───────────────────────────────────────────────────

DEFAULT_OUTPUT_DIR = str(Path.home() / "transcripts")
DEFAULT_MODEL = "small"
MODELS = ["tiny", "base", "small", "medium", "large"]
LANGUAGES = {
    "Авто (определить)": "auto",
    "Русский (ru)": "ru",
    "English (en)": "en",
}
SETTINGS_FILE = Path.home() / ".speech2text_whisper.json"


# ── Сохранение / загрузка настроек ───────────────────────────────────────────

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_settings(data: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Главный класс приложения ──────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Speech2Text Whisper")
        self.minsize(560, 520)
        self.resizable(True, True)

        self._queue: queue.Queue = queue.Queue()
        self._model_cache: dict = {}  # {model_size: WhisperModel}
        self._is_running: bool = False

        self._build_ui()
        self._restore_settings()
        self._update_transcribe_btn()

    # ── Построение UI ─────────────────────────────────────────────────────────

    def _build_ui(self):
        p = {"padx": 8, "pady": 4}

        # Инструкция
        instr = ttk.LabelFrame(self, text="Как пользоваться")
        instr.pack(fill="x", **p)
        ttk.Label(
            instr,
            text=(
                "1. Добавьте один или несколько аудиофайлов (mp3, wav, m4a).\n"
                "2. Выберите модель, язык и папку для результатов.\n"
                "3. Нажмите «Распознать» и ждите завершения."
            ),
            justify="left",
        ).pack(anchor="w", padx=6, pady=4)

        # Список файлов
        files_frame = ttk.LabelFrame(self, text="Аудиофайлы")
        files_frame.pack(fill="x", **p)
        files_frame.columnconfigure(0, weight=1)

        self._file_listbox = tk.Listbox(files_frame, height=4, selectmode="extended")
        self._file_listbox.grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=(4, 0))

        btn_frame = ttk.Frame(files_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, sticky="e", padx=6, pady=4)
        ttk.Button(btn_frame, text="Добавить...", command=self._browse_files).pack(side="left", padx=(0, 4))
        ttk.Button(btn_frame, text="Очистить", command=self._clear_files).pack(side="left")

        # Настройки
        settings = ttk.LabelFrame(self, text="Настройки")
        settings.pack(fill="x", **p)
        settings.columnconfigure(1, weight=1)
        settings.columnconfigure(3, weight=1)

        ttk.Label(settings, text="Модель:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self._model_var = tk.StringVar(value=DEFAULT_MODEL)
        ttk.Combobox(
            settings, textvariable=self._model_var,
            values=MODELS, state="readonly", width=10,
        ).grid(row=0, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(settings, text="Язык:").grid(row=0, column=2, sticky="w", padx=6, pady=4)
        self._lang_var = tk.StringVar(value=list(LANGUAGES.keys())[0])
        ttk.Combobox(
            settings, textvariable=self._lang_var,
            values=list(LANGUAGES.keys()), state="readonly", width=20,
        ).grid(row=0, column=3, sticky="w", padx=6, pady=4)

        ttk.Label(settings, text="Папка результатов:").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self._outdir_var = tk.StringVar(value=DEFAULT_OUTPUT_DIR)
        ttk.Entry(settings, textvariable=self._outdir_var).grid(
            row=1, column=1, columnspan=2, sticky="ew", padx=6, pady=4,
        )
        outdir_btns = ttk.Frame(settings)
        outdir_btns.grid(row=1, column=3, padx=(0, 6), pady=4)
        ttk.Button(outdir_btns, text="Обзор...", command=self._browse_output_dir).pack(side="left", padx=(0, 4))
        ttk.Button(outdir_btns, text="Открыть", command=self._open_output_dir).pack(side="left")

        # Кнопка запуска
        self._transcribe_btn = ttk.Button(self, text="Распознать", command=self._start)
        self._transcribe_btn.pack(pady=8)

        # Прогресс
        prog_frame = ttk.Frame(self)
        prog_frame.pack(fill="x", padx=8)
        self._progress_var = tk.DoubleVar(value=0.0)
        self._progressbar = ttk.Progressbar(prog_frame, variable=self._progress_var, maximum=100)
        self._progressbar.pack(fill="x")
        self._status_var = tk.StringVar(value="Готов к работе.")
        ttk.Label(prog_frame, textvariable=self._status_var, anchor="w").pack(fill="x", pady=(2, 0))

        # Лог
        log_frame = ttk.LabelFrame(self, text="Лог")
        log_frame.pack(fill="both", expand=True, **p)
        self._log = scrolledtext.ScrolledText(log_frame, state="disabled", height=10, wrap="word")
        self._log.pack(fill="both", expand=True, padx=4, pady=4)

    # ── Вспомогательные методы ────────────────────────────────────────────────

    def _browse_files(self):
        paths = filedialog.askopenfilenames(
            title="Выберите аудиофайлы",
            filetypes=[
                ("Аудио", "*.mp3 *.wav *.m4a"),
                ("Все файлы", "*.*"),
            ],
        )
        for p in paths:
            # Не добавлять дубликаты
            existing = self._file_listbox.get(0, "end")
            if p not in existing:
                self._file_listbox.insert("end", p)
        self._update_transcribe_btn()

    def _clear_files(self):
        self._file_listbox.delete(0, "end")
        self._update_transcribe_btn()

    def _browse_output_dir(self):
        path = filedialog.askdirectory(title="Выберите папку для результатов")
        if path:
            self._outdir_var.set(path)

    def _open_output_dir(self):
        import os, subprocess, platform
        path = self._outdir_var.get().strip() or DEFAULT_OUTPUT_DIR
        os.makedirs(path, exist_ok=True)
        system = platform.system()
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])

    def _update_transcribe_btn(self):
        has_files = self._file_listbox.size() > 0
        state = "normal" if (has_files and not self._is_running) else "disabled"
        self._transcribe_btn.config(state=state)

    def _log_append(self, message: str):
        self._log.config(state="normal")
        self._log.insert("end", message + "\n")
        self._log.see("end")
        self._log.config(state="disabled")

    def _restore_settings(self):
        settings = load_settings()
        if "model" in settings and settings["model"] in MODELS:
            self._model_var.set(settings["model"])
        if "language" in settings and settings["language"] in LANGUAGES:
            self._lang_var.set(settings["language"])
        if "output_dir" in settings:
            self._outdir_var.set(settings["output_dir"])

    # ── Запуск транскрипции ───────────────────────────────────────────────────

    def _start(self):
        file_paths = list(self._file_listbox.get(0, "end"))
        model_size = self._model_var.get()
        lang_display = self._lang_var.get()
        language = LANGUAGES[lang_display]
        output_dir = self._outdir_var.get().strip() or DEFAULT_OUTPUT_DIR

        # Сохраняем настройки
        save_settings({"model": model_size, "language": lang_display, "output_dir": output_dir})

        # Блокируем UI
        self._is_running = True
        self._update_transcribe_btn()
        self._progress_var.set(0.0)
        self._status_var.set("Запуск...")
        self._log_append(f"─── Начало обработки {len(file_paths)} файл(ов) ───")

        t = threading.Thread(
            target=self._worker,
            args=(file_paths, model_size, language, output_dir),
            daemon=True,
        )
        t.start()
        self.after(100, self._poll_queue)

    def _worker(self, file_paths: list, model_size: str, language: str, output_dir: str):
        q = self._queue

        def log(msg):
            q.put({"type": "log", "data": msg})

        def on_progress(percent):
            q.put({"type": "progress", "data": percent})

        def on_segment(text):
            q.put({"type": "log", "data": f"  {text}"})

        try:
            import os
            import transcriber  # ленивый импорт — torch грузится здесь, в фоне

            # Загрузка (или кеш) модели
            if model_size not in self._model_cache:
                q.put({"type": "model_loading"})
                model = transcriber.load_model(model_size, log_callback=log)
                self._model_cache[model_size] = model
                q.put({"type": "model_ready"})
            else:
                log(f"Модель '{model_size}' уже загружена.")
                model = self._model_cache[model_size]

            total = len(file_paths)
            for i, file_path in enumerate(file_paths, 1):
                name = os.path.basename(file_path)
                q.put({"type": "file", "data": (i, total, name)})
                log(f"[{i}/{total}] {name}")

                text = transcriber.transcribe_file(
                    model, file_path, language, on_progress, on_segment,
                )
                out_path = transcriber.save_result(text, file_path, output_dir)
                log(f"  Сохранено: {out_path}")
                q.put({"type": "progress", "data": 0.0})  # сброс для следующего файла

            q.put({"type": "done"})

        except Exception as e:
            q.put({"type": "error", "data": str(e)})

    def _poll_queue(self):
        try:
            while True:
                msg = self._queue.get_nowait()
                mtype = msg["type"]

                if mtype == "model_loading":
                    self._progressbar.config(mode="indeterminate")
                    self._progressbar.start(15)
                    self._status_var.set("Загрузка модели...")

                elif mtype == "model_ready":
                    self._progressbar.stop()
                    self._progressbar.config(mode="determinate")
                    self._progress_var.set(0.0)

                elif mtype == "log":
                    self._log_append(msg["data"])

                elif mtype == "progress":
                    pct = msg["data"]
                    self._progress_var.set(pct)
                    # Статус обновляется через "file"
                    if pct > 0:
                        current = self._status_var.get().split(":")[0]
                        self._status_var.set(f"{current}: {pct:.0f}%")

                elif mtype == "file":
                    i, total, name = msg["data"]
                    self._status_var.set(f"Файл {i} из {total}: {name}")

                elif mtype == "done":
                    self._is_running = False
                    self._progress_var.set(100.0)
                    self._status_var.set("Готово!")
                    self._log_append("─── Завершено ───")
                    self._update_transcribe_btn()
                    return

                elif mtype == "error":
                    self._is_running = False
                    self._progress_var.set(0.0)
                    self._status_var.set("Ошибка!")
                    self._log_append(f"ОШИБКА: {msg['data']}")
                    self._update_transcribe_btn()
                    return

        except queue.Empty:
            pass

        if self._is_running:
            self.after(100, self._poll_queue)


# ── Точка входа ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()
