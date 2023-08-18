import app
import logging
import os
import threading
import traveller
import typing
from PyQt5 import QtCore

class RecentWorlds(object):
    _SearchFileName = 'recentworlds.ini'
    _MaxCount = 50

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _settings = None # Created on first load
    _filePath = '.\\' # Static config path
    _history: typing.List[traveller.World] = []

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

    def worlds(self) -> typing.Iterable[traveller.World]:
        return RecentWorlds._history

    def addWorld(self, world: traveller.World) -> None:
        if world in RecentWorlds._history:
            # Remove the world from the history so it can be re-added as the first entry
            RecentWorlds._history.remove(world)

        # Prepend items so the history is stored in order from most recent to oldest
        RecentWorlds._history.insert(0, world)

        # Clamp history to max length
        RecentWorlds._history = RecentWorlds._history[:self._MaxCount]

        # Always save search history when a new item is added. It's a pain in the ass if you
        # loose what you've typed in if the app crashes
        self.save()

    def load(self):
        if not self._settings:
            filePath = os.path.join(app.Config.appDir(), self._SearchFileName)
            self._settings = QtCore.QSettings(filePath, QtCore.QSettings.Format.IniFormat)

        RecentWorlds._history.clear()
        size = self._settings.beginReadArray('RecentWorlds')
        for index in range(size):
            self._settings.setArrayIndex(index)
            try:
                sectorHex = self._settings.value('SectorHex', defaultValue=None, type=str)
                world = traveller.WorldManager.instance().world(sectorHex)
                if not world:
                    # Log this at a low level as it could happen if the user switches milieu
                    logging.debug(
                        f'Failed to find world at sector hex "{sectorHex}" when loading recent worlds list')
                    continue

                if world not in RecentWorlds._history:
                    RecentWorlds._history.append(world)
            except TypeError as ex:
                logging.error(
                    f'Failed to read SectorHex from "{self._settings.group()} in "{self._settings.fileName()}"  (value is not a {type.__name__})')
            except Exception as ex:
                logging.error(
                    f'Failed to read SectorHex from "{self._settings.group()}" in "{self._settings.fileName()}"',
                    exc_info=ex)

        self._settings.endArray()

        self._showToolTipImages = True

    def save(self):
        self._settings.beginWriteArray('RecentWorlds')
        for index, world in enumerate(RecentWorlds._history):
            self._settings.setArrayIndex(index)
            self._settings.setValue('SectorHex', world.sectorHex())
        self._settings.endArray()
