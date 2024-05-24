import copy
import construction
import logging
import os
import threading
import typing
import uuid

class _ConstructableMetadata(object):
    def __init__(
            self,
            filePath: typing.Optional[str],
            readOnly: bool
            ) -> None:
        super().__init__()
        self._filePath = filePath
        self._readOnly = readOnly

    def filePath(self) -> typing.Optional[str]:
        return self._filePath

    def readOnly(self) -> bool:
        return self._readOnly

class ConstructableStore(object):
    def __init__(
            self,
            typeString: str,
            readFileFn: typing.Callable[[
                str, # Input: Path of file to read from
                typing.Optional[construction.ConstructableInterface] # Input: Optional In place constructable ro read into
                ],
                construction.ConstructableInterface], # Output: Constructable
            writeFileFn: typing.Callable[[
                construction.ConstructableInterface, # Input: Constructable to write
                str # Input: Path of file to write to
                ],
                typing.Any], # Output: None
            userDir: str,
            exampleDir: typing.Optional[str] = None
            ) -> None:
        super().__init__()
        self._typeString = typeString
        self._readFileFn = readFileFn
        self._writeFileFn = writeFileFn
        self._userDir = userDir
        self._exampleDataDir = exampleDir
        self._constructableMap: typing.Dict[
            construction.ConstructableInterface,
            _ConstructableMetadata] = {}
        self._lock = threading.Lock()

    def typeString(self) -> str:
        return self._typeString

    def loadData(
            self,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> None:
        if not self._userDir:
            raise RuntimeError(f'{self._typeString} store failed to load data (User data directory not set)')

        self._constructableMap.clear()

        userFiles = self._findFiles(self._userDir)
        exampleFiles = []
        if self._exampleDataDir:
            exampleFiles = self._findFiles(self._exampleDataDir)

        constructableIndex = 0
        constructableCount = len(userFiles) + len(exampleFiles)

        for filePath in userFiles:
            try:
                if progressCallback:
                    progressCallback(os.path.basename(filePath), constructableIndex, constructableCount)
                constructableIndex += 1

                constructable = self._readFileFn(filePath)
                self._constructableMap[constructable] = _ConstructableMetadata(
                    filePath=filePath,
                    readOnly=False)
            except Exception as ex:
                logging.error(f'{self._typeString} store failed to load user file "{filePath}"', exc_info=ex)

        for filePath in exampleFiles:
            try:
                if progressCallback:
                    progressCallback(os.path.basename(filePath), constructableIndex, constructableCount)
                constructableIndex += 1

                constructable = self._readFileFn(filePath)
                self._constructableMap[constructable] = _ConstructableMetadata(
                    filePath=filePath,
                    readOnly=True)
            except Exception as ex:
                logging.error(f'{self._typeString} store failed to load example file "{filePath}"', exc_info=ex)

        if progressCallback:
            # Force 100% progress notification
            progressCallback('Complete', constructableCount, constructableCount)

    def constructables(self) -> typing.Iterable[construction.ConstructableInterface]:
        with self._lock:
            return list(self._constructableMap.keys())

    def isStored(
            self,
            constructable: construction.ConstructableInterface
            ) -> bool:
        metadata = self._constructableMap.get(constructable)
        return metadata != None and metadata.filePath() != None

    def isReadOnly(
            self,
            constructable: construction.ConstructableInterface
            ) -> bool:
        metadata = self._constructableMap.get(constructable)
        return metadata != None and metadata.readOnly()

    def exists(
            self,
            name: str
            ) -> bool:
        with self._lock:
            for constructable in self._constructableMap.keys():
                if name == constructable.name():
                    return True
        return False

    def add(
            self,
            constructable: construction.ConstructableInterface
            ) -> None:
        with self._lock:
            if constructable in self._constructableMap:
                return # Constructable is already in the store so nothing to do

            self._constructableMap[constructable] = _ConstructableMetadata(
                filePath=None, # Not saved yet
                readOnly=False)

    def save(
            self,
            constructable: construction.ConstructableInterface
            ) -> None:
        with self._lock:
            metadata = self._constructableMap.get(constructable)
            if not metadata:
                raise RuntimeError(f'{self._typeString} store unable to save "{constructable.name()}" (Unknown {self._typeString})')

            if metadata.readOnly():
                raise RuntimeError(f'{self._typeString} store unable to save "{constructable.name()}" ({self._typeString} is read-only)')

            filePath = None
            if metadata:
                filePath = metadata.filePath()
            if not filePath:
                # Generate a filename for the constructable
                filePath = self._generateUserFilePath()

            if not os.path.exists(self._userDir):
                os.makedirs(self._userDir)
            self._writeFileFn(constructable, filePath)

            # Update the constructable map after the file has been written
            self._constructableMap[constructable] = _ConstructableMetadata(
                filePath=filePath,
                readOnly=False)

    def delete(
            self,
            constructable: construction.ConstructableInterface
            ) -> None:
        with self._lock:
            metadata = self._constructableMap.get(constructable)
            if not metadata:
                raise RuntimeError(f'{self._typeString} store unable to delete "{constructable.name()}" (Unknown {self._typeString})')

            if metadata.readOnly():
                raise RuntimeError(f'{self._typeString} store unable to delete "{constructable.name()}" ({self._typeString} is read-only)')

            if metadata.filePath():
                os.remove(path=metadata.filePath())
            del self._constructableMap[constructable]

    def revert(
            self,
            constructable: construction.ConstructableInterface
            ) -> None:
        with self._lock:
            metadata = self._constructableMap.get(constructable)
            if not metadata:
                raise RuntimeError(f'{self._typeString} store unable to revert "{constructable.name()}" (Unknown {self._typeString})')

            filePath = metadata.filePath()
            if filePath:
                self._readFileFn(filePath, constructable)

    def copy(
            self,
            constructable: construction.ConstructableInterface,
            newConstructableName: str
            ) -> construction.ConstructableInterface:
        with self._lock:
            metadata = self._constructableMap.get(constructable)
            if not metadata:
                raise RuntimeError(f'{self._typeString} store unable to copy "{constructable.name()}" (Unknown {self._typeString})')

            newConstructable = copy.deepcopy(constructable)
            newConstructable.setName(name=newConstructableName)
            self._constructableMap[newConstructable] = _ConstructableMetadata(
                filePath=None, # Copied constructables hasn't been saved yet
                readOnly=False) # Copied constructables are writable even when copied from read only constructables

            return newConstructable

    def _generateUserFilePath(self) -> str:
        fileName = str(uuid.uuid4()) + '.json'
        return os.path.join(self._userDir, fileName)

    def _findFiles(
            self,
            searchDir: str,
            ) -> typing.Iterable[str]:
        if os.path.exists(searchDir):
            return [os.path.join(searchDir, x) for x in os.listdir(searchDir) if x.endswith(".json")]
        else:
            return []
