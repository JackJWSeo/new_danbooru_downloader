def update_artist_progress(app, downloaded, initial_exist, found_exist, total):
    if total <= 0:
        return

    owned = min(initial_exist + downloaded, total)
    percent = owned / total * 100

    app.bar_artist["value"] = owned
    app.lbl_artist_progress.config(
        text=f"{owned} / {total} ({percent:.1f}%)"
    )

    app.lbl_prog.config(
        text=(
            f"다운로드: {downloaded} / "
            f"기존: {initial_exist} (채크:{found_exist}) / "
            f"전체: {total}"
        )
    )
