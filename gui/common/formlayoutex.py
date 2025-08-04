import gui
import typing
from PyQt5 import QtWidgets, QtCore, sip

class FormLayoutEx(QtWidgets.QFormLayout):
    class _ParentChangeWatcher(QtCore.QObject):
        parentChanged = QtCore.pyqtSignal([object, object])

        def __init__(self, initialParent: typing.Optional[QtWidgets.QWidget] = None):
            super().__init__()
            self._detectedParent = initialParent

        def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent):
            if event.type() == QtCore.QEvent.Type.ParentChange:
                parent = obj.parent()
                if parent != self._detectedParent:
                    oldParent = self._detectedParent
                    self._detectedParent = parent
                    self.parentChanged.emit(oldParent, self._detectedParent)
            return super().eventFilter(obj, event)

    class _ChildWidgetChangeWatcher(QtCore.QObject):
        childAdded = QtCore.pyqtSignal([QtWidgets.QWidget])
        childRemoved = QtCore.pyqtSignal([QtWidgets.QWidget])
        childPolished = QtCore.pyqtSignal([QtWidgets.QWidget])

        def __init__(self):
            super().__init__()

        def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent):
            if event.type() == QtCore.QEvent.Type.ChildAdded:
                assert(isinstance(event, QtCore.QChildEvent))
                child = event.child()
                if isinstance(child, QtWidgets.QWidget):
                    self.childAdded.emit(child)
            elif event.type() == QtCore.QEvent.Type.ChildRemoved:
                assert(isinstance(event, QtCore.QChildEvent))
                child = event.child()
                if isinstance(child, QtWidgets.QWidget):
                    self.childRemoved.emit(child)
            elif event.type() == QtCore.QEvent.Type.ChildPolished:
                assert(isinstance(event, QtCore.QChildEvent))
                child = event.child()
                if isinstance(child, QtWidgets.QWidget):
                    self.childPolished.emit(child)
            return super().eventFilter(obj, event)

    class _WidgetEnabledChangeWatcher(QtCore.QObject):
        enableChanged = QtCore.pyqtSignal([QtWidgets.QWidget, bool])

        def __init__(self):
            super().__init__()

        def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent):
            if event.type() == QtCore.QEvent.Type.EnabledChange:
                if isinstance(obj, QtWidgets.QWidget):
                    self.enableChanged.emit(obj, obj.isEnabled())
            return super().eventFilter(obj, event)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._disableLabelWithField = True

        self._parentChangeWatcher = FormLayoutEx._ParentChangeWatcher(initialParent=parent)
        self._parentChangeWatcher.parentChanged.connect(self._parentChangeDetected)

        self._childChangeWatcher = FormLayoutEx._ChildWidgetChangeWatcher()
        self._childChangeWatcher.childAdded.connect(self._childAdditionDetected)
        self._childChangeWatcher.childRemoved.connect(self._childRemovalDetected)
        if parent:
            parent.installEventFilter(self._childChangeWatcher)

        self._enableChangedWatcher = FormLayoutEx._WidgetEnabledChangeWatcher()
        self._enableChangedWatcher.enableChanged.connect(self._enableChangedDetected)

        self.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)

    def setDisableLabelWithField(self, enable: bool) -> None:
        if self._disableLabelWithField == enable:
            return # Nothing to do

        self._disableLabelWithField = enable

        for row in range(self.rowCount()):
            label = self.labelAt(row)
            if label:
                field = self.fieldAt(row)
                label.setEnabled(self._shouldEnableLabel(field))

    def labelAt(self, row: int) -> typing.Optional[QtWidgets.QWidget]:
        item = self.itemAt(row, gui.FormLayoutEx.ItemRole.LabelRole)
        return item.widget() if item else None

    def fieldAt(
            self,
            row: int
            ) -> typing.Optional[typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]]:
        item = self.itemAt(row, gui.FormLayoutEx.ItemRole.FieldRole)
        if item:
            if item.widget():
                return item.widget()
            if item.layout():
                return item.layout()
        return None

    def widgetAt(self, row: int) -> typing.Optional[QtWidgets.QWidget]:
        item = self.itemAt(row, gui.FormLayoutEx.ItemRole.FieldRole)
        return item.widget() if item else None

    def layoutAt(self, row: int) -> typing.Optional[QtWidgets.QLayout]:
        item = self.itemAt(row, gui.FormLayoutEx.ItemRole.FieldRole)
        return item.layout() if item else None

    def clear(self) -> None:
        while self.rowCount() > 0:
            self.removeRow(self.rowCount() - 1)

    def setLabelText(
            self,
            row: int,
            text: str
            ) -> None:
        label = self.labelAt(row)
        if isinstance(label, QtWidgets.QLabel):
            label.setText(text)

    def addStretch(self) -> None:
        spacer = QtWidgets.QSpacerItem(
            0,
            0,
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Expanding)
        self.addItem(spacer)

    def rowForObject(
            self,
            obj: typing.Optional[typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]]
            ) -> int:
        index, _, _ = self._objectSearch(obj)
        return index

    def rowForLabel(self, label: typing.Optional[QtWidgets.QWidget]) -> int:
        for row in range(self.rowCount()):
            other = self.labelAt(row)
            if other == label:
                return row
        return -1

    def rowForField(
            self,
            field: typing.Optional[typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]]
            ) -> int:
        for row in range(self.rowCount()):
            other = self.fieldAt(row)
            if other == field:
                return row
        return -1

    def itemForObject(
            self,
            obj: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]
            ) -> typing.Optional[QtWidgets.QLayoutItem]:
        _, item, _ = self._objectSearch(obj)
        return item

    def roleForItem(
            self,
            item: QtWidgets.QLayoutItem
            ) -> typing.Optional['FormLayoutEx.ItemRole']:
        obj = item.widget() if item.widget() else item.layout()
        if not obj:
            return None
        _, _, role = self._objectSearch(obj)
        return role

    def roleForObject(
            self,
            obj: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]
            ) -> typing.Optional['FormLayoutEx.ItemRole']:
        _, _, role = self._objectSearch(obj)
        return role

    def replaceWidget(
            self,
            from_: typing.Optional[QtWidgets.QWidget],
            to: typing.Optional[QtWidgets.QWidget],
            options: typing.Union[
                QtCore.Qt.FindChildOptions,
                QtCore.Qt.FindChildOption
                ] = QtCore.Qt.FindChildOption.FindChildrenRecursively
            ) -> typing.Optional[QtWidgets.QLayoutItem]:
        row, _, role = self._objectSearch(from_) if from_ else (-1, None, None)

        removedItem = super().replaceWidget(from_, to, options)
        if not removedItem:
            return None # Widget was not replaced

        if role == FormLayoutEx.ItemRole.LabelRole:
            if to:
                field = self.fieldAt(row) if row >= 0 else None
                to.setEnabled(self._shouldEnableLabel(field))
        elif (role == FormLayoutEx.ItemRole.FieldRole) or (role == FormLayoutEx.ItemRole.SpanningRole):
            label = self.labelAt(row) if row >= 0 else None
            if label:
                label.setEnabled(self._shouldEnableLabel(to))

        if from_:
            from_.removeEventFilter(self._parentChangeWatcher)

        if to:
            to.installEventFilter(self._parentChangeWatcher)

        return removedItem

    def takeAt(
            self,
            index: int # NOTE: This is an QLayout index not a QFormLayout row
            ) -> typing.Optional[QtWidgets.QLayoutItem]:
        item = self.itemAt(index)
        obj = None
        if item:
            obj = item.widget() if item.widget() else item.layout()
        row, _, role = self._objectSearch(obj) if obj else (-1, None, None)

        result = super().takeAt(index)
        if not result:
            return None # Index not removed

        if obj:
            obj.removeEventFilter(self._parentChangeWatcher)

            if (role == FormLayoutEx.ItemRole.FieldRole) or (role == FormLayoutEx.ItemRole.SpanningRole):
                label = self.labelAt(row) if row >= 0 else None
                if label:
                    label.setEnabled(True)

        return result

    def removeItem(
            self,
            item: typing.Optional[QtWidgets.QLayoutItem]
            ) -> None:
        obj = item.widget() if item.widget() else item.layout()
        row, _, role = self._objectSearch(obj) if obj else (-1, None, None)

        super().removeItem(item)

        if self.indexOf(item) >= 0:
            return # Item not removed

        if obj:
            obj.removeEventFilter(self._parentChangeWatcher)

            if (role == FormLayoutEx.ItemRole.FieldRole) or (role == FormLayoutEx.ItemRole.SpanningRole):
                label = self.labelAt(row) if row >= 0 else None
                if label:
                    label.setEnabled(True)

    def removeWidget(
            self,
            widget: typing.Optional[QtWidgets.QWidget]
            ) -> None:
        index = self.indexOf(widget)
        row, _, role = self._objectSearch(widget) if widget else (-1, None, None)

        super().removeWidget(widget)

        item = self.itemAt(index)
        if (not item) or (item.widget() == widget):
            return # Widget wasn't removed

        if widget:
            widget.removeEventFilter(self._parentChangeWatcher)

            if (role == FormLayoutEx.ItemRole.FieldRole) or (role == FormLayoutEx.ItemRole.SpanningRole):
                label = self.labelAt(row) if row >= 0 else None
                if label:
                    label.setEnabled(True)

    def addItem(
            self,
            item: typing.Optional[QtWidgets.QLayoutItem]
            ) -> None:
        row = self.rowCount()

        super().addItem(item)

        if self.rowCount() <= row:
            return # Widget wasn't added

        label = self.labelAt(row)
        field = self.fieldAt(row)

        if label:
            label.setEnabled(self._shouldEnableLabel(field))
            label.installEventFilter(self._parentChangeWatcher)

        if field:
            field.installEventFilter(self._parentChangeWatcher)

    def addWidget(
            self,
            widget: typing.Optional[QtWidgets.QWidget]
            ) -> None:
        row = self.rowCount()

        super().addWidget(widget)

        if self.rowCount() <= row:
            return # Widget wasn't added

        label = self.labelAt(row)
        field = self.fieldAt(row)

        if label:
            label.setEnabled(self._shouldEnableLabel(field))
            label.installEventFilter(self._parentChangeWatcher)

        if field:
            field.installEventFilter(self._parentChangeWatcher)

    def takeRow(self, *args) -> QtWidgets.QFormLayout.TakeRowResult:
        results = super().takeRow(*args)
        if not results:
            return results

        label = None
        if results.labelItem:
            label = results.labelItem.widget() if results.labelItem.widget() else results.labelItem.layout()
        if label:
            label.removeEventFilter(self._parentChangeWatcher)

        field = None
        if results.fieldItem:
            field = results.fieldItem.widget() if results.fieldItem.widget() else results.fieldItem.layout()
        if field:
            field.removeEventFilter(self._parentChangeWatcher)

        return results

    # NOTE: There is no need to override removeRow to have it disconnect the
    # state watcher as the QFormLayout implementation deletes the label and
    # field QLayoutItems _and_ the widget/layout they manage at the point the
    # row is removed. As the field widget will be deleted, there is not need to
    # explicitly disconnect
    # https://codebrowser.dev/qt5/qtbase/src/widgets/kernel/qformlayout.cpp.html#_ZN11QFormLayout9removeRowEi
    #def removeRow(self, *args) -> None:
    #    super().removeRow(*args)

    def setWidget(
            self,
            row: int,
            role: QtWidgets.QFormLayout.ItemRole,
            widget: typing.Optional[QtWidgets.QWidget]
            ) -> None:
        item = self.itemAt(row, role)
        old = None
        if item:
            old = item.widget() if item.widget() else item.layout()

        super().setWidget(row, role, widget)

        item = self.itemAt(row, role)
        if (not item) or (item.widget() != widget):
            return # Item wasn't inserted

        if widget:
            if role == QtWidgets.QFormLayout.ItemRole.LabelRole:
                widget.setEnabled(
                    self._shouldEnableLabel(old))
            widget.installEventFilter(self._parentChangeWatcher)

        if old:
            old.removeEventFilter(self._parentChangeWatcher)

    @typing.overload
    def insertRow(self, row: int, label: typing.Optional[QtWidgets.QWidget], field: typing.Optional[QtWidgets.QWidget]) -> None: ...
    @typing.overload
    def insertRow(self, row: int, label: typing.Optional[QtWidgets.QWidget], field: typing.Optional[QtWidgets.QLayout]) -> None: ...
    @typing.overload
    def insertRow(self, row: int, labelText: typing.Optional[str], field: typing.Optional[QtWidgets.QWidget]) -> None: ...
    @typing.overload
    def insertRow(self, row: int, labelText: typing.Optional[str], field: typing.Optional[QtWidgets.QLayout]) -> None: ...
    @typing.overload
    def insertRow(self, row: int, widget: typing.Optional[QtWidgets.QWidget]) -> None: ...
    @typing.overload
    def insertRow(self, row: int, layout: typing.Optional[QtWidgets.QLayout]) -> None: ...

    def insertRow(self, *args) -> None:
        count = self.rowCount()

        super().insertRow(*args)

        if self.rowCount() <= count:
            return # Row wasn't inserted

        row = args[0]

        label = self.labelAt(row)
        field = self.fieldAt(row)

        if label:
            label.setEnabled(self._shouldEnableLabel(field))
            label.installEventFilter(self._parentChangeWatcher)

        if field:
            field.installEventFilter(self._parentChangeWatcher)

    @typing.overload
    def addRow(self, label: typing.Optional[QtWidgets.QWidget], field: typing.Optional[QtWidgets.QWidget]) -> None: ...
    @typing.overload
    def addRow(self, label: typing.Optional[QtWidgets.QWidget], field: typing.Optional[QtWidgets.QLayout]) -> None: ...
    @typing.overload
    def addRow(self, labelText: typing.Optional[str], field: typing.Optional[QtWidgets.QWidget]) -> None: ...
    @typing.overload
    def addRow(self, labelText: typing.Optional[str], field: typing.Optional[QtWidgets.QLayout]) -> None: ...
    @typing.overload
    def addRow(self, widget: typing.Optional[QtWidgets.QWidget]) -> None: ...
    @typing.overload
    def addRow(self, layout: typing.Optional[QtWidgets.QLayout]) -> None: ...

    def addRow(self, *args) -> None:
        row = self.rowCount()

        super().addRow(*args)

        if self.rowCount() <= row:
            return # Row wasn't added

        label = self.labelAt(row)
        field = self.fieldAt(row)

        if label:
            label.setEnabled(self._shouldEnableLabel(field))
            label.installEventFilter(self._parentChangeWatcher)

        if field:
            field.installEventFilter(self._parentChangeWatcher)

    def _objectSearch(
            self,
            obj: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]
            ) -> typing.Tuple[
                int,
                typing.Optional[QtWidgets.QLayoutItem],
                typing.Optional['FormLayoutEx.ItemRole']]:
        for row in range(self.rowCount()):
            # Spanning roles must be checked first as itemAt will also return spanning
            # widgets if gui.FormLayoutEx.ItemRole.FieldRole is specified
            # https://codebrowser.dev/qt5/qtbase/src/widgets/kernel/qformlayout.cpp.html#_ZNK11QFormLayout6itemAtEiNS_8ItemRoleE
            item = self.itemAt(row, gui.FormLayoutEx.ItemRole.SpanningRole)
            if obj == item.widget() or obj == item.layout():
                return (row, item, gui.FormLayoutEx.ItemRole.SpanningRole)

            item = self.itemAt(row, gui.FormLayoutEx.ItemRole.LabelRole)
            if obj == item.widget() or obj == item.layout():
                return (row, item, gui.FormLayoutEx.ItemRole.LabelRole)

            item = self.itemAt(row, gui.FormLayoutEx.ItemRole.FieldRole)
            if obj == item.widget() or obj == item.layout():
                return (row, item, gui.FormLayoutEx.ItemRole.FieldRole)

            return (-1, None, None)

    def _shouldEnableLabel(
            self,
            field: typing.Optional[typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]]
            ) -> bool:
        if not field:
            # Enable labels that have no field. The assumption is they've been added for
            # a reason so shouldn't be disabled
            return True

        if isinstance(field, QtWidgets.QWidget):
            return field.isEnabled()

        for child in field.children():
            if self._shouldEnableLabel(child):
                return True

        return False

    def _isHierarchicalChild(
            self,
            widget: QtWidgets.QWidget,
            parent: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]
            ) -> bool:
        if widget == parent:
            return True

        if isinstance(parent, QtWidgets.QWidget):
            for child in parent.children():
                if not isinstance(child, QtWidgets.QWidget):
                    continue
                if self._isHierarchicalChild(widget, child):
                    return True
        elif isinstance(parent, QtWidgets.QLayout):
            for index in range(parent.count()):
                item = parent.itemAt(index)

                child = item.widget()
                if child and self._isHierarchicalChild(widget, child):
                    return True

                child = item.layout()
                if child and self._isHierarchicalChild(widget, child):
                    return True

        return False

    def _rowForHierarchicalField(
            self,
            widget: QtWidgets.QWidget,
            ) -> typing.Optional[QtWidgets.QLayoutItem]:
        for row in range(self.rowCount()):
            field = self.fieldAt(row)
            if field:
                if self._isHierarchicalChild(widget, field):
                    return row
        return -1

    def _parentChangeDetected(
            self,
            oldParent: typing.Optional[QtWidgets.QWidget],
            newParent: typing.Optional[QtWidgets.QWidget]
            ) -> None:
        if oldParent:
            oldParent.removeEventFilter(self._childChangeWatcher)

        if newParent:
            newParent.installEventFilter(self._childChangeWatcher)

    def _childAdditionDetected(
            self,
            widget: QtWidgets.QWidget
            ) -> None:
        widget.installEventFilter(self._enableChangedWatcher)

    def _childRemovalDetected(
            self,
            widget: QtWidgets.QWidget
            ) -> None:
        # Checking if the object has been deleted is belt and braces. I've never
        # actually seen it be deleted at this point
        if not sip.isdeleted(widget):
            widget.removeEventFilter(self._enableChangedWatcher)

    def _enableChangedDetected(
            self,
            widget: QtWidgets.QWidget,
            enabled: bool
            ) -> None:
        if not self._disableLabelWithField:
            # Labels should always be enabled
            return True

        if self.rowForLabel(widget) >= 0:
            # The widget is a label so ignore it changing
            return

        row = self._rowForHierarchicalField(widget)
        label = self.labelAt(row) if row >= 0 else None
        if label:
            label.setEnabled(self._shouldEnableLabel(widget))
