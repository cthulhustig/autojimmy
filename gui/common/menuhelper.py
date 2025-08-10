import typing
from PyQt5 import QtWidgets

class MenuHelper(object):
    def __init__(self, menu: QtWidgets.QMenu) -> None:
        self._menu = menu

    def prependActions(
            self,
            actions: typing.Iterable[QtWidgets.QAction]
            ) -> None:
        existing = self._menu.actions()
        if existing:
            before = existing[0]
            self._menu.insertActions(before, actions)
        else:
            self._menu.addActions(actions)

    def prependAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self.prependActions(actions=[action])

    def appendActions(
            self,
            actions: typing.Iterable[QtWidgets.QAction]) -> None:
        self._menu.addActions(actions)

    def appendAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._menu.addAction(action)

    def insertActionsBefore(
            self,
            before: QtWidgets.QAction,
            actions: typing.Iterable[QtWidgets.QAction]
            ) -> None:
        self._menu.insertActions(before, actions)

    def insertActionBefore(
            self,
            before: QtWidgets.QAction,
            action: QtWidgets.QAction
            ) -> None:
        self._menu.insertAction(before, action)

    def insertActionsAfter(
            self,
            after: QtWidgets.QAction,
            actions: typing.Iterable[QtWidgets.QAction]
            ) -> None:
        existing = self._menu.actions()
        count = len(existing)
        for i in range(count):
            if existing[i] == after:
                if i == count - 1:
                    # The after action is the last item in the menu so append
                    # the new action
                    self._menu.addActions(actions)
                else:
                    before = existing[i + 1]
                    self._menu.insertActions(before, actions)
                return

        # The after action wasn't found so just add the action to the end
        # of the menu
        self._menu.addActions(actions)

    def insertActionAfter(
            self,
            after: QtWidgets.QAction,
            action: QtWidgets.QAction
            ) -> None:
        self.insertActionsAfter(
            after=after,
            actions=[action])

    def prependSeparator(self) -> None:
        existing = self._menu.actions()
        if existing:
            before = existing[0]
            self._menu.insertSeparator(before)
        else:
            self._menu.addSeparator()

    def appendSeparator(self) -> None:
        self._menu.addSeparator()

    def insertSeparatorBefore(
            self,
            before: QtWidgets.QAction
            ) -> None:
        self._menu.insertSeparator(before)

    def insertSeparatorAfter(
            self,
            after: QtWidgets.QAction
            ) -> None:
        existing = self._menu.actions()
        count = len(existing)
        for i in range(count):
            if existing[i] == after:
                if i == count - 1:
                    # The after action is the last item in the menu so append
                    # the new action
                    self._menu.addSeparator()
                else:
                    before = existing[i + 1]
                    self._menu.insertSeparator(before)
                return

        # The after action wasn't found so just add the separator to the end
        # of the menu
        self._menu.addSeparator()

    def removeAction(self, action: QtWidgets.QAction) -> None:
        self._menu.removeAction(action)
