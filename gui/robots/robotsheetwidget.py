import app
import common
import gui
import logging
import robots
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

class RobotSheetWidget(QtWidgets.QWidget):
    _StateVersion = 'RobotSheetWidget_v1'

    _ColumnCount = 6
    _RowCount = 9
    # Data Format: Section, Header Column, Header Row, Data Column, Data Row, Data Span Columns
    _LayoutData = (
        (robots.Worksheet.Field.Robot, 0, 0, 0, 1, False),
        (robots.Worksheet.Field.Hits, 1, 0, 1, 1, False),
        (robots.Worksheet.Field.Locomotion, 2, 0, 2, 1, False),
        (robots.Worksheet.Field.Speed, 3, 0, 3, 1, False),
        (robots.Worksheet.Field.TL, 4, 0, 4, 1, False),
        (robots.Worksheet.Field.Cost, 5, 0, 5, 1, False),
        (robots.Worksheet.Field.Skills, 0, 2, 1, 2, True),
        (robots.Worksheet.Field.Attacks, 0, 3, 1, 3, True),
        (robots.Worksheet.Field.Manipulators, 0, 4, 1, 4, True),
        (robots.Worksheet.Field.Endurance, 0, 5, 1, 5, True),
        (robots.Worksheet.Field.Traits, 0, 6, 1, 6, True),
        (robots.Worksheet.Field.Programming, 0, 7, 1, 7, True),
        (robots.Worksheet.Field.Options, 0, 8, 1, 8, True)
    )

    _ApplySkillModifiersToolTip = \
        """
        <p>Choose if the displayed skill values include the the characteristic
        DM as they do in the Robot Handbook.<p>
        <p>The skill values listed for robots in the Robot Handbook have the
        characteristic DMs included in the values as described in the Inherent
        Skill DMs and Finalisation sections (p73 & p76). This can result in
        confusion due to it being different to how skills are handled for
        player/NPC character sheets. It also makes it far harder to work out
        modifiers for robots with manipulators of different sizes or for
        situations where the 'standard' characteristic may not be the most
        suitable for the check being made.</p>
        <p>By default, {name} will only display the base skill level. This is
        done in an effort to make dealing with robots in game more straight
        forward. By doing this it means calculating the final DM is handled in
        the same way as for a meat sack traveller. When making a check, the DM
        for the appropriate characteristic is added to the skill level along
        with any situation specific DMs. The only difference is, unless your
        dealing with a robot that specifically has a SOC/EDU characteristic,
        the robots INT characteristic is used in their place as described in
        the Inherent Skill DMs section (p73).</p>
        <p>Alternatively, when this option is enabled, {name} will include
        characteristics DMs in the displayed skill values. However, displaying
        skills like this is <b>not recommended</b>.</p>
        <p><b>When characteristic DMs are being included in the displayed skill
        values, the list of automatically generated notes will still contain
        notes covering the modifiers that have been applied. It's up to the user
        to not double count them.</b></p>
        """.format(name=app.AppName)

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)
        self._robot = None
        self._dataItemMap: typing.Dict[RobotSheetWidget._Sections, QtWidgets.QTableWidgetItem] = {}

        self._characteristicsDMCheckBox = gui.CheckBoxEx('Include Characteristic DMs in Skill Levels')
        self._characteristicsDMCheckBox.setToolTip(RobotSheetWidget._ApplySkillModifiersToolTip)
        self._characteristicsDMCheckBox.stateChanged.connect(self._applySkillModifiersChanged)

        controlsLayout = QtWidgets.QVBoxLayout()
        controlsLayout.addWidget(self._characteristicsDMCheckBox)
        controlsLayout.addStretch()

        self._table = QtWidgets.QTableWidget()
        self._table.setColumnCount(RobotSheetWidget._ColumnCount)
        self._table.setRowCount(RobotSheetWidget._RowCount)        
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
        self._table.setItemDelegate(gui.TableViewSpannedWordWrapFixDelegate())
        self._table.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._table.installEventFilter(self)      
        self._table.customContextMenuRequested.connect(self._tableContextMenu)
        for field, headerColumn, headerRow, dataColumn, dataRow, dataSpan in RobotSheetWidget._LayoutData:
            if dataSpan:
                self._table.setSpan(dataRow, dataColumn, 1, RobotSheetWidget._ColumnCount - dataColumn)

            item = RobotSheetWidget._createHeaderItem(field)
            item.setTextAlignment(int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop))
            self._table.setItem(headerRow, headerColumn, item)

            item = RobotSheetWidget._createDataItem(field)
            item.setTextAlignment(int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop))
            self._table.setItem(dataRow, dataColumn, item)
            self._dataItemMap[field] = item

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
        width = event.size().width() - 2 # -2 is needed to stop horizontal scrollbar appearing
        maxWidth = int(width / RobotSheetWidget._ColumnCount)
        self._table.horizontalHeader().setMinimumSectionSize(maxWidth)
        self._table.horizontalHeader().setMaximumSectionSize(maxWidth)
        self._table.resizeRowsToContents()
        return super().resizeEvent(event)
    
    def eventFilter(self, object: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if object == self._table:
            if event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.matches(QtGui.QKeySequence.StandardKey.Copy):
                    self._copyToClipboard()
                    event.accept()
                    return True

        return super().eventFilter(object, event)    

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(self._StateVersion)

        modifiersState = self._characteristicsDMCheckBox.saveState()
        stream.writeUInt32(modifiersState.count() if modifiersState else 0)
        if modifiersState:
            stream.writeRawData(modifiersState.data())

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
        modifiersState = QtCore.QByteArray(stream.readRawData(count))
        if not self._characteristicsDMCheckBox.restoreState(modifiersState):
            return False

        return True

    def _updateTable(self) -> None:
        worksheet = self._robot.worksheet(
            applySkillModifiers=self._characteristicsDMCheckBox.isChecked())
        for field, item in self._dataItemMap.items():
            item.setText(worksheet.value(field=field))
            item.setData(
                QtCore.Qt.ItemDataRole.UserRole,
                worksheet.calculations(field=field))

        self._table.resizeRowsToContents()

    def _applySkillModifiersChanged(self) -> None:
        self._updateTable()

    def _copyToClipboard(self) -> None:
        clipboard = QtWidgets.QApplication.clipboard()
        if not clipboard:
            return
                
        content = ''
        for _, headerColumn, headerRow, dataColumn, dataRow, _ in RobotSheetWidget._LayoutData:
            headerItem = self._table.item(headerRow, headerColumn)
            dataItem = self._table.item(dataRow, dataColumn)
            if headerItem and dataItem:
                content += f'{headerItem.text()} -- {dataItem.text()}\n'
        if content:
            clipboard.setText(content)

    def _tableContextMenu(
            self,
            position: QtCore.QPoint
            ) -> None:
        item = self._table.itemAt(position)
        if not item:
            return
        
        calculations = item.data(QtCore.Qt.ItemDataRole.UserRole)
        menuItems = [
            gui.MenuItem(
                text='Calculation...',
                callback=lambda: self._showCalculations(calculations=calculations),
                enabled=calculations != None and len(calculations) > 0)
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._table.viewport().mapToGlobal(position))

    def _showCalculations(
            self,
            calculations: typing.Iterable[common.ScalarCalculation]
            ) -> None:
        try:
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
        return item
    
    @staticmethod
    def _createDataItem(field: robots.Worksheet.Field) -> QtWidgets.QTableWidgetItem:
        item = gui.TableWidgetItemEx()
        return item
