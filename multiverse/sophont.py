import threading
import multiverse
import typing

class SophontManager(object):
    _T5OfficialSophontsPath = "t5ss/sophont_codes.tab"

    _instance = None # Singleton instance
    _sophontMap = {}
    _lock = threading.Lock()

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
                    cls._instance._loadSophonts()
        return cls._instance

    def sophontName(self, code: str) -> str:
        if code not in self._sophontMap:
            return None
        return self._sophontMap[code]

    def allSophontCodes(self) -> typing.Iterable[str]:
        return self._sophontMap.keys()

    # This function assumes it's only called once when the singleton is created and that
    # the mutex is locked
    def _loadSophonts(self) -> None:
        _, results = multiverse.parseTabContent(
            content=multiverse.DataStore.instance().loadTextResource(
                filePath=SophontManager._T5OfficialSophontsPath))

        for sophont in results:
            code = sophont['Code']
            name = sophont['Name']

            if code not in self._sophontMap:
                self._sophontMap[code] = name
