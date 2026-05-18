import astronomer
import azathoth
import typing

class EditableSector(astronomer.Sector):
    def __init__(
            self,
            entity: str,
            isCustom: bool,
            milieu: astronomer.Milieu,
            position: astronomer.SectorPosition,
            name: str,
            alternateNames: typing.Optional[typing.Iterable[str]] = None,
            abbreviation: typing.Optional[str] = None,
            sectorLabel: typing.Optional[str] = None,
            subsectorNames: typing.Optional[typing.Mapping[str, str]] = None,
            worlds: typing.Optional[typing.Iterable[astronomer.World]] = None,
            allegiances: typing.Optional[typing.Iterable[astronomer.Allegiance]] = None,
            sophonts: typing.Optional[typing.Iterable[astronomer.Sophont]] = None,
            routes: typing.Optional[typing.Iterable[astronomer.Route]] = None,
            borders: typing.Optional[typing.Iterable[astronomer.Border]] = None,
            regions: typing.Optional[typing.Iterable[astronomer.Region]] = None,
            labels: typing.Optional[typing.Iterable[astronomer.Label]] = None,
            selected: bool = False,
            tagging: typing.Optional[astronomer.SectorTagging] = None,
            credits: typing.Optional[str] = None,
            source: typing.Optional[astronomer.SectorSource] = None,
            products: typing.Optional[typing.Iterable[astronomer.SectorSource]] = None
            ) -> None:
        super().__init__(
            entityId=entity,
            isCustom=isCustom,
            milieu=milieu,
            position=position,
            name=name,
            alternateNames=alternateNames,
            abbreviation=abbreviation,
            sectorLabel=sectorLabel,
            subsectorNames=subsectorNames,
            worlds=worlds,
            allegiances=allegiances,
            sophonts=sophonts,
            routes=routes,
            borders=borders,
            regions=regions,
            labels=labels,
            selected=selected,
            tagging=tagging,
            credits=credits,
            source=source,
            products=products)

        for world in self._worlds:
            assert(isinstance(world, azathoth.EditableWorld))
            world.setSectorId(sectorId=self._entityId)

        for border in self._borders:
            assert(isinstance(border, azathoth.EditableBorder))
            border.setSectorId(sectorId=self._entityId)

        for regions in self._regions:
            assert(isinstance(regions, azathoth.EditableRegion))
            regions.setSectorId(sectorId=self._entityId)

        for route in self._routes:
            assert(isinstance(route, azathoth.EditableRoute))
            route.setSectorId(sectorId=self._entityId)

        for label in self._labels:
            assert(isinstance(label, azathoth.EditableLabel))
            label.setSectorId(sectorId=self._entityId)