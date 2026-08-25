import common
import logging
import multiverse
import survey
import typing

# TODO: Why are the stars for bases different on Thoznaen now compared to the last
# release version. They were 5 point stars, now it looks like asterisks

def convertStockUniverseToDbUniverse(
        milieu: str,
        # TODO: Do something with progress
        progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None,
        # TODO: Do something with the reporter
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Tuple[
            typing.List[multiverse.DbAllegiance],
            typing.List[multiverse.DbSector],
            typing.List[multiverse.DbMapLabel],
            typing.List[multiverse.DbMapVector]]:
    if reporter:
        reporter.pushPrefix('Stock Allegiances: ')
    try:
        rawStockAllegiances = multiverse.loadSnapshotStockAllegiances(reporter=reporter)
    finally:
        if reporter:
            reporter.popPrefix()

    if reporter:
        reporter.pushPrefix('Stock Sophonts: ')
    try:
        rawStockSophonts = multiverse.loadSnapshotStockSophonts(reporter=reporter)
    finally:
        if reporter:
            reporter.popPrefix()

    if reporter:
        reporter.pushPrefix('Stock Style Sheet: ')
    try:
        rawStockStyleSheet = multiverse.loadSnapshotStyleSheet(reporter=reporter)
    finally:
        if reporter:
            reporter.popPrefix()

    if reporter:
        reporter.pushPrefix('Mega Labels: ')
    try:
        rawMegaLabels = multiverse.loadMegaLabels(reporter=reporter)
    finally:
        if reporter:
            reporter.popPrefix()

    if reporter:
        reporter.pushPrefix('Minor Labels: ')
    try:
        rawMinorLabels = multiverse.loadMinorLabels(reporter=reporter)
    finally:
        if reporter:
            reporter.popPrefix()

    if reporter:
        reporter.pushPrefix('World Labels: ')
    try:
        rawWorldLabels = multiverse.loadWorldLabels(reporter=reporter)
    finally:
        if reporter:
            reporter.popPrefix()

    if reporter:
        reporter.pushPrefix('Border Vectors: ')
    try:
        rawBorderVectors = multiverse.loadBorderVectors(reporter=reporter)
    finally:
        if reporter:
            reporter.popPrefix()

    if reporter:
        reporter.pushPrefix('Rift Vectors: ')
    try:
        rawRiftVectors = multiverse.loadRiftVectors(reporter=reporter)
    finally:
        if reporter:
            reporter.popPrefix()

    if reporter:
        reporter.pushPrefix('Route Vectors: ')
    try:
        rawRouteVectors = multiverse.loadRouteVectors(reporter=reporter)
    finally:
        if reporter:
            reporter.popPrefix()

    rawUniverseInfo = survey.parseUniverseInfo(
        content=multiverse.SnapshotManager.instance().readUniverseInfo(milieu=milieu))

    sectorNames = []
    for sectorInfo in rawUniverseInfo:
        nameInfos = sectorInfo.nameInfos()
        canonicalName = nameInfos[0].name() if nameInfos else None
        if not canonicalName:
            logging.warning(f'Stock universe import ignoring sector with no name in milieu {milieu}')
            continue
        sectorNames.append(canonicalName)

    rawSectors: typing.List[typing.Tuple[survey.RawMetadata, typing.List[survey.RawWorld]]] = []
    progressCount = 0
    for sectorName in sectorNames:
        if progressCallback:
            try:
                progressCallback(
                    f'Loading: {milieu} - {sectorName}',
                    progressCount,
                    len(sectorNames))
                progressCount += 1
            except Exception as ex:
                logging.warning('Stock universe import progress callback threw an exception', exc_info=ex)

        try:
            if reporter:
                reporter.pushPrefix(f'{milieu} {sectorName} Metadata - ')
            try:
                sectorMetadata = multiverse.SnapshotManager.instance().readSectorMetadata(
                    milieu=milieu,
                    sector=sectorName)
                rawMetadata = survey.parseMetadata(content=sectorMetadata, reporter=reporter)
            finally:
                if reporter:
                    reporter.popPrefix()

            if reporter:
                reporter.pushPrefix(f'{milieu} {sectorName} Sector - ')
            try:
                sectorContent = multiverse.SnapshotManager.instance().readSectorContent(
                    milieu=milieu,
                    sector=sectorName)
                rawSystems = survey.parseSector(content=sectorContent, reporter=reporter)
            finally:
                if reporter:
                    reporter.popPrefix()

            rawSectors.append((rawMetadata, rawSystems))
        except Exception as ex:
            logging.error(f'Stock universe import failed to load data for sector {sectorName} from {milieu}', exc_info=ex)

    dbMapLabels: typing.List[multiverse.DbMapLabel] = []
    dbMapLabels.extend(multiverse.convertRawLabelsToDbMapLabels(
        rawMegaLabels=rawMegaLabels,
        rawMinorLabels=rawMinorLabels,
        rawWorldLabels=rawWorldLabels,
        rawUniverseInfo=rawUniverseInfo))
    dbMapLabels.extend(multiverse.convertRawVectorsToDbMapLabels(
        rawBorderVectors=rawBorderVectors,
        rawRiftVectors=rawRiftVectors,
        rawRouteVectors=rawRouteVectors))

    dbMapVectors: typing.List[multiverse.DbMapVector] = []
    dbMapVectors.extend(multiverse.convertRawVectorsToDbMapVectors(
        rawBorderVectors=rawBorderVectors,
        rawRiftVectors=rawRiftVectors,
        rawRouteVectors=rawRouteVectors))

    styleMapper = multiverse.StyleMapper(
        rawSectors=rawSectors,
        rawStockStyleSheet=rawStockStyleSheet)
    allegianceMapper = multiverse.AllegianceMapper(
        milieu=milieu,
        rawSectors=rawSectors,
        rawStockAllegiances=rawStockAllegiances,
        styleMapper=styleMapper)

    dbSectors = multiverse.convertRawSectorsToDbSectors(
        rawSectors=rawSectors,
        rawStockSophonts=rawStockSophonts,
        allegianceMapper=allegianceMapper,
        styleMapper=styleMapper)

    if progressCallback:
        try:
            progressCallback(
                f'Converting: Complete!',
                len(sectorNames),
                len(sectorNames))
        except Exception as ex:
            logging.warning('Stock universe import progress callback threw an exception', exc_info=ex)

    return (
        allegianceMapper.listAllegiances(),
        dbSectors,
        dbMapLabels,
        dbMapVectors)
