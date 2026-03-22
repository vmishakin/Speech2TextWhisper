import os
import glob
from pathlib import Path
from datetime import date
from faster_whisper import WhisperModel


def load_model(model_size: str, log_callback) -> WhisperModel:
    """Загружает модель Whisper на CPU с int8-квантизацией."""
    log_callback(f"Загрузка модели '{model_size}'...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    log_callback(f"Модель '{model_size}' загружена (CPU, int8).")
    return model


def transcribe_file(
    model: WhisperModel,
    file_path: str,
    language: str,
    progress_callback,
    segment_callback,
) -> str:
    """
    Транскрибирует аудиофайл.

    language="auto" → faster-whisper определяет язык автоматически.
    progress_callback(percent: float) — вызывается по мере обработки сегментов.
    segment_callback(text: str) — вызывается для каждого распознанного сегмента.

    Возвращает полный текст транскрипции.
    """
    lang_arg = None if language == "auto" else language
    segments_gen, info = model.transcribe(file_path, language=lang_arg, beam_size=5)

    texts = []
    for segment in segments_gen:
        text = segment.text.strip()
        texts.append(text)
        segment_callback(text)
        if info.duration and info.duration > 0:
            percent = min(segment.end / info.duration * 100, 100.0)
            progress_callback(percent)

    return " ".join(texts)


def save_result(text: str, file_path: str, output_dir: str) -> str:
    """
    Сохраняет текст в файл вида {original_stem}_{YYYY-MM-DD}.txt.
    Возвращает полный путь к сохранённому файлу.
    """
    os.makedirs(output_dir, exist_ok=True)
    stem = Path(file_path).stem
    today = date.today().strftime("%Y-%m-%d")
    out_path = os.path.join(output_dir, f"{stem}_{today}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return out_path


def get_audio_files(directory: str) -> list:
    """Возвращает отсортированный список аудиофайлов в директории."""
    extensions = ["*.wav", "*.mp3", "*.m4a", "*.WAV", "*.MP3", "*.M4A"]
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(directory, ext)))
    return sorted(files)
