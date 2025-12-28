import os
import time
import requests
from typing import Tuple

from config import (
    BASE_URL,
    HEADERS,
    LIMIT,
    SLEEP_FILE,
    SLEEP_PAGE,
    LOGIN,
    API_KEY,
)
from utils.logger import log_write


# =========================
# 다운로드 허용 확장자
# =========================
ALLOWED_EXT = {
    ".jpg", ".jpeg", ".png", ".webp",
    ".gif",
    ".webm", ".mp4"
}


# =========================
# 파일 크기 기반 timeout 계산
# =========================
def calc_timeout(file_size_bytes: int) -> tuple[int, int]:
    size_mb = max(1.0, file_size_bytes / (1024 * 1024))
    connect_timeout = 5
    read_timeout = min(max(int(10 + size_mb * 2), 30), 300)
    return connect_timeout, read_timeout


def download_artist(
    artist: str,
    base_dir: str,
    log_path: str,
    ui_cb=None,
    stop_event=None,
    overwrite: bool = False,
) -> Tuple[bool, int]:

    page = 1
    downloaded = 0

    save_dir = os.path.join(base_dir, artist)
    save_dir_created = False

    while True:
        if stop_event and stop_event.is_set():
            return False, downloaded

        # -------------------------
        # posts.json 요청
        # -------------------------
        params = {
            "tags": artist,
            "limit": LIMIT,
            "page": page,
        }
        if LOGIN and API_KEY:
            params["login"] = LOGIN
            params["api_key"] = API_KEY

        try:
            r = requests.get(
                BASE_URL,
                params=params,
                headers=HEADERS,
                timeout=(5, 15),
            )
        except Exception as e:
            log_write(log_path, "ERROR", f"{artist} : posts request failed ({e})")
            return False, downloaded

        if r.status_code != 200:
            log_write(log_path, "ERROR", f"{artist} : HTTP {r.status_code}")
            return False, downloaded

        posts = r.json()
        if not posts:
            if page == 1:
                log_write(log_path, "WARN", f"{artist} : 검색 결과 0건")
            break

        # -------------------------
        # posts 순회
        # -------------------------
        for post in posts:
            if stop_event and stop_event.is_set():
                return False, downloaded

            # 🔥 진짜 원본 URL
            file_url = post.get("file_url")
            if not file_url:
                continue

            file_url = file_url + "?download=1"

            fname = file_url.split("/")[-1].split("?")[0]
            ext = os.path.splitext(fname.lower())[1]

            if ext not in ALLOWED_EXT:
                continue

            if not save_dir_created:
                os.makedirs(save_dir, exist_ok=True)
                save_dir_created = True

            fpath = os.path.join(save_dir, fname)
            if os.path.exists(fpath) and not overwrite:
                continue

            try:
                file_size = post.get("file_size", 0)
                size_mb = max(1.0, file_size / (1024 * 1024))

                timeout = calc_timeout(file_size)
                STALL_TIMEOUT = min(20 + size_mb * 1.5, 180)

                headers = dict(HEADERS)
                headers["Referer"] = "https://danbooru.donmai.us/"

                img = requests.get(
                    file_url,
                    headers=headers,
                    stream=True,
                    timeout=timeout,
                )

                if img.status_code != 200:
                    log_write(
                        log_path,
                        "WARN",
                        f"{artist} : file HTTP {img.status_code} ({fname})",
                    )
                    continue

                last_chunk_time = time.time()

                with open(fpath, "wb") as f:
                    for chunk in img.iter_content(8192):
                        if stop_event and stop_event.is_set():
                            return False, downloaded

                        if chunk:
                            f.write(chunk)
                            last_chunk_time = time.time()
                        else:
                            if time.time() - last_chunk_time > STALL_TIMEOUT:
                                raise TimeoutError(
                                    f"download stalled ({size_mb:.1f}MB)"
                                )

                downloaded += 1
                if ui_cb:
                    ui_cb(downloaded)

                time.sleep(SLEEP_FILE)

            except Exception as e:
                log_write(
                    log_path,
                    "ERROR",
                    f"{artist} : download failed {fname} ({e})",
                )

        page += 1
        time.sleep(SLEEP_PAGE)

    return downloaded > 0, downloaded
