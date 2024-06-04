import common
import enum
import gui
import robots
import traveller
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

class RobotSheetWidget(QtWidgets.QWidget):
    class _Sections(enum.Enum):
        Robot = 'Robot'
        Hits = 'Hits'
        Locomotion = 'Locomotion'
        Speed = "Speed"
        TL = "TL"
        Cost = "Cost"
        Skills = "Skills"
        Attacks = "Attacks"
        Manipulators = "Manipulators"
        Endurance = "Endurance"
        Traits = "Traits"
        Programming = "Programming"
        Options = "Options"

    _ColumnCount = 6
    _RowCount = 9
    # Data Format: Section, Header Column, Header Row, Data Column, Data Row, Data Span Columns
    _LayoutData = (
        (_Sections.Robot, 0, 0, 0, 1, False),
        (_Sections.Hits, 1, 0, 1, 1, False),
        (_Sections.Locomotion, 2, 0, 2, 1, False),
        (_Sections.Speed, 3, 0, 3, 1, False),
        (_Sections.TL, 4, 0, 4, 1, False),
        (_Sections.Cost, 5, 0, 5, 1, False),
        (_Sections.Skills, 0, 2, 1, 2, True),
        (_Sections.Attacks, 0, 3, 1, 3, True),
        (_Sections.Manipulators, 0, 4, 1, 4, True),
        (_Sections.Endurance, 0, 5, 1, 5, True),
        (_Sections.Traits, 0, 6, 1, 6, True),
        (_Sections.Programming, 0, 7, 1, 7, True),
        (_Sections.Options, 0, 8, 1, 8, True)
    )

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)
        self._robot = None
        self._dataItemMap: typing.Dict[RobotSheetWidget._Sections, QtWidgets.QTableWidgetItem] = {}

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
        #self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().sectionResized.connect(
            self._table.resizeRowsToContents)
        self._table.setItemDelegate(gui.TableViewSpannedWordWrapFixDelegate())
        for section, headerColumn, headerRow, dataColumn, dataRow, dataSpan in RobotSheetWidget._LayoutData:
            if dataSpan:
                self._table.setSpan(dataRow, dataColumn, 1, RobotSheetWidget._ColumnCount - dataColumn)
            item = RobotSheetWidget._createHeaderItem(section)
            self._table.setItem(headerRow, headerColumn, item)
            item = RobotSheetWidget._createDataItem(section)
            self._table.setItem(dataRow, dataColumn, item)
            self._dataItemMap[section] = item

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
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

    def _updateTable(self) -> None:
        for section, item in self._dataItemMap.items():
            if not self._robot:
                item.setText('')
                continue

            itemText = ''
            if section == RobotSheetWidget._Sections.Robot:
                itemText = self._robot.name()
            elif section == RobotSheetWidget._Sections.Hits:
                attributeValue = self._robot.attributeValue(
                    attributeId=robots.RobotAttributeId.Hits)
                if isinstance(attributeValue, common.ScalarCalculation):
                    itemText = common.formatNumber(number=attributeValue.value())
            elif section == RobotSheetWidget._Sections.Locomotion:
                primaryLocomotion = self._robot.findFirstComponent(
                    componentType=robots.PrimaryLocomotion)
                if isinstance(primaryLocomotion, robots.PrimaryLocomotion):
                    itemText = primaryLocomotion.componentString()
                # TODO: Handle secondary locomotion
            elif section == RobotSheetWidget._Sections.Speed:
                attributeValue = self._robot.attributeValue(
                    attributeId=robots.RobotAttributeId.Speed)
                if isinstance(attributeValue, common.ScalarCalculation):
                    itemText = common.formatNumber(
                        number=attributeValue.value(),
                        suffix='m')
            elif section == RobotSheetWidget._Sections.TL:
                # TODO: Should this also have the TL ehex in brackets (if it's > 9)
                itemText = str(self._robot.techLevel())
            elif section == RobotSheetWidget._Sections.Cost:
                cost = self._robot.totalCredits()
                itemText = common.formatNumber(
                    number=cost.value(),
                    prefix='Cr')
            elif section == RobotSheetWidget._Sections.Skills:
                for skillDef in traveller.AllStandardSkills:
                    skill = self._robot.skill(skillDef=skillDef)
                    if skill:
                        specialities = skill.specialities()
                        if not specialities:
                            specialities = [None]
                        for speciality in specialities:
                            itemText += '{separator}{skill} {level}'.format(
                                separator=', ' if itemText else '',
                                skill=skill.name(speciality=speciality),
                                level=skill.level(speciality=speciality).value())
                if not itemText:
                    itemText = 'None'
            elif section == RobotSheetWidget._Sections.Attacks:
                seenWeapons: typing.Dict[traveller.StockWeapon, int] = {}

                components = self._robot.findComponents(
                    componentType=robots.MountedWeapon)
                for component in components:
                    assert(isinstance(component, robots.MountedWeapon))
                    weapon = component.weaponData(
                        weaponSet=self._robot.weaponSet())
                    if weapon:
                        count = seenWeapons.get(weapon, 0)
                        seenWeapons[weapon] = count + 1

                components = self._robot.findComponents(
                    componentType=robots.HandHeldWeapon)
                for component in components:
                    assert(isinstance(component, robots.HandHeldWeapon))
                    weapon = component.weaponData(
                        weaponSet=self._robot.weaponSet())
                    if weapon:
                        count = seenWeapons.get(weapon, 0)
                        seenWeapons[weapon] = count + 1

                for weapon, count in seenWeapons.items():
                    damage = weapon.damage()
                    traits = weapon.traits()
                    weaponInfo = '{damage}{separator}{traits}'.format(
                        damage=weapon.damage(),
                        separator=', ' if len(damage) > 0 else '',
                        traits=traits)
                    itemText += '{separator}{count}{weapon}{info}'.format(
                        separator=', ' if itemText else '',
                        count=f'{count} X ' if count > 1 else '',
                        weapon=weapon.name(),
                        info=f' ({weaponInfo})' if weaponInfo else '')

                if not itemText:
                    itemText = 'None'
            elif section == RobotSheetWidget._Sections.Manipulators:
                seenCharacteristics: typing.Dict[typing.Tuple[int, int, int], int] = {}
                components = self._robot.findComponents(
                    componentType=robots.Manipulator)
                for component in components:
                    assert(isinstance(component, robots.Manipulator))
                    if isinstance(component, robots.RemoveBaseManipulator):
                        continue
                    characteristics = (
                        component.strength(),
                        component.dexterity())
                    count = seenCharacteristics.get(characteristics, 0)
                    seenCharacteristics[characteristics] = count + 1

                for characteristics, count in seenCharacteristics.items():
                    strength = characteristics[0]
                    dexterity = characteristics[1]
                    itemText += '{separator}{count} X (STR {strength} DEX {dexterity})'.format(
                        separator=', ' if itemText else '',
                        count=count,
                        strength=strength,
                        dexterity=dexterity)
            elif section == RobotSheetWidget._Sections.Endurance:
                attributeValue = self._robot.attributeValue(
                    attributeId=robots.RobotAttributeId.Endurance)
                if isinstance(attributeValue, common.ScalarCalculation):
                    itemText = common.formatNumber(
                        number=attributeValue.value(),
                        suffix=' hours')
                # TODO: Could check for power related components and add something (e.g. ' + Solar Coating')
            elif section == RobotSheetWidget._Sections.Traits:
                # TODO: Add traits to item string in alphabetical order
                for trait in robots.TraitAttributeIds:
                    attribute = self._robot.attribute(attributeId=trait)
                    if not attribute:
                        continue

                    value = attribute.value()
                    valueText = None
                    if isinstance(value, common.ScalarCalculation):
                        valueText = common.formatNumber(number=value.value())
                    elif isinstance(value, common.DiceRoll):
                        valueText = str(value)
                    elif isinstance(value, enum.Enum):
                        valueText = str(value.value)

                    itemText += '{separator}{attribute}{value}'.format(
                        separator=', ' if itemText else '',
                        attribute=attribute.name(),
                        value=f' {valueText}' if valueText else '')
            elif section == RobotSheetWidget._Sections.Programming:
                brain = self._robot.findFirstComponent(
                    componentType=robots.Brain)
                intelligence = self._robot.attributeValue(
                    attributeId=robots.RobotAttributeId.Intelligence)
                if brain and intelligence:
                    assert(isinstance(brain, robots.Brain))
                    assert(isinstance(intelligence, common.ScalarCalculation))
                    itemText = '{brain} (INT {intelligence})'.format(
                        brain=brain.componentString(),
                        intelligence=intelligence.value())
            elif section == RobotSheetWidget._Sections.Options:
                options: typing.Dict[typing.Union[robots.DefaultSuiteOption, robots.SlotOption], int] = {}
                components = self._robot.findComponents(
                    componentType=robots.DefaultSuiteOption)
                for component in components:
                    count = options.get(component, 0)
                    options[component] = count + 1
                # TODO: Add options to item string in alphabetical order
                for option, count in options.items():
                    itemText += '{separator}{count}{option}'.format(
                        separator=', ' if itemText else '',
                        count=f'{count} X ' if count > 1 else '',
                        option=option.componentString())

            item.setText(itemText)

        self._table.resizeRowsToContents()

    @staticmethod
    def _createHeaderItem(section: _Sections) -> QtWidgets.QTableWidgetItem:
        item = gui.TableWidgetItemEx(section.value)
        item.setBold(enable=True)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, section)
        return item
    
    @staticmethod
    def _createDataItem(section: _Sections) -> QtWidgets.QTableWidgetItem:
        item = gui.TableWidgetItemEx()
        item.setData(QtCore.Qt.ItemDataRole.UserRole, section)
        return item    