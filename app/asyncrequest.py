import aiohttp
import asyncio
import io
import logging
import multidict
import typing
from PyQt5 import QtCore

class AsyncResponse(object):
    def __init__(
            self,
            status: int,
            headers: multidict.MultiDictProxy,
            content: bytes
            ) -> None:
        self._status = status
        self._headers = headers
        self._content = content

    def status(self) -> int:
        return self._status

    def headers(self) -> multidict.MultiDictProxy:
        return self._headers
    
    def header(
            self,
            header: str,
            default: typing.Optional[str] = None
            ) -> typing.Optional[str]:
        return self._headers.get(header, default)
    
    def content(self) -> bytes:
        return self._content

class AsyncRequest(QtCore.QObject):
    class HttpException(RuntimeError):
        def __init__(
                self,
                status: int,
                reason: typing.Optional[str],
                headers: multidict.MultiDictProxy,
                content: bytes
                ) -> None:
            super().__init__(f'Request failed ({status} {reason})' if reason else f'Request failed ({status})')
            self._status = status
            self._reason  = reason
            self._headers = headers
            self._content = content

        def status(self) -> int:
            return self._status
        
        def reason(self) -> typing.Optional[str]:
            return self._reason

        def headers(self) -> multidict.MultiDictProxy:
            return self._headers
        
        def header(
                self,
                header: str,
                default: typing.Optional[str] = None
                ) -> typing.Optional[str]:
            return self._headers.get(header, default)
        
        def content(self) -> bytes:
            return self._content

    class TimeoutException(RuntimeError):
        def __init__(self) -> None:
            super().__init__('Request timed out')

    class _ProgressBufferReader(io.BufferedReader):
        def __init__(
                self,
                name: str,
                data: bytes,
                callback=typing.Callable[[int, int], typing.Any]
                ) -> None:
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

    # If a response is received this signal will be passed an instance of AsyncResponse.
    # If some other kind of exception occurs then the signal will be passed the exception
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
            timeout: typing.Optional[float],
            loop: typing.Optional[asyncio.AbstractEventLoop] = None # None means use current loop
            ) -> None:
        try:
            self._teardown() # Making a new request cancels any in progress request

            self._requestTask = asyncio.ensure_future(
                self._getRequestAsync(url),
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
            content: typing.Optional[typing.Union[bytes, str, typing.Mapping[str, typing.Union[bytes, str]]]],
            timeout: typing.Optional[float] = None,
            loop: typing.Optional[asyncio.AbstractEventLoop] = None # None means use current loop
            ) -> None:
        try:
            self._teardown() # Making a new request cancels any in progress request

            self._requestTask = asyncio.ensure_future(
                self._postRequestAsync(url, content),
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
            ) -> None:
        try:
            logging.info(f'Starting async GET request for {url}')

            async with aiohttp.ClientSession() as session:
                async with session.get(url=url) as response:
                    status = response.status
                    reason = response.reason
                    headers = response.headers.copy()

                    size = headers.get('Content-Length', 0)
                    self._updateDownloadProgress(0, size)

                    content = bytearray()
                    async for chunk in response.content.iter_chunked(self._chunkSize):
                        content.extend(chunk)
                        self._updateDownloadProgress(len(content), size)

            self._handleResponse(
                status=status,
                reason=reason,
                headers=headers,
                content=content)
        except Exception as ex:
            # Log errors are debug level, it's really up to the observer to log. In some cases errors are
            # expected (e.g. when linting if there are errors in the data)
            logging.debug(f'Async GET request for {url} failed', exc_info=ex)
            self.complete[object].emit(ex)
        finally:
            self._teardown()

    async def _postRequestAsync(
            self,
            url: str,
            content: typing.Optional[typing.Union[bytes, str, typing.Mapping[str, typing.Union[bytes, str]]]],
            ) -> None:
        try:
            logging.info(f'Starting async POST request to {url}')

            if isinstance(content, dict):
                data = data = aiohttp.FormData()
                for key, value in content.items():
                    if isinstance(value, str):
                        value = value.encode()

                    dataWrapper = AsyncRequest._ProgressBufferReader(
                        name=key,
                        data=value,
                        callback=self._updateUploadProgress)
                    data.add_field(key, dataWrapper)
            else:
                data = content

            async with aiohttp.ClientSession() as session:
                async with session.post(url=url, data=data) as response:
                    status = response.status
                    reason = response.reason
                    headers = response.headers.copy()
                
                    size = headers.get('Content-Length', 0)
                    self._updateDownloadProgress(0, size)

                    content = bytearray()
                    async for chunk in response.content.iter_chunked(self._chunkSize):
                        content.extend(chunk)
                        self._updateDownloadProgress(len(content), size)

            self._handleResponse(
                status=status,
                reason=reason,
                headers=headers,
                content=content)
        except Exception as ex:
            # Log errors are debug level, it's really up to the observer to log. In some cases errors are
            # expected (e.g. when linting if there are errors in the data)
            logging.debug(f'Async POST request to {url} failed', exc_info=ex)
            self.complete[object].emit(ex)
        finally:
            self._teardown()

    async def _timeoutRequestAsync(
            self,
            timeout: float
            ) -> None:
        await asyncio.sleep(timeout)
        self.complete[object].emit(AsyncRequest.TimeoutException())
        self._teardown()

    def _handleResponse(
            self,
            status: int,
            reason: typing.Optional[str],
            headers:  multidict.MultiDictProxy,
            content: bytearray
            ) -> None:
        if (status < 200) or (status > 299):
            raise AsyncRequest.HttpException(
                status=status,
                reason=reason,
                headers=headers,
                content=bytes(content))

        self.complete[object].emit(AsyncResponse(
            status=status,
            headers=headers,
            content=bytes(content)))

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
