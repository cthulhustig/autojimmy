import common
import glob
import logging
import hashlib
import os
import time
import urllib.request
import urllib.error
import threading
import typing

# This cache assumes the data returned for a URL is constant. It makes no attempt to
# automatically expire cache entries
class RequestCache(object):
    _instance = None # Singleton instance
    _lock = threading.Lock()
    _cacheDir = None
    _memoryCache = {}

    def __init__(self) -> None:
        raise RuntimeError('Call instance() instead')

    @classmethod
    def instance(cls):
        if not cls._instance:
            with cls._lock:
                # Recheck instance as another thread could have created it between the
                # first check adn the lock
                if not cls._instance:
                    cls._instance = cls.__new__(cls)
        return cls._instance

    @staticmethod
    def setCacheDir(cacheDir: str) -> None:
        if RequestCache._instance:
            raise RuntimeError('You can\'t set the cache directory after the singleton has been initialised')
        RequestCache._cacheDir = cacheDir

    def makeRequest(
            self,
            url: str,
            timeout: typing.Optional[typing.Union[int, float]] = None,
            cacheInMemory: bool = True
            ) -> bytes:
        hashedUrl = hashlib.sha256(url.encode('utf-8'), usedforsecurity=False).hexdigest()

        content = self._readCache(hashedUrl, cacheInMemory)
        if content != None:
            logging.debug(f'Request cache hit for {url}')
            return content

        # Leave this enabled to catch bugs that are causing LOTS of requests
        logging.debug(f'Request cache miss for {url}')

        startTime = time.time()

        # Any exception that occurs here is just allowed to pass up to the caller
        try:
            response = urllib.request.urlopen(url=url, timeout=timeout)
        except urllib.error.HTTPError as ex:
            raise RuntimeError(f'Request failed for {url} ({ex.reason})') from ex
        except urllib.error.URLError as ex:
            if isinstance(ex.reason, TimeoutError):
                raise TimeoutError(f'Request timeout for {url}') from ex
            raise RuntimeError(f'Request failed for {url} ({ex.reason})') from ex
        except Exception as ex:
            raise RuntimeError(f'Request failed for {url} ({ex})') from ex

        content = response.read()

        downloadTime = time.time() - startTime
        logging.debug(f'Download of {url} took {downloadTime}s')

        self._writeCache(hashedUrl, content, cacheInMemory)
        return content

    def cacheFilePath(self, url: str) -> typing.Optional[str]:
        #encodedUrl = base64.b32encode(url.encode('ascii')).decode('ascii')
        encodedUrl = common.encodeFileName(rawFileName=url)
        filePath = os.path.join(self._cacheDir, encodedUrl)

        # Lock the mutex to make sure we don't return a file path while another
        # thread is part way through writing the file.
        with self._lock:
            if os.path.exists(filePath):
                return filePath
            return None

    def clearCache(self) -> None:
        with self._lock:
            if not os.path.exists(self._cacheDir):
                return # Nothing to do

            cacheFiles = glob.glob(os.path.join(self._cacheDir, '*'))
            for file in cacheFiles:
                try:
                    os.remove(file)
                except Exception as ex:
                    logging.error(f'Failed to delete cache file {file}', exc_info=ex)

    def _readCache(
            self,
            hashedUrl: bytes,
            cacheInMemory: bool
            ) -> typing.Optional[bytes]:
        with self._lock:
            if hashedUrl in self._memoryCache:
                return self._memoryCache[hashedUrl]

            if self._cacheDir == None:
                return None

            filePath = os.path.join(self._cacheDir, hashedUrl)
            if os.path.exists(filePath):
                with open(filePath, 'rb') as file:
                    content = file.read()
                    if cacheInMemory:
                        self._memoryCache[hashedUrl] = content
                    return content

            return None

    def _writeCache(
            self,
            hashedUrl: bytes,
            content: bytes,
            cacheInMemory: bool
            ) -> None:
        with self._lock:
            if cacheInMemory:
                self._memoryCache[hashedUrl] = content

            os.makedirs(self._cacheDir, exist_ok=True)

            filePath = os.path.join(self._cacheDir, hashedUrl)
            with open(filePath, 'wb') as file:
                file.write(content)
