import app
import asyncio
import typing
import travellermap
import copy
import enum
from PyQt5 import QtCore

class PosterJobAsync(QtCore.QObject):
    class ProgressEvent(enum.Enum):
        Uploading = 0
        Downloading = 1

    # If successful, this signal will pass a dict mapping float pixel per parsec scales to
    # the bytes for that poster. If an exception occurs it will pass the exception.    
    complete = QtCore.pyqtSignal([object])

    # This signal passes the event type, scale being process, poster index, total posters,
    # current transfer bytes, total transfer bytes. The scale uses object as it can be in
    # int or a float
    progress = QtCore.pyqtSignal([ProgressEvent, object, int, int, int, int])

    def __init__(
            self,
            parent: QtCore.QObject,
            mapUrl: str,
            sectorData: str,
            sectorMetadata: typing.Optional[str],
            style: typing.Optional[travellermap.Style],
            options: typing.Optional[typing.Iterable[travellermap.Option]],
            scales: typing.Iterable[float],
            compositing: bool
            ) -> None:
        super().__init__(parent=parent)

        sectorBytes = sectorData.encode()
        metadataBytes = sectorMetadata.encode()

        self._mapUrl = mapUrl
        # NOTE: Use file for the sector data as AsyncRequest wraps the uploaded data in a byte
        # stream and that forces aiohttp to use multipart/form-data content
        self._data = {'file': sectorBytes, 'metadata': metadataBytes}
        self._style = style
        self._options = copy.copy(options) if options else None
        self._scales = copy.copy(scales)
        self._compositing = compositing

        self._uploadHistory = 0
        self._uploadSize = len(sectorBytes) + len(metadataBytes)        

        self._request = None
        self._posters: typing.Dict[float, bytes] = {}

    def run(self):          
        self._primeNextRequest(index=0)
        
    def cancel(self) -> None:
        if self._request:
            self._request.cancel()
            self._request = None

    def posters(self) -> typing.Mapping[float, bytes]:
        return self._posters
    
    def _primeNextRequest(
            self,
            index: int
            ) -> None:
        url = travellermap.formatPosterUrl(
            baseMapUrl=self._mapUrl,
            style=self._style,
            options=self._options,
            linearScale=self._scales[index],
            compositing=self._compositing,
            minimal=True)
        
        self._uploadHistory = 0
        self._emitProgress(
            event=PosterJobAsync.ProgressEvent.Uploading,
            index=index,
            currentBytes=0,
            totalBytes=self._uploadSize)

        self._request = app.AsyncRequest(parent=self)
        self._request.complete.connect(
            lambda result: self._requestCompleted(index, result))
        self._request.uploadProgress.connect(
            lambda _, current, total: self._requestUploadProgress(index, current, total))
        self._request.downloadProgress.connect(
            lambda current, total: self._requestDownloadProgress(index, current, total))
        self._request.post(
            url=url,
            data=self._data,
            loop=asyncio.get_event_loop())
        
    def _requestCompleted(
            self,
            index: int,
            result: typing.Union[bytes, Exception]
            ) -> None:
        if isinstance(result, Exception):
            self.complete[object].emit(result)
            return
        
        scale = self._scales[index]
        self._posters[scale] = result

        index += 1
        if index < len(self._scales):
            self._primeNextRequest(index=index)
        else:
            self.complete[object].emit(self._posters)

    def _requestUploadProgress(
            self,
            index: int,
            current: int,
            total: int
            ) -> None:
        # NOTE: This works on the assumption we're always notified when 100% complete
        totalUpload = self._uploadHistory + current
        if current == total:
            self._uploadHistory = totalUpload

        self._emitProgress(
            event=PosterJobAsync.ProgressEvent.Uploading,
            index=index,
            currentBytes=totalUpload,
            totalBytes=self._uploadSize)            

    def _requestDownloadProgress(
            self,
            index: int,
            current: int,
            total: int
            ) -> None:
        self._emitProgress(
            event=PosterJobAsync.ProgressEvent.Downloading,
            index=index,
            currentBytes=current,
            totalBytes=total)

    def _emitProgress(
            self,
            event: ProgressEvent,
            index: int,
            currentBytes: int,
            totalBytes: int
            ) -> None:
        scale = self._scales[index]
        self.progress[PosterJobAsync.ProgressEvent, object, int, int, int, int].emit(
            event,
            scale,
            index,
            len(self._scales),
            currentBytes,
            totalBytes)