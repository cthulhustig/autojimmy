import common
import diceroller
import gui
import objectdb
import typing
from PyQt5 import QtWidgets, QtCore

class DiceRollerManagerWidget(QtWidgets.QWidget):
    rollerSelected = QtCore.pyqtSignal(diceroller.DiceRollerDatabaseObject)
    rollerDeleted = QtCore.pyqtSignal(diceroller.DiceRollerDatabaseObject)

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

    # TODO: This could create a group if none exist
    def _newRollerClicked(self) -> None:
        item = self._treeWidget.currentItem()
        if not item:
            # TODO: Do something
            return
        if item.parent() != None:
            item = item.parent()
        group = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        assert(isinstance(group, diceroller.DiceRollerGroupDatabaseObject))

        try:
            roller = diceroller.DiceRollerDatabaseObject(
                name='New Roller',
                dieCount=1,
                dieType=common.DieType.D6)
            group.addRoller(roller)
            objectdb.ObjectDbManager.instance().createObject(
                object=roller)
        except Exception as ex:
            # TODO: Do something
            print(ex)
            return

        rollerItem = self._createRollerItem(
            roller=roller,
            groupItem=item)
        rollerItem.setSelected(True)
        self._treeWidget.setCurrentItem(rollerItem)

    def _newGroupClicked(self) -> None:
        try:
            roller = diceroller.DiceRollerDatabaseObject(
                name='New Roller',
                dieCount=1,
                dieType=common.DieType.D6)
            group = diceroller.DiceRollerGroupDatabaseObject(
                name='New Roller',
                rollers=[roller])

            objectdb.ObjectDbManager.instance().createObject(
                object=group)
        except Exception as ex:
            # TODO: Do something
            print(ex)
            return

        groupItem = self._createGroupItem(group=group)
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
        object = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        assert(isinstance(object, objectdb.DatabaseObject))

        try:
            objectdb.ObjectDbManager.instance().deleteObject(
                id=object.id())
        except Exception as ex:
            # TODO: Do something
            print(ex)
            pass

        if isGroup:
            itemIndex = self._treeWidget.indexOfTopLevelItem(item)
            self._treeWidget.takeTopLevelItem(itemIndex)
        else:
            parent = item.parent()
            parent.removeChild(item)
            self.rollerDeleted.emit(object)

    def _treeSelectionChanged(self) -> None:
        item = self._treeWidget.currentItem()
        if not item or not item.parent(): # No parent means it's a group
            return
        roller = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        self.rollerSelected.emit(roller)

    def _createGroupItem(
            self,
            group: diceroller.DiceRollerGroupDatabaseObject
            ) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem([group.name()])
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, group)
        return item

    def _createRollerItem(
            self,
            roller: diceroller.DiceRollerDatabaseObject,
            groupItem: QtWidgets.QTreeWidgetItem,
            ) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem([roller.name()])
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, roller)
        if groupItem:
            groupItem.addChild(item)
        return item

    def _syncToManager(self) -> None:
        with gui.SignalBlocker(self._treeWidget):
            groups = objectdb.ObjectDbManager.instance().readObjects(
                classType=diceroller.DiceRollerGroupDatabaseObject)
            for groupIndex, group in enumerate(groups):
                assert(isinstance(group, diceroller.DiceRollerGroupDatabaseObject))
                groupItem = self._treeWidget.topLevelItem(groupIndex)
                if not groupItem:
                    groupItem = self._createGroupItem(group=group)
                    self._treeWidget.addTopLevelItem(groupItem)
                for rollerIndex, roller in enumerate(group.rollers()):
                    rollerItem = groupItem.child(rollerIndex)
                    if not rollerItem:
                        rollerItem = self._createRollerItem(
                            roller=roller,
                            groupItem=groupItem)



