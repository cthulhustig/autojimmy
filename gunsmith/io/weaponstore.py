import construction
import gunsmith
import threading
import typing


class WeaponStore(object):
    _instance = None # Singleton instance
    _store = None
    _userDir = None
    _exampleDir = None
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
                    cls._store = construction.ConstructableStore(
                        typeString='Weapon',
                        readFileFn=gunsmith.readWeapon,
                        writeFileFn=gunsmith.writeWeapon,
                        userDir=WeaponStore._userDir,
                        exampleDir=WeaponStore._exampleDir)
        return cls._instance

    @staticmethod
    def setWeaponDirs(
            userDir: str,
            exampleDir: typing.Optional[str]
            ) -> None:
        if WeaponStore._instance:
            raise RuntimeError('Unable to set WeaponStore directories after singleton has been initialised')
        WeaponStore._userDir = userDir
        WeaponStore._exampleDir = exampleDir

    def constructableStore(self) -> construction.ConstructableStore:
        return WeaponStore._store

    def loadWeapons(
            self,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> None:
        WeaponStore._store.loadData(progressCallback=progressCallback)

    def allWeapons(self) -> typing.Iterable[gunsmith.Weapon]:
        return WeaponStore._store.constructables()

    def isStored(
            self,
            weapon: gunsmith.Weapon
            ) -> bool:
        return WeaponStore._store.isStored(constructable=weapon)

    def isReadOnly(
            self,
            weapon: gunsmith.Weapon
            ) -> bool:
        return WeaponStore._store.isReadOnly(constructable=weapon)

    def hasWeapon(
            self,
            weaponName: str
            ) -> bool:
        return WeaponStore._store.exists(name=weaponName)

    def newWeapon(
            self,
            weaponType: gunsmith.WeaponType,
            weaponName: str,
            techLevel: int
            ) -> gunsmith.Weapon:
        weapon = gunsmith.Weapon(
            weaponType=weaponType,
            name=weaponName,
            techLevel=techLevel)
        WeaponStore._store.add(constructable=weapon)
        return weapon

    def addWeapon(
            self,
            weapon: gunsmith.Weapon
            ) -> None:
        WeaponStore._store.add(constructable=weapon)

    def saveWeapon(
            self,
            weapon: gunsmith.Weapon
            ) -> None:
        WeaponStore._store.save(constructable=weapon)

    def deleteWeapon(
            self,
            weapon: gunsmith.Weapon
            ) -> None:
        WeaponStore._store.delete(constructable=weapon)

    def revertWeapon(
            self,
            weapon: gunsmith.Weapon
            ) -> None:
        WeaponStore._store.revert(constructable=weapon)

    def copyWeapon(
            self,
            weapon: gunsmith.Weapon,
            newWeaponName: str
            ) -> gunsmith.Weapon:
        return WeaponStore._store.copy(
            constructable=weapon,
            newConstructableName=newWeaponName)
