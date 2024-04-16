import app
import construction
import gui
import logging
import typing
from PyQt5 import QtWidgets, QtCore

class _ComponentConfigWidget(QtWidgets.QWidget):
    componentChanged = QtCore.pyqtSignal()
    deleteClicked = QtCore.pyqtSignal()

    _OptionsLayoutIndent = 10

    _NonePlaceholder = 'None'

    def __init__(
            self,
            components: typing.Optional[typing.Iterable[construction.ComponentInterface]] = None,
            current: typing.Optional[construction.ComponentInterface] = None,
            requirement: construction.ConstructionStage.RequirementLevel = construction.ConstructionStage.RequirementLevel.Optional,
            deletable: bool = False,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._requirement = requirement
        self._currentOptions: typing.Dict[QtWidgets.QWidget, construction.ComponentOption] = {}
        self._widgetConnections: typing.Dict[QtWidgets.QWidget, QtCore.QMetaObject.Connection] = {}

        self._comboBox = gui.ComboBoxEx()
        self._comboBox.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._comboBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._comboBox.currentIndexChanged.connect(self._selectionChanged)

        comboLayout = QtWidgets.QHBoxLayout()
        comboLayout.setContentsMargins(0, 0, 0, 0)
        comboLayout.addWidget(self._comboBox)

        self._deleteButton = None
        if deletable:
            closeIcon = gui.loadIcon(gui.Icon.CloseTab)
            self._deleteButton = QtWidgets.QPushButton()
            self._deleteButton.setIcon(closeIcon)
            self._deleteButton.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Fixed)
            self._deleteButton.clicked.connect(self._deleteButtonClicked)

            comboLayout.addWidget(self._deleteButton, alignment=QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)
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

    def teardown(self) -> None:
        self._comboBox.currentIndexChanged.disconnect(self._selectionChanged)
        if self._deleteButton:
            self._deleteButton.clicked.disconnect(self._deleteButtonClicked)

        for widget in list(self._currentOptions.keys()):
            self._removeOptionWidget(widget=widget)

    # Note this intentionally includes the None component for optional components
    def componentCount(self) -> int:
        return self._comboBox.count()

    def optionCount(self) -> int:
        return self._optionsLayout.count()

    def currentComponent(self) -> typing.Optional[construction.ComponentInterface]:
        return self._comboBox.currentData(QtCore.Qt.ItemDataRole.UserRole)

    def setCurrentComponent(
            self,
            current: typing.Optional[construction.ComponentInterface]
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
            components: typing.Optional[typing.Iterable[construction.ComponentInterface]],
            current: typing.Optional[construction.ComponentInterface] = None,
            ) -> None:
        oldCurrent = self.currentComponent()

        with gui.SignalBlocker(widget=self._comboBox):
            self._comboBox.clear()

            includeNone = True
            if self._requirement == construction.ConstructionStage.RequirementLevel.Mandatory:
                includeNone = False
            elif self._requirement == construction.ConstructionStage.RequirementLevel.Desirable:
                includeNone = not components

            if includeNone:
                self._comboBox.addItem(_ComponentConfigWidget._NonePlaceholder, None)
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
            option: construction.ComponentOption
            ) -> None:
        widget = None
        connection = None
        fullRow = False
        alignment = QtCore.Qt.AlignmentFlag(0)
        if isinstance(option, construction.BooleanOption):
            widget = gui.CheckBoxEx()
            widget.setChecked(option.value())
            widget.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Fixed)
            connection = widget.stateChanged.connect(lambda: self._checkBoxChanged(widget, option))
            alignment = QtCore.Qt.AlignmentFlag.AlignLeft
        if isinstance(option, construction.StringOption):
            stringOptions = option.options()
            if not stringOptions:
                # There are no pre-defined strings the user can select from so just use a line edit
                widget = gui.LineEditEx()
                widget.setText(option.value())
                widget.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Expanding, # give user as much space to type as possible
                    QtWidgets.QSizePolicy.Policy.Fixed)
                connection = widget.textChanged.connect(lambda: self._textEditChanged(widget, option))                
            else:
                # There are pre-defined strings the user can select from so use an editable combo box
                widget = gui.ComboBoxEx()
                widget.setEditable(option.isEditable())
                widget.setCurrentText(option.value())
                widget.setSizePolicy(
                    # If the option is editable give the user as much space as possible
                    QtWidgets.QSizePolicy.Policy.Expanding if option.isEditable() else QtWidgets.QSizePolicy.Policy.Fixed,
                    QtWidgets.QSizePolicy.Policy.Fixed)
                if option.isOptional():
                    widget.addItem(_ComponentConfigWidget._NonePlaceholder)
                for stringOption in stringOptions:
                    widget.addItem(stringOption)
                connection = widget.currentTextChanged.connect(lambda: self._textComboChanged(widget, option))
                if not option.isEditable():
                    alignment = QtCore.Qt.AlignmentFlag.AlignLeft
        elif isinstance(option, construction.IntegerOption):
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
            connection = widget.valueChanged.connect(lambda: self._spinBoxChanged(widget, option))
            alignment = QtCore.Qt.AlignmentFlag.AlignLeft
        elif isinstance(option, construction.FloatOption):
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
            connection = widget.valueChanged.connect(lambda: self._spinBoxChanged(widget, option))
            alignment = QtCore.Qt.AlignmentFlag.AlignLeft
        elif isinstance(option, construction.EnumOption):
            widget = gui.EnumComboBox(
                type=option.type(),
                value=option.value(),
                options=option.options(),
                isOptional=option.isOptional())
            widget.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
            widget.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Fixed)
            connection = widget.currentIndexChanged.connect(lambda: self._enumComboChanged(widget, option))
            alignment = QtCore.Qt.AlignmentFlag.AlignLeft

        if widget:
            description = option.description()
            if description:
                widget.setToolTip(gui.createStringToolTip(description, escape=False))

            self._currentOptions[widget] = option
            self._widgetConnections[widget] = connection
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

        connection = self._widgetConnections[widget]
        del self._widgetConnections[widget]

        if connection:
            if isinstance(widget, gui.CheckBoxEx):
                widget.stateChanged.disconnect(connection)
            elif isinstance(widget, gui.LineEditEx):
                widget.textChanged.disconnect(connection)
            elif isinstance(widget, gui.ComboBoxEx):
                widget.currentTextChanged.disconnect(connection)
            elif isinstance(widget, gui.SpinBoxEx):
                widget.valueChanged.disconnect(connection)
            elif isinstance(widget, gui.OptionalSpinBox):
                widget.valueChanged.disconnect(connection)
            elif isinstance(widget, gui.DoubleSpinBoxEx):
                widget.valueChanged.disconnect(connection)
            elif isinstance(widget, gui.OptionalDoubleSpinBox):
                widget.valueChanged.disconnect(connection)
            elif isinstance(widget, gui.EnumComboBox):
                widget.currentIndexChanged.disconnect(connection)

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

        # NOTE: Block signals when syncing controls to option. This prevents
        # current control values being pushed to the option due to events that
        # are generated while part way through. For example updating the max/min
        # of a spin box can cause a value changed event which causes which ever
        # value the control has clamped it's value to being pushed back to the
        # option when the option has already been clamped to a different value.
        # TODO: This change will probably need a decent amount of regression
        # testing
        with gui.SignalBlocker(widget=widget):
            if isinstance(option, construction.BooleanOption):
                assert(isinstance(widget, gui.CheckBoxEx))
                widget.setChecked(option.value())
            if isinstance(option, construction.StringOption):
                assert(isinstance(widget, gui.LineEditEx) or \
                       isinstance(widget, gui.ComboBoxEx))
                if isinstance(widget, gui.LineEditEx):
                    widget.setText(option.value())
                else:
                    stringOptions = option.options()
                    widget.clear()
                    if option.isOptional():
                        widget.addItem(_ComponentConfigWidget._NonePlaceholder)
                    for stringOption in stringOptions:
                        widget.addItem(stringOption)                    
                    widget.setCurrentText(option.value())
            elif isinstance(option, construction.IntegerOption):
                assert(isinstance(widget, gui.SpinBoxEx) or \
                       isinstance(widget, gui.OptionalSpinBox))
                if option.min() != None:
                    widget.setMinimum(option.min())
                else:
                    widget.setMinimum(-2147483648)

                if option.max() != None:
                    widget.setMaximum(option.max())
                else:
                    widget.setMaximum(2147483647)

                widget.setValue(option.value())
            elif isinstance(option, construction.FloatOption):
                assert(isinstance(widget, gui.DoubleSpinBoxEx) or \
                       isinstance(widget, gui.OptionalDoubleSpinBox))
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
            elif isinstance(option, construction.EnumOption):
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
            widget: gui.CheckBoxEx,
            option: construction.BooleanOption
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
            widget: gui.LineEditEx,
            option: construction.StringOption
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

    def _textComboChanged(
            self,
            widget: gui.ComboBoxEx,
            option: construction.StringOption
            ) -> None:
        try:
            value = widget.currentText()
            if option.isOptional() and value == _ComponentConfigWidget._NonePlaceholder:
                value = None
            option.setValue(value=value)
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
            option: construction.IntegerOption
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

    def _enumComboChanged(
            self,
            widget: QtWidgets.QComboBox,
            option: construction.EnumOption
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

    def _deleteButtonClicked(self) -> None:
        self.deleteClicked.emit()

# TODO: There are 2 REALLY annoying behaviours when dealing with stages
# where you can add/remove multiple components
# - If you're adding components and they start to go off the bottom of
# the current view, you have to manually scroll down to see the add
# button
# - If you've added a lot of components and you remove the last one, the
# view jumps back to the top of the list of widgets. This can be really
# annoying if you're removing multiple components from the end of the
# list
class _StageWidget(QtWidgets.QWidget):
    stageChanged = QtCore.pyqtSignal(construction.ConstructionStage)

    _RowSpacing = 10

    def __init__(
            self,
            context: construction.ConstructionContext,
            stage: construction.ConstructionStage,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)
        
        self._context = context
        self._stage = stage        

        minComponents = self._stage.minComponents()
        maxComponents = self._stage.maxComponents()
        self._dynamic = (minComponents == None or maxComponents == None) or \
            (maxComponents > 1 and minComponents < maxComponents)

        self._currentComponents: typing.Dict[_ComponentConfigWidget, construction.ComponentInterface] = {}
        
        self._addButton = None
        if self._dynamic:
            self._addButton = QtWidgets.QPushButton('Add Component')
            self._addButton.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Fixed)
            self._addButton.clicked.connect(self._addClicked)

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setSpacing(
            int(_StageWidget._RowSpacing * app.Config.instance().interfaceScale()))
        self._layout.setContentsMargins(0, 0, 0, 0)
        if self._addButton:
            self._layout.addWidget(self._addButton)

        self.setLayout(self._layout)

        self.synchronise()

    def context(self) -> construction.ConstructionContext:
        return self._context

    def stage(self) -> construction.ConstructionStage:
        return self._stage

    def teardown(self) -> None:
        if self._addButton:
            self._addButton.clicked.disconnect(self._addClicked)
        for widget in list(self._currentComponents.keys()):
            self._removeComponentWidget(widget)

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

        if not self._dynamic:
            maxComponents = self._stage.maxComponents()
            if maxComponents:
                while len(self._currentComponents) < maxComponents:
                    if not self._addComponentWidget():
                        # No widget added for whatever reason, bail to avoid an
                        # infinite loop
                        break

    def isPointless(self) -> bool:
        if self._dynamic:
            if len(self._currentComponents) > 0:
                # Dynamic widgets that have components aren't pointless
                return False
            # Dynamic widgets are pointless if there are no components for the
            # user to select
            return not self._context.findCompatibleComponents(stage=self._stage)
        else:
            hasChoice = False
            for widget in self._currentComponents:
                if widget.componentCount() > 1:
                    # This widget has more than one component to select so the
                    # user has a choice in their selection
                    hasChoice = True
                    break

                if widget.optionCount() > 0:
                    # Fixed widgets are never pointless if any of the component
                    # widgets have options
                    return False

            # Fixed widgets are pointless if none of the component widgets give
            # the user a choice in which component to select _and_ none of them
            # have any options
            return not hasChoice

    def _addComponentWidget(
            self,
            component: typing.Optional[construction.ComponentInterface] = None
            ) -> _ComponentConfigWidget:
        return self._insertComponentWidget(
            row=self._layout.count() - 1,
            component=component)

    def _insertComponentWidget(
            self,
            row: int,
            component: typing.Optional[construction.ComponentInterface] = None
            ) -> _ComponentConfigWidget:
        compatibleComponents = self._context.findCompatibleComponents(
            stage=self._stage,
            replaceComponent=component)

        if self._dynamic:
            if not compatibleComponents:
                return None
            
            if not component:
                component = compatibleComponents[0]            

            # Mandatory in the sense, if you add a component you must select what type it is. It's
            # only the adding of a component in the first place is optional            
            requirement = construction.ConstructionStage.RequirementLevel.Mandatory
        else:
            requirement = self._stage.requirement()

        componentWidget = _ComponentConfigWidget(
            components=compatibleComponents,
            current=component,
            requirement=requirement,
            deletable=self._dynamic)
        componentWidget.componentChanged.connect(self._componentChanged)
        componentWidget.deleteClicked.connect(self._deleteClicked)

        self._layout.insertWidget(row, componentWidget)
        self._currentComponents[componentWidget] = component

        return componentWidget

    def _removeComponentWidget(
            self,
            widget: _ComponentConfigWidget
            ) -> None:
        self._layout.removeWidget(widget)
        del self._currentComponents[widget]

        widget.componentChanged.disconnect(self._componentChanged)
        widget.deleteClicked.disconnect(self._deleteClicked)

        widget.teardown()
        widget.setParent(None)
        widget.setHidden(True)
        widget.deleteLater()

    # TODO: I think it would probably make sense if this function blocked
    # signals in a similar way to _ComponentConfigWidget._updateOptionWidget.
    # This function is called in two places
    # - synchronise: This wraps the call to this function with a signal blocker
    # - _updateAllComponentWidgets: This doesn't use a signal blocker but I can't
    # think why signals would be needed
    #
    # Any change to this will need a lot of regression testing
    def _updateComponentWidget(
            self,
            widget: _ComponentConfigWidget
            ) -> None:
        currentComponent = widget.currentComponent()
        # Generate the list of components to allow the user to select from. This
        # is the list of all components that would be compatible if the currently
        # selected component was to be removed.
        compatibleComponents = self._context.findCompatibleComponents(
            stage=self._stage,
            replaceComponent=currentComponent)
        widget.setComponents(
            components=compatibleComponents,
            current=currentComponent)

    def _updateAllComponentWidgets(
            self,
            skipWidget: typing.Optional[_ComponentConfigWidget] = None
            ) -> None:
        # NOTE: It's important to make a copy of the list of keys as entries
        # may be removed from the map as we iterate
        for widget in list(self._currentComponents.keys()):
            if widget == skipWidget:
                continue
            
            # If the component for this widget was dynamically added and is no
            # longer part of the stage, then the widget should be removed rather
            # than updated. Updating would cause a component the user didn't
            # select to be chosen which most likely won't be what they want.
            # Components being removed like this can happen if they become
            # incompatible due to a change in another component in the same
            # stage. It only happens with components in the same stage as
            # changes to components a previous stage cause synchronise to be
            # called which handles removal of components that are no longer part
            # of the stage.
            # An example would be a robot Satellite Uplink which requires a
            # Transceiver with a specific range. If the Transceiver is removed
            # _or_ has it's range reduced below the required value, it will
            # cause the uplink component to be removed.
            if self._dynamic:
                component = self._currentComponents[widget]
                if not component or not self._stage.containsComponent(component=component):
                    self._removeComponentWidget(widget=widget)
                    continue

            # Update the widget. If the component is no longer part of the stage
            # a new compatible component will be selected.
            self._updateComponentWidget(widget=widget)

    def _updateConstruction(
            self,
            removeComponent: typing.Optional[construction.ComponentInterface] = None,
            addComponent: typing.Optional[construction.ComponentInterface] = None
            ) -> None:
        try:
            if removeComponent != addComponent:
                self._context.replaceComponent(
                    stage=self._stage,
                    oldComponent=removeComponent,
                    newComponent=addComponent,
                    regenerate=True)
            else:
                self._context.regenerate()
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
        self._updateConstruction(addComponent=widget.currentComponent())
        self._updateAllComponentWidgets(skipWidget=widget)
        self.stageChanged.emit(self._stage)

    def _deleteClicked(self) -> None:
        widget = self.sender()
        assert(isinstance(widget, _ComponentConfigWidget))
        self._removeComponentWidget(widget=widget)
        self._updateConstruction(removeComponent=widget.currentComponent())
        self._updateAllComponentWidgets()
        self.stageChanged.emit(self._stage)

    def _componentChanged(self) -> None:
        widget = self.sender()
        assert(isinstance(widget, _ComponentConfigWidget))
        oldComponent = self._currentComponents[widget]
        newComponent = widget.currentComponent()
        self._updateConstruction(
            removeComponent=oldComponent,
            addComponent=newComponent)
        self._currentComponents[widget] = newComponent

        self._updateAllComponentWidgets(skipWidget=widget)
        self.stageChanged.emit(self._stage)

class StageGroupWidget(QtWidgets.QWidget):
    stageChanged = QtCore.pyqtSignal(construction.ConstructionStage)
    expansionChanged = QtCore.pyqtSignal(str, bool)

    _StateVersion = 'StageGroupWidget_v1'

    def __init__(
            self,
            context: construction.ConstructionContext,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._context = context
        self._stageOrder: typing.List[construction.ConstructionStage] = []
        self._stageWidgets: typing.Dict[construction.ConstructionStage, _StageWidget] = {}
        self._stageExpansions: typing.Dict[str, bool] = {}

        self._configurationWidget = gui.ExpanderGroupWidget()
        self._configurationWidget.expansionChanged.connect(self._expansionChanged)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._configurationWidget)

        self.setLayout(layout)

    def teardown(self) -> None:
        self._configurationWidget.expansionChanged.disconnect(self._expansionChanged)
        for stage in list(self._stageWidgets.keys()):
            self.removeStage(stage=stage)

    def stageCount(self) -> int:
        return len(self._stageWidgets)

    def addStage(
            self,
            stage: construction.ConstructionStage,
            stageName: typing.Optional[str] = None
            ) -> None:
        self.insertStage(
            index=self.stageCount(),
            stage=stage,
            stageName=stageName)

    def insertStage(
            self,
            index: int,
            stage: construction.ConstructionStage,
            stageName: typing.Optional[str] = None
            ) -> None:
        widget = _StageWidget(
            context=self._context,
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
            stage: construction.ConstructionStage
            ) -> None:
        self._stageOrder.remove(stage)

        widget = self._stageWidgets.get(stage)
        if not widget:
            return

        del self._stageWidgets[stage]

        self._configurationWidget.removeContent(content=widget)
        widget.stageChanged.disconnect(self._stageStateChanged)

        widget.teardown()
        widget.setParent(None)
        widget.setHidden(True)
        widget.deleteLater()

    def stageAt(
            self,
            index: int
            ) -> typing.Optional[construction.ConstructionStage]:
        widget = self._configurationWidget.contentFromIndex(index)
        if not isinstance(widget, _StageWidget):
            return None
        return widget.stage()

    def stageLabel(
            self,
            stage: construction.ConstructionStage
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
                
    def generateSequencePrefix(
            self,
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

    def _stageStateChanged(
            self,
            stage: construction.ConstructionStage
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
        
class SinglePhaseStageWidget(StageGroupWidget):
    def __init__(
            self,
            context: construction.ConstructionContext,
            phase: construction.ConstructionPhase,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(context=context, parent=parent)
        self._phase = phase
        self.synchronise()

    def synchronise(self) -> None:
        # Create a list of all the stages for this phase across all sequences
        stages: typing.Dict[construction.ConstructionStage, str] = {}
        sequences = self._context.sequences()
        for sequence in sequences:
            prefix = self.generateSequencePrefix(
                sequence=sequence,
                sequences=sequences)
            for stage in self._context.stages(sequence=sequence, phase=self._phase):
                stages[stage] = prefix

        # Remove stages that are no longer used by the context
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

class MultiPhaseStagesWidget(StageGroupWidget):
    def __init__(
            self,
            context: construction.ConstructionContext,
            phases: typing.Iterable[construction.ConstructionPhase],
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(context=context, parent=parent)
        self._phases = list(phases)
        self.synchronise()

    def synchronise(self) -> None:
        # Create a list of all the common phase stages
        stages: typing.List[construction.ConstructionStage] = []
        for phase in self._phases:
            stages.extend(self._context.stages(phase=phase))

        # Remove stages that are no longer used by the context
        for stage in list(self._stageWidgets.keys()):
            if stage not in stages:
                self.removeStage(stage=stage)

        # Insert new stages into the widget in order. This assumes the stages being displayed are
        # already in order.
        for index, stage in enumerate(stages):
            if stage != self.stageAt(index):
                self.insertStage(index=index, stage=stage)

        super().synchronise()
