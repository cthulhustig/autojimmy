import logic
import json
import packaging
import packaging.version
import traveller
import travellermap
import typing

class JumpRoute(object):
    def __init__(
            self,
            nodes: typing.Sequence[typing.Tuple[
                travellermap.HexPosition,
                typing.Optional[traveller.World]]]
            ) -> None:
        if not nodes:
            raise ValueError('A jump route can\'t have an empty nodes list')
        self._nodes = list(nodes)

        # The total parsecs calculation is done on demand as it's not often used and is relatively
        # expensive to calculate
        self._totalParsecs = None

    def jumpCount(self) -> int:
        return len(self._nodes) - 1

    def nodeCount(self) -> int:
        return len(self._nodes)

    def node(self, index) -> typing.Tuple[
            travellermap.HexPosition,
            typing.Optional[traveller.World]]:
        return self._nodes[index]

    def startNode(self) -> typing.Tuple[
            travellermap.HexPosition,
            typing.Optional[traveller.World]]:
        return self._nodes[0]

    def finishNode(self) -> typing.Tuple[
            travellermap.HexPosition,
            typing.Optional[traveller.World]]:
        return self._nodes[-1]

    def hex(self, index: int) -> travellermap.HexPosition:
        return self._nodes[index][0]

    def startHex(self) -> travellermap.HexPosition:
        return self._nodes[0][0]

    def finishHex(self) -> travellermap.HexPosition:
        return self._nodes[-1][0]

    def world(self, index: int) -> typing.Optional[traveller.World]:
        return self._nodes[index][1]

    def startWorld(self) -> typing.Optional[traveller.World]:
        return self._nodes[0][1]

    def finishWorld(self) -> typing.Optional[traveller.World]:
        return self._nodes[-1][1]

    def nodeParsecs(self, index: int) -> int:
        parsecs = 0
        for current in range(0, self.jumpCount()):
            if current >= index:
                break
            fromHex = self._nodes[current][0]
            toHex = self._nodes[current + 1][0]
            parsecs += fromHex.parsecsTo(toHex)
        return parsecs

    def totalParsecs(self) -> int:
        if self._totalParsecs == None:
            self._totalParsecs = self.nodeParsecs(index=len(self._nodes) - 1)
        return self._totalParsecs

    def __getitem__(self, index: int) -> typing.Tuple[
            travellermap.HexPosition,
            typing.Optional[traveller.World]]:
        return self._nodes.__getitem__(index)

    def __iter__(self) -> typing.Iterator[typing.Tuple[
            travellermap.HexPosition,
            typing.Optional[traveller.World]]]:
        return self._nodes.__iter__()

    def __next__(self) -> typing.Any:
        return self._nodes.__next__()

    def __len__(self) -> int:
        return self._nodes.__len__()

#
# Serialisation
#
_DefaultVersion = packaging.version.Version('1.0')

# Version 2.0 switched from world based to hex based jump routes as part of
# the work for dead space routing
_CurrentVersion = packaging.version.Version('2.0')

def _serialiseNode(
        node: typing.Tuple[
            travellermap.HexPosition,
            typing.Optional[traveller.World]]
        ) -> typing.Mapping[str, typing.Any]:
    pos, world = node

    data = {'absoluteX': pos.absoluteX(),
            'absoluteY': pos.absoluteY()}

    # Include the sector hex as it could be useful to users. It's a best effort
    # thing, if the hex can't be resolved to a sector hex we don't barf
    try:
        data['sectorHex'] = \
            world.sectorHex() \
            if world else \
            traveller.WorldManager.instance().positionToSectorHex(pos=pos)
    except:
        pass

    return data

def _deserialiseNode(
        data: typing.Mapping[str, typing.Any]
        ) -> typing.Tuple[
            travellermap.HexPosition,
            typing.Optional[traveller.World]]:
    absoluteX = data.get('absoluteX')
    absoluteY = data.get('absoluteY')
    if absoluteX != None and absoluteY == None:
        raise RuntimeError('Node is missing absoluteY property')
    if absoluteX == None and absoluteY != None:
        raise RuntimeError('Node is missing absoluteX property')

    if absoluteX != None and absoluteY != None:
        if not isinstance(absoluteX, int):
            raise RuntimeError('Node absoluteX property is not a integer')
        if not isinstance(absoluteY, int):
            raise RuntimeError('Node absoluteX property is not a integer')
        return (
            travellermap.HexPosition(absoluteX=absoluteX, absoluteY=absoluteY),
            traveller.WorldManager.instance().worldByPosition(pos=pos))

    sectorHex = data.get('sectorHex')
    if sectorHex != None:
        if not isinstance(sectorHex, str):
            raise RuntimeError('Node sectorHex property is not a string')
        try:
            pos = traveller.WorldManager.instance().sectorHexToPosition(sectorHex=sectorHex)
            return (
                pos,
                traveller.WorldManager.instance().worldByPosition(pos=pos))
        except:
            raise RuntimeError(f'Node sector hex "{sectorHex}" couldn\'t be resolved to a hex')

    raise RecursionError('Node as no absoluteX/absoluteY or sectorHex properties')

def serialiseJumpRoute(
        jumpRoute: JumpRoute
        ) -> typing.Mapping[str, typing.Any]:
    return {
        'version': str(_CurrentVersion),
        'hexes': [_serialiseNode(node=node) for node in jumpRoute]}

def deserialiseJumpRoute(
        data: typing.Mapping[str, typing.Any]
        ) -> JumpRoute:
    version = data.get('version')
    if version == None:
        # There was no version number in original format
        version = str(_DefaultVersion)
    if not isinstance(version, str):
        raise RuntimeError('Jump route version property is not a string')
    try:
        version = packaging.version.Version(version)
    except Exception:
        raise RuntimeError(f'Jump route version property "{version}" could not be parsed')

    if version.major == 1:
        worlds = logic.deserialiseWorldList(data)
        nodes = [(world.hex(), world) for world in worlds]
    elif version.major == 2:
        hexes = data.get('hexes')
        if hexes == None:
            raise RuntimeError('Jump route has no hexes property')
        if not isinstance(hexes, list):
            raise RuntimeError('Jump route hexes property is not a list')
        nodes = [_deserialiseNode(data=data) for data in hexes]
    else:
        raise RuntimeError(f'Unsupported file format {version}')

    return logic.JumpRoute(notes=nodes)

def writeJumpRoute(
        jumpRoute: JumpRoute,
        filePath: str
        ) -> None:
    with open(filePath, 'w', encoding='UTF8') as file:
        json.dump(serialiseJumpRoute(jumpRoute=jumpRoute), file, indent=4)

def readJumpRoute(filePath: str) -> JumpRoute:
    with open(filePath, 'r') as file:
        return deserialiseJumpRoute(data=json.load(file))
