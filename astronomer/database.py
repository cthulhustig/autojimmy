import astronomer
import logging
import multiverse
import typing

# TODO: Progress is currently broken
_ProgressStageCount = 6
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

    logging.info('Loading universe {name!r} ({id})'.format(
        name=universeInfo.name(),
        id=universeInfo.id()))

    milieu = multiverse.UniverseManager.instance().universeMilieu(id=universeId)
    try:
        milieu = astronomer.Milieu[milieu]
    except:
        raise ValueError(f'Universe {universeId!r} has unknown milieu {milieu!r}')

    progressStage = None
    progressCount = 0
    if progressCallback:
        progressStage = 'Loading Universe {name!r}:'.format(name=universeInfo.name())
        progressCallback(progressStage, progressCount, _ProgressStageCount)

    allegiances = astronomer.convertDbAllegiancesToAstronomerAllegiances(
        dbAllegiances=multiverse.UniverseManager.instance().allegiances(id=universeId),
        entityFactory=entityFactory)

    if progressCallback:
        progressCount += 1
        progressCallback(progressStage, progressCount, _ProgressStageCount)

    sophonts = astronomer.convertDbSophontsToAstronomerSophonts(
        dbSophonts=multiverse.UniverseManager.instance().sophonts(id=universeId),
        entityFactory=entityFactory)

    if progressCallback:
        progressCount += 1
        progressCallback(progressStage, progressCount, _ProgressStageCount)

    sectors = astronomer.convertDbSectorsToAstronomerSectors(
        dbSectors=multiverse.UniverseManager.instance().sectors(id=universeId),
        astroAllegiances=allegiances,
        entityFactory=entityFactory)

    if progressCallback:
        progressCount += 1
        progressCallback(progressStage, progressCount, _ProgressStageCount)

    worlds = astronomer.convertDbSystemsToAstronomerWorlds(
        dbSystems=multiverse.UniverseManager.instance().systems(id=universeId),
        astroAllegiances=allegiances,
        astroSophonts=sophonts,
        entityFactory=entityFactory)

    if progressCallback:
        progressCount += 1
        progressCallback(progressStage, progressCount, _ProgressStageCount)

    labels = astronomer.convertDbMapLabelsToAstronomerMapLabels(
        dbLabels=multiverse.UniverseManager.instance().mapLabels(id=universeId),
        entityFactory=entityFactory)

    if progressCallback:
        progressCount += 1
        progressCallback(progressStage, progressCount, _ProgressStageCount)

    vectors = astronomer.convertDbMapVectorsToAstronomerMapVectors(
        dbVectors=multiverse.UniverseManager.instance().mapVectors(id=universeId),
        entityFactory=entityFactory)

    if progressCallback:
        progressCount += 1
        progressCallback(progressStage, _ProgressStageCount, _ProgressStageCount)

    logging.debug('Universe {name!r} ({id}) contains:'.format(
        name=universeInfo.name(),
        id=universeInfo.id()))
    logging.debug('Allegiances: {count}'.format(count=len(allegiances)))
    logging.debug('Sophonts: {count}'.format(count=len(sophonts)))
    logging.debug('Sectors: {count}'.format(count=len(sectors)))
    logging.debug('Systems: {count}'.format(count=len(worlds)))
    logging.debug('Map Labels: {count}'.format(count=len(labels)))
    logging.debug('Map Vectors: {count}'.format(count=len(vectors)))

    return entityFactory.createUniverse(
        universeId=universeId,
        milieu=milieu,
        allegiances=allegiances,
        sophonts=sophonts,
        sectors=sectors,
        worlds=worlds,
        labels=labels,
        vectors=vectors)