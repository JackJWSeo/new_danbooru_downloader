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
from core.downloader import (
    download_artist,
    get_total_count_by_pages
)

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
        self._load_last_state()

    # ==================================================
    # UI
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
            bg="#E0E0E0",
            fg="black",
            command=self.toggle_start_stop
        )
        self.btn_start_stop.grid(row=0, column=1, sticky="nsew")

        # -------------------------
        # 작가 목록 파일
        # -------------------------
        file_row = tk.Frame(root)
        file_row.pack(fill="x", pady=(10, 0))

        self.lbl_artist_file = tk.Label(file_row, text="작가 목록 파일: -", anchor="w")
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
        # 전체 진행 상태
        # -------------------------
        status = tk.LabelFrame(root, text="진행 상태", padx=12, pady=10)
        status.pack(fill="x", pady=(16, 0))

        artist_row = tk.Frame(status)
        artist_row.pack(fill="x")

        self.lbl_artist = tk.Label(artist_row, text="작가: -", anchor="w")
        self.lbl_artist.pack(side="left", fill="x", expand=True)

        self.btn_stop_after = tk.Button(
            artist_row,
            text="⏭ 이번 작가까지 받기",
            state="disabled",
            bg="#E0E0E0",
            fg="black",
            command=self.stop_after_current_artist
        )
        self.btn_stop_after.pack(side="right")

        path_row = tk.Frame(status)
        path_row.pack(fill="x", pady=(4, 0))

        self.lbl_path = tk.Label(path_row, text="저장 경로: -", anchor="w", fg="#1565C0")
        self.lbl_path.pack(side="left", fill="x", expand=True)

        self.btn_open_path = tk.Button(
            path_row,
            text="📂 열기",
            width=6,
            state="disabled",
            command=self.open_current_path
        )
        self.btn_open_path.pack(side="right")

        self.lbl_mode = tk.Label(status, text="모드: 전체 다운로드", anchor="w", fg="#455A64")
        self.lbl_mode.pack(fill="x", pady=(6, 0))

        self.lbl_total = tk.Label(status, text="0 / 0", anchor="w")
        self.lbl_total.pack(fill="x")

        self.bar = ttk.Progressbar(status)
        self.bar.pack(fill="x", pady=(12, 0))

        # -------------------------
        # 현재 작가 진행
        # -------------------------
        artist_prog = tk.LabelFrame(root, text="현재 작가 진행", padx=12, pady=10)
        artist_prog.pack(fill="x", pady=(12, 0))

        self.lbl_prog = tk.Label(
            artist_prog,
            text="다운로드: 0 / 기존: 0 (채크:0) / 전체: -",
            anchor="w"
        )
        self.lbl_prog.pack(fill="x")

        self.lbl_artist_progress = tk.Label(
            artist_prog,
            text="- / - (0.0%)",
            anchor="w"
        )
        self.lbl_artist_progress.pack(fill="x", pady=(4, 0))

        self.bar_artist = ttk.Progressbar(
            artist_prog,
            orient="horizontal",
            mode="determinate"
        )
        self.bar_artist.pack(fill="x", pady=(8, 0))

        self._set_start_button("disabled")


    # ==================================================
    # 버튼 상태 / 색상 관리 (복원 핵심)
    # ==================================================
    def _set_start_button(self, mode: str):
        if mode == "disabled":
            self.btn_start_stop.config(
                text="시작",
                state="disabled",
                bg="#E0E0E0",
                fg="black"
            )
            self.btn_stop_after.config(state="disabled")

        elif mode == "start":
            self.btn_start_stop.config(
                text="시작",
                state="normal",
                bg="#43A047",
                fg="white"
            )
            self.btn_stop_after.config(state="disabled")

        elif mode == "stop":
            self.btn_start_stop.config(
                text="중지",
                state="normal",
                bg="#E53935",
                fg="white"
            )
            self.btn_stop_after.config(state="normal")

    # ==================================================
    # 컨트롤
    # ==================================================
    def toggle_start_stop(self):
        if self.state in ("READY", "STOPPED"):
            self.start_download()
        elif self.state == "RUNNING":
            self.stop_download()

    def stop_after_current_artist(self):
        if self.state != "RUNNING":
            return

        self.stop_after_current = not self.stop_after_current

        if self.stop_after_current:
            self.btn_stop_after.config(
                text="⏭ 이번 작가까지 (활성)",
                bg="#FB8C00",
                fg="white"
            )
            self.lbl_mode.config(text="모드: 이번 작가까지만")
        else:
            self.btn_stop_after.config(
                text="⏭ 이번 작가까지 받기",
                bg="#E0E0E0",
                fg="black"
            )
            self.lbl_mode.config(text="모드: 전체 다운로드")

    def _update_artist_progress(self, downloaded, initial_exist, found_exist, total):
        if total <= 0:
            return

        owned = initial_exist + downloaded
        if owned > total:
            owned = total

        percent = owned / total * 100

        self.bar_artist["value"] = owned

        self.lbl_artist_progress.config(
            text=f"{owned} / {total} ({percent:.1f}%)"
        )

        self.lbl_prog.config(
            text=(
                f"다운로드: {downloaded} / "
                f"기존: {initial_exist} (채크:{found_exist}) / "
                f"전체: {total}"
            )
        )
        
    # ==================================================
    # 다운로드 (이하 로직은 이전 A 기준 그대로)
    # ==================================================
    def start_download(self):
        self.stop_event.clear()
        self.stop_after_current = False

        overwrite = self.overwrite_var.get() == "overwrite"
        self.state = "RUNNING"
        self._set_start_button("stop")

        def worker():
            completed = set(read_completed(self.completed_path))
            done = len(completed)

            for artist, base_dir in self.all_pairs:
                if artist in completed or self.stop_event.is_set():
                    continue

                # -------------------------
                # 작가 기본 정보
                # -------------------------
                save_dir = os.path.join(base_dir, artist)
                os.makedirs(save_dir, exist_ok=True)
                self.current_save_dir = save_dir

                initial_exist = len([
                    f for f in os.listdir(save_dir)
                    if os.path.isfile(os.path.join(save_dir, f))
                ])

                total_count = get_total_count_by_pages(artist, log_path=self.log_path)
                dis_total_count = total_count if total_count > 0 else "?"

                # -------------------------
                # UI 초기 표시
                # -------------------------
                self.after(0, lambda a=artist:
                        self.lbl_artist.config(text=f"작가: {a}"))
                self.after(0, lambda p=save_dir:
                        self.lbl_path.config(text=f"저장 경로: {p}"))
                self.after(0, lambda ie=initial_exist, tc=dis_total_count:
                        self.lbl_prog.config(
                            text=f"다운로드: 0 / 기존: {ie} (채크:0) / 전체: {tc}"
                        ))
                self.after(0, lambda:
                        self.btn_open_path.config(state="normal"))

                # -------------------------
                # 작가 진행률 초기화
                # -------------------------
                max_total = total_count if total_count > 0 else 0
                owned_initial = initial_exist
                percent = (owned_initial / max_total * 100) if max_total > 0 else 0.0

                self.after(0, lambda:
                        self.bar_artist.config(
                            maximum=max_total,
                            value=owned_initial
                        ))
                self.after(0, lambda oi=owned_initial, mt=max_total, pc=percent:
                        self.lbl_artist_progress.config(
                            text=f"{oi} / {mt} ({pc:.1f}%)"
                        ))

                # -------------------------
                # 다운로드 실행
                # -------------------------
                ok, _ = download_artist(
                    artist=artist,
                    base_dir=base_dir,
                    log_path=self.log_path,
                    total_count=total_count,
                    initial_exist_count=initial_exist,
                    ui_cb=lambda d, init_e, found_e, t:
                        self.after(
                            0,
                            lambda dd=d, ie=init_e, fe=found_e, tt=t:
                            self._update_artist_progress(dd, ie, fe, tt)
                        ),
                    stop_event=self.stop_event,
                    overwrite=overwrite
                )

                # -------------------------
                # 완료 처리
                # -------------------------
                if ok:
                    append_completed(self.completed_path, artist)
                    completed.add(artist)

                done += 1
                self.after(0, self.bar.step)
                self.after(0, lambda d=done:
                        self.lbl_total.config(
                            text=f"{d} / {len(self.all_pairs)}"
                        ))

                # 🔥 여기만 수정하면 된다 (정답 위치)
                if self.stop_after_current:
                    self.stop_after_current = False
                    self.after(0, lambda:
                        self.btn_stop_after.config(
                            text="⏭ 이번 작가까지 받기",
                            bg="#E0E0E0",
                            fg="black",
                            state="disabled"
                        )
                    )
                    self.after(0, lambda:
                        self.lbl_mode.config(text="모드: 전체 다운로드")
                    )
                    break

            # -------------------------
            # 전체 종료
            # -------------------------
            self.state = "STOPPED"
            self.after(0, lambda: self._set_start_button("start"))

        threading.Thread(target=worker, daemon=True).start()

    def stop_download(self):
        self.stop_event.set()

    # ==================================================
    # 기타
    # ==================================================
    def open_current_path(self):
        if self.current_save_dir and os.path.isdir(self.current_save_dir):
            os.startfile(self.current_save_dir)

    def open_artist_file(self):
        if self.artist_file_path and os.path.isfile(self.artist_file_path):
            os.startfile(self.artist_file_path)

    def select_txt(self):
        path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if path:
            self._load_artist_file(path)
            self._save_last_state()

    def _load_artist_file(self, path):
        self.artist_file_path = path
        self.lbl_artist_file.config(text=f"작가 목록 파일: {path}")

        base, _ = os.path.splitext(path)
        self.completed_path = base + "_completed.txt"
        self.log_path = base + "_log.txt"

        self.all_pairs = parse_artist_file(path)
        completed = read_completed(self.completed_path)

        self.bar["maximum"] = len(self.all_pairs)
        self.bar["value"] = len(completed)
        self.lbl_total.config(text=f"{len(completed)} / {len(self.all_pairs)}")

        # 현재 작가 진행 초기화
        self.bar_artist.config(maximum=1, value=0)
        self.lbl_artist_progress.config(text="- / - (0.0%)")
        self.lbl_prog.config(text="다운로드: 0 / 기존: 0 (채크:0) / 전체: -")

        self.state = "READY"
        self._set_start_button("start")
        self.btn_open_artist_file.config(state="normal")


    def _save_last_state(self):
        if self.artist_file_path:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"last_artist_file": self.artist_file_path}, f)

    def _load_last_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                path = data.get("last_artist_file")
                if path and os.path.isfile(path):
                    self._load_artist_file(path)
            except Exception:
                pass


if __name__ == "__main__":
    DownloaderApp().mainloop()
