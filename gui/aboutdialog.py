import app
import gui
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore

_AboutText = """
    <html>
    <h1 style="text-align: center">{name} v{version}</h1>
    <p>Copyright (C) 2025 CthulhuStig</p>
    <p>Universe Data Timestamp: {timestamp}</p>
    <p>Source Code: <a href="{url}">{url}</a></p>
    <p>This program is free software: you can redistribute it and/or modify<br>
    it under the terms of the GNU General Public License as published by<br>
    the Free Software Foundation, either version 3 of the License, or<br>
    (at your option) any later version.</p>
    <p>This program is distributed in the hope that it will be useful,<br>
    but WITHOUT ANY WARRANTY; without even the implied warranty of<br>
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the<br>
    GNU General Public License for more details.</p>
    <p>You should have received a copy of the GNU General Public License<br>
    along with this program.  If not, see <a href="http://www.gnu.org/licenses/">http://www.gnu.org/licenses/</a>.</p>
"""

class AboutDialog(gui.DialogEx):
    def __init__(
            self,
            licenseDir: str,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='About',
            configSection='AboutDialog',
            parent=parent)

        self._licenseDir = licenseDir

        universeTimestamp = travellermap.DataStore.instance().universeTimestamp()
        if universeTimestamp:
            universeTimestamp = universeTimestamp.astimezone()
            universeTimestamp = universeTimestamp.strftime('%c')
        else:
            universeTimestamp = 'Unknown'
        self._aboutLabel = QtWidgets.QLabel(_AboutText.format(
            name=app.AppName,
            version=app.AppVersion,
            timestamp=universeTimestamp,
            url=app.AppURL))
        self._aboutLabel.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse | QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self._aboutLabel.setOpenExternalLinks(True)

        self._licensingButton = QtWidgets.QPushButton("Licensing...")
        self._licensingButton.clicked.connect(self._licensingClicked)

        self._closeButton = QtWidgets.QPushButton('Close')
        self._closeButton.clicked.connect(self.close)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addWidget(self._licensingButton)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._closeButton)

        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)
        mainLayout.addWidget(self._aboutLabel)
        mainLayout.addSpacing(10)
        mainLayout.addLayout(buttonLayout)

        self.setLayout(mainLayout)
        self.setSizeGripEnabled(False)

    def _licensingClicked(self) -> None:
        dlg = gui.LicensingDialog(
            parent=self,
            licenseDir=self._licenseDir)
        dlg.exec()
