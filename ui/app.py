import os
import json
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from core.artist_list import (
    parse_artist_file,
    read_completed,
    append_completed
)
from core.downloader import download_artist


STATE_FILE = "ui_last_state.json"


class DownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Danbooru Artist Downloader")
        self.geometry("800x680")
        self.resizable(False, False)

        # 상태
        self.state = "IDLE"  # IDLE / READY / RUNNING / STOPPED

        self.stop_event = threading.Event()
        self.stop_after_current = False
        self.current_save_dir = None

        self.all_pairs = []
        self.artist_file_path = None
        self.completed_path = ""
        self.log_path = ""

        self.overwrite_var = tk.StringVar(value="skip")

        self._build()
        self._load_last_state()   # ⭐ 마지막 파일 자동 로드

    def open_artist_file(self):
        if self.artist_file_path and os.path.isfile(self.artist_file_path):
            os.startfile(self.artist_file_path)

    # ==================================================
    # UI 구성
    # ==================================================
    def _build(self):
        root = tk.Frame(self, padx=18, pady=18)
        root.pack(fill="both", expand=True)

        # -------------------------
        # 상단 컨트롤
        # -------------------------
        card = tk.LabelFrame(root, text="작업 제어", padx=12, pady=12)
        card.pack(fill="x")

        card.columnconfigure(0, weight=3)
        card.columnconfigure(1, weight=1)

        tk.Button(
            card,
            text="작가 목록 TXT 선택",
            height=3,
            command=self.select_txt
        ).grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.btn_start_stop = tk.Button(
            card,
            text="시작",
            height=3,
            state="disabled",
            command=self.toggle_start_stop
        )
        self.btn_start_stop.grid(row=0, column=1, sticky="nsew")

        # -------------------------
        # 선택된 작가 목록 파일 표시 + 열기 버튼
        # -------------------------
        file_row = tk.Frame(root)
        file_row.pack(fill="x", pady=(10, 0))

        self.lbl_artist_file = tk.Label(
            file_row,
            text="작가 목록 파일: -",
            anchor="w",
            fg="#37474F"
        )
        self.lbl_artist_file.pack(side="left", fill="x", expand=True)

        self.btn_open_artist_file = tk.Button(
            file_row,
            text="📄 열기",
            state="disabled",
            command=self.open_artist_file
        )
        self.btn_open_artist_file.pack(side="right")


        # -------------------------
        # 옵션
        # -------------------------
        opt = tk.LabelFrame(root, text="다운로드 옵션", padx=12, pady=8)
        opt.pack(fill="x", pady=(12, 0))

        tk.Radiobutton(
            opt, text="이미 있으면 건너뛰기 (권장)",
            variable=self.overwrite_var, value="skip"
        ).pack(anchor="w")

        tk.Radiobutton(
            opt, text="이미 있으면 덮어쓰기",
            variable=self.overwrite_var, value="overwrite"
        ).pack(anchor="w")

        # -------------------------
        # 상태
        # -------------------------
        status = tk.LabelFrame(root, text="진행 상태", padx=12, pady=10)
        status.pack(fill="x", pady=(16, 0))

        self.lbl_artist = tk.Label(status, text="작가: -", anchor="w")
        self.lbl_artist.pack(fill="x")

        self.lbl_path = tk.Label(
            status,
            text="저장 경로: -",
            anchor="w",
            fg="#1565C0"
        )
        self.lbl_path.pack(fill="x", pady=(2, 0))

        path_row = tk.Frame(status)
        path_row.pack(fill="x", pady=(6, 0))

        self.btn_open_path = tk.Button(
            path_row,
            text="📂 현재 경로 열기",
            state="disabled",
            command=self.open_current_path
        )
        self.btn_open_path.pack(side="left")

        self.btn_stop_after = tk.Button(
            path_row,
            text="⏭ 이번 작가까지 받기",
            state="disabled",
            bg="#E0E0E0",
            command=self.stop_after_current_artist
        )
        self.btn_stop_after.pack(side="left", padx=(8, 0))

        self.lbl_mode = tk.Label(
            status,
            text="모드: 전체 다운로드",
            anchor="w",
            fg="#455A64"
        )
        self.lbl_mode.pack(fill="x", pady=(6, 0))

        self.lbl_prog = tk.Label(status, text="작가 내 다운로드: 0", anchor="w")
        self.lbl_prog.pack(fill="x", pady=(10, 0))

        self.lbl_total = tk.Label(status, text="0 / 0", anchor="w")
        self.lbl_total.pack(fill="x")

        self.bar = ttk.Progressbar(status)
        self.bar.pack(fill="x", pady=(12, 0))

        self._set_start_button("disabled")

    # ==================================================
    # 상태 저장 / 로드
    # ==================================================
    def _save_last_state(self):
        if not self.artist_file_path:
            return
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {"last_artist_file": self.artist_file_path},
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except Exception:
            pass

    def _load_last_state(self):
        if not os.path.exists(STATE_FILE):
            return
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            path = data.get("last_artist_file")
            if path and os.path.isfile(path):
                self._load_artist_file(path)
        except Exception:
            pass

    # ==================================================
    # 버튼 / 상태
    # ==================================================
    def _set_start_button(self, mode: str):
        if mode == "disabled":
            self.btn_start_stop.config(text="시작", state="disabled", bg="#E0E0E0")
            self.btn_stop_after.config(state="disabled")
        elif mode == "start":
            self.btn_start_stop.config(text="시작", state="normal", bg="#43A047", fg="white")
            self.btn_stop_after.config(state="disabled")
        elif mode == "stop":
            self.btn_start_stop.config(text="중지", state="normal", bg="#E53935", fg="white")
            self.btn_stop_after.config(state="normal")

    def toggle_start_stop(self):
        if self.state in ("READY", "STOPPED"):
            self.start_download()
        elif self.state == "RUNNING":
            self.stop_download()

    # ==================================================
    # 파일 선택 / 로드
    # ==================================================
    def select_txt(self):
        path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if not path:
            return
        self._load_artist_file(path)
        self._save_last_state()

    def _load_artist_file(self, path: str):
        self.artist_file_path = path
        self.lbl_artist_file.config(text=f"작가 목록 파일: {path}")

        if not os.path.isfile(path):
            self.btn_open_artist_file.config(state="disabled")
            return

        base, _ = os.path.splitext(path)
        self.completed_path = base + "_completed.txt"
        self.log_path = base + "_log.txt"

        self.all_pairs = parse_artist_file(path)
        completed = read_completed(self.completed_path)

        if not self.all_pairs:
            messagebox.showwarning("경고", "작가 목록이 비어 있습니다.")
            return

        self.bar["maximum"] = len(self.all_pairs)
        self.bar["value"] = len(completed)
        self.lbl_total.config(text=f"{len(completed)} / {len(self.all_pairs)}")

        self.state = "READY"
        self._set_start_button("start")
        self.btn_open_artist_file.config(state="normal")

    # ==================================================
    # 컨트롤
    # ==================================================
    def stop_after_current_artist(self):
        if self.state != "RUNNING":
            return
        self.stop_after_current = not self.stop_after_current
        if self.stop_after_current:
            self.btn_stop_after.config(text="⏭ 이번 작가까지 (활성)", bg="#FB8C00", fg="white")
            self.lbl_mode.config(text="모드: 이번 작가까지만")
        else:
            self.btn_stop_after.config(text="⏭ 이번 작가까지 받기", bg="#E0E0E0", fg="black")
            self.lbl_mode.config(text="모드: 전체 다운로드")

    def open_current_path(self):
        if self.current_save_dir and os.path.isdir(self.current_save_dir):
            os.startfile(self.current_save_dir)

    def start_download(self):
        self.stop_event.clear()
        self.stop_after_current = False
        
        if not self.all_pairs:
            return
    
        self.lbl_mode.config(text="모드: 전체 다운로드")

        self.state = "RUNNING"
        self._set_start_button("stop")

        overwrite = self.overwrite_var.get() == "overwrite"

        def worker():
            completed = read_completed(self.completed_path)
            if not isinstance(completed, set):
                completed = set()

            done = len(completed)

            for artist, base_dir in self.all_pairs:
                if artist in completed:
                    continue
                if self.stop_event.is_set():
                    break

                save_dir = os.path.join(base_dir, artist)
                self.current_save_dir = save_dir

                self.after(0, lambda a=artist: self.lbl_artist.config(text=f"작가: {a}"))
                self.after(0, lambda p=save_dir: self.lbl_path.config(text=f"저장 경로: {p}"))
                self.after(0, lambda: self.btn_open_path.config(state="normal"))
                self.after(0, lambda: self.lbl_prog.config(text="작가 내 다운로드: 0"))

                ok, _ = download_artist(
                    artist,
                    base_dir,
                    self.log_path,
                    ui_cb=lambda c: self.after(
                        0, lambda: self.lbl_prog.config(text=f"작가 내 다운로드: {c}")
                    ),
                    stop_event=self.stop_event,
                    overwrite=overwrite
                )

                if ok:
                    append_completed(self.completed_path, artist)
                    completed.add(artist)

                done += 1
                self.after(0, lambda: self.bar.step(1))
                self.after(0, lambda d=done: self.lbl_total.config(
                    text=f"{d} / {len(self.all_pairs)}"
                ))

                if self.stop_after_current:
                    break

            self.state = "STOPPED"
            self.stop_after_current = False
            self.after(0, lambda: self._set_start_button("start"))
            self.after(0, lambda: self.lbl_mode.config(text="모드: 전체 다운로드"))

        threading.Thread(target=worker, daemon=True).start()

    def stop_download(self):
        self.stop_event.set()
        self.state = "STOPPED"
        self._set_start_button("start")


if __name__ == "__main__":
    DownloaderApp().mainloop()
