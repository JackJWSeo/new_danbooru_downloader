from datetime import datetime

def log_write(path: str, level: str, msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] [{level}] {msg}\n")
