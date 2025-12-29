import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
import threading

from ui.state import AppState
from ui.ui_builder import build_ui
from ui.ui_state_apply import apply_state

from core.artist_list import parse_artist_file, read_completed
from ui.download_controller import start_download_worker

STATE_FILE = "ui_last_state.json"


class DownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Danbooru Artist Downloader")
        self.geometry("800x700")
        self.resizable(False, False)

        # 상태
        self.state = AppState.IDLE

        # 실행 제어
        self.stop_event = threading.Event()
        self.stop_after_current = False

        # 데이터
        self.artist_file_path = None
        self.completed_path = ""
        self.log_path = ""
        self.all_pairs = []
        self.current_save_dir = None

        # UI
        build_ui(self)

        # 마지막 파일 경로만 로드 (IDLE 유지)
        self._load_last_state_ui_only()

        self.apply_state()

    # ==================================================
    # 상태 머신
    # ==================================================
    def set_state(self, new_state: AppState):
        if self.state == new_state:
            return
        self.state = new_state
        self.apply_state()

        # 상태 진입 액션(기능 연결)
        if new_state == AppState.RUNNING:
            start_download_worker(self)
        elif new_state == AppState.STOPPING:
            # STOPPING은 "요청" 상태: downloader 쪽 정책대로 마무리
            self.stop_event.set()

    def apply_state(self):
        apply_state(self)

    # ==================================================
    # UI 핸들러
    # ==================================================
    def on_select_txt(self):
        initialdir = None
        initialfile = None

        if self.artist_file_path and os.path.isfile(self.artist_file_path):
            initialdir = os.path.dirname(self.artist_file_path)
            initialfile = os.path.basename(self.artist_file_path)

        path = filedialog.askopenfilename(
            title="작가 목록 TXT 선택",
            filetypes=[("Text Files", "*.txt")],
            initialdir=initialdir,
            initialfile=initialfile
        )
        if not path:
            return

        self.artist_file_path = path
        self._save_last_state()

        # 선택 후에만 LOADING → READY
        self.set_state(AppState.LOADING)
        self._load_artist_file(path)

    def on_start_or_stop_clicked(self):
        if self.state in (AppState.READY, AppState.FINISHED):
            self.set_state(AppState.RUNNING)
        elif self.state == AppState.RUNNING:
            self.set_state(AppState.STOPPING)

    def toggle_stop_after(self):
        if self.state != AppState.RUNNING:
            return
        self.stop_after_current = not self.stop_after_current
        self.apply_state()

    def open_current_path(self):
        if self.current_save_dir and os.path.isdir(self.current_save_dir):
            os.startfile(self.current_save_dir)

    def open_artist_file(self):
        if self.artist_file_path and os.path.isfile(self.artist_file_path):
            os.startfile(self.artist_file_path)

    # ==================================================
    # 로딩
    # ==================================================
    def _load_artist_file(self, path: str):
        if not os.path.isfile(path):
            messagebox.showwarning("경고", "파일이 존재하지 않습니다.")
            self.set_state(AppState.IDLE)
            return

        base, _ = os.path.splitext(path)
        self.completed_path = base + "_completed.txt"
        self.log_path = base + "_log.txt"

        self.all_pairs = parse_artist_file(path)
        completed = read_completed(self.completed_path)

        if not self.all_pairs:
            messagebox.showwarning("경고", "작가 목록이 비어 있습니다.")
            self.set_state(AppState.IDLE)
            return

        # 전체 진행
        self.bar_total["maximum"] = len(self.all_pairs)
        self.bar_total["value"] = len(completed)
        self.lbl_total.config(text=f"{len(completed)} / {len(self.all_pairs)}")

        # 현재 작가 진행 초기화
        self._reset_current_artist_ui()

        self.set_state(AppState.READY)

    def _reset_current_artist_ui(self):
        self.lbl_artist.config(text="작가: -")
        self.lbl_path.config(text="저장 경로: -")
        self.lbl_prog.config(text="다운로드: 0 / 기존: 0 (체크:0) / 전체: -")
        self.lbl_artist_progress.config(text="- / - (0.0%)")
        try:
            self.bar_artist.config(maximum=1, value=0)
        except Exception:
            pass
        self.current_save_dir = None

    # ==================================================
    # 현재 작가 UI 업데이트 (다운로더 콜백에서 호출)
    # ==================================================
    def update_current_artist_progress(self, downloaded: int, initial_exist: int, found_exist: int, total: int):
        # total이 0 이하일 땐 대략치를 못 구한 경우
        if total and total > 0:
            owned = initial_exist + downloaded
            if owned > total:
                owned = total
            percent = owned / total * 100.0
            try:
                self.bar_artist["value"] = owned
            except Exception:
                pass
            self.lbl_artist_progress.config(text=f"{owned} / {total} ({percent:.1f}%)")
        else:
            # total을 모르면 숫자만 유지
            self.lbl_artist_progress.config(text="- / - (0.0%)")

        self.lbl_prog.config(
            text=(
                f"다운로드: {downloaded} / "
                f"기존: {initial_exist} (체크:{found_exist}) / "
                f"전체: {total if total and total > 0 else '-'}"
            )
        )

    # ==================================================
    # last_state (IDLE에서 UI만 표시)
    # ==================================================
    def _save_last_state(self):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"last_artist_file": self.artist_file_path}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_last_state_ui_only(self):
        if not os.path.exists(STATE_FILE):
            # IDLE 기본
            self.lbl_artist_file.config(text="작가 목록 파일: -")
            return

        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            path = data.get("last_artist_file")
            if path:
                self.artist_file_path = path
                self.lbl_artist_file.config(text=f"작가 목록 파일: {path}")
            else:
                self.lbl_artist_file.config(text="작가 목록 파일: -")
        except Exception:
            self.lbl_artist_file.config(text="작가 목록 파일: -")
