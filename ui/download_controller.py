import threading
from ui.state import AppState
from core.downloader import download_artist, get_total_count_by_pages
from core.artist_list import read_completed, append_completed
from ui.ui_artist_progress import update_artist_progress


def start_download(app):
    app.stop_event.clear()
    app.stop_after_current = False
    app.state = AppState.RUNNING
    app.apply_state()

    def worker():
        completed = set(read_completed(app.completed_path))
        done = len(completed)

        for artist, base_dir in app.all_pairs:
            if artist in completed or app.stop_event.is_set():
                continue

            total = get_total_count_by_pages(artist, log_path=app.log_path)

            app.after(0, lambda a=artist:
                      app.lbl_artist.config(text=f"작가: {a}"))

            ok, _ = download_artist(
                artist=artist,
                base_dir=base_dir,
                log_path=app.log_path,
                total_count=total,
                initial_exist_count=0,
                ui_cb=lambda d, ie, fe, t:
                    app.after(
                        0,
                        lambda:
                        update_artist_progress(app, d, ie, fe, t)
                    ),
                stop_event=app.stop_event,
                overwrite=False
            )

            if ok:
                append_completed(app.completed_path, artist)
                completed.add(artist)

            done += 1
            app.after(0, lambda:
                      app.bar_total.step(1))

            if app.stop_after_current:
                app.stop_after_current = False
                break

        app.state = AppState.FINISHED
        app.after(0, app.apply_state)

    threading.Thread(target=worker, daemon=True).start()
