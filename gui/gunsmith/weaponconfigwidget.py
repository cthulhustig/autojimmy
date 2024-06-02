import construction
import gui
import gunsmith
import logging
import typing
from PyQt5 import QtWidgets, QtCore

class _SequenceStagesWidget(gui.StageGroupWidget):
    weaponTypeChanged = QtCore.pyqtSignal(str)

    def __init__(
            self,
            sequence: str,
            weapon: gunsmith.Weapon,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(context=weapon.context(), parent=parent)

        self._weapon = weapon
        self._sequence = sequence
        self._prefix = self.generateSequencePrefix(
            sequence=sequence,
            sequences=weapon.sequences())

        self._weaponTypeComboBox = gui.EnumComboBox(type=gunsmith.WeaponType)
        self._weaponTypeComboBox.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._weaponTypeComboBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._weaponTypeComboBox.currentIndexChanged.connect(self._weaponTypeChanged)

        self._configurationWidget.addExpandingContent(
            label='', # Set an empty label for now, the real one is set when synchronise is called
            content=self._weaponTypeComboBox,
            expanded=True)

        self.synchronise()

    def teardown(self) -> None:
        self._weaponTypeComboBox.currentIndexChanged.disconnect(self._weaponTypeChanged)
        super().teardown()

    def synchronise(self) -> None:
        # Update the weapon type combo box. Signals are blocked when doing this to prevent
        # it generating weapon changed events
        with gui.SignalBlocker(widget=self._weaponTypeComboBox):
            self._weaponTypeComboBox.setCurrentEnum(
                self._weapon.weaponType(sequence=self._sequence))

            self._configurationWidget.setExpanderLabel(
                content=self._weaponTypeComboBox,
                label=self._formatSectionName(baseText='Weapon Type:'))

        # Create a list of all the required phase stages for this sequence
        stages: typing.List[construction.ConstructionStage] = []
        for phase in gunsmith.SequenceConstructionPhases:
            stages.extend(self._weapon.stages(sequence=self._sequence, phase=phase))

        # Remove stages that are no longer used by the weapon
        for stage in list(self._stageWidgets.keys()):
            if stage not in stages:
                self.removeStage(stage=stage)

        # Insert new stages into the widget in order. This assumes the stages being displayed are
        # already in order. For stages that have already been added to the widget the label is
        # updated as it may have changed.
        # Note that the +1 applied to the index is to account for the weapon type combo box that is
        # inserted before the stage widgets.
        for index, stage in enumerate(stages):
            stageName = self._formatSectionName(baseText=stage.name())
            if stage != self.stageAt(index + 1):
                self.insertStage(index=index + 1, stage=stage, stageName=stageName)
            else:
                self._configurationWidget.setExpanderLabel(
                    content=self._stageWidgets[stage],
                    label=stageName)

        super().synchronise()

    def gatherTabOrder(
            self,
            tabWidgets: typing.List[QtWidgets.QWidget]
            ) -> None:
        tabWidgets.append(self._weaponTypeComboBox)
        return super().gatherTabOrder(tabWidgets)

    def _weaponTypeChanged(self, index: int) -> None:
        self._weapon.setWeaponType(
            sequence=self._sequence,
            weaponType=self._weaponTypeComboBox.currentEnum())
        self.weaponTypeChanged.emit(self._sequence)

    def _formatSectionName(
            self,
            baseText: str
            ) -> str:
        if not self._prefix:
            return baseText
        return self._prefix + baseText

class WeaponConfigWidget(QtWidgets.QWidget):
    weaponModified = QtCore.pyqtSignal(gunsmith.Weapon)

    _StateVersion = 'WeaponConfigWidget_v1'

    # Limit the number of secondary weapons as the UI gets slower to update the more
    # are added
    _MaxSecondaryWeapons = 4

    def __init__(
            self,
            weapon: gunsmith.Weapon,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._weapon = None
        self._ruleWidgets: typing.Dict[gunsmith.RuleId, gui.CheckBoxEx] = {}
        self._sequenceWidgets: typing.Dict[str, _SequenceStagesWidget] = {}
        self._commonWidget = None
        self._loadingWidget = None
        self._munitionsWidget = None
        self._stageExpansionMap: typing.Dict[str, bool] = {}

        self._noWheelFilter = gui.NoWheelEventUnlessFocusedFilter()

        self._techLevelSpinBox = gui.SpinBoxEx()
        self._techLevelSpinBox.setMinimum(0)
        self._techLevelSpinBox.setValue(weapon.techLevel())
        self._techLevelSpinBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._techLevelSpinBox.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self._techLevelSpinBox.installEventFilter(self._noWheelFilter)
        self._techLevelSpinBox.valueChanged.connect(self._techLevelChanged)

        self._secondaryCountSpinBox = gui.SpinBoxEx()
        self._secondaryCountSpinBox.setMinimum(0)
        self._secondaryCountSpinBox.setMaximum(WeaponConfigWidget._MaxSecondaryWeapons)
        self._secondaryCountSpinBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._secondaryCountSpinBox.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self._secondaryCountSpinBox.installEventFilter(self._noWheelFilter)        
        self._secondaryCountSpinBox.valueChanged.connect(self._secondaryCountChanged)

        globalLayout = gui.VBoxLayoutEx()
        globalLayout.addLabelledWidget(
            label='Tech Level:',
            widget=self._techLevelSpinBox,
            widgetAlignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        globalLayout.addLabelledWidget(
            label='Secondary Weapon Count:',
            widget=self._secondaryCountSpinBox,
            widgetAlignment=QtCore.Qt.AlignmentFlag.AlignLeft)

        for rule in gunsmith.RuleId:
            ruleCheckBox = gui.CheckBoxEx()
            # Note the slightly odd way this lambda is specified is to work around the issue of connecting
            # lambdas to events in a loop (https://www.xingyulei.com/post/qt-signal-in-for-loop/index.html)
            ruleCheckBox.stateChanged.connect(lambda state, r=rule: self._ruleStateChanged(state, r))
            ruleCheckBox.setToolTip(gui.createStringToolTip(gunsmith.RuleDescriptions[rule], escape=False))
            globalLayout.addLabelledWidget(
                label=rule.value + ':',
                widget=ruleCheckBox,
                widgetAlignment=QtCore.Qt.AlignmentFlag.AlignLeft)
            self._ruleWidgets[rule] = ruleCheckBox

        self._configurationWidget = gui.ExpanderGroupWidgetEx()
        self._configurationWidget.setPersistExpanderStates(True)
        self._configurationWidget.addExpandingContent(
            label='Global',
            content=globalLayout,
            expanded=True)

        self.setWeapon(weapon=weapon)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._configurationWidget)
        widgetLayout.addStretch(1)

        self.setLayout(widgetLayout)

    def techLevel(self) -> None:
        return self._weapon.techLevel()

    def weapon(self) -> gunsmith.Weapon:
        return self._weapon

    def setWeapon(
            self,
            weapon: gunsmith.Weapon
            ) -> None:
        self._weapon = weapon

        with gui.SignalBlocker(widget=self._techLevelSpinBox):
            self._techLevelSpinBox.setValue(self._weapon.techLevel())

        with gui.SignalBlocker(widget=self._secondaryCountSpinBox):
            self._secondaryCountSpinBox.setValue(self._weapon.sequenceCount() - 1)

        for rule, ruleWidget in self._ruleWidgets.items():
            assert(isinstance(rule, gunsmith.RuleId))
            assert(isinstance(ruleWidget, gui.CheckBoxEx))
            with gui.SignalBlocker(widget=ruleWidget):
                ruleWidget.setChecked(self._weapon.isRuleEnabled(rule=rule))

        self._configureDynamicWidgets()

        self.weaponModified.emit(self._weapon)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(WeaponConfigWidget._StateVersion)

        expanderState = self._configurationWidget.saveState()
        stream.writeUInt32(expanderState.count() if expanderState else 0)
        if expanderState:
            stream.writeRawData(expanderState.data())

        stream.writeUInt32(len(self._stageExpansionMap))
        for label, isExpanded in self._stageExpansionMap.items():
            stream.writeQString(label)
            stream.writeBool(isExpanded)

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != WeaponConfigWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore WeaponConfigWidget state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count > 0:
            expanderState = QtCore.QByteArray(stream.readRawData(count))
            if not self._configurationWidget.restoreState(state=expanderState):
                return False

        count = stream.readUInt32()
        if count > 0:
            self._stageExpansionMap.clear()
            for _ in range(count):
                label = stream.readQString()
                isExpanded = stream.readBool()
                self._stageExpansionMap[label] = isExpanded

            for sequenceWidget in self._sequenceWidgets.values():
                with gui.SignalBlocker(sequenceWidget):
                    sequenceWidget.expandStages(
                        expansionMap=self._stageExpansionMap,
                        animated=False)

            if self._commonWidget:
                with gui.SignalBlocker(self._commonWidget):
                    self._commonWidget.expandStages(
                        expansionMap=self._stageExpansionMap,
                        animated=False)

            if self._loadingWidget:
                with gui.SignalBlocker(self._loadingWidget):
                    self._loadingWidget.expandStages(
                        expansionMap=self._stageExpansionMap,
                        animated=False)

            if self._munitionsWidget:
                with gui.SignalBlocker(self._munitionsWidget):
                    self._munitionsWidget.expandStages(
                        expansionMap=self._stageExpansionMap,
                        animated=False)

        return True

    def _techLevelChanged(self, techLevel: int) -> None:
        self._weapon.setTechLevel(techLevel=techLevel)
        self._synchroniseStages()
        self.weaponModified.emit(self._weapon)

    def _secondaryCountChanged(self, count: int) -> None:
        requiredCount = count + 1 # Add 1 for primary weapon
        modified = False

        while requiredCount < self._weapon.sequenceCount():
            sequences = self._weapon.sequences()
            self._weapon.removeSequence(
                sequence=sequences[-1],
                regenerate=False)
            modified = True

        while requiredCount > self._weapon.sequenceCount():
            self._weapon.addSequence(
                weaponType=gunsmith.WeaponType.GrenadeLauncherWeapon,
                regenerate=False)
            modified = True

        if modified:
            self._weapon.regenerate()
            self._configureDynamicWidgets()
            self.weaponModified.emit(self._weapon)

    def _ruleStateChanged(
            self,
            state: int,
            rule: gunsmith.RuleId
            ) -> None:
        enabled = not not state
        if enabled:
            self._weapon.enableRule(rule=rule)
        else:
            self._weapon.disableRule(rule=rule)
        self._synchroniseStages()
        self.weaponModified.emit(self._weapon)

    def _configureDynamicWidgets(self) -> None:
        self._removeWidgets()

        if not self._weapon:
            return # No more to do

        sequences = self._weapon.sequences()
        for index, sequence in enumerate(sequences):
            if index == 0:
                sectionName = 'Primary Weapon'
            elif len(sequences) == 2:
                sectionName = 'Secondary Weapon'
            else:
                sectionName = f'Secondary Weapon {index}'

            sequenceWidget = _SequenceStagesWidget(
                sequence=sequence,
                weapon=self._weapon)
            sequenceWidget.expandStages(expansionMap=self._stageExpansionMap, animated=False)
            sequenceWidget.weaponTypeChanged.connect(self._weaponTypeChanged)
            sequenceWidget.stageChanged.connect(self._stageChanged)
            sequenceWidget.expansionChanged.connect(self._expansionChanged)
            self._sequenceWidgets[sequence] = sequenceWidget
            self._configurationWidget.addExpandingContent(
                label=sectionName,
                content=sequenceWidget,
                expanded=True)
            self._configurationWidget.setContentHidden(
                content=sequenceWidget,
                hidden=sequenceWidget.isPointless())

        self._commonWidget = gui.MultiPhaseStagesWidget(
            context=self._weapon.context(),
            phases=gunsmith.CommonConstructionPhases)
        self._commonWidget.expandStages(expansionMap=self._stageExpansionMap, animated=False)
        self._commonWidget.stageChanged.connect(self._stageChanged)
        self._commonWidget.expansionChanged.connect(self._expansionChanged)
        self._configurationWidget.addExpandingContent(
            label='Furniture',
            content=self._commonWidget,
            expanded=True)
        self._configurationWidget.setContentHidden(
            content=self._commonWidget,
            hidden=self._commonWidget.isPointless())        

        self._loadingWidget = gui.SinglePhaseStageWidget(
            context=self._weapon.context(),
            phase=gunsmith.WeaponPhase.Loading)
        self._loadingWidget.expandStages(expansionMap=self._stageExpansionMap, animated=False)
        self._loadingWidget.stageChanged.connect(self._stageChanged)
        self._loadingWidget.expansionChanged.connect(self._expansionChanged)
        self._configurationWidget.addExpandingContent(
            label='Loading',
            content=self._loadingWidget,
            expanded=True)
        self._configurationWidget.setContentHidden(
            content=self._loadingWidget,
            hidden=self._loadingWidget.isPointless())          

        self._munitionsWidget = gui.SinglePhaseStageWidget(
            context=self._weapon.context(),
            phase=gunsmith.WeaponPhase.Munitions)
        self._munitionsWidget.expandStages(expansionMap=self._stageExpansionMap, animated=False)
        self._munitionsWidget.stageChanged.connect(self._stageChanged)
        self._munitionsWidget.expansionChanged.connect(self._expansionChanged)
        self._configurationWidget.addExpandingContent(
            label='Munitions',
            content=self._munitionsWidget,
            expanded=True)
        self._configurationWidget.setContentHidden(
            content=self._munitionsWidget,
            hidden=self._munitionsWidget.isPointless())

        self._updateTabOrder()       

    def _removeWidgets(self) -> None:
        for sequenceWidget in self._sequenceWidgets.values():
            sequenceWidget.weaponTypeChanged.disconnect(self._weaponTypeChanged)
            sequenceWidget.stageChanged.disconnect(self._stageChanged)
            sequenceWidget.expansionChanged.disconnect(self._expansionChanged)
            sequenceWidget.teardown()
            self._removeWidget(widget=sequenceWidget)
        self._sequenceWidgets.clear()

        if self._commonWidget:
            self._commonWidget.stageChanged.disconnect(self._stageChanged)
            self._commonWidget.expansionChanged.disconnect(self._expansionChanged)
            self._commonWidget.teardown()
            self._removeWidget(widget=self._commonWidget)
            self._commonWidget = None

        if self._loadingWidget:
            self._loadingWidget.stageChanged.disconnect(self._stageChanged)
            self._loadingWidget.expansionChanged.disconnect(self._expansionChanged)
            self._loadingWidget.teardown()
            self._removeWidget(widget=self._loadingWidget)
            self._loadingWidget = None

        if self._munitionsWidget:
            self._munitionsWidget.stageChanged.disconnect(self._stageChanged)
            self._munitionsWidget.expansionChanged.disconnect(self._expansionChanged)
            self._munitionsWidget.teardown()
            self._removeWidget(widget=self._munitionsWidget)
            self._munitionsWidget = None

    def _removeWidget(
            self,
            widget: QtWidgets.QWidget
            ) -> None:
        self._configurationWidget.removeContent(content=widget)
        widget.setParent(None)
        widget.setHidden(True)
        widget.deleteLater()

    def _weaponTypeChanged(self, sequence: str) -> None:
        self._synchroniseStages(sequence=sequence)
        self.weaponModified.emit(self._weapon)

    def _stageChanged(
            self,
            stage: construction.ConstructionStage
            ) -> None:
        self._synchroniseStages()
        self.weaponModified.emit(self._weapon)

    def _expansionChanged(
            self,
            label: str,
            expanded: bool
            ) -> None:
        self._stageExpansionMap[label] = expanded

    def _synchroniseStages(
            self,
            sequence: typing.Optional[str] = None
            ) -> None:
        if sequence:
            sequenceWidget = self._sequenceWidgets.get(sequence)
            if sequenceWidget:
                sequenceWidget.synchronise()
                self._configurationWidget.setContentHidden(
                    content=sequenceWidget,
                    hidden=sequenceWidget.isPointless())
        else:
            for sequenceWidget in self._sequenceWidgets.values():
                sequenceWidget.synchronise()
                self._configurationWidget.setContentHidden(
                    content=sequenceWidget,
                    hidden=sequenceWidget.isPointless())

        if self._commonWidget:
            self._commonWidget.synchronise()
            self._configurationWidget.setContentHidden(
                content=self._commonWidget,
                hidden=self._commonWidget.isPointless())            

        if self._loadingWidget:
            self._loadingWidget.synchronise()
            self._configurationWidget.setContentHidden(
                content=self._loadingWidget,
                hidden=self._loadingWidget.isPointless())               

        if self._munitionsWidget:
            self._munitionsWidget.synchronise()
            self._configurationWidget.setContentHidden(
                content=self._munitionsWidget,
                hidden=self._munitionsWidget.isPointless())

        self._updateTabOrder()         

    def _updateTabOrder(self) -> None:
        tabOrder = [self._techLevelSpinBox, self._secondaryCountSpinBox]
        tabOrder.extend(self._ruleWidgets.values())
        for widget in self._sequenceWidgets.values():
            if widget.isEnabled():
                widget.gatherTabOrder(tabWidgets=tabOrder)
        if self._commonWidget and self._commonWidget.isEnabled():
            self._commonWidget.gatherTabOrder(tabWidgets=tabOrder)
        if self._loadingWidget and self._loadingWidget.isEnabled():
            self._loadingWidget.gatherTabOrder(tabWidgets=tabOrder)
        if self._munitionsWidget and self._munitionsWidget.isEnabled():
            self._munitionsWidget.gatherTabOrder(tabWidgets=tabOrder)

        lastTabWidget = tabOrder[0]
        QtWidgets.QWidget.setTabOrder(self, lastTabWidget)
        for tabWidget in tabOrder[1:]:
            QtWidgets.QWidget.setTabOrder(lastTabWidget, tabWidget)
            lastTabWidget = tabWidget        
