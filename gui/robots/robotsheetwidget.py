import app
import common
import construction
import enum
import gui
import logging
import robots
import traveller
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

# NOTE: This maps skills to the characteristic that gives the DM
# modifier. The values come from the table on p74
_SkillCharacteristicMap = {
    traveller.AdminSkillDefinition: traveller.Characteristics.Intellect,
    traveller.AdvocateSkillDefinition: traveller.Characteristics.Intellect,
    traveller.AnimalsSkillDefinition: traveller.Characteristics.Intellect,
    traveller.ArtSkillDefinition: traveller.Characteristics.Intellect,
    traveller.AstrogationSkillDefinition: traveller.Characteristics.Intellect,
    traveller.AthleticsSkillDefinition: {
        traveller.AthleticsSkillSpecialities.Dexterity: traveller.Characteristics.Dexterity,
        traveller.AthleticsSkillSpecialities.Endurance: None, # No characteristic modifier for Endurance
        traveller.AthleticsSkillSpecialities.Strength: traveller.Characteristics.Strength,
    },
    traveller.BrokerSkillDefinition: traveller.Characteristics.Intellect,
    traveller.CarouseSkillDefinition: traveller.Characteristics.Intellect,
    traveller.DeceptionSkillDefinition: traveller.Characteristics.Intellect,
    traveller.DiplomatSkillDefinition: traveller.Characteristics.Intellect,
    traveller.DriveSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.ElectronicsSkillDefinition: traveller.Characteristics.Intellect,
    traveller.EngineerSkillDefinition: traveller.Characteristics.Intellect,
    traveller.ExplosivesSkillDefinition: traveller.Characteristics.Intellect,
    traveller.FlyerSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.GamblerSkillDefinition: traveller.Characteristics.Intellect,
    traveller.GunCombatSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.GunnerSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.HeavyWeaponsSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.InvestigateSkillDefinition: traveller.Characteristics.Intellect,
    traveller.JackOfAllTradesSkillDefinition: traveller.Characteristics.Intellect,
    traveller.LanguageSkillDefinition: traveller.Characteristics.Intellect,
    traveller.LeadershipSkillDefinition: traveller.Characteristics.Intellect,
    traveller.MechanicSkillDefinition: traveller.Characteristics.Intellect,
    traveller.MedicSkillDefinition: traveller.Characteristics.Intellect,
    traveller.MeleeSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.NavigationSkillDefinition: traveller.Characteristics.Intellect,
    traveller.PersuadeSkillDefinition: traveller.Characteristics.Intellect,
    traveller.PilotSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.ProfessionSkillDefinition: traveller.Characteristics.Intellect,
    traveller.ReconSkillDefinition: traveller.Characteristics.Intellect,
    traveller.ScienceSkillDefinition: traveller.Characteristics.Intellect,
    traveller.SeafarerSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.StealthSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.StewardSkillDefinition: traveller.Characteristics.Intellect,
    traveller.StreetwiseSkillDefinition: traveller.Characteristics.Intellect,
    traveller.SurvivalSkillDefinition: traveller.Characteristics.Intellect,
    traveller.TacticsSkillDefinition: traveller.Characteristics.Intellect,
    # Vacc Suit isn't included in the list of skills on p74. The fact it
    # uses Intellect is based on the fact the example use of the skill in
    # the core rules use EDU which is INT for a robot
    traveller.VaccSuitSkillDefinition: traveller.Characteristics.Intellect,
    # Jack of all trades is needed for Brain in a Jar
    traveller.JackOfAllTradesSkillDefinition: None,
    # Non-standard skills added for robot construction
    robots.RobotVehicleSkillDefinition: traveller.Characteristics.Dexterity,
    robots.RobotWeaponSkillDefinition: traveller.Characteristics.Dexterity,
}

# TODO: There is a deficiency in the way I'm applying characteristics
# modifiers but it's not really in this piece of code. The issue can be seen
# with the StarTek example robot. In the book it's final sheet shows Athletics
# (Strength) 2 where as I'm showing it as Athletics 0. I think this is because
# the book is taking into account the the Athletics you get from manipulators
# (p26). I'm currently handling it with a note but it would be good if I
# could somehow show it in the actual skill like the book. As usual ambiguities
# with multiple manipulators apply

def _calcModifierSkillLevel(
        robot: robots.Robot,
        skill: construction.Skill,
        speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
        ) -> common.ScalarCalculation:
    level = skill.level(speciality=speciality)
    flags = skill.flags(speciality=speciality)
    if (flags & construction.SkillFlagsCharacteristicModifierMask) == 0:
        # Characteristic modifiers aren't applied for this skill
        return level

    characteristic = _SkillCharacteristicMap[skill.skillDef()]
    if isinstance(characteristic, dict):
        characteristic = characteristic.get(speciality)   
    if not characteristic:
        # There is no applicable robot characteristic for this skill
        return level
        
    if characteristic == traveller.Characteristics.Intellect:
        characteristicValue = robot.attributeValue(
            attributeId=robots.RobotAttributeId.Intellect)
        if not characteristicValue:
            return level
    else:
        manipulators = robot.findComponents(
            componentType=robots.Manipulator)
        highestValue = None
        for manipulator in manipulators:
            if isinstance(manipulator, robots.RemoveBaseManipulator):
                continue
            assert(isinstance(manipulator, robots.Manipulator))
            if characteristic == traveller.Characteristics.Strength:
                manipulatorValue = manipulator.strength()
            else:
                manipulatorValue = manipulator.dexterity()
            if highestValue == None or manipulatorValue > highestValue:
                highestValue = manipulatorValue
        if not highestValue:
            # No manipulators so no DEX characteristic
            return level

        characteristicValue = common.ScalarCalculation(
            value=highestValue,
            name=f'Highest Manipulator {characteristic.value}')
    
    characteristicModifier = common.ScalarCalculation(
        value=traveller.CharacteristicDMFunction(
            characteristic=characteristic,
            level=characteristicValue))
    if characteristicModifier.value() > 0:
        if (flags & construction.SkillFlags.ApplyPositiveCharacteristicModifier) == 0:
            return level
    elif characteristicModifier.value() < 0:
        if (flags & construction.SkillFlags.ApplyNegativeCharacteristicModifier) == 0:
            return level
    else:
        return level

    return common.Calculator.add(
        lhs=level,
        rhs=characteristicModifier,
        name=f'Modified {skill.name(speciality=speciality)} Skill Level')

class RobotSheetWidget(QtWidgets.QWidget):
    # TODO: Need something to allow you to copy/paste all the data (similar to
    # notes widget)

    _StateVersion = 'RobotSheetWidget_v1'

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
        for section, item in self._dataItemMap.items():
            if not self._robot:
                item.setText('')
                continue

            itemText = ''
            calculations = []
            if section == RobotSheetWidget._Sections.Robot:
                itemText = self._robot.name()
            elif section == RobotSheetWidget._Sections.Hits:
                attributeValue = self._robot.attributeValue(
                    attributeId=robots.RobotAttributeId.Hits)
                if isinstance(attributeValue, common.ScalarCalculation):
                    itemText = common.formatNumber(number=attributeValue.value())
                    calculations.append(attributeValue)
                else:
                    itemText = '-'
            elif section == RobotSheetWidget._Sections.Locomotion:
                primaryLocomotion = self._robot.findFirstComponent(
                    componentType=robots.PrimaryLocomotion)
                secondaryLocomotions = self._robot.findComponents(
                    componentType=robots.SecondaryLocomotion)
                locomotionStrings = []
                if primaryLocomotion:
                    locomotionStrings.append(primaryLocomotion.componentString())
                for locomotion in secondaryLocomotions:
                    componentString = locomotion.componentString()
                    if componentString not in locomotionStrings:
                        locomotionStrings.append(componentString)
                itemText = RobotSheetWidget._formatListString(locomotionStrings)
            elif section == RobotSheetWidget._Sections.Speed:
                attributeValue = self._robot.attributeValue(
                    attributeId=robots.RobotAttributeId.Speed)
                if isinstance(attributeValue, common.ScalarCalculation):
                    itemText = common.formatNumber(
                        number=attributeValue.value(),
                        suffix='m')
                    calculations.append(attributeValue)
                else:
                    itemText = '-'
            elif section == RobotSheetWidget._Sections.TL:
                itemText = str(self._robot.techLevel())
            elif section == RobotSheetWidget._Sections.Cost:
                cost = self._robot.totalCredits()
                itemText = common.formatNumber(
                    number=cost.value(),
                    prefix='Cr')
                calculations.append(cost)
            elif section == RobotSheetWidget._Sections.Skills:
                applySkillModifiers = self._characteristicsDMCheckBox.isChecked()
                skillString = []
                for skill in self._robot.skills():
                    specialities = skill.specialities()
                    if not specialities:
                        specialities = [None]
                    for speciality in specialities:
                        if applySkillModifiers:
                            skillLevel = _calcModifierSkillLevel(
                                robot=self._robot,
                                skill=skill,
                                speciality=speciality)
                        else:
                            skillLevel = skill.level(speciality=speciality)

                        skillString.append('{skill} {level}'.format(
                            skill=skill.name(speciality=speciality),
                            level=skillLevel.value()))
                        calculations.append(skillLevel)
                skillString.sort()

                # Add the amount of spare bandwidth, this should always be done at
                # end of the string (i.e. after sorting)
                spareBandwidth = self._robot.spareBandwidth()
                if spareBandwidth.value() > 0:
                    skillString.append(f' +{spareBandwidth.value()} available Bandwidth')
                    calculations.append(spareBandwidth)

                itemText = RobotSheetWidget._formatListString(skillString)
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

                weaponStrings = []
                for weapon, count in seenWeapons.items():
                    damage = weapon.damage()
                    traits = weapon.traits()
                    weaponInfo = '{damage}{separator}{traits}'.format(
                        damage=weapon.damage(),
                        separator=', ' if damage and traits else '',
                        traits=traits)
                    weaponStrings.append('{count}{weapon}{info}'.format(
                        count=f'{count} x ' if count > 1 else '',
                        weapon=weapon.name(),
                        info=f' ({weaponInfo})' if weaponInfo else ''))
                itemText = RobotSheetWidget._formatListString(weaponStrings)
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

                manipulatorStrings = []
                for characteristics, count in seenCharacteristics.items():
                    strength = characteristics[0]
                    dexterity = characteristics[1]
                    manipulatorStrings.append('{count} x (STR {strength} DEX {dexterity})'.format(
                        count=count,
                        strength=strength,
                        dexterity=dexterity))
                itemText = RobotSheetWidget._formatListString(manipulatorStrings)
            elif section == RobotSheetWidget._Sections.Endurance:
                attributeValue = self._robot.attributeValue(
                    attributeId=robots.RobotAttributeId.Endurance)
                if isinstance(attributeValue, common.ScalarCalculation):
                    itemText = common.formatNumber(
                        number=attributeValue.value(),
                        suffix=' hours')
                    calculations.append(attributeValue)
                else:
                    itemText = 'None'
            elif section == RobotSheetWidget._Sections.Traits:
                traitStrings = []
                for trait in robots.TraitAttributeIds:
                    attribute = self._robot.attribute(attributeId=trait)
                    if not attribute:
                        continue
                    traitString = trait.value
                    value = attribute.value()
                    valueString = None
                    if isinstance(value, common.ScalarCalculation):
                        valueString = common.formatNumber(
                            number=value.value(),
                            alwaysIncludeSign=True)
                    elif isinstance(value, common.DiceRoll):
                        valueString = str(value)
                    elif isinstance(value, enum.Enum):
                        valueString = str(value.value)
                    if valueString:
                        traitString += f' ({valueString})'
                    traitStrings.append(traitString)
                    calculations.extend(attribute.calculations())
                traitStrings.sort()
                itemText = RobotSheetWidget._formatListString(traitStrings)
            elif section == RobotSheetWidget._Sections.Programming:
                brain = self._robot.findFirstComponent(
                    componentType=robots.Brain)
                if brain:
                    assert(isinstance(brain, robots.Brain))
                    itemText = brain.componentString()

                    characteristicStrings = []
                    for characteristic in robots.CharacteristicAttributeIds:
                        characteristicValue = self._robot.attributeValue(
                            attributeId=characteristic)
                        if characteristicValue:
                            assert(isinstance(characteristicValue, common.ScalarCalculation))
                            characteristicStrings.append(
                                f'{characteristic.value} {characteristicValue.value()}')
                            calculations.append(characteristicValue)
                    if characteristicStrings:
                        itemText += ' ({characteristics})'.format(
                            characteristics=', '.join(characteristicStrings))
                else:
                    itemText = 'None'
            elif section == RobotSheetWidget._Sections.Options:
                options: typing.Dict[str, int] = {}
                components: typing.List[robots.RobotComponentInterface] = []
                components.extend(self._robot.findComponents(
                    componentType=robots.DefaultSuiteOption))
                components.extend(self._robot.findComponents(
                    componentType=robots.SlotOption))                
                for component in components:
                    componentString = component.componentString()
                    count = options.get(componentString, 0)
                    options[componentString] = count + 1

                optionStrings = []
                orderedKeys = list(options.keys())
                orderedKeys.sort()
                for componentString in orderedKeys:
                    count = options[componentString]
                    if count > 1:
                        componentString += f'X {count}'
                    optionStrings.append(componentString)

                # Add the number of spare slots, this should always be done at
                # end of the string (i.e. after sorting)
                spareSlots = self._robot.spareSlots()
                if spareSlots.value() > 0:
                    optionStrings.append(f'Spare Slots x {spareSlots.value()}')
                    calculations.append(spareSlots)

                # At this point the strings should already be sorted
                # alphabetically (but ignoring any count multiplier)
                itemText = RobotSheetWidget._formatListString(optionStrings)

            item.setText(itemText)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, calculations)

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
    def _createHeaderItem(section: _Sections) -> QtWidgets.QTableWidgetItem:
        item = gui.TableWidgetItemEx(section.value)
        item.setBold(enable=True)
        return item
    
    @staticmethod
    def _createDataItem(section: _Sections) -> QtWidgets.QTableWidgetItem:
        item = gui.TableWidgetItemEx()
        return item
    
    @staticmethod
    def _formatListString(
            stringList: typing.Iterable[str]
            ) -> str:
        if not stringList:
            return 'None'
        return ', '.join(stringList)