import logging
import time
import typing
import urllib

class Downloader(object):
    class _CancelledException(Exception):
        pass

    _RetryHttpCodes = [
        408, # Request timeout
        409, # Conflict (not sure about this one)
        425, # Too early
        429, # Too many requests
        500, # Internal Server Error
        502, # Bad Gateway
        503, # Service Unavailable
        504, # Gateway Timeout
        509 # Bandwidth limit exceeded
    ]

    _initialRetryDelaySeconds = 5

    def __init__(self):
        pass

    def downloadToFile(
            self,
            url: str,
            filePath: str,
            retryCount=3,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> None:
        logging.info(f'Downloading {url}')

        progressLambda = None
        if isCancelledCallback:
            progressLambda = lambda count, blockSize, totalSize: \
                Downloader._downloadProgressCallback(count, blockSize, totalSize, isCancelledCallback)

        retryDelay = self._initialRetryDelaySeconds
        while True:
            try:
                urllib.request.urlretrieve(
                    url,
                    filePath,
                    progressLambda)
                return
            except Downloader._CancelledException as ex:
                return
            except urllib.error.HTTPError as ex:
                isRetrying = False
                if ex.code in Downloader._RetryHttpCodes:
                    if retryCount > 0:
                        logging.warning(f'Downloading {url} failed, retrying in {retryDelay} seconds', exc_info=ex)
                        time.sleep(retryDelay)
                        retryCount -= 1
                        retryDelay *= 2 # Double the delay
                        isRetrying = True

                if not isRetrying:
                    raise

    @staticmethod
    def _downloadProgressCallback(
            count: int,
            blockSize: int,
            totalSize: int,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None,
            ) -> None:
        if isCancelledCallback and isCancelledCallback():
            raise Downloader._CancelledException()
