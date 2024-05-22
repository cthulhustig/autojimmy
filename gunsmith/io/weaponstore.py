import copy
import gunsmith
import logging
import os
import threading
import typing
import uuid

class _WeaponMetadata(object):
    def __init__(
            self,
            filePath: typing.Optional[str],
            readOnly: bool
            ) -> None:
        self._filePath = filePath
        self._readOnly = readOnly

    def filePath(self) -> typing.Optional[str]:
        return self._filePath

    def readOnly(self) -> bool:
        return self._readOnly

class WeaponStore(object):
    _instance = None # Singleton instance
    _userWeaponDir = None
    _exampleWeaponDir = None
    _weaponMap: typing.Dict[gunsmith.Weapon, _WeaponMetadata] = {}
    _lock = threading.Lock()

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
    def setWeaponDirs(
            userWeaponDir: str,
            exampleWeaponDir: typing.Optional[str]
            ) -> None:
        if WeaponStore._instance:
            raise RuntimeError('Unable to set WeaponStore directories after singleton has been initialised')
        WeaponStore._userWeaponDir = userWeaponDir
        WeaponStore._exampleWeaponDir = exampleWeaponDir

    def loadWeapons(
            self,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> None:
        if not WeaponStore._userWeaponDir:
            raise RuntimeError('Unable to load weapons (Weapon user weapon directory not set)')

        self._weaponMap.clear()

        userWeaponFiles = self._findWeaponFiles(self._userWeaponDir)
        exampleWeaponFiles = []
        if self._exampleWeaponDir:
            exampleWeaponFiles = self._findWeaponFiles(self._exampleWeaponDir)

        weaponIndex = 0
        weaponCount = len(userWeaponFiles) + len(exampleWeaponFiles)

        for filePath in userWeaponFiles:
            try:
                if progressCallback:
                    progressCallback(os.path.basename(filePath), weaponIndex, weaponCount)
                weaponIndex += 1

                weapon = gunsmith.readWeapon(filePath=filePath)
                self._weaponMap[weapon] = _WeaponMetadata(
                    filePath=filePath,
                    readOnly=False)
            except Exception as ex:
                logging.error(f'Weapon store failed to load user weapon from file "{filePath}"', exc_info=ex)

        for filePath in exampleWeaponFiles:
            try:
                if progressCallback:
                    progressCallback(os.path.basename(filePath), weaponIndex, weaponCount)
                weaponIndex += 1

                weapon = gunsmith.readWeapon(filePath=filePath)
                self._weaponMap[weapon] = _WeaponMetadata(
                    filePath=filePath,
                    readOnly=True)
            except Exception as ex:
                logging.error(f'Weapon store failed to load example weapon from file "{filePath}"', exc_info=ex)

        if progressCallback:
            # Force 100% progress notification
            progressCallback('Complete', weaponCount, weaponCount)

    def weapons(self) -> typing.Iterable[gunsmith.Weapon]:
        with self._lock:
            return list(self._weaponMap.keys())

    def isStored(
            self,
            weapon: gunsmith.Weapon
            ) -> bool:
        metadata = self._weaponMap.get(weapon)
        return metadata != None and metadata.filePath() != None

    def isReadOnly(
            self,
            weapon: gunsmith.Weapon
            ) -> bool:
        metadata = self._weaponMap.get(weapon)
        return metadata != None and metadata.readOnly()

    def hasWeapon(
            self,
            weaponName: str
            ) -> bool:
        with self._lock:
            for weapon in self._weaponMap.keys():
                if weaponName == weapon.weaponName():
                    return True
        return False

    def newWeapon(
            self,
            weaponType: gunsmith.WeaponType,
            weaponName: str,
            techLevel: int
            ) -> gunsmith.Weapon:
        weapon = gunsmith.Weapon(
            weaponType=weaponType,
            weaponName=weaponName,
            techLevel=techLevel)
        with self._lock:
            self._weaponMap[weapon] = _WeaponMetadata(
                filePath=None, # Not saved yet
                readOnly=False)
        return weapon

    def addWeapon(
            self,
            weapon: gunsmith.Weapon
            ) -> None:
        with self._lock:
            if weapon in self._weaponMap:
                return # Weapon is already in the store so nothing to do

            self._weaponMap[weapon] = _WeaponMetadata(
                filePath=None, # Not saved yet
                readOnly=False)

    def saveWeapon(
            self,
            weapon: gunsmith.Weapon
            ) -> None:
        with self._lock:
            metadata = self._weaponMap.get(weapon)
            if not metadata:
                raise RuntimeError(f'Unable to save "{weapon.weaponName()}" (Unknown Weapon)')
            
            if metadata.readOnly():
                raise RuntimeError(f'Unable to save "{weapon.weaponName()}" (weapon is read-only)')

            filePath = None
            if metadata:
                filePath = metadata.filePath()
            if not filePath:
                # Generate a filename for the weapon
                filePath = self._generateUserFilePath()

            if not os.path.exists(self._userWeaponDir):
                os.makedirs(self._userWeaponDir)
            gunsmith.writeWeapon(
                weapon=weapon,
                filePath=filePath)

            # Update the WeaponStores map after the file has been written
            self._weaponMap[weapon] = _WeaponMetadata(
                filePath=filePath,
                readOnly=False)

    def deleteWeapon(
            self,
            weapon: gunsmith.Weapon
            ) -> None:
        with self._lock:
            metadata = self._weaponMap.get(weapon)
            if not metadata:
                raise RuntimeError(f'Unable to delete "{weapon.weaponName()}" (Unknown weapon)')

            if metadata.readOnly():
                raise RuntimeError(f'Unable to delete "{weapon.weaponName()}" (Weapon is read-only)')

            if metadata.filePath():
                os.remove(path=metadata.filePath())
            del self._weaponMap[weapon]

    def revertWeapon(
            self,
            weapon: gunsmith.Weapon
            ) -> None:
        with self._lock:
            metadata = self._weaponMap.get(weapon)
            if not metadata:
                raise RuntimeError(f'Unable to revert "{weapon.weaponName()}" (Unknown weapon)')

            filePath = metadata.filePath()
            if filePath:
                gunsmith.readWeapon(filePath=filePath, inPlace=weapon)

    def copyWeapon(
            self,
            weapon: gunsmith.Weapon,
            newWeaponName: str
            ) -> gunsmith.Weapon:
        with self._lock:
            metadata = self._weaponMap.get(weapon)
            if not metadata:
                raise RuntimeError(f'Unable to copy "{weapon.weaponName()}" (Unknown weapon)')

            newWeapon = copy.deepcopy(weapon)
            newWeapon.setWeaponName(name=newWeaponName)
            self._weaponMap[newWeapon] = _WeaponMetadata(
                filePath=None, # Copied weapon hasn't been saved yet
                readOnly=False) # Copied weapons are writable even when copied from read only weapons

            return newWeapon

    def _generateUserFilePath(self) -> str:
        fileName = str(uuid.uuid4()) + '.json'
        return os.path.join(self._userWeaponDir, fileName)

    def _findWeaponFiles(
            self,
            searchDir: str,
            ) -> typing.Iterable[str]:
        if os.path.exists(searchDir):
            return [os.path.join(searchDir, x) for x in os.listdir(searchDir) if x.endswith(".json")]
        else:
            return []
