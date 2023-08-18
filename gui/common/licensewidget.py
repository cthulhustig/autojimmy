import gui
import os
import typing
from PyQt5 import QtWidgets

class LicenseWidget(QtWidgets.QWidget):
    def __init__(
            self,
            licenseDir: str,
            forcedOrder: typing.Optional[typing.Iterable[str]],
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._licenseDir = licenseDir
        self._forcedOrder = forcedOrder

        self._productTabs = gui.VerticalTabWidget()

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._productTabs)

        self._createLicenseWidgets()

        self.setLayout(widgetLayout)

    def _createLicenseWidgets(self) -> None:
        directoryNames = os.listdir(self._licenseDir)
        if self._forcedOrder:
            productNames = list(self._forcedOrder)
            productNames.extend([productName for productName in directoryNames if productName not in self._forcedOrder])
        else:
            productNames = directoryNames

        for productName in productNames:
            productDir = os.path.join(self._licenseDir, productName)
            if not os.path.isdir(productDir):
                continue

            licenseFiles = self._loadProductLicenseFiles(productDir)

            licenseTabs = gui.TabWidgetEx()
            for licenseName, licenseData in licenseFiles.items():
                licenseWidget = gui.TextEditEx()
                licenseWidget.setText(licenseData)
                licenseWidget.setReadOnly(True)
                licenseTabs.addTab(licenseWidget, licenseName)
            self._productTabs.addTab(licenseTabs, productName)

    def _loadProductLicenseFiles(
            self,
            productDir
            ) -> typing.Mapping[str, str]:
        licenseFiles: typing.Dict[str, str] = {}
        for licenseName in os.listdir(productDir):
            licensePath = os.path.join(productDir, licenseName)
            if not os.path.isfile(licensePath):
                continue

            try:
                with open(licensePath, 'r', encoding='utf-8') as file:
                    licenseFiles[licenseName] = file.read()
            except:
                licenseFiles[licenseName] = f'Failed to load license file "{licensePath}"'
        if not licenseFiles:
            licenseFiles['ERROR'] = f'Failed to find any license files in "{productDir}"'
        return licenseFiles
