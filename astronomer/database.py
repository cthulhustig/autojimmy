import astronomer
import logging
import multiverse
import typing

def loadUniverseFromDatabase(
        universeId: str,
        placeholderMilieu: typing.Optional[astronomer.Milieu] = None,
        entityFactory: typing.Optional[astronomer.EntityFactoryInterface] = None,
        progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
        ) -> astronomer.Universe:
    if entityFactory is None:
        entityFactory = astronomer.DefaultEntityFactory()

    universeInfo = multiverse.UniverseManager.instance().universeInfo(
        universeId=universeId)
    if not universeInfo:
        raise ValueError(f'Unknown universe "{universeId}"')

    logging.info(f'Loaded universe {universeId} ({universeInfo.name()})')

    customSectors = set()
    if not universeInfo.isStock():
        sectorInfos = multiverse.UniverseManager.instance().sectorInfos(
            universeId=universeId)
        for sectorInfo in sectorInfos:
            fromStockData = sectorInfo.stockDataHash() is not None
            isModified = sectorInfo.modifiedTimestamp() is not None
            if fromStockData and isModified:
                customSectors.add(sectorInfo.id())

    # NOTE: Using a generator is important as it means converting
    # each db sector to an astronomer sector is included in the
    # progress tick for that sector rather than the progress just
    # covering loading the sectors then a long pause at the end
    # while it converts them all to astronomer sectors.
    dbSectorGenerator = multiverse.UniverseManager.instance().yieldSectors(
        universeId=universeId,
        progressCallback=progressCallback)
    sectors = []
    for dbSector in dbSectorGenerator:
        try:
            sector = astronomer.convertDbSectorToAstronomerSector(
                dbSector=dbSector,
                isCustom=dbSector.id() in customSectors,
                entityFactory=entityFactory)
            sectors.append(sector)

            logging.debug(
                'Loaded {worlds} worlds for sector {name} at ({x}, {y}) from {milieu}'.format(
                    worlds=sector.worldCount(),
                    name=sector.name(),
                    x=sector.position().sectorX(),
                    y=sector.position().sectorY(),
                    milieu=sector.milieu().value))
        except Exception as ex:
            logging.error(
                'Failed to load sector {name} at ({x}, {y}) from {milieu.value}'.format(
                    name=sector.name(),
                    x=sector.position().sectorX(),
                    y=sector.position().sectorY(),
                    milieu=sector.milieu().value),
                exc_info=ex)
            continue

    return entityFactory.createUniverse(
        universeId=universeId,
        sectors=sectors,
        placeholderMilieu=placeholderMilieu)