import os


def parse_artist_file(path: str) -> list[tuple[str, str]]:
    """
    TXT 파일을 읽어 (artist, save_base_dir) 목록 반환

    규칙:
    - 존재하는 디렉토리 경로가 나오면 current_dir 변경
    - 이후 나오는 작가들은 해당 디렉토리에 저장
    - 빈 줄 무시
    """
    result = []
    current_dir = None

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue

            if os.path.isdir(s):
                current_dir = s
                continue

            if current_dir is None:
                continue

            result.append((s, current_dir))

    return result


def read_completed(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return {l.strip() for l in f if l.strip()}


def append_completed(path: str, artist: str):
    with open(path, "a", encoding="utf-8") as f:
        f.write(artist + "\n")
