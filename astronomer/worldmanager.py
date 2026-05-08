import astronomer
import threading

class WorldManager(object):
    _instance = None # Singleton instance
    _lock = threading.Lock()
    _universe: astronomer.Universe = None

    def __init__(self) -> None:
        raise RuntimeError('Call instance() instead')

    @classmethod
    def instance(cls):
        if not cls._instance:
            with cls._lock:
                # Recheck instance as another thread could have created it between the
                # first check adn the lock
                if not cls._instance:
                    cls._instance = cls.__new__(cls)
        return cls._instance

    def setUniverse(
            self,
            universe: astronomer.Universe,
            ) -> None:
        self._universe = universe

    def universe(self) -> astronomer.Universe:
        return self._universe
