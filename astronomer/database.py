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

    dbAllegiances = multiverse.UniverseManager.instance().allegiances(id=universeId)
    allegiances: typing.List[astronomer.Allegiance] = []
    for dbAllegiance in dbAllegiances:
        try:
            allegiance = astronomer.convertDbAllegianceToAstronomerAllegiance(
                dbAllegiance=dbAllegiance,
                entityFactory=entityFactory)
            allegiances.append(allegiance)
        except Exception as ex:
            logging.error(
                'Failed to load allegiance {name!r}'.format(
                    name=dbAllegiance.name()),
                exc_info=ex)
            continue

    dbSophonts = multiverse.UniverseManager.instance().sophonts(id=universeId)
    sophonts: typing.List[astronomer.Allegiance] = []
    for dbSophont in dbSophonts:
        try:
            sophont = astronomer.convertDbSophontToAstronomerSophont(
                dbSophont=dbSophont,
                entityFactory=entityFactory)
            sophonts.append(sophont)
        except Exception as ex:
            logging.error(
                'Failed to load sophont {name!r}'.format(
                    name=dbSophont.name()),
                exc_info=ex)
            continue

    # NOTE: Using a generator is important as it means converting
    # each db sector to an astronomer sector is included in the
    # progress tick for that sector rather than the progress just
    # covering loading the sectors then a long pause at the end
    # while it converts them all to astronomer sectors.
    dbSectorGenerator = multiverse.UniverseManager.instance().yieldSectors(
        id=universeId,
        progressCallback=progressCallback)
    sectors: typing.List[astronomer.Sector] = []
    for dbSector in dbSectorGenerator:
        try:
            sector = astronomer.convertDbSectorToAstronomerSector(
                dbSector=dbSector,
                astroAllegiances=allegiances,
                astroSophonts=sophonts,
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

    dbLabels = multiverse.UniverseManager.instance().mapLabels(id=universeId)
    labels: typing.List[astronomer.MapLabel] = []
    for dbLabel in dbLabels:
        try:
            label = astronomer.convertDbMapLabelToAstronomerMapLabel(
                dbLabel=dbLabel,
                entityFactory=entityFactory)
            labels.append(label)
        except Exception as ex:
            logging.error(
                'Failed to load label {name!r} at ({x}, {y})'.format(
                    name=dbLabel.text(),
                    x=dbLabel.worldX(),
                    y=dbLabel.worldY()),
                exc_info=ex)
            continue

    dbVectors = multiverse.UniverseManager.instance().mapVectors(id=universeId)
    vectors: typing.List[astronomer.MapVector] = []
    for dbVector in dbVectors:
        try:
            vector = astronomer.convertDbMapVectorToAstronomerMapVector(
                dbVector=dbVector,
                entityFactory=entityFactory)
            vectors.append(vector)
        except Exception as ex:
            logging.error(
                'Failed to load vector {name!r}'.format(
                    name=dbVector.id()),
                exc_info=ex)
            continue

    # TODO: This needs done differently when I've finished detaching systems
    # from sectors
    worlds = []
    for sector in sectors:
        worlds.extend(sector.worlds())

    return entityFactory.createUniverse(
        universeId=universeId,
        milieu=milieu,
        allegiances=allegiances,
        sophonts=sophonts,
        sectors=sectors,
        worlds=worlds,
        labels=labels,
        vectors=vectors)