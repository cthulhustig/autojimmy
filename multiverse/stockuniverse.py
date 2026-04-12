import hashlib
import logging
import multiverse
import survey
import typing

# This returns true if the universe snapshot from the snapshot manager
# is newer than the stock universe database (or if there is no stock
# universe database)
def isStockUniverseSnapshotNewer() -> bool:
    snapshotTimestamp = multiverse.SnapshotManager.instance().snapshotTimestamp()
    if not snapshotTimestamp:
        return False
    return multiverse.UniverseManager.instance().checkStockUniverseTimestamp(
        snapshotTimestamp=snapshotTimestamp)

def importStockUniverseSnapshot(
        progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
        ) -> None:
    importTimestamp = multiverse.SnapshotManager.instance().snapshotTimestamp()
    isSnapshotNewer = multiverse.UniverseManager.instance().checkStockUniverseTimestamp(
        snapshotTimestamp=importTimestamp)
    if not isSnapshotNewer:
        return # Nothing to do

    rawStockAllegiances = survey.parseStockAllegiances(
        content=multiverse.SnapshotManager.instance().readSnapshotStockAllegiances())
    rawStockSophonts = survey.parseStockSophonts(
        content=multiverse.SnapshotManager.instance().readSnapshotStockSophonts())
    rawStockStyleSheet = survey.parseStyleSheet(
        content=multiverse.SnapshotManager.instance().readSnapshotStyleSheet())

    milieuSectors: typing.List[typing.Tuple[
        str, # Milieu
        typing.List[str] # List of sector names in the milieu
    ]] = []
    totalSectorCount = 0
    for milieu in multiverse.SnapshotManager.instance().listMilieu():
        universeInfo = survey.parseUniverseInfo(
            content=multiverse.SnapshotManager.instance().readUniverseInfo(milieu=milieu))

        sectorNames = []
        for sectorInfo in universeInfo.sectorInfos():
            nameInfos = sectorInfo.nameInfos()
            canonicalName = nameInfos[0].name() if nameInfos else None
            if not canonicalName:
                logging.warning(f'Stock universe import ignoring sector with no name in milieu {milieu}')
                continue
            sectorNames.append(canonicalName)
            totalSectorCount += 1

        milieuSectors.append((milieu, sectorNames))

    dbSectors = []
    sourceDataHashes: typing.Dict[multiverse.DbSector, str] = {}
    progressCount = 0
    for milieu, sectorNames in milieuSectors:
        for sectorName in sectorNames:
            if progressCallback:
                try:
                    progressCallback(
                        f'Converting: {milieu} - {sectorName}',
                        progressCount,
                        totalSectorCount)
                    progressCount += 1
                except Exception as ex:
                    logging.warning('Stock universe import progress callback threw an exception', exc_info=ex)

            try:
                sectorMetadata = multiverse.SnapshotManager.instance().readSectorMetadata(
                    milieu=milieu,
                    sector=sectorName)
                sectorContent = multiverse.SnapshotManager.instance().readSectorContent(
                    milieu=milieu,
                    sector=sectorName)

                dbSector = multiverse.convertRawSectorToDbSector(
                    milieu=milieu,
                    rawMetadata=survey.parseMetadata(sectorMetadata),
                    rawSystems=survey.parseSector(sectorContent),
                    rawStockAllegiances=rawStockAllegiances,
                    rawStockSophonts=rawStockSophonts,
                    rawStockStyleSheet=rawStockStyleSheet)
                dbSectors.append(dbSector)

                hash = hashlib.sha256()
                hash.update(hashlib.sha256(sectorMetadata.encode()).digest())
                hash.update(hashlib.sha256(sectorContent.encode()).digest())
                sourceDataHashes[dbSector] = hash.hexdigest()
            except Exception as ex:
                logging.error(f'Stock universe import failed to load data for sector {sectorName} from {milieu}', exc_info=ex)

    if progressCallback:
        try:
            progressCallback(
                f'Converting: Complete!',
                totalSectorCount,
                totalSectorCount)
        except Exception as ex:
            logging.warning('Stock universe import progress callback threw an exception', exc_info=ex)

    multiverse.UniverseManager.instance().updateStockUniverse(
        sectors=dbSectors,
        snapshotTimestamp=importTimestamp,
        progressCallback=progressCallback,
        sourceDataHashes=sourceDataHashes)

