import app
import logging
import os
import threading
import multiverse
import typing
from PyQt5 import QtCore

class HexHistory(object):
    _SearchFileName = 'hexhistory.ini'
    _MaxCount = 50

    # Based on the default list Traveller Map shows in a drop down if you click
    # on the search edit box when it has no content
    _DefaultSectorHexes = [
        multiverse.HexPosition(absoluteX=0, absoluteY=0), # Reference/Core 0140
        multiverse.HexPosition(absoluteX=20, absoluteY=-22), # Capital/Core 2118
        multiverse.HexPosition(absoluteX=-110, absoluteY=-70), # Regina/Spinward Marches 1910
        multiverse.HexPosition(absoluteX=-16, absoluteY=-63), # Vland/Vland 1717 (Vilani Home World)
        multiverse.HexPosition(absoluteX=17, absoluteY=107), # Terra/Solomani Rim 1827 (Solomani Home World)
        multiverse.HexPosition(absoluteX=-198, absoluteY=-101), # Zhdant/Zhodane 2719 (Zhodani Home World)
        multiverse.HexPosition(absoluteX=-41, absoluteY=-118), # Lair/Provence 2402 (Vargr Home World)
        multiverse.HexPosition(absoluteX=-53, absoluteY=106), # Kusyu/Dark Nebula 1226 (Aslan Home World)
        multiverse.HexPosition(absoluteX=167, absoluteY=67), # Guaran/Ricenden 0827 (Hive Home World)
        multiverse.HexPosition(absoluteX=153, absoluteY=89), # Glea/Centrax 2609 (Hive Capital)
        multiverse.HexPosition(absoluteX=172, absoluteY=-65), # Kirur/Ruupiin 1315 (K'kree Home World)
        multiverse.HexPosition(absoluteX=-9, absoluteY=68) # Girillovitch/Daibei 2428 (Jimmy's Home World)
    ]

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _settings = None # Created on first load
    _filePath = '.\\' # Static config path
    _history: typing.List[multiverse.HexPosition] = []

    def __init__(self):
        raise RuntimeError('Call instance() instead')

    @classmethod
    def instance(cls):
        if not cls._instance:
            with cls._lock:
                # Recheck instance as another thread could have created it between the
                # first check adn the lock
                if not cls._instance:
                    cls._instance = cls.__new__(cls)
                    cls._instance.load()
        return cls._instance

    def hexes(self) -> typing.Iterable[multiverse.HexPosition]:
        return list(HexHistory._history)

    def addHex(self, hex: multiverse.HexPosition) -> None:
        if hex in HexHistory._history:
            # Remove the hex from the history so it can be re-added as the first entry
            HexHistory._history.remove(hex)

        # Prepend items so the history is stored in order from most recent to oldest
        HexHistory._history.insert(0, hex)

        # Clamp history to max length
        HexHistory._history = HexHistory._history[:self._MaxCount]

        # Always save search history when a new item is added. It's a pain in the ass if you
        # loose what you've typed in if the app crashes
        self.save()

    def load(self):
        if not self._settings:
            filePath = os.path.join(app.Config.instance().appDir(), self._SearchFileName)
            self._settings = QtCore.QSettings(filePath, QtCore.QSettings.Format.IniFormat)

        HexHistory._history.clear()
        size = self._settings.beginReadArray('RecentWorlds')
        for index in range(size):
            self._settings.setArrayIndex(index)
            try:
                value: typing.Optional[str] = self._settings.value('Hex', defaultValue=None, type=str)
                if not value:
                    raise RuntimeError(f'Empty hex at index {index}')
                tokens = value.split(':')
                if len(tokens) != 2:
                    raise RuntimeError(f'Invalid hex string {value} at {index}')
                HexHistory._history.append(multiverse.HexPosition(
                    absoluteX=int(tokens[0]),
                    absoluteY=int(tokens[1])))
            except TypeError as ex:
                logging.error(
                    f'Failed to read hex from "{self._settings.group()}" in "{self._settings.fileName()}"  (value is not a {type.__name__})')
            except Exception as ex:
                logging.error(
                    f'Failed to read hex from "{self._settings.group()}" in "{self._settings.fileName()}"',
                    exc_info=ex)
        self._settings.endArray()

        if not HexHistory._history:
            HexHistory._history.extend(HexHistory._DefaultSectorHexes)

    def save(self):
        self._settings.beginWriteArray('RecentWorlds')
        index = 0
        for hex in HexHistory._history:
            self._settings.setArrayIndex(index)
            self._settings.setValue('Hex', f'{hex.absoluteX()}:{hex.absoluteY()}')
            index += 1
        self._settings.endArray()
