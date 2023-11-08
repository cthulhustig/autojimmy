import os
import shutil
import threading
import typing

# NOTE: This is NOT a general purpose solution. It's holds a lock for all filesystem access so isn't
# suited to general multithreaded access.
# NOTE: The cache assumes that all access to the files it's managing go through it
# TODO: Need some kind of cache eviction (probably based on a max cache size and last read/write time)
class FileSystemCache(object):
    def __init__(self) -> None:
        # The cache is a dictionary hierarchy that maps to filesystem elements. If an entry is a file
        # it maps to a bytes object, if it's a directory it maps to another dict for the cache of that
        # directory
        self._cache: typing.Dict[str, dict] = {}
        self._lock = threading.Lock()

    def read(self, path: str) -> bytes:
        elements = FileSystemCache._splitPath(path)

        with self._lock:
            data = self._readCache(elements=elements)
            if data != None:
                return data
  
            with open(path, 'rb') as file:
                data = file.read()

            self._storeCache(elements=elements, data=data)

        return data

    def write(self, path: str, data: typing.Union[str, bytes]) -> None:
        elements = FileSystemCache._splitPath(path)

        if not isinstance(data, bytes):
            data = data.encode()

        with self._lock:
            with open(path, 'wb') as file:
                file.write(data)

            self._storeCache(elements=elements, data=data)

    def rename(self, srcPath: str, dstPath) -> None:
        srcElements = FileSystemCache._splitPath(srcPath)
        dstElements = FileSystemCache._splitPath(dstPath)

        with self._lock:
            os.rename(srcPath, dstPath)
            # TODO: If data is cached it should be moved to it's new location in the
            # cache. This would need the code that renames after a download updated to
            # clear the old data out the cache as we don't want to keep it (may not be
            # needed if I implement some kind of cache eviction). For now just clear
            # the source and dest out the cache
            self._removeCache(elements=srcElements)
            self._removeCache(elements=dstElements)

    def remove(self, path: str) -> None:
        elements = FileSystemCache._splitPath(path)

        with self._lock:
            os.remove(path)
            self._removeCache(elements=elements)

    def rmtree(self, path: str) -> None:
        elements = FileSystemCache._splitPath(path)

        with self._lock:
            shutil.rmtree(path)
            self._removeCache(elements=elements)

    def clearCache(self, path: typing.Optional[str] = None) -> None:
        if path != None:
            elements = FileSystemCache._splitPath(path)
            with self._lock:
                self._removeCache(elements=elements)
        else:
            with self._lock:
                self._cache.clear()

    # NOTE: The following methods are just here to give consumers a single consistent interface for
    # the filesystem. They don't have anything to do with the cache so don't take the lock
    def makedirs(self, path: str, canExist = False) -> None:
        os.makedirs(path, exist_ok=canExist)

    def exists(self, path) -> bool:
        return os.path.exists(path)
    
    def isfile(self, path) -> bool:
        return os.path.isfile(path)

    def isdir(self, path) -> bool:
        return os.path.isdir(path)

    def _readCache(
            self,
            elements: typing.Iterable[str]
            ) -> typing.Optional[bytes]:
        next = self._cache
        for element in elements:
            next = next.get(element)
            if next == None:
                break
        return next if isinstance(next, bytes) else None

    def _storeCache(
            self,
            elements: typing.Iterable[str],
            data: bytes
            ) -> None:
        last = len(elements) - 1
        dir = self._cache
        for index, element in enumerate(elements):
            if index == last:
                dir[element] = data
            else:
                next = dir.get(element)
                if not isinstance(next, dict): # Also handles next being none
                    next = {}
                    dir[element] = next
                dir = next

    def _removeCache(
            self,
            elements: typing.Iterable[str]
            ) -> None:
        last = len(elements) - 1
        dir = self._cache
        for index, element in enumerate(elements):
            if index == last:
                if element in dir:
                    del dir[element]
            else:
                next = dir.get(element)
                if next == None:
                    return
                dir = next

    @staticmethod
    def _splitPath(path) -> typing.Iterable[str]:
        path = os.path.normpath(os.path.abspath(path))
        return path.split(os.sep)