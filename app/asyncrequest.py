import aiohttp
import asyncio
import io
import logging
import typing
from PyQt5 import QtCore

class AsyncRequest(QtCore.QObject):
    class HttpException(RuntimeError):
        def __init__(
                self,
                status: int,
                reason: str
                ) -> None:
            super().__init__(f'Request failed ({status} {reason})')

    class TimeoutException(RuntimeError):
        def __init__(self) -> None:
            super().__init__('Request timed out')

    class _ProgressBufferReader(io.BufferedReader):
        def __init__(
                self,
                name: str,
                data: bytes,
                callback=typing.Callable[[int, int], typing.Any]
                ):
            self._name = name
            self._data = io.BytesIO(data)
            self._callback = callback
            self._dataRead = 0
            self._dataSize = len(data)
            super().__init__(raw=self._data)

        def seek(self, __offset: int, __whence: int = ...) -> int:
            return super().seek(__offset, __whence)

        def read(self, size=None) -> bytes:
            data = super().read(size)
            pos = self.tell()
            if pos > self._dataRead:
                self._dataRead = pos
                self._callback(self._name, self._dataRead, self._dataSize)
            return data

    # If successful, this signal will return a dict mapping float pixel per parsec scales to
    # the bytes for that poster. If an exception occurs it will return the exception.
    complete = QtCore.pyqtSignal([object])

    uploadProgress = QtCore.pyqtSignal([str, int, int])
    downloadProgress = QtCore.pyqtSignal([int, int])

    def __init__(
            self,
            parent: typing.Optional[QtCore.QObject] = None
            ) -> None:
        super().__init__(parent=parent)

        self._chunkSize = 10240
        self._requestTask: typing.Optional[asyncio.Task] = None
        self._timeoutTask: typing.Optional[asyncio.Task] = None

    def cancel(self) -> None:
        self._teardown()

    def get(
            self,
            url,
            data: typing.Optional[typing.Dict[str, str]],
            timeout: typing.Optional[float],
            loop: typing.Optional[asyncio.AbstractEventLoop] = None # None means use current loop
            ) -> None:
        try:
            self._teardown() # Making a new request cancels any in progress request

            self._requestTask = asyncio.ensure_future(
                self._getRequestAsync(url, data),
                loop=loop)
            
            if timeout != None:
                self._timeoutTask = asyncio.ensure_future(
                    self._timeoutRequestAsync(timeout),
                    loop=loop)
        except Exception as ex:
            self.complete[object].emit(ex)

    def post(
            self,
            url,
            data: typing.Optional[typing.Dict[str, str]],
            timeout: typing.Optional[float] = None,
            loop: typing.Optional[asyncio.AbstractEventLoop] = None # None means use current loop
            ) -> None:
        try:
            self._teardown() # Making a new request cancels any in progress request

            self._requestTask = asyncio.ensure_future(
                self._postRequestAsync(url, data.copy()),
                loop=loop)
            
            if timeout != None:
                self._timeoutTask = asyncio.ensure_future(
                    self._timeoutRequestAsync(timeout),
                    loop=loop)
        except Exception as ex:
            self.complete[object].emit(ex)

    async def _getRequestAsync(
            self,
            url: str
            ):
        try:
            logging.info(f'Starting async GET request for {url}')

            content = None
            async with aiohttp.ClientSession() as session:                       
                async with session.get(url=url) as response:
                    if response.status != 200:
                        raise AsyncRequest.HttpException(response.status, response.reason)
                    
                    size = response.headers.get('Content-Length', 0)
                    self._updateDownloadProgress(0, size)

                    content = bytearray()
                    async for chunk in response.content.iter_chunked(self._chunkSize):
                        content.extend(chunk)
                        self._updateDownloadProgress(len(content), size)
            self.complete[object].emit(content)
        except Exception as ex:
            logging.critical(f'Async GET request for {url} failed', exc_info=ex)
            self.complete[object].emit(ex)
        finally:
            self._teardown()

    async def _postRequestAsync(
            self,
            url: str,
            data: typing.Optional[typing.Dict[str, typing.Union[str, bytes]]],
            ):
        try:
            logging.info(f'Starting async POST request to {url}')

            formData = None
            if data:
                formData = aiohttp.FormData()
                for key, value in data.items():
                    if isinstance(value, str):
                        value = value.encode()

                    dataWrapper = AsyncRequest._ProgressBufferReader(
                        name=key,
                        data=value,
                        callback=self._updateUploadProgress)
                    formData.add_field(key, dataWrapper)
            async with aiohttp.ClientSession() as session:     
                async with session.post(url=url, data=formData) as response:
                    if response.status != 200:
                        raise AsyncRequest.HttpException(response.status, response.reason)

                    size = response.headers.get('Content-Length', 0)
                    self._updateDownloadProgress(0, size)

                    content = bytearray()
                    async for chunk in response.content.iter_chunked(self._chunkSize):
                        content.extend(chunk)
                        self._updateDownloadProgress(len(content), size)
                    
            self.complete[object].emit(bytes(content))
        except Exception as ex:
            logging.critical(f'Async POST request to {url} failed', exc_info=ex)
            self.complete[object].emit(ex)
        finally:
            self._teardown()

    async def _timeoutRequestAsync(
            self,
            timeout: float
            ):
        await asyncio.sleep(timeout)
        self.complete[object].emit(AsyncRequest.TimeoutException())
        self._teardown()

    def _updateUploadProgress(
            self,
            name: str,
            current: int,
            total: int
            ) -> None:
        self.uploadProgress[str, int, int].emit(name, current, total)

    def _updateDownloadProgress(
            self,
            current: int,
            total: int
            ) -> None:
        self.downloadProgress[int, int].emit(current, total)

    def _teardown(self) -> None:
        if self._requestTask != None:
            self._requestTask.cancel()
            self._requestTask = None

        if self._timeoutTask != None:
            self._timeoutTask.cancel()
            self._timeoutTask = None