import copy
import travellermap
import typing
from PyQt5 import QtCore

class PosterJob(QtCore.QThread):
    # If successful, this signal will return a dict mapping float pixel per parsec scales to
    # the bytes for that poster. If an exception occurs it will return the exception.
    _finishedSignal = QtCore.pyqtSignal([object])

    def __init__(
            self,
            parent: QtCore.QObject,
            mapUrl: str,
            sectorData: str,
            sectorMetadata: typing.Optional[str],
            style: typing.Optional[travellermap.Style],
            options: typing.Optional[typing.Iterable[travellermap.Option]],
            scales: typing.Iterable[float],
            compositing: bool,
            finishedCallback: typing.Callable[[typing.Union[str, Exception]], typing.Any],
            ) -> None:
        super().__init__(parent=parent)

        self._mapUrl = mapUrl
        self._sectorData = sectorData
        self._sectorMetadata = sectorMetadata
        self._style = style
        self._options = copy.copy(options) if options else None
        self._scales = copy.copy(scales)
        self._compositing = compositing

        if finishedCallback:
            self._finishedSignal[object].connect(finishedCallback)

        self._cancelled = False
        self._lastProgressTime = None
        self._avgFileDownloadTime = None

        self.start()

    def cancel(self, block=False) -> None:
        self._cancelled = True
        if block:
            self.quit()
            self.wait()

    def isCancelled(self) -> bool:
        return self._cancelled

    def run(self) -> None:
        try:
            posterClient = travellermap.PosterClient(
                mapUrl=self._mapUrl,
                sectorData=self._sectorData,
                sectorMetadata=self._sectorMetadata,
                style=self._style,
                options=self._options,
                compositing=self._compositing)
            posters: typing.Dict[float, bytes] = {}
            for scale in self._scales:
                poster = posterClient.makePoster(linearScale=scale)
                posters[scale] = poster

            self._finishedSignal[object].emit(posters)
        except Exception as ex:
            self._finishedSignal[object].emit(ex)

