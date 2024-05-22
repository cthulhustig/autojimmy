import construction
import robots
import threading
import traveller
import typing


class RobotStore(object):
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
                        typeString='Robot',
                        readFileFn=robots.readRobot,
                        writeFileFn=robots.writeRobot,
                        userDir=RobotStore._userDir,
                        exampleDir=RobotStore._exampleDir)
        return cls._instance

    @staticmethod
    def setRobotDirs(
            userDir: str,
            exampleDir: typing.Optional[str]
            ) -> None:
        if RobotStore._instance:
            raise RuntimeError('Unable to set RobotStore directories after singleton has been initialised')
        RobotStore._userDir = userDir
        RobotStore._exampleDir = exampleDir

    def loadRobots(
            self,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> None:
        RobotStore._store.loadData(progressCallback=progressCallback)

    def allRobots(self) -> typing.Iterable[robots.Robot]:
        return RobotStore._store.constructables()

    def isStored(
            self,
            robot: robots.Robot
            ) -> bool:
        return RobotStore._store.isStored(constructable=robot)

    def isReadOnly(
            self,
            robot: robots.Robot
            ) -> bool:
        return RobotStore._store.isReadOnly(constructable=robot)

    def hasRobot(
            self,
            robotName: str
            ) -> bool:
        return RobotStore._store.exists(name=robotName)

    def newRobot(
            self,
            robotName: str,
            techLevel: int,
            weaponSet: traveller.StockWeaponSet,            
            ) -> robots.Robot:
        robot = robots.Robot(
            robotName=robotName,
            techLevel=techLevel,
            weaponSet=weaponSet)
        RobotStore._store.add(constructable=robot)
        return robot

    def addRobot(
            self,
            robot: robots.Robot
            ) -> None:
        RobotStore._store.add(constructable=robot)

    def saveRobot(
            self,
            robot: robots.Robot
            ) -> None:
        RobotStore._store.save(constructable=robot)

    def deleteRobot(
            self,
            robot: robots.Robot
            ) -> None:
        RobotStore._store.delete(constructable=robot)

    def revertRobot(
            self,
            robot: robots.Robot
            ) -> None:
        RobotStore._store.revert(constructable=robot)

    def copyRobot(
            self,
            robot: robots.Robot,
            newRobotName: str
            ) -> robots.Robot:
        return RobotStore._store.copy(
            constructable=robot,
            newConstructableName=newRobotName)
