import astronomer
import azathoth
import common
import logging
import threading
import typing
import weakref

class UniverseEditor(object):
    # To mimic the behaviour of Traveller Map, the world position data for
    # M1105 is used as placeholders if the specified milieu doesn't have
    # a sector at that location. The world details may not be valid for the
    # specified milieu but the position is
    _PlaceholderMilieu = astronomer.Milieu.M1105

    _UndoStackSize = 4 # TODO: This should be a lot higher

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _observers = common.ObserverSet[azathoth.ChangeEvent]()
    _entityFactory = azathoth.EditableEntityFactory()
    _universe: azathoth.EditableUniverse = None
    _undoStack = azathoth.UndoRedoStack(maxDepth=_UndoStackSize)
    _modifiedSectors = set[str]()

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

    def universe(self) -> astronomer.Universe:
        return self._universe

    def loadUniverse(
            self,
            universeId: str,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> None:
        if self._universe and self._universe.universeId() == universeId:
            return # Nothing to do

        self._universe = astronomer.loadUniverseFromDatabase(
            universeId=universeId,
            placeholderMilieu=UniverseEditor._PlaceholderMilieu,
            entityFactory=self._entityFactory,
            progressCallback=progressCallback)

        # Clear undo stack of content from the previous universe
        self._undoStack.clear()

        astronomer.WorldManager.instance().setUniverse(universe=self._universe)

    def entityFactory(self) -> azathoth.EditableEntityFactory:
        return self._entityFactory

    def addObserver(self, handler: typing.Callable[[azathoth.ChangeEvent], None]) -> None:
        self._observers.register(handler)

    def removeObserver(self, handler: typing.Callable[[azathoth.ChangeEvent], None]) -> None:
        self._observers.unregister(handler)

    def executeCommand(self, command: azathoth.EditCommandInterface) -> None:
        self._applyCommand(command=command)
        self._undoStack.push(command=command)

    def saveChanges(self) -> None:
        pass

    def revertChanges(self) -> None:
        pass

    def undo(self) -> None:
        command = self._undoStack.undo()
        self._revertCommand(command=command)

    def redo(self) -> None:
        command = self._undoStack.redo()
        self._applyCommand(command=command)

    def _notifyObservers(
            self,
            changeEvent: azathoth.ChangeEvent,
            errorMsg: str
            ) -> None:
        self._observers.notify(
            changeEvent,
            exceptionCallback=lambda ex: logging.error(errorMsg, exc_info=ex))

    def _applyCommand(self, command: azathoth.EditCommandInterface) -> None:
        changeEvent = command.applyEvent()

        self._notifyObservers(
            changeEvent=changeEvent,
            errorMsg='Editor observer threw an exception when handling pre change notification')

        command.applyChanges(universe=self._universe)

        self._notifyObservers(
            changeEvent=changeEvent,
            errorMsg='Editor observer threw an exception when handling post change notification')

    def _revertCommand(self, command: azathoth.EditCommandInterface) -> None:
        changeEvent = command.revertEvent()

        self._notifyObservers(
            changeEvent=changeEvent,
            errorMsg='Editor observer threw an exception when handling pre revert notification')

        command.revertChanges(universe=self._universe)

        self._notifyObservers(
            changeEvent=changeEvent,
            errorMsg='Editor observer threw an exception when handling post revert notification')