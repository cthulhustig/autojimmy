import gui
import gunsmith
import logging
import typing
from PyQt5 import QtWidgets, QtCore

class _ComponentConfigWidget(QtWidgets.QWidget):
    componentChanged = QtCore.pyqtSignal()
    deleteClicked = QtCore.pyqtSignal()

    _OptionsLayoutIndent = 10

    def __init__(
            self,
            components: typing.Optional[typing.Iterable[gunsmith.ComponentInterface]] = None,
            current: typing.Optional[gunsmith.ComponentInterface] = None,
            requirement: gunsmith.ConstructionStage.RequirementLevel = gunsmith.ConstructionStage.RequirementLevel.Optional,
            deletable: bool = False,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._requirement = requirement
        self._currentOptions: typing.Dict[QtWidgets.QWidget, gunsmith.ComponentOption] = {}

        self._comboBox = gui.ComboBoxEx()
        self._comboBox.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._comboBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._comboBox.currentIndexChanged.connect(self._selectionChanged)

        comboLayout = QtWidgets.QHBoxLayout()
        comboLayout.setContentsMargins(0, 0, 0, 0)
        comboLayout.addWidget(self._comboBox)

        if deletable:
            closeIcon = gui.loadIcon(gui.Icon.CloseTab)
            deleteButton = QtWidgets.QPushButton()
            deleteButton.setIcon(closeIcon)
            deleteButton.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Fixed)
            deleteButton.clicked.connect(self.deleteClicked.emit)

            comboLayout.addWidget(deleteButton, alignment=QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)
        comboLayout.addStretch(1)

        self._optionsLayout = gui.VBoxLayoutEx()
        self._optionsLayout.setContentsMargins(_ComponentConfigWidget._OptionsLayoutIndent, 0, 0, 0)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addLayout(comboLayout)
        widgetLayout.addLayout(self._optionsLayout)

        self.setComponents(
            components=components,
            current=current)

        self.setLayout(widgetLayout)

    # Note this intentionally includes the None component for optional components
    def componentCount(self) -> int:
        return self._comboBox.count()

    def optionCount(self) -> int:
        return self._optionsLayout.count()

    def currentComponent(self) -> typing.Optional[gunsmith.ComponentInterface]:
        return self._comboBox.currentData(QtCore.Qt.ItemDataRole.UserRole)

    def setCurrentComponent(
            self,
            current: typing.Optional[gunsmith.ComponentInterface]
            ) -> bool:
        for index in range(self._comboBox.count()):
            component = self._comboBox.itemData(index, QtCore.Qt.ItemDataRole.UserRole)
            if component == current:
                self._comboBox.setCurrentIndex(index)
                self._updateOptionControls()
                return True
        return False

    def setComponents(
            self,
            components: typing.Optional[typing.Iterable[gunsmith.ComponentInterface]],
            current: typing.Optional[gunsmith.ComponentInterface] = None,
            ) -> None:
        oldCurrent = self.currentComponent()

        with gui.SignalBlocker(widget=self._comboBox):
            self._comboBox.clear()

            includeNone = True
            if self._requirement == gunsmith.ConstructionStage.RequirementLevel.Mandatory:
                includeNone = False
            elif self._requirement == gunsmith.ConstructionStage.RequirementLevel.Desirable:
                includeNone = not components

            if includeNone:
                self._comboBox.addItem('<None>', None)
            if components:
                for component in components:
                    self._comboBox.addItem(component.componentString(), component)
            #self._comboBox.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
            if not self.setCurrentComponent(current=current):
                # The specified current component couldn't be set so update the options so they sync
                # to whatever the current component is (if there is one)
                self._updateOptionControls()

        # When generating an event check what the actual current value is just in case
        # the specified one couldn't be selected for whatever reason
        if self.currentComponent() != oldCurrent:
            self.componentChanged.emit()

    def _updateOptionControls(self) -> None:
        component = self.currentComponent()
        options = component.options() if component else []

        # Remove any old option widgets from layout
        for widget in list(self._currentOptions.keys()):
            option = self._currentOptions.get(widget)
            if option not in options:
                self._removeOptionWidget(widget=widget)

        # Add new option widgets to layout.
        optionWidgets = {v: k for k, v in self._currentOptions.items()}
        for index, option in enumerate(options):
            widget = optionWidgets.get(option)
            if not widget:
                self._insertOptionWidget(index=index, option=option)
            else:
                self._updateOptionWidget(widget=widget)

    def _insertOptionWidget(
            self,
            index: int,
            option: gunsmith.ComponentOption
            ) -> None:
        widget = None
        fullRow = False
        alignment = QtCore.Qt.AlignmentFlag(0)
        if isinstance(option, gunsmith.BooleanComponentOption):
            widget = gui.CheckBoxEx()
            widget.setChecked(option.value())
            widget.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Fixed)
            widget.stateChanged.connect(lambda: self._checkBoxChanged(widget, option))
            alignment = QtCore.Qt.AlignmentFlag.AlignLeft
        if isinstance(option, gunsmith.StringComponentOption):
            widget = gui.LineEditEx()
            widget.setText(option.value())
            widget.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding, # give user as much space to type as possible
                QtWidgets.QSizePolicy.Policy.Fixed)
            widget.textChanged.connect(lambda: self._textEditChanged(widget, option))
        elif isinstance(option, gunsmith.IntegerComponentOption):
            widget = gui.OptionalSpinBox() if option.isOptional() else gui.SpinBoxEx()

            if option.min() != None:
                widget.setMinimum(option.min())
            else:
                widget.setMinimum(-2147483648)

            if option.max() != None:
                widget.setMaximum(option.max())
            else:
                widget.setMaximum(2147483647)

            widget.setValue(option.value())
            widget.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Fixed)
            widget.valueChanged.connect(lambda: self._spinBoxChanged(widget, option))
            alignment = QtCore.Qt.AlignmentFlag.AlignLeft
        elif isinstance(option, gunsmith.FloatComponentOption):
            widget = gui.OptionalDoubleSpinBox() if option.isOptional() else gui.DoubleSpinBoxEx()

            if option.min() != None:
                widget.setDecimalsForValue(option.min())
                widget.setMinimum(option.min())
            else:
                widget.setMinimum(-2147483648)

            if option.max() != None:
                widget.setDecimalsForValue(option.max())
                widget.setMaximum(option.max())
            else:
                widget.setMaximum(2147483647)

            widget.setValue(option.value())
            widget.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Fixed)
            widget.valueChanged.connect(lambda: self._spinBoxChanged(widget, option))
            alignment = QtCore.Qt.AlignmentFlag.AlignLeft
        elif isinstance(option, gunsmith.EnumComponentOption):
            widget = gui.EnumComboBox(
                type=option.type(),
                value=option.value(),
                options=option.options(),
                isOptional=option.isOptional())
            widget.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
            widget.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Fixed)
            widget.currentIndexChanged.connect(lambda: self._comboBoxChanged(widget, option))
            alignment = QtCore.Qt.AlignmentFlag.AlignLeft

        if widget:
            description = option.description()
            if description:
                widget.setToolTip(gui.createStringToolTip(description, escape=False))

            self._currentOptions[widget] = option
            if fullRow:
                self._optionsLayout.insertWidget(
                    index,
                    widget,
                    alignment=alignment)
            else:
                self._optionsLayout.insertLabelledWidget(
                    index,
                    option.name() + ':',
                    widget,
                    alignment=alignment)

    def _removeOptionWidget(
            self,
            widget: QtWidgets.QWidget
            ) -> None:
        self._optionsLayout.removeWidget(widget)
        del self._currentOptions[widget]
        widget.setParent(None)
        widget.setHidden(True)
        widget.deleteLater()

    def _updateOptionWidget(
            self,
            widget: QtWidgets.QWidget
            ) -> None:
        option = self._currentOptions.get(widget)
        if not option:
            assert(False) # Shouldn't happen
            return

        if isinstance(option, gunsmith.BooleanComponentOption):
            assert(isinstance(widget, gui.CheckBoxEx))
            widget.setChecked(option.value())
        if isinstance(option, gunsmith.StringComponentOption):
            assert(isinstance(widget, gui.LineEditEx))
            widget.setText(option.value())
        elif isinstance(option, gunsmith.IntegerComponentOption):
            assert(isinstance(widget, gui.SpinBoxEx))
            if option.min() != None:
                widget.setMinimum(option.min())
            else:
                widget.setMinimum(-2147483648)

            if option.max() != None:
                widget.setMaximum(option.max())
            else:
                widget.setMaximum(2147483647)

            widget.setValue(option.value())
        elif isinstance(option, gunsmith.FloatComponentOption):
            assert(isinstance(widget, gui.DoubleSpinBoxEx))
            if option.min() != None:
                widget.setDecimalsForValue(option.min())
                widget.setMinimum(option.min())
            else:
                widget.setMinimum(-2147483648)

            if option.max() != None:
                widget.setDecimalsForValue(option.max())
                widget.setMaximum(option.max())
            else:
                widget.setMaximum(2147483647)

            widget.setValue(option.value())
        elif isinstance(option, gunsmith.EnumComponentOption):
            assert(isinstance(widget, gui.EnumComboBox))
            widget.setEnumType(
                type=option.type(),
                options=option.options(),
                isOptional=option.isOptional())
            widget.setCurrentEnum(value=option.value())

    def _selectionChanged(self) -> None:
        self._updateOptionControls()
        self.componentChanged.emit()

    def _checkBoxChanged(
            self,
            widget: QtWidgets.QCheckBox,
            option: gunsmith.BooleanComponentOption
            ) -> None:
        try:
            option.setValue(value=widget.isChecked())
            self.componentChanged.emit()
            self._updateOptionControls()
        except Exception as ex:
            message = f'Failed to update {option.name()}'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _textEditChanged(
            self,
            widget: QtWidgets.QLineEdit,
            option: gunsmith.StringComponentOption
            ) -> None:
        try:
            option.setValue(value=widget.text())
            self.componentChanged.emit()
            self._updateOptionControls()
        except Exception as ex:
            message = f'Failed to update {option.name()}'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _spinBoxChanged(
            self,
            widget: typing.Union[QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox],
            option: gunsmith.IntegerComponentOption
            ) -> None:
        try:
            option.setValue(value=widget.value())
            self.componentChanged.emit()
            self._updateOptionControls()
        except Exception as ex:
            message = f'Failed to update {option.name()}'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _comboBoxChanged(
            self,
            widget: QtWidgets.QComboBox,
            option: gunsmith.EnumComponentOption
            ) -> None:
        try:
            if widget.currentIndex() < 0:
                return # There is no current selection so nothing to do

            option.setValue(value=widget.currentData(QtCore.Qt.ItemDataRole.UserRole))
            self.componentChanged.emit()
            self._updateOptionControls()
        except Exception as ex:
            message = f'Failed to update {option.name()}'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

class _StageWidget(QtWidgets.QWidget):
    def __init__(
            self,
            weapon: gunsmith.Weapon,
            stage: gunsmith.ConstructionStage,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)
        self._weapon = weapon
        self._stage = stage

    def weapon(self) -> gunsmith.Weapon:
        return self._weapon

    def stage(self) -> gunsmith.ConstructionStage:
        return self._stage

    def synchronise(self) -> None:
        raise RuntimeError('The synchronise method must be implemented by classes derived from _StageWidget')

    def isPointless(self) -> bool:
        raise RuntimeError('The isPointless method must be implemented by classes derived from _StageWidget')

class _SingleSelectStageWidget(_StageWidget):
    stageChanged = QtCore.pyqtSignal(gunsmith.ConstructionStage)

    def __init__(
            self,
            weapon: gunsmith.Weapon,
            stage: gunsmith.ConstructionStage,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            weapon=weapon,
            stage=stage,
            parent=parent)

        self._currentComponent = None

        self._componentWidget = _ComponentConfigWidget(
            requirement=self._stage.requirement())
        self._componentWidget.componentChanged.connect(self._componentChanged)

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(self._componentWidget)

        self.setLayout(self._layout)

        self.synchronise()

    def synchronise(self) -> None:
        currentComponents = self._stage.components()
        self._currentComponent = currentComponents[0] if currentComponents else None
        compatibleComponents = self._weapon.findCompatibleComponents(
            stage=self._stage,
            replaceComponent=self._currentComponent)

        # Block signals while new state is pushed to component widget
        with gui.SignalBlocker(widget=self._componentWidget):
            self._componentWidget.setComponents(
                components=compatibleComponents,
                current=self._currentComponent)

    def isPointless(self) -> bool:
        if self._componentWidget.componentCount() <= 0:
            return True # Single select widgets with no options to select are always pointless
        if self._componentWidget.optionCount() > 0:
            return False # Single select widgets aren't pointless if the current component has options
        # Single select widgets are pointless if there is only one entry for the user to select (and
        # it has no options)
        return self._componentWidget.componentCount() <= 1

    def _updateWeapon(self) -> None:
        component = self._componentWidget.currentComponent()
        try:
            if component != self._currentComponent:
                # The component has changed so replace the current component with the new one. Note
                # that either the current component or the new component may be None (indicating there
                # is no component). In those cases this will have the effect of adding the new component
                # or removing the old component respectively
                self._weapon.replaceComponent(
                    stage=self._stage,
                    oldComponent=self._currentComponent,
                    newComponent=component,
                    regenerate=True)
                self._currentComponent = component
            else:
                # It's the same component instance but the options may have changed so regenerate
                # the weapon
                self._weapon.regenerate()
        except Exception as ex:
            message = 'Failed to update weapon'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _componentChanged(self) -> None:
        self._updateWeapon()
        self.stageChanged.emit(self._stage)

class _MultiSelectStageWidget(_StageWidget):
    stageChanged = QtCore.pyqtSignal(gunsmith.ConstructionStage)

    _RowSpacing = 20

    def __init__(
            self,
            weapon: gunsmith.Weapon,
            stage: gunsmith.ConstructionStage,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            weapon=weapon,
            stage=stage,
            parent=parent)

        self._currentComponents: typing.Dict[_ComponentConfigWidget, gunsmith.ComponentInterface] = {}

        self._addButton = QtWidgets.QPushButton('Add Component')
        self._addButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._addButton.clicked.connect(self._addClicked)

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setSpacing(_MultiSelectStageWidget._RowSpacing)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(self._addButton)

        self.setLayout(self._layout)

        self.synchronise()

    def synchronise(self) -> None:
        stageComponents = list(self._stage.components()) # Copy list to allow easier removing while iterating

        # Remove widgets for components that are no longer present
        for widget in list(self._currentComponents.keys()):
            component = self._currentComponents[widget]
            if component not in stageComponents:
                self._removeComponentWidget(widget=widget)

        # Add widgets for components that don't have one yet and update compatibility for the
        # components that do have widgets
        componentWidgets = {v: k for k, v in self._currentComponents.items()}
        for index, component in enumerate(stageComponents):
            widget = componentWidgets.get(component)
            if not widget:
                self._insertComponentWidget(row=index, component=component)
            else:
                # Block signals while pushing new state to an existing widget
                with gui.SignalBlocker(widget=widget):
                    self._updateComponentWidget(widget=widget)

    def isPointless(self) -> bool:
        if len(self._currentComponents) > 0:
            return False # Multi-select widgets that have components aren't pointless
        # Multi-select widgets are pointless if there are no options for the
        # user to select
        return not self._weapon.findCompatibleComponents(stage=self._stage)

    def _addComponentWidget(
            self,
            component: typing.Optional[gunsmith.ComponentInterface] = None
            ) -> _ComponentConfigWidget:
        return self._insertComponentWidget(
            row=self._layout.count() - 1,
            component=component)

    def _insertComponentWidget(
            self,
            row: int,
            component: typing.Optional[gunsmith.ComponentInterface] = None
            ) -> _ComponentConfigWidget:
        compatibleComponents = self._weapon.findCompatibleComponents(
            stage=self._stage,
            replaceComponent=component)
        if not compatibleComponents:
            return None
        if not component:
            component = compatibleComponents[0]
        componentWidget = _ComponentConfigWidget(
            components=compatibleComponents,
            current=component,
            # Mandatory in the sense, if you add a component you must select what type it is. It's
            # only the adding of a component in the first place is optional
            requirement=gunsmith.ConstructionStage.RequirementLevel.Mandatory,
            deletable=True)
        componentWidget.componentChanged.connect(lambda: self._componentChanged(componentWidget))
        componentWidget.deleteClicked.connect(lambda: self._deleteClicked(componentWidget))

        self._layout.insertWidget(row, componentWidget)
        self._currentComponents[componentWidget] = component

        return componentWidget

    def _removeComponentWidget(
            self,
            widget: _ComponentConfigWidget
            ) -> None:
        self._layout.removeWidget(widget)
        del self._currentComponents[widget]
        widget.setParent(None)
        widget.setHidden(True)
        widget.deleteLater()

    def _updateComponentWidget(
            self,
            widget: _ComponentConfigWidget
            ) -> None:
        currentComponent = widget.currentComponent()
        compatibleComponents = self._weapon.findCompatibleComponents(
            stage=self._stage,
            replaceComponent=currentComponent)
        widget.setComponents(
            components=compatibleComponents,
            current=currentComponent)

    def _updateAllComponentWidgets(
            self,
            skipWidget: typing.Optional[_ComponentConfigWidget] = None
            ) -> None:
        for widget in self._currentComponents.keys():
            if widget == skipWidget:
                continue
            self._updateComponentWidget(widget=widget)

    def _updateWeaponComponent(
            self,
            removeComponent: typing.Optional[gunsmith.ComponentInterface] = None,
            addComponent: typing.Optional[gunsmith.ComponentInterface] = None
            ) -> None:
        try:
            self._weapon.replaceComponent(
                stage=self._stage,
                oldComponent=removeComponent,
                newComponent=addComponent,
                regenerate=True)
        except Exception as ex:
            message = 'Failed to replace component'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _addClicked(self) -> None:
        widget = self._addComponentWidget()
        if not widget:
            gui.MessageBoxEx.information(
                parent=self,
                text='No more compatible components to add')
            return
        self._updateWeaponComponent(addComponent=widget.currentComponent())
        self._updateAllComponentWidgets(skipWidget=widget)
        self.stageChanged.emit(self._stage)

    def _deleteClicked(
            self,
            widget: _ComponentConfigWidget
            ) -> None:
        self._removeComponentWidget(widget=widget)
        self._updateWeaponComponent(removeComponent=widget.currentComponent())
        self._updateAllComponentWidgets()
        self.stageChanged.emit(self._stage)

    def _componentChanged(
            self,
            widget: _ComponentConfigWidget
            ) -> None:
        oldComponent = self._currentComponents[widget]
        newComponent = widget.currentComponent()
        self._updateWeaponComponent(
            removeComponent=oldComponent,
            addComponent=newComponent)
        self._currentComponents[widget] = newComponent

        self._updateAllComponentWidgets(skipWidget=widget)
        self.stageChanged.emit(self._stage)

class _StageGroupWidget(QtWidgets.QWidget):
    stageChanged = QtCore.pyqtSignal(gunsmith.ConstructionStage)
    expansionChanged = QtCore.pyqtSignal(str, bool)

    _StateVersion = 'StageGroupWidget_v1'

    def __init__(
            self,
            weapon: gunsmith.Weapon,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._weapon = weapon
        self._stageOrder: typing.List[gunsmith.ConstructionStage] = []
        self._stageWidgets: typing.Dict[gunsmith.ConstructionStage, _StageWidget] = {}
        self._stageExpansions: typing.Dict[str, bool] = {}

        self._configurationWidget = gui.ExpanderGroupWidget()
        self._configurationWidget.expansionChanged.connect(self._expansionChanged)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._configurationWidget)

        self.setLayout(layout)

    def stageCount(self) -> int:
        return len(self._stageWidgets)

    def addStage(
            self,
            stage: gunsmith.ConstructionStage,
            stageName: typing.Optional[str] = None
            ) -> None:
        self.insertStage(
            index=self.stageCount(),
            stage=stage,
            stageName=stageName)

    def insertStage(
            self,
            index: int,
            stage: gunsmith.ConstructionStage,
            stageName: typing.Optional[str] = None
            ) -> None:
        if stage.singular():
            widget = _SingleSelectStageWidget(
                weapon=self._weapon,
                stage=stage)
            widget.stageChanged.connect(self._stageStateChanged)
        else:
            widget = _MultiSelectStageWidget(
                weapon=self._weapon,
                stage=stage)
            widget.stageChanged.connect(self._stageStateChanged)

        self._stageOrder.insert(index, stage)
        self._stageWidgets[stage] = widget

        self._configurationWidget.insertExpandingContent(
            index=index,
            label=stageName if stageName != None else stage.name(),
            content=widget,
            expanded=True)

        self._updateStageVisibility(stageWidget=widget)

    def removeStage(
            self,
            stage: gunsmith.ConstructionStage
            ) -> None:
        widget = self._stageWidgets.get(stage)
        if not widget:
            return

        self._stageOrder.remove(stage)
        del self._stageWidgets[stage]

        self._configurationWidget.removeContent(content=widget)
        widget.setParent(None)
        widget.setHidden(True)
        widget.deleteLater()

    def stageAt(
            self,
            index: int
            ) -> typing.Optional[gunsmith.ConstructionStage]:
        widget = self._configurationWidget.contentFromIndex(index)
        if not isinstance(widget, _StageWidget):
            return None
        return widget.stage()

    def stageLabel(
            self,
            stage: gunsmith.ConstructionStage
            ) -> typing.Optional[str]:
        stageWidget = self._stageWidgets.get(stage)
        if not stageWidget:
            return None
        return self._configurationWidget.labelFromContent(
            content=stageWidget)

    def synchronise(self) -> None:
        for widget in self._stageWidgets.values():
            widget.synchronise()
            self._updateStageVisibility(stageWidget=widget)

    def expandStages(
            self,
            expansionMap: typing.Mapping[str, bool],
            animated: bool = True
            ) -> None:
        for expander in self._configurationWidget.expanders():
            if expander.label() in expansionMap:
                expander.setExpanded(
                    expanded=expansionMap[expander.label()],
                    animated=animated)

    def _stageStateChanged(
            self,
            stage: gunsmith.ConstructionStage
            ) -> None:
        self.stageChanged.emit(stage)

    def _expansionChanged(
            self,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout],
            expanded: bool,
            animated: bool
            ) -> None:
        label = self._configurationWidget.labelFromContent(content=content)
        if not label:
            return
        self.expansionChanged.emit(label, expanded)

    def _updateStageVisibility(
            self,
            stageWidget: _StageWidget
            ) -> None:
        self._configurationWidget.setContentHidden(
            content=stageWidget,
            hidden=stageWidget.isPointless())

def _generateSequencePrefix(
        sequence: str,
        sequences: typing.Iterable[str]
        ) -> typing.Optional[str]:
    if len(sequences) <= 1:
        return None

    sequenceIndex = None
    for index, otherSequence in enumerate(sequences):
        if sequence == otherSequence:
            sequenceIndex = index
            break
    if sequenceIndex == None:
        return None

    if sequenceIndex == 0:
        return 'Primary '
    elif len(sequences) == 2:
        return 'Secondary '
    else:
        return f'Secondary {sequenceIndex} '

class _SequenceStagesWidget(_StageGroupWidget):
    weaponTypeChanged = QtCore.pyqtSignal(str)

    def __init__(
            self,
            sequence: str,
            weapon: gunsmith.Weapon,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(weapon=weapon, parent=parent)

        self._sequence = sequence
        self._prefix = _generateSequencePrefix(
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
        stages: typing.List[gunsmith.ConstructionStage] = []
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

class _CommonStagesWidget(_StageGroupWidget):
    def __init__(
            self,
            weapon: gunsmith.Weapon,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(weapon=weapon, parent=parent)
        self.synchronise()

    def synchronise(self) -> None:
        # Create a list of all the common phase stages
        stages: typing.List[gunsmith.ConstructionStage] = []
        for phase in gunsmith.CommonConstructionPhases:
            stages.extend(self._weapon.stages(phase=phase))

        # Remove stages that are no longer used by the weapon
        for stage in list(self._stageWidgets.keys()):
            if stage not in stages:
                self.removeStage(stage=stage)

        # Insert new stages into the widget in order. This assumes the stages being displayed are
        # already in order.
        for index, stage in enumerate(stages):
            if stage != self.stageAt(index):
                self.insertStage(index=index, stage=stage)

        super().synchronise()

class _PhaseStagesWidget(_StageGroupWidget):
    def __init__(
            self,
            weapon: gunsmith.Weapon,
            phase: gunsmith.ConstructionPhase,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(weapon=weapon, parent=parent)
        self._phase = phase
        self.synchronise()

    def synchronise(self) -> None:
        # Create a list of all the stages for this phase across all sequences
        stages: typing.Dict[gunsmith.ConstructionStage, str] = {}
        sequences = self._weapon.sequences()
        for sequence in sequences:
            prefix = _generateSequencePrefix(
                sequence=sequence,
                sequences=sequences)
            for stage in self._weapon.stages(sequence=sequence, phase=self._phase):
                stages[stage] = prefix

        # Remove stages that are no longer used by the weapon
        for stage in list(self._stageWidgets.keys()):
            if stage not in stages:
                self.removeStage(stage=stage)

        # Insert new stages into the widget in order. This assumes the stages being displayed
        # are already in order. For stages that have already been added to the widget the label
        # is updated as it may have changed.
        for index, stage in enumerate(stages.keys()):
            prefix = stages[stage]
            stageName = prefix + stage.name() if prefix else stage.name()
            if stage != self.stageAt(index):
                self.insertStage(index=index, stage=stage, stageName=stageName)
            else:
                self._configurationWidget.setExpanderLabel(
                    content=self._stageWidgets[stage],
                    label=stageName)

        super().synchronise()

class WeaponConfigWidget(QtWidgets.QWidget):
    weaponChanged = QtCore.pyqtSignal(gunsmith.Weapon)

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

        self._techLevelSpinBox = gui.SpinBoxEx()
        self._techLevelSpinBox.setMinimum(0)
        self._techLevelSpinBox.setValue(weapon.techLevel())
        self._techLevelSpinBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._techLevelSpinBox.valueChanged.connect(self._techLevelChanged)

        self._secondaryCountSpinBox = gui.SpinBoxEx()
        self._secondaryCountSpinBox.setMinimum(0)
        self._secondaryCountSpinBox.setMaximum(WeaponConfigWidget._MaxSecondaryWeapons)
        self._secondaryCountSpinBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._secondaryCountSpinBox.valueChanged.connect(self._secondaryCountChanged)

        globalLayout = gui.VBoxLayoutEx()
        globalLayout.addLabelledWidget(
            label='Tech Level:',
            widget=self._techLevelSpinBox,
            alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        globalLayout.addLabelledWidget(
            label='Secondary Weapon Count:',
            widget=self._secondaryCountSpinBox,
            alignment=QtCore.Qt.AlignmentFlag.AlignLeft)

        for rule in gunsmith.RuleId:
            ruleCheckBox = QtWidgets.QCheckBox()
            # Note the slightly odd way this lambda is specified is to work around the issue of connecting
            # lambdas to events in a loop (https://www.xingyulei.com/post/qt-signal-in-for-loop/index.html)
            ruleCheckBox.stateChanged.connect(lambda state, r=rule: self._ruleStateChanged(state, r))
            ruleCheckBox.setToolTip(gui.createStringToolTip(gunsmith.RuleDescriptions[rule], escape=False))
            globalLayout.addLabelledWidget(
                label=rule.value + ':',
                widget=ruleCheckBox,
                alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
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
            assert(isinstance(ruleWidget, QtWidgets.QCheckBox))
            with gui.SignalBlocker(widget=ruleWidget):
                ruleWidget.setChecked(self._weapon.isRuleEnabled(rule=rule))

        self._configureDynamicWidgets()

        self.weaponChanged.emit(self._weapon)

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
        self.weaponChanged.emit(self._weapon)

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
            self.weaponChanged.emit(self._weapon)

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
        self.weaponChanged.emit(self._weapon)

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

        self._commonWidget = _CommonStagesWidget(weapon=self._weapon)
        self._commonWidget.expandStages(expansionMap=self._stageExpansionMap, animated=False)
        self._commonWidget.stageChanged.connect(self._stageChanged)
        self._commonWidget.expansionChanged.connect(self._expansionChanged)
        self._configurationWidget.addExpandingContent(
            label='Furniture',
            content=self._commonWidget,
            expanded=True)

        self._loadingWidget = _PhaseStagesWidget(
            weapon=self._weapon,
            phase=gunsmith.ConstructionPhase.Loading)
        self._loadingWidget.expandStages(expansionMap=self._stageExpansionMap, animated=False)
        self._loadingWidget.stageChanged.connect(self._stageChanged)
        self._loadingWidget.expansionChanged.connect(self._expansionChanged)
        self._configurationWidget.addExpandingContent(
            label='Loading',
            content=self._loadingWidget,
            expanded=True)

        self._munitionsWidget = _PhaseStagesWidget(
            weapon=self._weapon,
            phase=gunsmith.ConstructionPhase.Munitions)
        self._munitionsWidget.expandStages(expansionMap=self._stageExpansionMap, animated=False)
        self._munitionsWidget.stageChanged.connect(self._stageChanged)
        self._munitionsWidget.expansionChanged.connect(self._expansionChanged)
        self._configurationWidget.addExpandingContent(
            label='Munitions',
            content=self._munitionsWidget,
            expanded=True)

    def _removeWidgets(self) -> None:
        for sequenceWidget in self._sequenceWidgets.values():
            self._removeWidget(widget=sequenceWidget)
        self._sequenceWidgets.clear()

        if self._commonWidget:
            self._removeWidget(widget=self._commonWidget)
            self._commonWidget = None

        if self._loadingWidget:
            self._removeWidget(widget=self._loadingWidget)
            self._loadingWidget = None

        if self._munitionsWidget:
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
        self.weaponChanged.emit(self._weapon)

    def _stageChanged(
            self,
            stage: gunsmith.ConstructionStage
            ) -> None:
        self._synchroniseStages()
        self.weaponChanged.emit(self._weapon)

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
        for sequenceWidget in self._sequenceWidgets.values():
            sequenceWidget.synchronise()

        if self._commonWidget:
            self._commonWidget.synchronise()

        if self._loadingWidget:
            self._loadingWidget.synchronise()

        if self._munitionsWidget:
            self._munitionsWidget.synchronise()
