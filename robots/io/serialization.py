import construction
import logging
import json
import robots
import traveller
import typing

def serialiseComponents(
        robot: robots.Robot
        ) -> typing.Iterable[typing.Mapping[str, typing.Any]]:
    components: typing.List[robots.RobotComponentInterface] = []
    for stage in robot.stages():
        if stage.phase() in robots.InternalConstructionPhases:
            continue # Don't write internal phases
        components.extend(stage.components())
    return construction.serialiseComponentList(components=components)

def deserialiseComponents(
        robot: robots.Robot,
        componentData: typing.Iterable[typing.Mapping[str, typing.Any]]
        ) -> typing.Mapping[str, typing.Any]:
    components = construction.deserialiseComponentList(
        components=componentData)
    robot.loadComponents(components=components)

def serialiseRobot(
        robot: robots.Robot,
        ) -> typing.Mapping[str, typing.Any]:
    return {
        'name': robot.robotName(),
        'techLevel': robot.techLevel(),
        'weaponSet': robot.weaponSet().name,
        'components': serialiseComponents(robot=robot),
        'notes': json.dumps(robot.userNotes()) # This is user entered content so use dumps to escape it
    }

def deserialiseRobot(
        data: typing.Mapping[str, typing.Any],
        inPlace: typing.Optional[robots.Robot] = None,
        ) -> robots.Robot:
    robotName = data.get('name')
    if robotName == None:
        raise RuntimeError('Robot data is missing the name element')

    techLevel = data.get('techLevel')
    if techLevel == None:
        raise RuntimeError('Robot data is missing the techLevel element')
    techLevel = int(techLevel)

    weaponSet = data.get('weaponSet')
    if weaponSet:
        try:
            weaponSet = traveller.StockWeaponSet[weaponSet]
        except Exception:
            logging.warning(f'Ignoring unknown weapon set \'{weaponSet}\' when loading robot \'{robot.robotName()}\'')
    if not weaponSet:
        weaponSet = traveller.StockWeaponSet.CSC2023    

    if inPlace:
        inPlace.setRobotName(name=robotName)
        inPlace.setTechLevel(techLevel=techLevel, regenerate=True) # Only regenerate on last step
        inPlace.setWeaponSet(weaponSet=weaponSet)
        robot = inPlace
    else:
        robot = robots.Robot(
            name=robotName,
            techLevel=techLevel,
            weaponSet=weaponSet)

    components = data.get('components')
    if components:
        deserialiseComponents(
            robot=robot,
            componentData=components)

    notes = data.get('notes')
    if notes:
        robot.setUserNotes(notes=json.loads(notes)) # Unescape string when loading

    return robot

def writeRobot(
        robot: robots.Robot,
        filePath: str
        ) -> None:
    data = serialiseRobot(robot=robot)
    with open(filePath, 'w', encoding='UTF8') as file:
        json.dump(data, file, indent=4)

def readRobot(
        filePath: str,
        inPlace: typing.Optional[robots.Robot] = None
        ) -> robots.Robot:
    with open(filePath, 'r') as file:
        return deserialiseRobot(
            data=json.load(file),
            inPlace=inPlace)
