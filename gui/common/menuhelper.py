import enum
import typing
from PyQt5 import QtWidgets

# TODO: Delete this if it ends up not being used
class MenuHelper(object):
    class Position(enum.Enum):
        First = 0
        Last = 1

    def __init__(
            self,
            menu: QtWidgets.QMenu
            ) -> None:
        super().__init__()
        self._menu = menu

    def addAction(
            self,
            action: QtWidgets.QAction,
            path: typing.Optional[typing.Sequence[str]] = None,
            position: 'MenuHelper.Position' = Position.Last
            ) -> None:
        if path:
            menu = self._findMenu(
                path=path,
                menu=self._menu)
        else:
            menu = self._menu

        actions = menu.actions()
        if not actions:
            menu.addAction(action)

        if position is MenuHelper.Position.First:
            menu.insertAction(actions[0], action)
        elif position is MenuHelper.Position.Last:
            menu.addAction(action)

    def addSeparator(
            self,
            path: typing.Optional[typing.Sequence[str]] = None,
            position: 'MenuHelper.Position' = Position.Last
            ) -> None:
        if path:
            menu = self._findMenu(
                path=path,
                menu=self._menu)
        else:
            menu = self._menu

        actions = menu.actions()
        if not actions:
            menu.addSeparator()

        if position is MenuHelper.Position.First:
            menu.insertSeparator(actions[0])
        elif position is MenuHelper.Position.Last:
            menu.addSeparator()

    def _findMenu(
            self,
            path: typing.Sequence[str],
            menu: QtWidgets.QMenu
            ) -> QtWidgets.QMenu:
        if not path:
            return menu

        segment = path[0]
        remaining = path[1:]

        # https://stackoverflow.com/questions/9399840/how-to-iterate-through-a-menus-actions-in-qt
        for action in menu.actions():
            child = action.menu()
            if child is not None and child.title() == segment:
               return self._findMenu(path=remaining, menu=child)

        child = QtWidgets.QMenu(segment, menu)
        menu.addMenu(child)
        return self._findMenu(path=remaining, menu=child)