import azathoth
import typing

class UndoRedoStack(object):
    def __init__(self, maxDepth: int = 100) -> None:
        self._undoStack = []
        self._redoStack = []
        self._maxDepth = maxDepth

    def push(self, command: azathoth.EditCommandInterface):
        self._undoStack.append(command)
        if len(self._undoStack) > self._maxDepth:
            self._undoStack.pop(0)
        self._redoStack.clear()

    def undo(self) -> typing.Optional[azathoth.EditCommandInterface]:
        if not self._undoStack:
            return None

        command = self._undoStack.pop()
        self._redoStack.append(command)

        return command

    def redo(self) -> typing.Optional[azathoth.EditCommandInterface]:
        if not self._redoStack:
            return None

        command = self._redoStack.pop()
        self._undoStack.append(command)

        return command

    def clear(self) -> None:
        self._undoStack.clear()
        self._redoStack.clear()