import app
import common
import gui
import logging
import robots
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

class RobotSheetWidget(QtWidgets.QWidget):
    _StateVersion = 'RobotSheetWidget_v2'

    _WorksheetTopRow = [
        robots.Worksheet.Field.Robot,
        robots.Worksheet.Field.Hits,
        robots.Worksheet.Field.Locomotion,
        robots.Worksheet.Field.Speed,
        robots.Worksheet.Field.TL,
        robots.Worksheet.Field.Cost
    ]

    _ApplySkillModifiersToolTip = \
        """
        <p>Specify if the skill levels displayed include the characteristic DMs
        and other modifiers.</p>
        <p>The skill values listed for robots in the Robot Handbook have
        characteristic DMs and some other modifiers (e.g. manipulator athletics
        skills) pre-applied. This can result in ambiguities and unnecessary
        complexities when dealing with anything other than simple robots and
        encounters, for example, robots that have manipulators with different
        characteristics or making skill check where the standard characteristic
        isn't the one that is appropriate for the situation at hand (e.g. using
        Gun Combat to try and identify an obscure model of pistol would use INT
        or EDU rather than DEX). To avoid these potential issues, by default,
        {name} will only display the base skill level without characteristic DMs
        included.</p>
        <p><b>When characteristic DMs are being included in the displayed skill
        values, the list of automatically generated notes will still contain
        notes covering the modifiers that have been pre-applied. It's up to the
        user to not double count them.</p>
        """.format(name=app.AppName)

    _GroupSkillSpecialitiesToolTip = \
        """
        <p>Specify the number of specialities that must be taken in a skill for
        the robot to be classes as having all specialities in that skill.</p>
        <p>The robot handbook suggests that, at the referees discretion, taking
        a number of specialities in the same skill at the same level can be
        taken to mean the robot all specialities in that skill (p73). The
        suggested number of specialities to require is 4.</p>
        """

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)
        self._robot = None

        self._applySkillModifiersCheckBox = gui.CheckBoxEx('Include DMs in Skill Levels:')
        self._applySkillModifiersCheckBox.setTextOnLeft(True)
        self._applySkillModifiersCheckBox.setToolTip(RobotSheetWidget._ApplySkillModifiersToolTip)
        self._applySkillModifiersCheckBox.stateChanged.connect(self._applySkillModifiersChanged)

        self._specialityGroupCountSpinBox = gui.OptionalSpinBox('Group Skill Specialities:')
        self._specialityGroupCountSpinBox.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
        self._specialityGroupCountSpinBox.setRange(3, 10)
        self._specialityGroupCountSpinBox.setValue(4)
        self._specialityGroupCountSpinBox.setUncheckedValue(0)
        self._specialityGroupCountSpinBox.setToolTip(RobotSheetWidget._GroupSkillSpecialitiesToolTip)
        self._specialityGroupCountSpinBox.valueChanged.connect(self._specialityGroupCountChanged)

        interfaceScale = app.ConfigEx.instance().asFloat(
            option=app.ConfigOption.InterfaceScale)
        controlsLayout = QtWidgets.QHBoxLayout()
        controlsLayout.addWidget(self._applySkillModifiersCheckBox)
        controlsLayout.addSpacing(int(10 * interfaceScale))
        controlsLayout.addWidget(self._specialityGroupCountSpinBox)
        controlsLayout.addStretch()

        self._table = gui.TableWidgetEx()
        self._table.setShowFocusRect(enabled=True)
        self._table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self._table.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self._table.setWordWrap(True)
        self._table.setEditTriggers(QtWidgets.QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().hide()
        self._table.verticalHeader().hide()
        self._table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Fixed)
        self._table.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().sectionResized.connect(
            self._table.resizeRowsToContents)
        self._table.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._table.setTextElideMode(QtCore.Qt.TextElideMode.ElideNone)
        itemDelegate = gui.TableViewSpannedWordWrapFixDelegate()
        itemDelegate.setHighlightCurrentItem(enabled=False)
        self._table.setItemDelegate(itemDelegate)
        self._table.installEventFilter(self)
        self._table.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._tableContextMenu)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(controlsLayout)
        layout.addWidget(self._table)

        self.setLayout(layout)

    def robot(self) -> typing.Optional[robots.Robot]:
        return self._robot

    def setRobot(
            self,
            robot: typing.Optional[robots.Robot]
            ) -> None:
        self._robot = robot
        self._updateTable()

    def clear(self) -> None:
        self._robot = None
        self._updateTable()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        columnCount = self._table.columnCount()
        if columnCount:
            width = event.size().width() - 2 # -2 is needed to stop horizontal scrollbar appearing
            maxWidth = int(width / columnCount)
            self._table.horizontalHeader().setMinimumSectionSize(maxWidth)
            self._table.horizontalHeader().setMaximumSectionSize(maxWidth)
            self._table.resizeRowsToContents()
        return super().resizeEvent(event)

    def eventFilter(self, object: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if object == self._table:
            if event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.matches(QtGui.QKeySequence.StandardKey.Copy):
                    self._copyToClipboardHtml()
                    event.accept()
                    return True

        return super().eventFilter(object, event)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(self._StateVersion)

        childState = self._applySkillModifiersCheckBox.saveState()
        stream.writeUInt32(childState.count() if childState else 0)
        if childState:
            stream.writeRawData(childState.data())

        childState = self._specialityGroupCountSpinBox.saveState()
        stream.writeUInt32(childState.count() if childState else 0)
        if childState:
            stream.writeRawData(childState.data())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != self._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug('Failed to restore RobotSheetWidget state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count <= 0:
            return True
        childState = QtCore.QByteArray(stream.readRawData(count))
        if not self._applySkillModifiersCheckBox.restoreState(childState):
            return False

        count = stream.readUInt32()
        if count <= 0:
            return True
        childState = QtCore.QByteArray(stream.readRawData(count))
        if not self._specialityGroupCountSpinBox.restoreState(childState):
            return False

        return True

    def _updateTable(self) -> None:
        worksheet = self._robot.worksheet(
            applySkillModifiers=self._applySkillModifiersCheckBox.isChecked(),
            specialityGroupingCount=self._specialityGroupCountSpinBox.value())

        self._table.clear()

        columnCount = 0
        for field in RobotSheetWidget._WorksheetTopRow:
            if worksheet.hasField(field=field):
                columnCount += 1
        if not columnCount:
            return # This should never happen
        self._table.setColumnCount(columnCount)
        self._table.setRowCount(2)

        columnIndex = 0
        for field in RobotSheetWidget._WorksheetTopRow:
            if not worksheet.hasField(field=field):
                continue
            item = RobotSheetWidget._createHeaderItem(field)
            self._table.setItem(0, columnIndex, item)
            columnIndex += 1

        columnIndex = 0
        for field in RobotSheetWidget._WorksheetTopRow:
            if not worksheet.hasField(field=field):
                continue
            item = RobotSheetWidget._createDataItem(
                value=worksheet.value(field=field),
                calculations=worksheet.calculations(field=field))
            self._table.setItem(1, columnIndex, item)
            columnIndex += 1

        for field in robots.Worksheet.Field:
            if field in RobotSheetWidget._WorksheetTopRow:
                continue
            if not worksheet.hasField(field=field):
                continue

            rowIndex = self._table.rowCount()
            self._table.insertRow(rowIndex)
            self._table.setSpan(rowIndex, 1, 1, columnCount - 1)

            item = RobotSheetWidget._createHeaderItem(field)
            self._table.setItem(rowIndex, 0, item)

            item = RobotSheetWidget._createDataItem(
                value=worksheet.value(field=field),
                calculations=worksheet.calculations(field=field))
            self._table.setItem(rowIndex, 1, item)

        self._table.resizeRowsToContents()

    def _applySkillModifiersChanged(self) -> None:
        self._updateTable()

    def _specialityGroupCountChanged(self) -> None:
        self._updateTable()

    def _copyToClipboardHtml(self) -> None:
        clipboard = QtWidgets.QApplication.clipboard()
        if not clipboard:
            return

        content = self._table.contentToHtml()
        if content:
            clipboard.setText(content)

    def _copyToClipboardBitmap(self) -> None:
        clipboard = QtWidgets.QApplication.clipboard()
        if not clipboard:
            return

        pixmap = self._table.grab()
        if pixmap:
            clipboard.setImage(pixmap.toImage())

    def _tableContextMenu(
            self,
            point: QtCore.QPoint
            ) -> None:
        menuItems = [
            gui.MenuItem(
                text='Show Calculations...',
                callback=self._showCalculations),
            None,
            gui.MenuItem(
                text='Copy as Bitmap',
                callback=self._copyToClipboardBitmap),
            gui.MenuItem(
                text='Copy as HTML',
                callback=self._copyToClipboardHtml)
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._table.viewport().mapToGlobal(point))

    def _showCalculations(self) -> None:
        try:
            calculations = []
            for row in range(self._table.rowCount()):
                for column in range(self._table.columnCount()):
                    item = self._table.item(row, column)
                    data = item.data(QtCore.Qt.ItemDataRole.UserRole) if item else None
                    if data:
                        calculations.extend(data)

            calculationWindow = gui.WindowManager.instance().showCalculationWindow()
            calculationWindow.showCalculations(
                calculations=calculations,
                decimalPlaces=robots.ConstructionDecimalPlaces)
        except Exception as ex:
            message = 'Failed to show calculations'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    @staticmethod
    def _createHeaderItem(field: robots.Worksheet.Field) -> QtWidgets.QTableWidgetItem:
        item = gui.TableWidgetItemEx(field.value)
        item.setBold(enable=True)
        item.setTextAlignment(
            int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop))
        return item

    @staticmethod
    def _createDataItem(
            value: str,
            calculations: typing.Iterable[common.ScalarCalculation]
            ) -> QtWidgets.QTableWidgetItem:
        item = gui.TableWidgetItemEx(value)
        item.setTextAlignment(
            int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop))
        item.setData(
            QtCore.Qt.ItemDataRole.UserRole,
            calculations)
        return item
