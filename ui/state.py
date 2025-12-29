from enum import Enum, auto


class AppState(Enum):
    IDLE = auto()
    LOADING = auto()
    READY = auto()
    RUNNING = auto()
    STOPPING = auto()
    FINISHED = auto()
