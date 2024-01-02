import typing
from PyQt5 import QtWidgets, QtCore

class SectionWidget(QtWidgets.QWidget):
    def __init__(
            self,
            label: str,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._content = None

        self._label = QtWidgets.QLabel(label)

        self._headerLine = QtWidgets.QFrame()
        self._headerLine.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self._headerLine.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self._headerLine.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Maximum)

        self._contentArea = QtWidgets.QWidget()

        # don't waste space
        self._mainLayout = QtWidgets.QGridLayout()
        self._mainLayout.setSpacing(0)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)
        row = 0
        self._mainLayout.addWidget(self._label, row, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignLeft)
        self._mainLayout.addWidget(self._headerLine, row, 2, 1, 1)
        row += 1
        self._mainLayout.addWidget(self._contentArea, row, 0, 1, 3)
        self.setLayout(self._mainLayout)

        self._contentArea.installEventFilter(self)

    def label(self) -> str:
        return self._label.text()

    def setLabel(self, label: str) -> None:
        self._label.setText(label)

    def content(self) -> typing.Optional[typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]]:
        return self._content

    def setContent(
            self,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]
            ) -> None:
        if isinstance(content, QtWidgets.QWidget):
            # This layout intentionally keeps the default padding to indent the widget a little
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(content)
        elif isinstance(content, QtWidgets.QLayout):
            layout = content
        else:
            raise TypeError('Layout object must be a widget or layout')
        self._content = content
        self._contentArea.setLayout(layout)

class SectionGroupWidget(QtWidgets.QWidget):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)
        self._sections: typing.List[SectionWidget] = []

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.setLayout(self._layout)

    def sections(self) -> typing.Iterable[SectionWidget]:
        return self._sections

    def addSection(
            self,
            section: SectionWidget,
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> None:
        self._insertSection(
            index=-1, # Insert at end
            section=section,
            stretch=stretch,
            alignment=alignment)

    def insertSection(
            self,
            index: int,
            section: SectionWidget,
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> None:
        self._insertSection(
            index=index,
            section=section,
            stretch=stretch,
            alignment=alignment)

    def addSectionContent(
            self,
            label: str,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout],
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> SectionWidget:
        return self._insertSectionContent(
            index=-1, # Insert at end
            label=label,
            content=content,
            stretch=stretch,
            alignment=alignment)

    def insertSectionContent(
            self,
            index: int,
            label: str,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout],
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> SectionWidget:
        return self._insertSectionContent(
            index=index,
            label=label,
            content=content,
            stretch=stretch,
            alignment=alignment)

    def addStretch(
            self,
            stretch: int
            ) -> None:
        self._layout.addStretch(stretch=stretch)

    def insertStretch(
            self,
            index: int,
            stretch: int
            ) -> None:
        self._layout.insertStretch(index, stretch)

    def sectionFromContent(
            self,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]
            ) -> typing.Optional[SectionWidget]:
        for section in self._sections:
            if content == section.content():
                return section
        return None

    def labelFromContent(
            self,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]
            ) -> typing.Optional[str]:
        section = self.sectionFromContent(content)
        if not section:
            return None
        return section.label()

    def contentFromLabel(
            self,
            label: str
            ) -> typing.Optional[typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]]:
        for section in self._sections:
            if section.label() == label:
                return section.content()
        return None

    # This is named removeWidget but QVBoxLayout also (as far as I can tell) uses it to remove
    # layouts so I've gone with the same approach
    def removeContent(
            self,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]
            ) -> None:
        section = self.sectionFromContent(content)
        if section:
            # If an section is used then it's the section that needs to be removed
            self._sections.remove(section)
            content = section

        self._layout.removeWidget(content)

        if section:
            # Destroy the section after removing it. Reset the parent on the widget to detach it
            # from the parent the widget that the layout would have set for it (i.e. the widget the
            # layout is attached to). I'm not sure why removeWidget doesn't do this as it would seem
            # logical when addWidget sets the parent. I found that in most cases this was enough to
            # stop the removed widget from being displayed. However if adding/removing widgets is
            # done rapidly (e.g. by the user scrolling up and down through the weapon list with the
            # cursor keys) then sometimes the removed widgets would be left displayed in separate
            # floating windows (I've no idea why this is happening but ut doesn't appear to be my
            # code). The explicit deleteLater fixes this. Hiding the widget is done to prevent it
            # temporarily being displayed in a floating window before deleteLater kicks in.
            section.setParent(None)
            section.setHidden(True)
            section.deleteLater()

    def contentFromIndex(
            self,
            index: int
            ) -> typing.Optional[typing.Union[QtWidgets.QWidget, QtWidgets.QLabel]]:
        layoutItem = self._layout.itemAt(index)
        if not layoutItem:
            return None
        widget = layoutItem.widget()
        if not widget:
            return layoutItem.layout()
        if widget in self._sections:
            assert(isinstance(widget, SectionWidget))
            return widget.content()
        return widget

    def setSectionLabel(
            self,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout],
            label: str
            ) -> None:
        section = self.sectionFromContent(content)
        if not section:
            return # Nothing to do
        section.setLabel(label=label)

    def isWidgetHidden(
            self,
            widget: QtWidgets.QWidget
            ) -> bool:
        section = self.sectionFromContent(widget)
        if section:
            widget = section
        return widget.isHidden()

    def setContentHidden(
            self,
            content: QtWidgets.QWidget,
            hidden: bool
            ) -> None:
        section = self.sectionFromContent(content)
        if section:
            section.setHidden(hidden)
        else:
            content.setHidden(hidden)

    def _insertSection(
            self,
            index: int,
            section: SectionWidget,
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> None:
        assert(isinstance(section, SectionWidget))
        self._sections.append(section)
        self._layout.insertWidget(index, section, stretch, alignment)

    def _insertSectionContent(
            self,
            index: int,
            label: str,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout],
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> SectionWidget:
        section = SectionWidget(label=label)
        section.setContent(content)
        self._insertSection(
            index=index,
            section=section,
            stretch=stretch,
            alignment=alignment)
        return section
