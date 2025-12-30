import os
import threading

from core.artist_list import read_completed, append_completed
from core.downloader import download_artist, get_total_count_by_pages, sanitize_folder_name
from ui.state import AppState


def _count_existing_files(save_dir: str) -> int:
    try:
        return sum(
            1 for f in os.listdir(save_dir)
            if os.path.isfile(os.path.join(save_dir, f))
        )
    except Exception:
        return 0


def start_download_worker(app):
    # RUNNING 진입 시 여기서 시작됨
    app.stop_event.clear()
    app.stop_after_current = False

    overwrite = (app.overwrite_var.get() == "overwrite")

    def worker():
        completed = set(read_completed(app.completed_path))
        done = len(completed)

        for artist, base_dir in app.all_pairs:
            # STOPPING 요청이면 루프 종료 (정책: 현재 이미지/페이지는 downloader가 처리)
            if app.stop_event.is_set():
                break

            if artist in completed:
                continue

            safe_name = sanitize_folder_name(artist)
            save_dir = os.path.join(base_dir, safe_name)
            os.makedirs(save_dir, exist_ok=True)
            app.current_save_dir = save_dir

            initial_exist = _count_existing_files(save_dir)
            total_count = get_total_count_by_pages(artist, log_path=app.log_path)

            # UI 초기 표시(현재 작가)
            app.after(0, lambda a=artist: app.lbl_artist.config(text=f"작가: {a}"))
            app.after(0, lambda p=save_dir: app.lbl_path.config(text=f"저장 경로: {p}"))

            # 현재 작가 progress 초기 세팅
            if total_count and total_count > 0:
                app.after(0, lambda mt=total_count, v=min(initial_exist, total_count):
                          app.bar_artist.config(maximum=mt, value=v))
                owned = min(initial_exist, total_count)
                percent = owned / total_count * 100.0
                app.after(0, lambda o=owned, t=total_count, pc=percent:
                          app.lbl_artist_progress.config(text=f"{o} / {t} ({pc:.1f}%)"))
            else:
                app.after(0, lambda: app.bar_artist.config(maximum=1, value=0))
                app.after(0, lambda: app.lbl_artist_progress.config(text="- / - (0.0%)"))

            # 현재 작가 카운트 표시 초기화
            app.after(0, lambda ie=initial_exist, tc=total_count:
                      app.lbl_prog.config(text=f"다운로드: 0 / 기존: {ie} (체크:0) / 전체: {tc if tc and tc>0 else '-'}"))

            # 다운로드 실행 (다운로더가 ui_cb로 계속 갱신)
            ok, downloaded = download_artist(
                artist=artist,
                base_dir=base_dir,
                log_path=app.log_path,
                total_count=total_count,
                initial_exist_count=initial_exist,
                ui_cb=lambda d, init_e, found_e, t:
                    app.after(0, lambda dd=d, ie=init_e, fe=found_e, tt=t:
                              app.update_current_artist_progress(dd, ie, fe, tt)),
                stop_event=app.stop_event,
                overwrite=overwrite
            )

            # 완료 기록
            if ok:
                append_completed(app.completed_path, artist)
                completed.add(artist)

            done += 1
            app.after(0, lambda: app.bar_total.step(1))
            app.after(0, lambda d=done: app.lbl_total.config(text=f"{d} / {len(app.all_pairs)}"))

            # “이번 작가까지”
            if app.stop_after_current:
                # 다음 루프 진행 막고 종료
                break

        # 종료 상태 처리
        app.stop_after_current = False
        app.after(0, lambda: app.set_state(AppState.FINISHED))

    threading.Thread(target=worker, daemon=True).start()
