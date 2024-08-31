import common
import diceroller
import gui
import typing
from PyQt5 import QtWidgets, QtCore

class DiceRollerManagerWidget(QtWidgets.QWidget):
    rollerSelected = QtCore.pyqtSignal(diceroller.DiceRoller)
    rollerDeleted = QtCore.pyqtSignal(diceroller.DiceRoller)

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._treeWidget = gui.TreeWidgetEx()
        self._treeWidget.setColumnCount(1)
        self._treeWidget.header().setStretchLastSection(True)
        self._treeWidget.setHeaderHidden(True)
        self._treeWidget.setVerticalScrollMode(QtWidgets.QTreeView.ScrollMode.ScrollPerPixel)
        self._treeWidget.verticalScrollBar().setSingleStep(10) # This seems to give a decent scroll speed without big jumps
        self._treeWidget.setAutoScroll(False)
        self._treeWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        itemDelegate = gui.StyledItemDelegateEx()
        itemDelegate.setHighlightCurrentItem(enabled=False)
        self._treeWidget.setItemDelegate(itemDelegate)
        self._treeWidget.itemSelectionChanged.connect(self._treeSelectionChanged)

        self._toolbar = QtWidgets.QToolBar('Toolbar')
        self._toolbar.setIconSize(QtCore.QSize(32, 32))
        self._toolbar.setOrientation(QtCore.Qt.Orientation.Vertical)
        self._toolbar.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)

        self._newGroupAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.NewList), 'New Group', self)
        self._newGroupAction.triggered.connect(self._newGroupClicked)
        self._treeWidget.addAction(self._newGroupAction)
        self._toolbar.addAction(self._newGroupAction)

        self._newRollerAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.NewGrid), 'New Roller', self)
        self._newRollerAction.triggered.connect(self._newRollerClicked)
        self._treeWidget.addAction(self._newRollerAction)
        self._toolbar.addAction(self._newRollerAction)

        self._deleteAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DeleteFile), 'Delete...', self)
        self._deleteAction.triggered.connect(self._deleteClicked)
        self._treeWidget.addAction(self._deleteAction)
        self._toolbar.addAction(self._deleteAction)

        self._treeWidget.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.ActionsContextMenu)

        widgetLayout = QtWidgets.QHBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._toolbar)
        widgetLayout.addWidget(self._treeWidget)

        self.setLayout(widgetLayout)

        self._syncToManager()

    def groupCount(self) -> int:
        return self._treeWidget.topLevelItemCount()

    # TODO: This could create a group if none exist
    def _newRollerClicked(self) -> None:
        item = self._treeWidget.currentItem()
        if not item:
            # TODO: Do something
            return
        if item.parent() != None:
            item = item.parent()
        groupId = item.data(0, QtCore.Qt.ItemDataRole.UserRole)

        try:
            rollerName = 'New Roller'
            manager = diceroller.DiceRollerManager.instance()
            roller = manager.createRoller(
                name=rollerName,
                groupId=groupId,
                dieCount=1,
                dieType=common.DieType.D6)
        except Exception as ex:
            # TODO: Do something
            return

        rollerItem = self._createRollerItem(
            roller=roller,
            groupItem=item)
        rollerItem.setSelected(True)
        self._treeWidget.setCurrentItem(rollerItem)

    def _newGroupClicked(self) -> None:
        try:
            groupName = 'Group'
            rollerName = 'New Roller'
            manager = diceroller.DiceRollerManager.instance()
            groupId = manager.createGroup(groupName)
            roller = manager.createRoller(
                name=rollerName,
                groupId=groupId,
                dieCount=1,
                dieType=common.DieType.D6)
        except Exception as ex:
            # TODO: Do something
            return

        groupItem = self._createGroupItem(
            groupId=groupId,
            groupName=groupName)
        self._treeWidget.addTopLevelItem(groupItem)

        rollerItem = self._createRollerItem(
            roller=roller,
            groupItem=groupItem)

        # It looks like you have to expand after the item has been
        # added to the control
        groupItem.setExpanded(True)
        rollerItem.setSelected(True)
        self._treeWidget.setCurrentItem(rollerItem)

    def _deleteClicked(self) -> None:
        item = self._treeWidget.currentItem()
        if not item:
            # TODO: Do something?
            return

        isGroup = item.parent() == None
        objectKey = item.data(0, QtCore.Qt.ItemDataRole.UserRole)

        try:
            if isGroup:
                diceroller.DiceRollerManager().instance().removeGroup(objectKey)
            else:
                diceroller.DiceRollerManager().instance().removeRoller(objectKey)
        except Exception as ex:
            # TODO: Do something
            pass

        if isGroup:
            itemIndex = self._treeWidget.indexOfTopLevelItem(item)
            self._treeWidget.takeTopLevelItem(itemIndex)
        else:
            parent = item.parent()
            parent.removeChild(item)
            self.rollerDeleted.emit(objectKey)

    def _treeSelectionChanged(self) -> None:
        item = self._treeWidget.currentItem()
        if not item or not item.parent(): # No parent means it's a group
            return
        roller = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        self.rollerSelected.emit(roller)

    def _createGroupItem(
            self,
            groupId: str,
            groupName: str,
            ) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem([groupName])
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, groupId)
        return item

    def _createRollerItem(
            self,
            roller: diceroller.DiceRoller,
            groupItem: QtWidgets.QTreeWidgetItem,
            ) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem([roller.name()])
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, roller)
        if groupItem:
            groupItem.addChild(item)
        return item

    def _syncToManager(self) -> None:
        with gui.SignalBlocker(self._treeWidget):
            manager = diceroller.DiceRollerManager.instance()
            for groupIndex, groupId in enumerate(manager.yieldGroups()):
                groupItem = self._treeWidget.topLevelItem(groupIndex)
                groupName = manager.groupName(groupId)
                if not groupItem:
                    groupItem = self._createGroupItem(
                        groupId=groupId,
                        groupName=groupName)
                    self._treeWidget.addTopLevelItem(groupItem)
                for rollerIndex, roller in enumerate(manager.yieldRollers(groupId=groupId)):
                    rollerItem = groupItem.child(rollerIndex)
                    if not rollerItem:
                        rollerItem = self._createRollerItem(
                            roller=roller,
                            groupItem=groupItem)



