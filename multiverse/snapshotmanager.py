import datetime
import enum
import io
import logging
import os
import re
import requests
import shutil
import threading
import typing
import zipfile

class SnapshotDataFormat(object):
    def __init__(self, major: int, minor: int) -> None:
        self._major = major
        self._minor = minor

    def major(self) -> int:
        return self._major

    def minor(self) -> int:
        return self._minor

    def __str__(self) -> str:
        return f'{self._major}.{self._minor}'

    def __eq__(self, other: 'SnapshotDataFormat') -> bool:
        if self.__class__ is other.__class__:
            return (self._major == other._major) and (self._minor == other._minor)
        return False

    def __lt__(self, other: 'SnapshotDataFormat') -> bool:
        if self.__class__ is other.__class__:
            if self._major < other._major:
                return True
            if self._major > other._major:
                return False
            return self._minor < other._minor
        return NotImplemented

    def __le__(self, other: 'SnapshotDataFormat') -> bool:
        if self.__class__ is other.__class__:
            if self._major < other._major:
                return True
            if self._major > other._major:
                return False
            return self._minor <= other._minor
        return NotImplemented

    def __gt__(self, other: 'SnapshotDataFormat') -> bool:
        if self.__class__ is other.__class__:
            if self._major > other._major:
                return True
            if self._major < other._major:
                return False
            return self._minor > other._minor
        return NotImplemented

    def __ge__(self, other: 'SnapshotDataFormat') -> bool:
        if self.__class__ is other.__class__:
            if self._major > other._major:
                return True
            if self._major < other._major:
                return False
            return self._minor >= other._minor
        return NotImplemented

class SnapshotManager(object):
    class SnapshotAvailability(enum.Enum):
        NewSnapshotAvailable = 0
        NoNewSnapshot = 1
        AppToOld = 2
        AppToNew = 3

    class UpdateStage(enum.Enum):
        DownloadStage = 0
        ExtractStage = 1

    _TimestampFileName = 'timestamp.txt'
    _DataFormatFileName = 'dataformat.txt'
    _TimestampFormat = '%Y-%m-%d %H:%M:%S.%f'
    _DataArchiveUrl = 'https://github.com/cthulhustig/autojimmy-data/archive/refs/heads/main.zip'
    _DataArchiveMapPath = 'autojimmy-data-main/map/' # Trailing slash is important
    _TimestampUrl = 'https://raw.githubusercontent.com/cthulhustig/autojimmy-data/main/map/timestamp.txt'
    _DataFormatUrl = 'https://raw.githubusercontent.com/cthulhustig/autojimmy-data/main/map/dataformat.txt'
    _SnapshotCheckTimeout = 3 # Seconds
    _SnapshotDownloadTimeout = 60 # Seconds
    _SnapshotChunkSize = 10 * 1024 * 1024 # Bytes
    # NOTE: Pattern for matching data version treats the second digit as optional, if not specified it's
    # assumed to be 0. It also allows white space at the end to stop an easy typo in the snapshot breaking
    # all instances of the app everywhere
    _DataVersionPattern = re.compile(r'^(\d+)(?:\.(\d+))?\s*$')
    _MinDataFormatVersion = SnapshotDataFormat(4, 1)

    _instance = None # Singleton instance
    _lock = threading.RLock() # Recursive lock
    _installDir = None
    _overlayDir = None

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
                    # Check the overlay version and age, the overlay directory will be deleted if
                    # it's no longer valid
                    cls._instance._checkOverlayDataFormat()
                    cls._instance._checkOverlayAge()
        return cls._instance

    @staticmethod
    def setSectorDirs(
            installDir: str,
            overlayDir: str
            ) -> None:
        if SnapshotManager._instance:
            raise RuntimeError('You can\'t set the snapshot manager directories after the singleton has been initialised')
        SnapshotManager._installDir = installDir
        SnapshotManager._overlayDir = overlayDir

    def loadBinaryResource(self, filePath: str) -> bytes:
        return self._readResourceFile(
            relativeFilePath=filePath)

    def loadTextResource(self, filePath: str) -> bytes:
        return self._bytesToString(bytes=self._readResourceFile(
            relativeFilePath=filePath))

    def snapshotTimestamp(self) -> typing.Optional[datetime.datetime]:
        try:
            return SnapshotManager._parseTimestamp(
                data=self._readResourceFile(relativeFilePath=self._TimestampFileName))
        except Exception as ex:
            logging.error(f'Failed to read universe timestamp', exc_info=ex)
            return None

    def snapshotDataFormat(self) -> typing.Optional[SnapshotDataFormat]:
        try:
            return SnapshotManager._parseDataFormat(
                data=self._readResourceFile(relativeFilePath=self._DataFormatFileName))
        except Exception as ex:
            logging.error(f'Failed to read universe data format', exc_info=ex)
            return None

    # NOTE: This will block while it downloads the latest snapshot timestamp from the github repo
    def checkForNewSnapshot(self) -> SnapshotAvailability:
        currentTimestamp = self.snapshotTimestamp()
        try:
            with requests.get(
                    url=SnapshotManager._TimestampUrl,
                    timeout=SnapshotManager._SnapshotCheckTimeout
                    ) as response:
                repoTimestamp = SnapshotManager._parseTimestamp(data=response.content)
        except Exception as ex:
            raise RuntimeError(f'Failed to retrieve snapshot timestamp ({str(ex)})')

        if currentTimestamp and (repoTimestamp <= currentTimestamp):
            # No new snapshot available
            return SnapshotManager.SnapshotAvailability.NoNewSnapshot

        try:
            with requests.get(
                    url=SnapshotManager._DataFormatUrl,
                    timeout=SnapshotManager._SnapshotCheckTimeout
                    ) as response:
                repoDataFormat = SnapshotManager._parseDataFormat(data=response.content)
        except Exception as ex:
            raise RuntimeError(f'Failed to retrieve snapshot data format ({str(ex)})')

        if repoDataFormat < SnapshotManager._MinDataFormatVersion:
            # The repo contains data in an older format than the app is expecting. This should
            # only happen when running a dev branch
            return SnapshotManager.SnapshotAvailability.AppToNew

        # The data format is versioned such that the minor version increments should be backwards
        # compatible. If the major version is higher then the app is to old to use the data
        nextMajorVersion = SnapshotDataFormat(
            major=SnapshotManager._MinDataFormatVersion.major() + 1,
            minor=0)
        if repoDataFormat >= nextMajorVersion:
            return SnapshotManager.SnapshotAvailability.AppToOld

        return SnapshotManager.SnapshotAvailability.NewSnapshotAvailable

    def downloadSnapshot(
            self,
            progressCallback: typing.Optional[typing.Callable[[UpdateStage, int, int], typing.Any]] = None,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> None:
        with self._lock:
            logging.info('Downloading snapshot')
            if progressCallback:
                progressCallback(SnapshotManager.UpdateStage.DownloadStage, 0, 0)

            dataBuffer = io.BytesIO()
            with requests.get(
                    url=SnapshotManager._DataArchiveUrl,
                    timeout=SnapshotManager._SnapshotDownloadTimeout,
                    stream=True
                    ) as response:
                length = response.headers.get('content-length')
                length = int(length) if length else 0
                progress = 0
                for chunk in response.iter_content(chunk_size=SnapshotManager._SnapshotChunkSize):
                    if isCancelledCallback and isCancelledCallback():
                        return # Operation cancelled
                    dataBuffer.write(chunk)
                    progress += len(chunk)
                    progressCallback(
                        SnapshotManager.UpdateStage.DownloadStage,
                        progress,
                        length)

            logging.info('Extracting snapshot')
            if progressCallback:
                progressCallback(SnapshotManager.UpdateStage.ExtractStage, 0, 0)

            workingDirPath = SnapshotManager._makeWorkingDir(
                baseDirPath=self._overlayDir)
            zipData = zipfile.ZipFile(dataBuffer)
            fileInfoList = zipData.infolist()

            # Find the data format file to sanity check that the snapshot is compatible
            dataFormatPath = SnapshotManager._DataArchiveMapPath + SnapshotManager._DataFormatFileName
            dataFormatInfo = None
            for fileInfo in fileInfoList:
                if fileInfo.is_dir():
                    continue # Skip directories
                if fileInfo.filename == dataFormatPath:
                    dataFormatInfo = fileInfo
                    break

            if not dataFormatInfo:
                raise RuntimeError('Snapshot has no data format file')
            try:
                dataFormat = self._parseDataFormat(
                    data=zipData.read(dataFormatInfo.filename))
            except Exception as ex:
                raise RuntimeError(f'Unable to read snapshot data format file ({str(ex)})')
            if not dataFormat or not self._isDataFormatCompatible(dataFormat):
                raise RuntimeError(f'Snapshot is incompatible')

            extractIndex = 0
            for fileInfo in fileInfoList:
                if isCancelledCallback and isCancelledCallback():
                    return # Operation cancelled

                extractIndex += 1
                if progressCallback:
                    progressCallback(
                        SnapshotManager.UpdateStage.ExtractStage,
                        extractIndex,
                        len(fileInfoList))

                if fileInfo.is_dir():
                    continue # Skip directories
                if not fileInfo.filename.startswith(SnapshotManager._DataArchiveMapPath):
                    continue # Skip files not in the map directory

                subPath = fileInfo.filename[len(SnapshotManager._DataArchiveMapPath):]
                targetPath = os.path.join(workingDirPath, subPath)

                logging.info(f'Extracting {subPath}')
                directoryHierarchy = os.path.dirname(targetPath)
                if not os.path.exists(directoryHierarchy):
                    os.makedirs(directoryHierarchy, exist_ok=True)
                SnapshotManager._writeFile(
                    path=targetPath,
                    data=zipData.read(fileInfo.filename))

            logging.info('Replacing old snapshot')
            SnapshotManager._replaceDir(
                workingDirPath=workingDirPath,
                currentDirPath=self._overlayDir)

    def _checkOverlayDataFormat(self) -> None:
        if not os.path.exists(self._overlayDir):
            # If the overlay directory doesn't exist there is nothing to check
            return
        overlayDataFormat = self.snapshotDataFormat()
        if (overlayDataFormat is not None) and self._isDataFormatCompatible(checkFormat=overlayDataFormat):
            # The overlay data format meets the min requirements for this version of the app and
            # it's still within the same major version so it should be compatible
            return

        # The overlay is using an incompatible data format (either to old or to new), delete the
        # directory to fall back to the install data (which should always be valid)
        self._deleteOverlayDir()

    def _isDataFormatCompatible(
            self,
            checkFormat: SnapshotDataFormat
            ) -> bool:
        nextMajorVersion = SnapshotDataFormat(
            major=SnapshotManager._MinDataFormatVersion.major() + 1,
            minor=0)

        return (checkFormat >= SnapshotManager._MinDataFormatVersion) and \
            (checkFormat < nextMajorVersion)

    def _checkOverlayAge(self) -> None:
        if not os.path.exists(self._overlayDir):
            # If the overlay directory doesn't exist there is nothing to check
            return
        overlayTimestampPath = os.path.join(self._overlayDir, self._TimestampFileName)
        if not os.path.exists(overlayTimestampPath):
            # Overlay timestamp file doesn't exist, err on th side of caution and don't do anything
            logging.warning(f'Overlay timestamp file "{overlayTimestampPath}" not found')
            return

        installTimestampPath = os.path.join(self._installDir, self._TimestampFileName)
        if not os.path.exists(installTimestampPath):
            # Install timestamp file doesn't exist, err on th side of caution and don't do anything
            logging.warning(f'Install timestamp file "{installTimestampPath}" not found')
            return

        try:
            overlayTimestamp = SnapshotManager._parseTimestamp(
                data=SnapshotManager._readFile(path=overlayTimestampPath))
        except Exception as ex:
            logging.error(
                f'Failed to load overlay timestamp from "{overlayTimestampPath}"',
                exc_info=ex)
            return

        try:
            installTimestamp = SnapshotManager._parseTimestamp(
                data=SnapshotManager._readFile(path=installTimestampPath))
        except Exception as ex:
            logging.error(
                f'Failed to load install timestamp from "{installTimestampPath}"',
                exc_info=ex)
            return

        if overlayTimestamp >= installTimestamp:
            # The overlay data is newer (or equal) to the install timestamp so keep the overlay
            return

        # The overlay data is older than the install data so delete the overlay to fall back to
        # the install
        self._deleteOverlayDir()

    def _deleteOverlayDir(self) -> None:
        logging.info(f'Deleting overlay directory "{self._overlayDir}"')
        try:
            shutil.rmtree(self._overlayDir)
        except Exception as ex:
            logging.error(
                f'Failed to delete overlay directory "{self._overlayDir}"',
                exc_info=ex)

    def _readResourceFile(
            self,
            relativeFilePath: str
            ) -> bytes:
        # If the overlay directory exists load files from there, if not load from the
        # install directory. This approach allows for files to be deleted (or renamed
        # in an overlay (compared to checking if the file exists in the overlay
        # directory and loading it from the install dir if it doesn't). This is important
        # as sectors can be renamed/deleted
        filePath = os.path.join(
            self._overlayDir if os.path.isdir(self._overlayDir) else self._installDir,
            relativeFilePath)
        return SnapshotManager._readFile(path=filePath)

    @staticmethod
    def _readFile(path: str) -> bytes:
        with open(path, 'rb') as file:
            return file.read()

    @staticmethod
    def _writeFile(
            path: str,
            data: typing.Union[bytes, str]
            ) -> None:
        if not isinstance(data, bytes):
            data = data.encode()

        with open(path, 'wb') as file:
            file.write(data)

    @staticmethod
    def _bytesToString(bytes: bytes) -> str:
        return bytes.decode('utf-8-sig') # Use utf-8-sig to strip BOM from unicode files

    @staticmethod
    def _parseTimestamp(data: bytes) -> datetime.datetime:
        timestamp = datetime.datetime.strptime(
            SnapshotManager._bytesToString(data),
            SnapshotManager._TimestampFormat)
        return timestamp.replace(tzinfo=datetime.timezone.utc)

    @staticmethod
    def _formatTimestamp(timestamp: datetime.datetime) -> bytes:
        timestamp = timestamp.astimezone(datetime.timezone.utc)
        return timestamp.strftime(SnapshotManager._TimestampFormat).encode()

    # NOTE: The data format is a major.minor version number with the minor number
    # being optional (assumed 0 if not present)
    @staticmethod
    def _parseDataFormat(data: bytes) -> SnapshotDataFormat:
        result = SnapshotManager._DataVersionPattern.match(
            SnapshotManager._bytesToString(data))
        if not result:
            raise RuntimeError('Invalid data format')
        major = result.group(1)
        minor = result.group(2)
        return SnapshotDataFormat(
            major=int(major),
            minor=int(minor) if minor else 0)

    @staticmethod
    def _makeWorkingDir(baseDirPath: str) -> str:
        workingDir = baseDirPath + '_working'
        if os.path.exists(workingDir):
            # Delete any previous working directory that may have been left kicking about
            shutil.rmtree(workingDir)
        os.makedirs(workingDir)
        return workingDir

    @staticmethod
    def _replaceDir(
            workingDirPath: str,
            currentDirPath: str
            ) -> None:
        oldDirPath = None
        if os.path.exists(currentDirPath):
            oldDirPath = currentDirPath + '_old'
            if os.path.exists(oldDirPath):
                shutil.rmtree(oldDirPath)
            os.rename(currentDirPath, oldDirPath)

        try:
            os.rename(workingDirPath, currentDirPath)
        except Exception:
            if oldDirPath:
                os.rename(oldDirPath, currentDirPath)
            raise
