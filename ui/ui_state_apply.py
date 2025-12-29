from ui.state import AppState


def apply_state(app):
    s = app.state
    app.lbl_mode.config(text=f"상태: {s.name}")

    def disable(*ws):
        for w in ws:
            try:
                w.config(state="disabled")
            except Exception:
                pass

    def enable(*ws):
        for w in ws:
            try:
                w.config(state="normal")
            except Exception:
                pass

    # 공통: 기본 버튼 색(테마)
    def set_start_btn_idle():
        app.btn_start_stop.config(text="시작", bg="#E0E0E0", fg="black")

    def set_start_btn_start():
        app.btn_start_stop.config(text="시작", bg="#43A047", fg="white")

    def set_start_btn_stop():
        app.btn_start_stop.config(text="중지", bg="#E53935", fg="white")

    def set_start_btn_stopping():
        app.btn_start_stop.config(text="중지 중...", bg="#BDBDBD", fg="black")

    # stop-after 버튼 색
    def apply_stop_after_color():
        if app.stop_after_current:
            app.btn_stop_after.config(text="⏭ 이번 작가까지 (활성)", bg="#FB8C00", fg="white")
        else:
            app.btn_stop_after.config(text="⏭ 이번 작가까지 받기", bg="#E0E0E0", fg="black")

    # ==================================================
    # 상태별
    # ==================================================
    if s == AppState.IDLE:
        # ✅ 요구사항: IDLE에서는 파일 선택만 활성
        enable(app.btn_select_txt)
        disable(
            app.btn_start_stop,
            app.btn_stop_after,
            app.btn_open_path,
            app.btn_open_artist_file,
            app.radio_skip,
            app.radio_overwrite
        )
        set_start_btn_idle()
        app.btn_stop_after.config(bg="#E0E0E0", fg="black")
        app.btn_open_path.config(state="disabled")

    elif s == AppState.LOADING:
        disable(
            app.btn_select_txt,
            app.btn_start_stop,
            app.btn_stop_after,
            app.btn_open_path,
            app.btn_open_artist_file,
            app.radio_skip,
            app.radio_overwrite
        )
        set_start_btn_idle()

    elif s == AppState.READY:
        enable(app.btn_select_txt, app.btn_start_stop, app.btn_open_artist_file, app.radio_skip, app.radio_overwrite)
        disable(app.btn_stop_after, app.btn_open_path)
        set_start_btn_start()
        app.stop_after_current = False
        apply_stop_after_color()

    elif s == AppState.RUNNING:
        disable(app.btn_select_txt, app.btn_open_artist_file, app.radio_skip, app.radio_overwrite)
        enable(app.btn_start_stop, app.btn_stop_after, app.btn_open_path)
        set_start_btn_stop()
        apply_stop_after_color()

    elif s == AppState.STOPPING:
        disable(app.btn_select_txt, app.btn_start_stop, app.btn_stop_after, app.btn_open_path, app.btn_open_artist_file, app.radio_skip, app.radio_overwrite)
        set_start_btn_stopping()

    elif s == AppState.FINISHED:
        enable(app.btn_select_txt, app.btn_start_stop, app.btn_open_artist_file, app.radio_skip, app.radio_overwrite)
        disable(app.btn_stop_after, app.btn_open_path)
        set_start_btn_start()
        app.stop_after_current = False
        apply_stop_after_color()
