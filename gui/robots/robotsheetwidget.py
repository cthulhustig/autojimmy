import app
import common
import gui
import logging
import robots
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

class RobotSheetWidget(QtWidgets.QWidget):
    # TODO: Need something to allow you to copy/paste all the data (similar to
    # notes widget)

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

    # TODO: The wording of this probably need improved
    # - Cover the fact "other modifiers" aren't applied
    _ApplySkillModifiersToolTip = \
        """
        <p>Choose if Skills have the relevant characteristic modifier
        pre-applied as they do in the book.<p>
        <p>By default {name} will just display the base skill level in an
        effort to make dealing with robots in game more straight forward. By
        doing this it means calculating the final modifier is handled in the
        same way as for a meat sack traveller. Any relevant characteristic
        modifiers are applied to the skill level along with any other applicable
        modifiers. The only difference is, with the exception of robots using a
        Brain in a Jar, if the SOC or EDU characteristic modifier would usually
        be applied, instead you use the INT characteristic modifier as described
        in Inherent Skill DMs (p73).<br>
        This aim of displaying the skill levels in this way is to make it easier
        to deal with situations where a non-standard characteristic modifier
        might be required (e.g. using Deception combined with DEX for slight of
        hand) or when dealing with more complex robots (e.g. physical skills for
        robots with no manipulators or manipulators with different STR/DEX
        modifiers).</p>
        <p>Alternatively {name} can be configured to display skills with the
        default characteristic modifier pre-applied in an attempt to replicate
        how robots are displayed in the Robot Handbook and described in the
        Finalisation section (p76).<br>
        However, displaying skills like this is <b>not recommended</b>. As well
        as making it more difficult to calculate modifiers for more complex
        robots or more unusual tasks, the logic behind the values that are
        shown in the book also makes it prohibitively complex to create code
        that would replicate the values for all of the example robots. What it
        currently does is a best effort attempt to replicate how skill values
        are shown and it's only really intended as an aid if you're trying to
        replicate one of the example robots from the book.</p>
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
        self._table.customContextMenuRequested.connect(self._tableContextMenu)
        for field, headerColumn, headerRow, dataColumn, dataRow, dataSpan in RobotSheetWidget._LayoutData:
            if dataSpan:
                self._table.setSpan(dataRow, dataColumn, 1, RobotSheetWidget._ColumnCount - dataColumn)
            item = RobotSheetWidget._createHeaderItem(field)
            self._table.setItem(headerRow, headerColumn, item)
            item = RobotSheetWidget._createDataItem(field)
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
