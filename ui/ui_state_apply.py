from ui.state import AppState


def apply_state(app):
    s = app.state

    def disable(*ws):
        for w in ws:
            w.config(state="disabled")

    def enable(*ws):
        for w in ws:
            w.config(state="normal")

    if s == AppState.IDLE:
        disable(app.btn_start_stop)
        app.lbl_mode.config(text="모드: 대기")

    elif s == AppState.LOADING:
        disable(app.btn_start_stop)
        app.lbl_mode.config(text="상태: 파일 확인 중...")

    elif s == AppState.READY:
        enable(app.btn_start_stop)
        app.btn_start_stop.config(text="시작")
        app.lbl_mode.config(text="모드: 준비됨")

    elif s == AppState.RUNNING:
        enable(app.btn_start_stop)
        app.btn_start_stop.config(text="중지")
        app.lbl_mode.config(text="모드: 다운로드 중")

    elif s == AppState.STOPPING:
        disable(app.btn_start_stop)
        app.lbl_mode.config(text="모드: 마무리 중...")

    elif s == AppState.FINISHED:
        enable(app.btn_start_stop)
        app.btn_start_stop.config(text="시작")
        app.lbl_mode.config(text="모드: 완료")
