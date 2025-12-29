import os


def parse_artist_file(path: str):
    """
    작가 목록 TXT 파싱 (새 형식)

    형식:
        1번째 줄: base_dir
        2번째 줄부터: artist 태그 (1줄 1작가)

    특징:
        - artist 기준 중복 제거 (처음 것만 유지)
        - 순서 유지
        - 공백/빈 줄 자동 무시

    반환:
        List[Tuple[str, str]] -> (artist, base_dir)
    """
    if not os.path.isfile(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        return []

    # 첫 줄 = 저장 경로
    base_dir = lines[0]

    # 경로 정규화 (선택이지만 권장)
    base_dir = os.path.normpath(base_dir)

    pairs = []
    seen_artists = set()

    for artist in lines[1:]:
        # artist 기준 중복 제거
        if artist in seen_artists:
            continue

        seen_artists.add(artist)
        pairs.append((artist, base_dir))

    return pairs


def read_completed(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return {l.strip() for l in f if l.strip()}


def append_completed(path: str, artist: str):
    with open(path, "a", encoding="utf-8") as f:
        f.write(artist + "\n")
