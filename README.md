# Видео в GIF

Десктоп-приложение для преобразования видеофайлов в анимированные GIF.

## Возможности

- Темный современный интерфейс (customtkinter)
- Выбор любого видео: MP4, MKV, AVI, WEBM, MOV
- Настройки: время начала, длительность, кадры в секунду, ширина
- Живой прогресс конвертации и лог
- Автономная работа: ffmpeg можно встроить в приложение (не требуется установка в систему)

## Установка

Требуется Python 3.9+.

```bash
pip install -r requirements.txt
```

Если ffmpeg не добавлять — он должен быть установлен в системе и доступен в PATH
(например, `winget install ffmpeg` или https://ffmpeg.org).

## Запуск

```bash
python app.py
```

или двойным кликом по `run.bat`.

## Сборка в EXE

Скрипт `build.bat` собирает автономный `VideoToGif.exe` (ffmpeg встраивается в файл):

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "VideoToGif" --collect-all customtkinter --add-data "bin;bin" app.py
```

Готовый файл: `dist\VideoToGif.exe`.

Чтобы ffmpeg попал внутрь EXE, положи `ffmpeg.exe` и `ffprobe.exe` в папку `bin/`.
Без этой папки приложение использует ffmpeg из PATH.

## Распространение

Можно использовать `pyproject.toml` или приложить `VideoToGif.exe` к GitHub Release.
