import os
import shutil
import subprocess
import sys
import threading
import time
import customtkinter as ctk
from tkinter import filedialog, messagebox

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG = "#141419"
CARD = "#1d1d24"
FIELD = "#26262e"
MUTED = "#9a9aa3"
ACCENT = "#3b82f6"
ACCENT_HOVER = "#5b95ff"


def bundled_bin_dir():
    candidates = []
    for base in (getattr(sys, "_MEIPASS", None), os.path.dirname(os.path.abspath(__file__))):
        if base:
            p = os.path.join(base, "bin")
            if os.path.isdir(p):
                candidates.append(p)
    for d in candidates:
        if os.path.isfile(os.path.join(d, "ffmpeg.exe")):
            return d
    return None


def find_tool(name):
    d = bundled_bin_dir()
    if d:
        path = os.path.join(d, name + ".exe")
        if os.path.isfile(path):
            return path
    found = shutil.which(name)
    return found


def probe_duration(path, ffprobe):
    out = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, timeout=120,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return None


def convert(video_path, opts, on_progress, log):
    ffmpeg = find_tool("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("Не найден ffmpeg (нет в папке bin и в PATH).")
    try:
        log("Анализирую видео...")
        dur = probe_duration(video_path, find_tool("ffprobe"))
        total_ms = dur * 1000 if dur else None
        if dur:
            log(f"Длительность: {dur:.1f} c")

        target_ms = opts["duration"] * 1000 if opts["duration"] > 0 else (total_ms or None)
        out_path = os.path.splitext(video_path)[0] + ".gif"

        w = opts["width"]
        scale = "scale=-2:-1" if w == "auto" else f"scale={w}:-1"
        vf = f"fps={opts['fps']}, {scale}, split[a][b]; [a]palettegen[p]; [b][p]paletteuse"

        cmd = [ffmpeg, "-y", "-loglevel", "error", "-nostats", "-progress", "pipe:1"]
        if opts["start"] > 0:
            cmd += ["-ss", str(opts["start"])]
        cmd += ["-i", video_path]
        if opts["duration"] > 0:
            cmd += ["-t", str(opts["duration"])]
        cmd += ["-vf", vf, "-loop", "0", out_path]

        log("Конвертирую в GIF...")
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, encoding="utf-8", errors="replace",
        )
        for line in proc.stdout:
            line = line.strip()
            if line.startswith("out_time_ms="):
                try:
                    t = float(line.split("=", 1)[1])
                    if target_ms:
                        on_progress(min(99, t / target_ms * 100))
                except ValueError:
                    pass
        proc.stdout.close()
        err = proc.stderr.read()
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(err.strip() or "ffmpeg завершился с ошибкой")

        on_progress(100)
        log(f"Готово: {out_path}")
        return out_path
    except FileNotFoundError:
        log("Ошибка: не найден ffmpeg. Установите его и добавьте в PATH.")
        raise
    except Exception as e:
        log(f"Ошибка: {e}")
        raise


class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=BG)
        self.title("Видео в GIF")
        self.geometry("740x640")
        self.minsize(640, 540)

        self.thread = None
        self._full_path = None
        self._out_path = None
        self._prev_progress = 0.0
        self.t0 = 0.0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header, text="Видео в GIF",
            font=ctk.CTkFont("Segoe UI", 24, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header, text="Преобразование видеофайла в анимированный GIF",
            font=ctk.CTkFont("Segoe UI", 13), text_color=MUTED,
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14)
        card.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 14))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="Файл", font=ctk.CTkFont("Segoe UI", 13, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 8))

        self.file_var = ctk.StringVar()
        self.file_entry = ctk.CTkEntry(
            card, textvariable=self.file_var, fg_color=FIELD, border_width=0,
            placeholder_text="Выберите видеофайл...", height=40,
        )
        self.file_entry.grid(row=1, column=0, sticky="ew", padx=(18, 10))
        ctk.CTkButton(
            card, text="Обзор", width=110, height=40, corner_radius=10,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.pick_video,
        ).grid(row=1, column=1, sticky="e", padx=(0, 18))

        self.file_info = ctk.CTkLabel(
            card, text="", font=ctk.CTkFont("Segoe UI", 12), text_color=MUTED,
        )
        self.file_info.grid(row=2, column=0, columnspan=2, sticky="w", padx=18, pady=(6, 14))

        opts = ctk.CTkFrame(card, fg_color="transparent")
        opts.grid(row=3, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 18))
        opts.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(
            opts, text="Начало (сек)", font=ctk.CTkFont("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            opts, text="Длительность (сек)", font=ctk.CTkFont("Segoe UI", 12, "bold"),
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            opts, text="Кадры/сек", font=ctk.CTkFont("Segoe UI", 12, "bold"),
        ).grid(row=0, column=2, sticky="w")
        ctk.CTkLabel(
            opts, text="Ширина, px", font=ctk.CTkFont("Segoe UI", 12, "bold"),
        ).grid(row=0, column=3, sticky="w")

        self.start_var = ctk.StringVar(value="0")
        self.dur_var = ctk.StringVar(value="0")
        ctk.CTkEntry(
            opts, textvariable=self.start_var, fg_color=FIELD, border_width=0, height=38,
        ).grid(row=1, column=0, sticky="ew", pady=(6, 2), padx=(0, 6))
        ctk.CTkEntry(
            opts, textvariable=self.dur_var, fg_color=FIELD, border_width=0, height=38,
        ).grid(row=1, column=1, sticky="ew", pady=(6, 2), padx=(0, 6))

        self.fps_menu = ctk.CTkOptionMenu(
            opts, values=["5", "10", "15", "20", "25"],
            fg_color=FIELD, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            dropdown_fg_color=FIELD, dropdown_hover_color=ACCENT,
            text_color="#ffffff", height=38, corner_radius=10,
        )
        self.fps_menu.set("10")
        self.fps_menu.grid(row=1, column=2, sticky="ew", pady=(6, 2), padx=(0, 6))

        self.width_menu = ctk.CTkOptionMenu(
            opts, values=["320", "480", "640", "720", "auto"],
            fg_color=FIELD, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            dropdown_fg_color=FIELD, dropdown_hover_color=ACCENT,
            text_color="#ffffff", height=38, corner_radius=10,
        )
        self.width_menu.set("480")
        self.width_menu.grid(row=1, column=3, sticky="ew", pady=(6, 2))

        ctk.CTkLabel(
            opts, text="Начало: 0 = с начала   •   Длительность: 0 = весь файл   •   Ширина: auto = без изменения",
            font=ctk.CTkFont("Segoe UI", 11), text_color=MUTED,
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))

        self.start_btn = ctk.CTkButton(
            self, text="Создать GIF", height=46, corner_radius=12,
            font=ctk.CTkFont("Segoe UI", 15, "bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.run,
        )
        self.start_btn.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 8))

        self.progress = ctk.CTkProgressBar(
            self, progress_color=ACCENT, fg_color=FIELD, height=6, corner_radius=3,
        )
        self.progress.set(0)
        self.progress.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 6))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="ew", padx=24, pady=(0, 6))
        actions.grid_columnconfigure(0, weight=1)
        self.status_var = ctk.StringVar(value="Готов к работе.")
        ctk.CTkLabel(
            actions, textvariable=self.status_var, font=ctk.CTkFont("Segoe UI", 12), text_color=MUTED,
        ).grid(row=0, column=0, sticky="w")
        self.open_btn = ctk.CTkButton(
            actions, text="Открыть GIF", width=120, height=32, corner_radius=10,
            fg_color=FIELD, hover_color="#32323c", font=ctk.CTkFont("Segoe UI", 12),
            command=self.open_result, state="disabled",
        )
        self.open_btn.grid(row=0, column=1, padx=(8, 0))
        self.folder_btn = ctk.CTkButton(
            actions, text="Открыть папку", width=120, height=32, corner_radius=10,
            fg_color=FIELD, hover_color="#32323c", font=ctk.CTkFont("Segoe UI", 12),
            command=self.open_folder, state="disabled",
        )
        self.folder_btn.grid(row=0, column=2, padx=(8, 0))

        log_box = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14)
        log_box.grid(row=5, column=0, sticky="nsew", padx=24, pady=(0, 22))
        log_box.grid_columnconfigure(0, weight=1)
        log_box.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            log_box, text="Результат", font=ctk.CTkFont("Segoe UI", 13, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 6))
        self.log = ctk.CTkTextbox(
            log_box, fg_color="#101014", corner_radius=10,
            wrap="word", font=ctk.CTkFont("Cascadia Mono", 12), text_color="#d6d6dc",
        )
        self.log.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        self.log.configure(state="disabled")

    def write_log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.update_idletasks()

    def set_progress(self, value):
        self.progress.set(value / 100)

    def set_status(self, msg):
        self.status_var.set(msg)
        self.update_idletasks()

    def pick_video(self):
        path = filedialog.askopenfilename(
            filetypes=[("Video", "*.mp4 *.mkv *.avi *.webm *.mov *.m4v"), ("All files", "*.*")]
        )
        if path:
            self._full_path = path
            name = os.path.basename(path)
            size = os.path.getsize(path) / (1024 * 1024)
            self.file_var.set(name)
            self.file_info.configure(text=f"{name}  •  {size:.1f} МБ")
            self.set_status("Файл выбран. Нажмите «Создать GIF».")

    def run(self):
        if self.thread and self.thread.is_alive():
            return
        video = self._full_path
        if not video or not os.path.isfile(video):
            messagebox.showerror("Ошибка", "Сначала выберите видео.")
            return
        try:
            opts = {
                "start": max(0.0, float(self.start_var.get())),
                "duration": max(0.0, float(self.dur_var.get())),
                "fps": min(30, max(1, int(self.fps_menu.get()))),
                "width": self.width_menu.get(),
            }
        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте числовые значения.")
            return
        self._out_path = None
        self.open_btn.configure(state="disabled")
        self.folder_btn.configure(state="disabled")
        self._prev_progress = 0.0
        self.set_progress(0)
        self.thread = threading.Thread(target=self.worker, args=(video, opts), daemon=True)
        self.thread.start()

    def worker(self, video, opts):
        self.start_btn.configure(state="disabled")
        self.t0 = time.time()
        try:
            out = convert(
                video, opts,
                on_progress=self.throttle_progress,
                log=self.write_log,
            )
            self._out_path = out
            elapsed = time.time() - self.t0
            self.write_log(f"Готово за {elapsed:.0f} c.")
            self.set_status("Готово.")
            self.open_btn.configure(state="normal")
            self.folder_btn.configure(state="normal")
        except Exception:
            self.set_status("Ошибка при конвертации.")
        finally:
            self.start_btn.configure(state="normal")

    def throttle_progress(self, value):
        if value - self._prev_progress >= 1 or value >= 100:
            self._prev_progress = value
            self.set_progress(value)

    def open_result(self):
        if self._out_path:
            os.startfile(self._out_path)

    def open_folder(self):
        if self._out_path:
            os.startfile(os.path.dirname(self._out_path))


if __name__ == "__main__":
    App().mainloop()