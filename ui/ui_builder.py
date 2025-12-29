import tkinter as tk
from tkinter import ttk


def build_ui(app):
    root = tk.Frame(app, padx=18, pady=18)
    root.pack(fill="both", expand=True)

    # ==================================================
    # 작업 제어
    # ==================================================
    card = tk.LabelFrame(root, text="작업 제어", padx=12, pady=12)
    card.pack(fill="x")

    card.columnconfigure(0, weight=3)
    card.columnconfigure(1, weight=1)

    app.btn_select_txt = tk.Button(
        card,
        text="작가 목록 TXT 선택",
        height=3,
        command=app.on_select_txt
    )
    app.btn_select_txt.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

    app.btn_start_stop = tk.Button(
        card,
        text="시작",
        height=3,
        command=app.on_start_or_stop_clicked
    )
    app.btn_start_stop.grid(row=0, column=1, sticky="nsew")

    # ==================================================
    # 작가 목록 파일 표시 (이전 파일 정보)
    # ==================================================
    file_row = tk.Frame(root)
    file_row.pack(fill="x", pady=(10, 0))

    app.lbl_artist_file = tk.Label(
        file_row,
        text="작가 목록 파일: -",
        anchor="w",
        fg="#37474F"
    )
    app.lbl_artist_file.pack(side="left", fill="x", expand=True)

    app.btn_open_artist_file = tk.Button(
        file_row,
        text="📄 열기",
        command=app.open_artist_file
    )
    app.btn_open_artist_file.pack(side="right")

    # ==================================================
    # 옵션
    # ==================================================
    opt = tk.LabelFrame(root, text="다운로드 옵션", padx=12, pady=8)
    opt.pack(fill="x", pady=(12, 0))

    app.overwrite_var = tk.StringVar(value="skip")

    app.radio_skip = tk.Radiobutton(
        opt,
        text="이미 있으면 건너뛰기 (권장)",
        variable=app.overwrite_var,
        value="skip"
    )
    app.radio_skip.pack(anchor="w")

    app.radio_overwrite = tk.Radiobutton(
        opt,
        text="이미 있으면 덮어쓰기",
        variable=app.overwrite_var,
        value="overwrite"
    )
    app.radio_overwrite.pack(anchor="w")

    # ==================================================
    # 전체 진행 (전체 상태/전체 작가 진행)
    # ==================================================
    overall = tk.LabelFrame(root, text="전체 진행", padx=12, pady=10)
    overall.pack(fill="x", pady=(16, 0))

    app.lbl_mode = tk.Label(
        overall,
        text="상태: IDLE",
        anchor="w",
        fg="#455A64"
    )
    app.lbl_mode.pack(fill="x")

    total_row = tk.Frame(overall)
    total_row.pack(fill="x", pady=(8, 0))

    app.lbl_total = tk.Label(
        total_row,
        text="0 / 0",
        anchor="w"
    )
    app.lbl_total.pack(side="left")

    app.bar_total = ttk.Progressbar(
        overall,
        orient="horizontal",
        mode="determinate"
    )
    app.bar_total.pack(fill="x", pady=(8, 0))

    # ==================================================
    # 현재 작가 진행 (🔥 빠진 UI 복구 핵심)
    # ==================================================
    curr = tk.LabelFrame(root, text="현재 작가 진행", padx=12, pady=10)
    curr.pack(fill="x", pady=(12, 0))

    # 작가 라인 + 이번 작가까지 버튼
    artist_row = tk.Frame(curr)
    artist_row.pack(fill="x")

    app.lbl_artist = tk.Label(
        artist_row,
        text="작가: -",
        anchor="w"
    )
    app.lbl_artist.pack(side="left", fill="x", expand=True)

    app.btn_stop_after = tk.Button(
        artist_row,
        text="⏭ 이번 작가까지 받기",
        command=app.toggle_stop_after
    )
    app.btn_stop_after.pack(side="right")

    # 저장 경로 라인 + 열기 버튼
    path_row = tk.Frame(curr)
    path_row.pack(fill="x", pady=(4, 0))

    app.lbl_path = tk.Label(
        path_row,
        text="저장 경로: -",
        anchor="w",
        fg="#1565C0"
    )
    app.lbl_path.pack(side="left", fill="x", expand=True)

    app.btn_open_path = tk.Button(
        path_row,
        text="📂 열기",
        width=6,
        command=app.open_current_path
    )
    app.btn_open_path.pack(side="right")

    # 다운로드/기존/전체 표시(현재 작가 전용)
    app.lbl_prog = tk.Label(
        curr,
        text="다운로드: 0 / 기존: 0 (체크:0) / 전체: -",
        anchor="w"
    )
    app.lbl_prog.pack(fill="x", pady=(8, 0))

    # 현재 작가 진행률 텍스트 + 바
    app.lbl_artist_progress = tk.Label(
        curr,
        text="- / - (0.0%)",
        anchor="w"
    )
    app.lbl_artist_progress.pack(fill="x", pady=(6, 0))

    app.bar_artist = ttk.Progressbar(
        curr,
        orient="horizontal",
        mode="determinate"
    )
    app.bar_artist.pack(fill="x", pady=(8, 0))
