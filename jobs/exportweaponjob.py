import copy
import gunsmith
import pdf
import time
import typing
from PyQt5 import QtCore

class ExportWeaponJob(QtCore.QThread):
    _progressSignal = QtCore.pyqtSignal([int, int])
    _finishedSignal = QtCore.pyqtSignal([str], [Exception])

    def __init__(
            self,
            parent: QtCore.QObject,
            weapon: gunsmith.Weapon,
            filePath: str,
            colour: bool,
            includeEditableFields: bool,
            includeManifestTable: bool,
            includeAmmoTable: bool,
            usePurchasedMagazines: bool,
            usePurchasedAmmo: bool,
            progressCallback: typing.Callable[[int, int], typing.Any],
            finishedCallback: typing.Callable[[typing.Union[str, Exception]], typing.Any],
            ) -> None:
        super().__init__(parent=parent)

        # Create a copy of the weapon to avoid issues if the passed in one is modified
        self._weapon = copy.deepcopy(weapon)
        self._filePath = filePath
        self._colour = colour
        self._includeEditableFields = includeEditableFields
        self._includeManifestTable = includeManifestTable
        self._includeAmmoTable = includeAmmoTable
        self._usePurchasedMagazines = usePurchasedMagazines
        self._usePurchasedAmmo = usePurchasedAmmo

        if progressCallback:
            self._progressSignal[int, int].connect(progressCallback)
        if finishedCallback:
            self._finishedSignal[str].connect(finishedCallback)
            self._finishedSignal[Exception].connect(finishedCallback)

        self.start()

    def run(self) -> None:
        try:
            exporter = pdf.WeaponToPdf()
            exporter.export(
                weapon=self._weapon,
                filePath=self._filePath,
                colour=self._colour,
                includeEditableFields=self._includeEditableFields,
                includeManifestTable=self._includeManifestTable,
                includeAmmoTable=self._includeAmmoTable,
                usePurchasedMagazines=self._usePurchasedMagazines,
                usePurchasedAmmo=self._usePurchasedAmmo,
                progressCallback=self._handleProgressUpdate)

            self._finishedSignal[str].emit('Finished')
        except Exception as ex:
            self._finishedSignal[Exception].emit(ex)

    def _handleProgressUpdate(
            self,
            current: int,
            total: int
            ) -> None:
        self._progressSignal[int, int].emit(current, total)
        time.sleep(0.01)
