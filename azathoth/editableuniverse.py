import astronomer
import azathoth
import common
import typing

class EditableUniverse(astronomer.Universe):
    def __init__(
            self,
            universeId: str,
            milieu: astronomer.Milieu,
            allegiances: typing.Collection[astronomer.Allegiance],
            sophonts: typing.Collection[astronomer.Sophont],
            sectors: typing.Collection[astronomer.Sector],
            worlds: typing.Collection[astronomer.World],
            routes: typing.Collection[astronomer.Route],
            labels: typing.Collection[astronomer.MapLabel],
            vectors: typing.Collection[astronomer.MapVector]
            ) -> None:
        super().__init__(
            universeId=universeId,
            milieu=milieu,
            allegiances=allegiances,
            sophonts=sophonts,
            sectors=sectors,
            worlds=worlds,
            routes=routes,
            labels=labels,
            vectors=vectors)

    def insertSector(
            self,
            sector: azathoth.EditableSector,
            worlds: typing.Optional[typing.Collection[azathoth.EditableWorld]]
            ) -> None:
        common.validateObject(name='sector', value=sector, objectType=azathoth.EditableSector, allowNone=False)
        common.validateCollection(name='worlds', value=worlds, elementType=azathoth.EditableWorld, allowNone=True)

        self.deleteSector(sector.position())

        self._addSector(sector)
        if worlds:
            for world in worlds:
                self._addWorld(world)

    def deleteSector(
            self,
            sectorPos: astronomer.SectorPosition
            ) -> None:
        common.validateObject(name='sectorPos', value=sectorPos, objectType=astronomer.SectorPosition, allowNone=False)

        sector = self.sectorByPosition(sectorPos)
        if sector:
            self._removeSector(sector)

        worlds = self.worldsInSector(sectorPos)
        if worlds:
            for world in worlds:
                self._removeWorld(world)