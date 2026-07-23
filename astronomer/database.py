import astronomer
import logging
import multiverse
import typing

def loadUniverseFromDatabase(
        universeId: str,
        entityFactory: typing.Optional[astronomer.EntityFactoryInterface] = None,
        progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
        ) -> astronomer.Universe:
    if entityFactory is None:
        entityFactory = astronomer.DefaultEntityFactory()

    universeInfo = multiverse.UniverseManager.instance().universeInfoById(
        id=universeId)
    if not universeInfo:
        raise ValueError(f'Unknown universe {universeId!r}')

    logging.info(f'Loaded universe {universeId!r} ({universeInfo.name()})')

    milieu = multiverse.UniverseManager.instance().universeMilieu(id=universeId)
    try:
        milieu = astronomer.Milieu[milieu]
    except:
        raise ValueError(f'Universe {universeId!r} has unknown milieu {milieu!r}')

    # NOTE: Using a generator is important as it means converting
    # each db sector to an astronomer sector is included in the
    # progress tick for that sector rather than the progress just
    # covering loading the sectors then a long pause at the end
    # while it converts them all to astronomer sectors.
    dbSectorGenerator = multiverse.UniverseManager.instance().yieldSectors(
        id=universeId,
        progressCallback=progressCallback)
    sectors = []
    for dbSector in dbSectorGenerator:
        try:
            sector = astronomer.convertDbSectorToAstronomerSector(
                dbSector=dbSector,
                entityFactory=entityFactory)
            sectors.append(sector)

            logging.debug(
                'Loaded {worlds} worlds for sector {name!r} at ({x}, {y})'.format(
                    worlds=sector.worldCount(),
                    name=sector.name(),
                    x=sector.position().sectorX(),
                    y=sector.position().sectorY()))
        except Exception as ex:
            logging.error(
                'Failed to load sector {name!r} at ({x}, {y})'.format(
                    name=dbSector.name(),
                    x=dbSector.sectorX(),
                    y=dbSector.sectorY()),
                exc_info=ex)
            continue

    return entityFactory.createUniverse(
        universeId=universeId,
        milieu=milieu,
        sectors=sectors)