import app
import asyncio
import typing
import multiverse
import enum
from PyQt5 import QtCore

class LintJobAsync(QtCore.QObject):
    class ProgressEvent(enum.Enum):
        Uploading = 0
        Downloading = 1

    class Stage(enum.Enum):
        Sector = 0
        Metadata = 1

    class LinterResult(object):
        def __init__(
                self,
                content: str,
                mimeType: typing.Optional[str]
                ) -> None:
            self._content = content
            self._mimeType = mimeType

        def content(self) -> str:
            return self._content

        def mimeType(self) -> typing.Optional[str]:
            return self._mimeType

    # If successful, this signal will pass a dict mapping stages where the linter found issues to the
    # LinterResult object holding the content information. If an exception occurs it will pass the exception.
    complete = QtCore.pyqtSignal([object])

    # This signal passes the event type, stage, current transfer bytes, total transfer bytes.
    progress = QtCore.pyqtSignal([ProgressEvent, Stage, int, int])

    def __init__(
            self,
            parent: QtCore.QObject,
            mapUrl: str,
            sectorData: typing.Union[str, bytes],
            xmlMetadata: typing.Optional[typing.Union[str, bytes]] # Must be XML format metadata
            ) -> None:
        super().__init__(parent=parent)

        self._mapUrl = mapUrl
        self._sectorBytes = sectorData.encode() if isinstance(sectorData, str) else sectorData
        self._metadataBytes = xmlMetadata.encode() if isinstance(xmlMetadata, str) else xmlMetadata

        self._request = None
        self._results = None

    def run(self):
        self._primeSectorLint()

    def cancel(self) -> None:
        if self._request:
            self._request.cancel()
            self._request = None

    def results(self) -> typing.Optional[typing.Mapping[Stage, LinterResult]]:
        return self._results

    def _primeSectorLint(self) -> None:
        url = multiverse.formatPosterLintUrl(baseMapUrl=self._mapUrl)

        self._results: typing.Dict[LintJobAsync.Stage, LintJobAsync.LinterResult] = {}

        self._emitProgress(
            event=LintJobAsync.ProgressEvent.Uploading,
            stage=LintJobAsync.Stage.Sector,
            currentBytes=0,
            totalBytes=len(self._sectorBytes))

        self._request = app.AsyncRequest(parent=self)
        self._request.complete.connect(self._sectorLintCompleted)
        self._request.uploadProgress.connect(
            lambda _, current, total: self._requestUploadProgress(LintJobAsync.Stage.Sector, current, total))
        self._request.downloadProgress.connect(
            lambda current, total: self._requestDownloadProgress(LintJobAsync.Stage.Sector, current, total))
        self._request.post(
            url=url,
            content={'file': self._sectorBytes},
            loop=asyncio.get_event_loop())

    def _sectorLintCompleted(
            self,
            result: typing.Union[app.AsyncResponse, Exception]
            ) -> None:
        if isinstance(result, app.AsyncRequest.HttpException):
            # NOTE: The API docs say a 400 response is returned if the linter finds an issue. However I've
            # found that a 500 is returned in some cases (e.g. failure to parse invalid xml)
            if result.status() != 400 and result.status() != 500:
                self.complete[object].emit(result)
                return

            self._results[LintJobAsync.Stage.Sector] = LintJobAsync.LinterResult(
                content=result.content().decode(),
                mimeType=result.header(header='content-type'))
        elif isinstance(result, Exception):
            self.complete[object].emit(result)
            return

        self._primeMetadataLint()

    def _primeMetadataLint(self) -> None:
        url = multiverse.formatMetadataLintUrl(baseMapUrl=self._mapUrl)

        self._emitProgress(
            event=LintJobAsync.ProgressEvent.Uploading,
            stage=LintJobAsync.Stage.Metadata,
            currentBytes=0,
            totalBytes=len(self._metadataBytes))

        self._request = app.AsyncRequest(parent=self)
        self._request.complete.connect(self._metadataLintCompleted)
        self._request.uploadProgress.connect(
            lambda _, current, total: self._requestUploadProgress(LintJobAsync.Stage.Metadata, current, total))
        self._request.downloadProgress.connect(
            lambda current, total: self._requestDownloadProgress(LintJobAsync.Stage.Metadata, current, total))
        self._request.post(
            url=url,
            content=self._metadataBytes,
            loop=asyncio.get_event_loop())

    def _metadataLintCompleted(
            self,
            result: typing.Union[app.AsyncResponse, Exception]
            ) -> None:
        if isinstance(result, app.AsyncRequest.HttpException):
            # NOTE: The API docs say a 400 response is returned if the linter finds an issue. However I've
            # found that a 500 is returned in some cases (e.g. failure to parse invalid xml)
            if result.status() != 400 and result.status() != 500:
                self.complete[object].emit(result)
                return

            self._results[LintJobAsync.Stage.Metadata] = LintJobAsync.LinterResult(
                content=result.content().decode(),
                mimeType=result.header(header='content-type'))
        elif isinstance(result, Exception):
            self.complete[object].emit(result)
            return

        self.complete[object].emit(self._results)

    def _requestUploadProgress(
            self,
            stage: Stage,
            current: int,
            total: int
            ) -> None:
        self._emitProgress(
            event=LintJobAsync.ProgressEvent.Uploading,
            stage=stage,
            currentBytes=current,
            totalBytes=total)

    def _requestDownloadProgress(
            self,
            stage: Stage,
            current: int,
            total: int
            ) -> None:
        self._emitProgress(
            event=LintJobAsync.ProgressEvent.Downloading,
            stage=stage,
            currentBytes=current,
            totalBytes=total)

    def _emitProgress(
            self,
            event: ProgressEvent,
            stage: Stage,
            currentBytes: int,
            totalBytes: int
            ) -> None:
        self.progress[LintJobAsync.ProgressEvent, LintJobAsync.Stage, int, int].emit(
            event,
            stage,
            currentBytes,
            totalBytes)
