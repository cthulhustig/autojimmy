import app
import logging
import os
import threading
import traveller
import travellermap
import typing
from PyQt5 import QtCore

class HexHistory(object):
    # NOTE: This class uses a file called recentworlds.ini even though it can
    # contain hexes that don't contain worlds. This is for legacy reasons as
    # the history feature was added before I added for support for dead space
    # routing
    _SearchFileName = 'recentworlds.ini'
    _MaxCount = 50

    # Based on the default list Traveller Map shows in a drop down if you click
    # on the search edit box when it has no content
    _DefaultSectorHexes = [
        'Core 0140', # Reference
        'Core 2118', # Capital
        'Spinward Marches 1910', # Regina
        'Vland 1717', # Vland (Vilani Home World)
        'Solomani Rim 1827', # Terra (Solomani Home World)
        'Zhodane 2719', # Zhdant (Zhodani Home World)
        'Provence 2402', # Lair (Vargr Home World)
        'Dark Nebula 1226', # Kusyu (Aslan Home World)
        'Ricenden 0827', # Guaran (Hive Home World)
        'Centrax 2609', # Glea (Hive Capital)
        'Ruupiin 1315', # Kirur (K'kree Home World)
        'Daibei 2428' # Girillovitch (Jimmy's Home World)
    ]

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _settings = None # Created on first load
    _filePath = '.\\' # Static config path
    _history: typing.List[travellermap.HexPosition] = []

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

    def hexes(self) -> typing.Iterable[travellermap.HexPosition]:
        return list(HexHistory._history)

    def addHex(self, pos: travellermap.HexPosition) -> None:
        if pos in HexHistory._history:
            # Remove the hex from the history so it can be re-added as the first entry
            HexHistory._history.remove(pos)

        # Prepend items so the history is stored in order from most recent to oldest
        HexHistory._history.insert(0, pos)

        # Clamp history to max length
        HexHistory._history = HexHistory._history[:self._MaxCount]

        # Always save search history when a new item is added. It's a pain in the ass if you
        # loose what you've typed in if the app crashes
        self.save()

    def load(self):
        if not self._settings:
            filePath = os.path.join(app.Config.appDir(), self._SearchFileName)
            self._settings = QtCore.QSettings(filePath, QtCore.QSettings.Format.IniFormat)

        HexHistory._history.clear()
        size = self._settings.beginReadArray('RecentWorlds')
        sectorHexes = []
        for index in range(size):
            self._settings.setArrayIndex(index)
            try:
                sectorHexes.append(self._settings.value('SectorHex', defaultValue=None, type=str))
            except TypeError as ex:
                logging.error(
                    f'Failed to read SectorHex from "{self._settings.group()}" in "{self._settings.fileName()}"  (value is not a {type.__name__})')
            except Exception as ex:
                logging.error(
                    f'Failed to read SectorHex from "{self._settings.group()}" in "{self._settings.fileName()}"',
                    exc_info=ex)
        self._settings.endArray()

        for sectorHex in sectorHexes:
            try:
                pos = traveller.WorldManager.instance().sectorHexToPosition(sectorHex)
                HexHistory._history.append(pos)
            except Exception as ex:
                logging.error(
                    f'Failed to resolve sector hex "{sectorHex}" when reading "{self._settings.fileName()}"',
                    exc_info=ex)

        if not HexHistory._history:
            for sectorHex in HexHistory._DefaultSectorHexes:
                try:
                    pos = traveller.WorldManager.instance().sectorHexToPosition(sectorHex)
                    HexHistory._history.append(pos)
                except Exception as ex:
                    logging.error(
                        f'Failed to resolve default sector hex "{sectorHex}" when reading "{self._settings.fileName()}"',
                        exc_info=ex)

    def save(self):
        self._settings.beginWriteArray('RecentWorlds')
        index = 0
        for pos in HexHistory._history:
            try:
                sectorHex = traveller.WorldManager.instance().positionToSectorHex(pos=pos)
            except Exception as ex:
                logging.error(
                    f'Failed to determine sector hex for position {pos} when saving "{self._settings.fileName()}"',
                    exc_info=ex)
                continue

            self._settings.setArrayIndex(index)
            self._settings.setValue('SectorHex', sectorHex)
            index += 1
        self._settings.endArray()
