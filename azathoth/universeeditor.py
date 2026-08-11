import astronomer
import azathoth
import common
import logging
import threading
import typing

# TODO: Need to have controls other than map subscribe to be notified when changes
# occur and update their state when they do
# - PurchaseCalculatorWindow
# - SaleCalculatorWindow



class UniverseEditor(object):
    _UndoStackSize = 4 # TODO: This should be a lot higher

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _preUpdateObservers = common.ObserverSet[azathoth.EditableUniverse, azathoth.ChangeEvent]()
    _postUpdateObservers = common.ObserverSet[azathoth.EditableUniverse, azathoth.ChangeEvent]()
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

    def universe(self) -> azathoth.EditableUniverse:
        return self._universe

    def loadUniverse(
            self,
            universeId: str,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> None:
        if self._universe and self._universe.id() == universeId:
            return # Nothing to do

        self._universe = astronomer.loadUniverseFromDatabase(
            universeId=universeId,
            entityFactory=self._entityFactory,
            progressCallback=progressCallback)

        # Clear undo stack of content from the previous universe
        self._undoStack.clear()

        astronomer.WorldManager.instance().setUniverse(universe=self._universe)

    def entityFactory(self) -> azathoth.EditableEntityFactory:
        return self._entityFactory

    def addPreUpdateObserver(self, handler: typing.Callable[[azathoth.EditableUniverse, azathoth.ChangeEvent], None]) -> None:
        self._preUpdateObservers.register(handler)

    def addPostUpdateObserver(self, handler: typing.Callable[[azathoth.EditableUniverse, azathoth.ChangeEvent], None]) -> None:
        self._postUpdateObservers.register(handler)

    def removeObserver(self, handler: typing.Callable[[azathoth.EditableUniverse, azathoth.ChangeEvent], None]) -> None:
        self._preUpdateObservers.unregister(handler)
        self._postUpdateObservers.unregister(handler)

    def executeCommand(self, command: azathoth.EditCommandInterface) -> None:
        self._applyCommand(command=command)
        self._undoStack.push(command=command)

    def saveChanges(self) -> None:
        pass

    def revertChanges(self) -> None:
        pass

    def canUndo(self) -> bool:
        return self._undoStack.canUndo()

    def undo(self) -> None:
        command = self._undoStack.undo()
        self._revertCommand(command=command)

    def canRedo(self) -> bool:
        return self._undoStack.canRedo()

    def redo(self) -> None:
        command = self._undoStack.redo()
        self._applyCommand(command=command)

    def _applyCommand(self, command: azathoth.EditCommandInterface) -> None:
        changeEvent = command.applyEvent()

        self._notifyObservers(
            observers=self._preUpdateObservers,
            changeEvent=changeEvent,
            errorMsg='Editor observer threw an exception when handling pre change notification')

        command.applyChanges(universe=self._universe)

        self._notifyObservers(
            observers=self._postUpdateObservers,
            changeEvent=changeEvent,
            errorMsg='Editor observer threw an exception when handling post change notification')

    def _revertCommand(self, command: azathoth.EditCommandInterface) -> None:
        changeEvent = command.revertEvent()

        self._notifyObservers(
            observers=self._preUpdateObservers,
            changeEvent=changeEvent,
            errorMsg='Editor observer threw an exception when handling pre revert notification')

        command.revertChanges(universe=self._universe)

        self._notifyObservers(
            observers=self._postUpdateObservers,
            changeEvent=changeEvent,
            errorMsg='Editor observer threw an exception when handling post revert notification')

    def _notifyObservers(
            self,
            observers: common.ObserverSet[azathoth.ChangeEvent],
            changeEvent: azathoth.ChangeEvent,
            errorMsg: str
            ) -> None:
        observers.notify(
            self._universe,
            changeEvent,
            exceptionCallback=lambda ex: logging.error(errorMsg, exc_info=ex))