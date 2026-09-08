import astronomer
import common
import database
import logging
import multiverse
import typing

# TODO: The convertDB* functions should take a a progress tracker as well
class _Loader(object):
    def __init__(
            self,
            universeId: str,
            universeName: str,
            universeDb: multiverse.UniverseDb,
            milieu: astronomer.Milieu,
            entityFactory: astronomer.EntityFactoryInterface,
            ) -> None:
        self._universeId = universeId
        self._universeName = universeName
        self._universeDb = universeDb
        self._milieu = milieu
        self._entityFactory = entityFactory
        self._allegiances = None
        self._sophonts = None
        self._sectors = None
        self._worlds = None
        self._mapLabels = None
        self._mapVectors = None

    def loadAllegiances(
            self,
            transaction: database.Transaction,
            progress: typing.Optional[common.ProgressTracker]
            ) -> None:
        dbAllegiances = self._universeDb.loadAllegiances(
            transaction=transaction,
            progress=progress.createChild(weight=0.5))
        self._allegiances = astronomer.convertDbAllegiancesToAstronomerAllegiances(
            dbAllegiances=dbAllegiances,
            entityFactory=self._entityFactory,
            progress=progress.createChild(weight=0.5))

    def loadSophonts(
            self,
            transaction: database.Transaction,
            progress: typing.Optional[common.ProgressTracker]
            ) -> None:
        dbSophonts = self._universeDb.loadSophonts(
            transaction=transaction,
            progress=progress.createChild(weight=0.5))
        self._sophonts = astronomer.convertDbSophontsToAstronomerSophonts(
            dbSophonts=dbSophonts,
            entityFactory=self._entityFactory,
            progress=progress.createChild(weight=0.5))

    def loadSectors(
            self,
            transaction: database.Transaction,
            progress: typing.Optional[common.ProgressTracker]
            ) -> None:
        dbSectors = self._universeDb.loadSectors(
            transaction=transaction,
            progress=progress.createChild(weight=0.5))
        self._sectors = astronomer.convertDbSectorsToAstronomerSectors(
            dbSectors=dbSectors,
            astroAllegiances=self._allegiances,
            entityFactory=self._entityFactory,
            progress=progress.createChild(weight=0.5))

    def loadWorlds(
            self,
            transaction: database.Transaction,
            progress: typing.Optional[common.ProgressTracker]
            ) -> None:
        dbSystems = self._universeDb.loadSystems(
            transaction=transaction,
            progress=progress.createChild(weight=0.5))
        self._worlds = astronomer.convertDbSystemsToAstronomerWorlds(
            dbSystems=dbSystems,
            astroAllegiances=self._allegiances,
            astroSophonts=self._sophonts,
            entityFactory=self._entityFactory,
            progress=progress.createChild(weight=0.5))

    def loadMapLabels(
            self,
            transaction: database.Transaction,
            progress: typing.Optional[common.ProgressTracker]
            ) -> None:
        dbMapLabels = self._universeDb.loadMapLabels(
            transaction=transaction,
            progress=progress.createChild(weight=0.5))
        self._mapLabels = astronomer.convertDbMapLabelsToAstronomerMapLabels(
            dbLabels=dbMapLabels,
            entityFactory=self._entityFactory,
            progress=progress.createChild(weight=0.5))

    def loadMapVectors(
            self,
            transaction: database.Transaction,
            progress: typing.Optional[common.ProgressTracker]
            ) -> None:
        dbMapVectors = self._universeDb.loadMapVectors(
            transaction=transaction,
            progress=progress.createChild(weight=0.5))
        self._mapVectors = astronomer.convertDbMapVectorsToAstronomerMapVectors(
            dbVectors=dbMapVectors,
            entityFactory=self._entityFactory,
            progress=progress.createChild(weight=0.5))

    def createUniverse(self) -> astronomer.Universe:
        if self._allegiances is None:
            raise RuntimeError('Allegiances have not been loaded for universe {name!r} ({id})'.format(
                name=self._universeName,
                id=self._universeDb.id()))
        if self._sophonts is None:
            raise RuntimeError('Sophonts have not been loaded for universe {name!r} ({id})'.format(
                name=self._universeName,
                id=self._universeId))
        if self._sectors is None:
            raise RuntimeError('Sectors have not been loaded for universe {name!r} ({id})'.format(
                name=self._universeName,
                id=self._universeId))
        if self._worlds is None:
            raise RuntimeError('Worlds have not been loaded for universe {name!r} ({id})'.format(
                name=self._universeName,
                id=self._universeId))
        if self._mapLabels is None:
            raise RuntimeError('Map labels have not been loaded for universe {name!r} ({id})'.format(
                name=self._universeName,
                id=self._universeId))
        if self._mapVectors is None:
            raise RuntimeError('Map vectors have not been loaded for universe {name!r} ({id})'.format(
                name=self._universeName,
                id=self._universeId))

        logging.debug('Universe {name!r} ({id}) contains:'.format(
            name=self._universeName,
            id=self._universeId))
        logging.debug('Allegiances: {count}'.format(count=len(self._allegiances)))
        logging.debug('Sophonts: {count}'.format(count=len(self._sophonts)))
        logging.debug('Sectors: {count}'.format(count=len(self._sectors)))
        logging.debug('Systems: {count}'.format(count=len(self._worlds)))
        logging.debug('Map Labels: {count}'.format(count=len(self._mapLabels)))
        logging.debug('Map Vectors: {count}'.format(count=len(self._mapVectors)))

        return self._entityFactory.createUniverse(
            universeId=self._universeId,
            milieu=self._milieu,
            allegiances=self._allegiances,
            sophonts=self._sophonts,
            sectors=self._sectors,
            worlds=self._worlds,
            labels=self._mapLabels,
            vectors=self._mapVectors)

def loadUniverseFromDatabase(
        universeId: str,
        entityFactory: typing.Optional[astronomer.EntityFactoryInterface] = None,
        progress: typing.Optional[common.ProgressTracker] = None
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

    universeDb = multiverse.UniverseManager.instance().universeDbById(id=universeId)

    with universeDb.createTransaction() as transaction:
        milieu = universeDb.milieu(transaction=transaction)
        try:
            milieu = astronomer.Milieu[milieu]
        except:
            raise ValueError(f'Universe {universeId!r} has unknown milieu {milieu!r}')

        # TODO: Routes, borders & regions (and possibly sector labels) should go here when I move them to the universe
        allegianceCount = universeDb.countAllegiances(transaction=transaction)
        sophontCount = universeDb.countSophonts(transaction=transaction)
        sectorCount = universeDb.countSectors(transaction=transaction)
        systemCount = universeDb.countSystems(transaction=transaction)
        mapLabelCount = universeDb.countMapLabels(transaction=transaction)
        mapVectorCount = universeDb.countMapVectors(transaction=transaction)
        objectCount = allegianceCount + sophontCount + sectorCount + systemCount + mapLabelCount + mapVectorCount

        loader = _Loader(
            universeId=universeId,
            universeName=universeInfo.name(),
            universeDb=universeDb,
            milieu=milieu,
            entityFactory=entityFactory)
        tasks = [
            (loader.loadAllegiances, allegianceCount / objectCount),
            (loader.loadSophonts, sophontCount / objectCount),
            (loader.loadSectors, sectorCount / objectCount),
            (loader.loadWorlds, systemCount / objectCount),
            (loader.loadMapLabels, mapLabelCount / objectCount),
            (loader.loadMapVectors, mapVectorCount / objectCount)]

        for function, weight in tasks:
            function(
                transaction=transaction,
                progress=progress.createChild(weight=weight) if progress is not None else None)

        return loader.createUniverse()
