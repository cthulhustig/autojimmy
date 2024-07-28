import copy
import pdf
import robots
import time
import typing
from PyQt5 import QtCore

class ExportRobotJob(QtCore.QThread):
    _progressSignal = QtCore.pyqtSignal([int, int])
    _finishedSignal = QtCore.pyqtSignal([str], [Exception])

    def __init__(
            self,
            parent: QtCore.QObject,
            robot: robots.Robot,
            filePath: str,
            colour: bool,
            includeEditableFields: bool,
            includeManifestTable: bool,
            applySkillModifiers: bool,
            specialityGroupCount: int,
            progressCallback: typing.Callable[[int, int], typing.Any],
            finishedCallback: typing.Callable[[typing.Union[str, Exception]], typing.Any],
            ) -> None:
        super().__init__(parent=parent)

        # Create a copy of the robot to avoid issues if the passed in one is modified
        self._robot = copy.deepcopy(robot)
        self._filePath = filePath
        self._colour = colour
        self._includeEditableFields = includeEditableFields
        self._includeManifestTable = includeManifestTable
        self._applySkillModifiers = applySkillModifiers
        self._specialityGroupCount = specialityGroupCount

        if progressCallback:
            self._progressSignal[int, int].connect(progressCallback)
        if finishedCallback:
            self._finishedSignal[str].connect(finishedCallback)
            self._finishedSignal[Exception].connect(finishedCallback)

        self.start()

    def run(self) -> None:
        try:
            exporter = pdf.RobotToPdf()
            exporter.export(
                robot=self._robot,
                filePath=self._filePath,
                colour=self._colour,
                includeEditableFields=self._includeEditableFields,
                includeManifestTable=self._includeManifestTable,
                applySkillModifiers=self._applySkillModifiers,
                specialityGroupingCount=self._specialityGroupCount,
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
