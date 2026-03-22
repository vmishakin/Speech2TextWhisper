#!/usr/bin/env python3
"""
Speech2Text Whisper — консольный режим.

Использование:
  python main.py [папка] [модель] [выходная_папка] [язык]

Примеры:
  python main.py
  python main.py ./audio small transcripts ru
  python main.py ./audio large ./results en

Модели: tiny, base, small, medium, large
Языки:  ru, en, auto (автоопределение)
"""

import os
import sys
import time

import transcriber


def main():
    input_dir  = sys.argv[1] if len(sys.argv) > 1 else "./assets"
    model_size = sys.argv[2] if len(sys.argv) > 2 else "small"
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "transcripts"
    language   = sys.argv[4] if len(sys.argv) > 4 else "ru"

    print(f"Директория:  {input_dir}")
    print(f"Модель:      {model_size}")
    print(f"Выход:       {output_dir}")
    print(f"Язык:        {language}\n")

    audio_files = transcriber.get_audio_files(input_dir)
    if not audio_files:
        print(f"Аудиофайлы не найдены в '{input_dir}'")
        print("Поддерживаемые форматы: wav, mp3, m4a")
        return

    print(f"Найдено файлов: {len(audio_files)}")
    for f in audio_files:
        size_mb = os.path.getsize(f) / (1024 * 1024)
        print(f"  {os.path.basename(f)} ({size_mb:.1f} MB)")
    print()

    model = transcriber.load_model(model_size, log_callback=print)
    print()

    total = len(audio_files)
    for i, file_path in enumerate(audio_files, 1):
        print(f"[{i}/{total}] {os.path.basename(file_path)}")
        start = time.time()

        text = transcriber.transcribe_file(
            model,
            file_path,
            language,
            progress_callback=lambda _: None,
            segment_callback=lambda t: print(f"  {t}"),
        )

        out_path = transcriber.save_result(text, file_path, output_dir)
        elapsed = time.time() - start
        print(f"  → {out_path} ({elapsed:.1f}с)\n")

    print(f"Готово. Результаты в '{output_dir}/'")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    try:
        main()
    except KeyboardInterrupt:
        print("\nПрервано пользователем.")
    except Exception as e:
        print(f"\nОшибка: {e}")
        sys.exit(1)
