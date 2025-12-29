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
# 스킵 관련 설정
# =========================
MAX_EXIST_SKIP = 30
OWNED_RATIO_THRESHOLD = 0.9


# =========================
# 파일 크기 기반 timeout 계산
# =========================
def calc_timeout(file_size_bytes: int) -> tuple[int, int]:
    size_mb = max(1.0, file_size_bytes / (1024 * 1024))
    connect_timeout = 5
    read_timeout = min(max(int(10 + size_mb * 2), 30), 300)
    return connect_timeout, read_timeout


# =========================
# 작가 전체 작품 수 조회
# (다운로드 태그는 건드리지 않음)
# =========================
def get_total_count_by_pages(artist: str, log_path: str = "") -> int:
    """
    전체 개수 = ((전체 페이지 수 - 1) * LIMIT) + 마지막 페이지의 이미지 수
    반환:
      >0  : 계산된 전체 이미지 수
      0   : 작품 없음
      -1  : 계산 실패
    """

    def log(msg: str):
        if log_path:
            try:
                log_write(log_path, "INFO", msg)
            except Exception:
                pass

    def fetch_page(page: int):
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
            if r.status_code != 200:
                return None
            data = r.json()
            if not isinstance(data, list):
                return None
            return data
        except Exception:
            return None

    # 1️⃣ 1페이지 확인
    first = fetch_page(1)
    if first is None:
        log("[total_by_pages] failed to fetch page 1")
        return -1
    if len(first) == 0:
        return 0  # 작품 없음

    # 2️⃣ 상한 찾기 (1,2,4,8... 방식)
    low = 1
    high = 1

    while True:
        high *= 2
        data = fetch_page(high)
        if data is None:
            log(f"[total_by_pages] failed at page {high}")
            return -1
        if len(data) == 0:
            break
        low = high

        # 안전장치 (원하면 늘려도 됨)
        if high > 50000:
            log("[total_by_pages] page too large, abort")
            return -1

    # 3️⃣ 이분 탐색으로 마지막 페이지 찾기
    last_page = low
    last_count = len(fetch_page(low))

    left = low
    right = high  # right는 비어 있음 보장

    while left + 1 < right:
        mid = (left + right) // 2
        data = fetch_page(mid)
        if data is None:
            log(f"[total_by_pages] failed at page {mid}")
            return -1
        if len(data) == 0:
            right = mid
        else:
            left = mid
            last_page = mid
            last_count = len(data)

    # 4️⃣ 최종 계산
    total = (last_page - 1) * LIMIT + last_count
    return total

# =========================
# 작가 다운로드
# =========================
def download_artist(
    artist: str,
    base_dir: str,
    log_path: str,
    total_count: int,
    initial_exist_count: int,
    ui_cb=None,
    stop_event=None,
    overwrite: bool = False,
) -> Tuple[bool, int]:

    page = 1
    downloaded = 0

    # 🔒 UI 기준값 (고정)
    initial_exist = initial_exist_count

    # 🔥 스캔 중 다시 발견한 기존 파일 수 (괄호용)
    encountered_exist = 0

    # 스킵 판단용
    exist_skip_streak = 0

    def owned_ratio() -> float:
        if total_count <= 0:
            return 0.0
        return (initial_exist + downloaded) / total_count

    save_dir = os.path.join(base_dir, artist)
    save_dir_created = False

    while True:
        # 페이지 단위 중지 확인
        if stop_event and stop_event.is_set():
            log_write(log_path, "INFO", f"{artist} : stop requested (page end)")
            break

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
            break

        for post in posts:
            # 새 이미지 시작 전 중지 확인
            if stop_event and stop_event.is_set():
                log_write(log_path, "INFO", f"{artist} : stop requested (before new image)")
                return downloaded > 0, downloaded

            file_url = post.get("file_url")
            if not file_url:
                continue

            file_url += "?download=1"
            fname = file_url.split("/")[-1].split("?")[0]
            ext = os.path.splitext(fname.lower())[1]

            if ext not in ALLOWED_EXT:
                continue

            if not save_dir_created:
                os.makedirs(save_dir, exist_ok=True)
                save_dir_created = True

            fpath = os.path.join(save_dir, fname)

            # -------------------------
            # 이미 파일이 있는 경우
            # -------------------------
            if os.path.exists(fpath) and not overwrite:
                encountered_exist += 1

                # 90% 이상일 때만 스킵 카운트 증가
                if owned_ratio() >= OWNED_RATIO_THRESHOLD:
                    exist_skip_streak += 1
                    if exist_skip_streak >= MAX_EXIST_SKIP:
                        log_write(
                            log_path,
                            "INFO",
                            f"{artist} : owned {owned_ratio():.1%}, exist streak reached → skip artist"
                        )
                        return downloaded > 0, downloaded
                else:
                    # 90% 미만이면 스킵 로직 완전 비활성
                    exist_skip_streak = 0

                if ui_cb:
                    ui_cb(
                        downloaded,
                        initial_exist,
                        exist_skip_streak,
                        total_count
                    )
                continue

            # -------------------------
            # 새 파일 다운로드
            # -------------------------
            exist_skip_streak = 0

            try:
                file_size = post.get("file_size", 0)
                timeout = calc_timeout(file_size)

                headers = dict(HEADERS)
                headers["Referer"] = "https://danbooru.donmai.us/"

                img = requests.get(
                    file_url,
                    headers=headers,
                    stream=True,
                    timeout=timeout,
                )

                if img.status_code != 200:
                    continue

                # ❌ 다운로드 중에는 stop_event 검사 안 함
                with open(fpath, "wb") as f:
                    for chunk in img.iter_content(8192):
                        if chunk:
                            f.write(chunk)

                downloaded += 1

                if ui_cb:
                    ui_cb(
                        downloaded,
                        initial_exist,
                        encountered_exist,
                        total_count
                    )

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
