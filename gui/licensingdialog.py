import gui
import typing
from PyQt5 import QtWidgets, QtCore

class LicensingDialog(gui.DialogEx):
    _ForcedLicenseOrder = [
        'Auto-Jimmy',
        'Traveller',
        'Sector Data',
        'Traveller Map',
        'Application Icon',
        'Tabler Icons'
    ]

    def __init__(
            self,
            licenseDir: str,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Licensing Information',
            configSection='LicensingDialog',
            parent=parent)

        self._licenseWidget = gui.LicenseWidget(
            licenseDir=licenseDir,
            forcedOrder=LicensingDialog._ForcedLicenseOrder)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._licenseWidget)

        self.setLayout(layout)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowMaximizeButtonHint, True)
        self.resize(900, 600)
