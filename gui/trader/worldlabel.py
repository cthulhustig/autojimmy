import app
import gui
import traveller
import typing
from PyQt5 import QtWidgets

class WorldLabel(QtWidgets.QLabel):
    def __init__(
            self,
            world: typing.Optional[traveller.World] = None,
            prefixText: typing.Optional[str] = None,
            noWorldText: typing.Optional[str] = None,
            ) -> None:
        super().__init__()

        self._world = world
        self._prefixText = prefixText
        self._noWorldText = noWorldText
        self._defaultStyle = self.styleSheet()

        self._updateText()

    def world(self) -> typing.Optional[traveller.World]:
        return self._world

    def setWorld(
            self,
            world: typing.Optional[traveller.World] = None
            ) -> None:
        self._world = world
        self._updateText()

    def setPrefixText(
            self,
            prefix: typing.Optional[str] = None
            ) -> None:
        self._prefixText = prefix
        self._updateText()

    def setNoWorldText(
            self,
            noWorldText: typing.Optional[str] = None
            ) -> None:
        self._noWorldText = noWorldText
        self._updateText()

    def _updateText(self) -> None:
        text = ''
        style = self._defaultStyle
        toolTip = None

        if self._world:
            if self._prefixText:
                text = self._prefixText

            text += self._world.name(includeSubsector=True)

            tagLevel = app.calculateWorldTagLevel(world=self._world)
            if tagLevel:
                # Specifically set QLabel background. If we just set the general background for this
                # widget it will also be applied to the tool tip background
                style = f'QLabel{{background-color: {app.tagColour(tagLevel)}}}'

            toolTip = gui.createWorldToolTip(self._world)
        elif self._noWorldText:
            text = self._noWorldText

        self.setText(text)
        self.setStyleSheet(style)
        self.setToolTip(toolTip)
