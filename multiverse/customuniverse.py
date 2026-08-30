import common
import hashlib
import json
import logging
import multiverse
import os
import survey
import typing

# TODO: At some point in the future I should be able to delete this code.
# However, I'll need to wait for a good few releases as I can only really
# delete it once I'm sure nobody will be upgrading from a version so old
# it will still be using custom sectors stored in the filesystem

_SectorFormatExtensions = {
    # NOTE: The sec format is short for second survey, not the legacy sec format
    survey.SectorFormat.T5Column: 'sec',
    survey.SectorFormat.T5Tab: 'tab'}
_MetadataFormatExtensions = {
    survey.MetadataFormat.JSON: 'json',
    survey.MetadataFormat.XML: 'xml'}

def importLegacyCustomSectors(
        directoryPath: str,
        universeId: str,
        milieu: str,
        progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None,
        reporter: typing.Optional[common.Reporter] = None
        ) -> None:
    # TODO: Legacy custom sectors are currently broken as systems (and anything else
    # I moved from the sector to the universe) won't be deleted
    return

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

    # NOTE: This is done early to verify the universe exists before loading all the
    # custom sectors
    existingSectorInfos = {(s.sectorX(), s.sectorY()): s for s in multiverse.UniverseManager.instance().sectorInfos(universeId)}

    universeInfoPath = os.path.join(directoryPath, 'universe.json')

    try:
        logging.info(f'Loading legacy custom universe file {universeInfoPath}')

        with open(universeInfoPath, 'r', encoding='utf-8-sig') as file:
            universeInfoContent = file.read()
        universeElement = json.loads(universeInfoContent)

        sectorsElement = universeElement.get('Sectors')
        if not sectorsElement:
            raise RuntimeError(f'No Sectors element found in "{universeInfoPath}"')

        sectorData: typing.List[typing.Tuple[
            str, # Sector name
            survey.MetadataFormat,
            survey.SectorFormat
            ]] = []
        for index, sectorElement in enumerate(sectorsElement):
            namesElements = sectorElement.get('Names')
            if not namesElements:
                raise RuntimeError(f'No Names element found for sector {index + 1} in "{universeInfoPath}"')

            nameElement = namesElements[0]
            sectorName = nameElement.get('Text')
            if not sectorName:
                raise RuntimeError(f'No Text element for Sector {index + 1} Name element')
            sectorName = str(sectorName)

            # If the universe doesn't specify the metadata format it must be a standard traveller map
            # universe file which means the corresponding metadata files all use XML format
            metadataFormatTag = sectorElement.get('MetadataFormat')
            metadataFormat = survey.MetadataFormat.XML
            if metadataFormatTag != None:
                metadataFormat = survey.MetadataFormat.__members__.get(
                    str(metadataFormatTag),
                    metadataFormat)

            # If the universe doesn't specify the sector format it must be a standard traveller map
            # universe file which means the corresponding sectors files all use T5 column format
            sectorFormatTag = sectorElement.get('SectorFormat')
            sectorFormat = survey.SectorFormat.T5Column
            if sectorFormatTag != None:
                sectorFormat = survey.SectorFormat.__members__.get(
                    str(sectorFormatTag),
                    sectorFormat)

            sectorData.append((sectorName, metadataFormat, sectorFormat))
    except Exception as ex:
        # Log and continue to import any custom sectors that can be processed
        # TODO: I should probably do something to inform the user that some
        # of the data couldn't be imported
        logging.warn(
            f'Legacy custom sector import failed to process "{universeInfoPath}"',
            exc_info=ex)

    if not sectorData:
        # No legacy custom sectors to import
        return

    dbSectors: typing.List[multiverse.DbSector] = []
    progressCount = 0
    for sectorName, metadataFormat, sectorFormat in sectorData:
        try:
            if progressCallback:
                progressCallback(
                    f'Converting: {sectorName}',
                    progressCount,
                    len(sectorData))
                progressCount += 1

            escapedName = common.encodeFileName(rawFileName=sectorName)

            metadataExtension = _MetadataFormatExtensions[metadataFormat]
            metadataPath = os.path.join(directoryPath, f'{escapedName}.{metadataExtension}')
            logging.info(f'Loading legacy custom metadata file {metadataPath}')
            with open(metadataPath, 'r', encoding='utf-8-sig') as file:
                metadataContent = file.read()

            sectorExtension = _SectorFormatExtensions[sectorFormat]
            sectorPath = os.path.join(directoryPath, f'{escapedName}.{sectorExtension}')
            logging.info(f'Loading legacy custom sector file {sectorPath}')
            with open(sectorPath, 'r', encoding='utf-8-sig') as file:
                sectorContent = file.read()

            reporter.pushPrefix(f'{metadataPath} - ')
            try:
                rawMetadata = survey.parseMetadata(
                    content=metadataContent,
                    format=metadataFormat,
                    reporter=reporter)
            finally:
                if reporter:
                    reporter.popPrefix()

            reporter.pushPrefix(f'{sectorPath} - ')
            try:
                rawSystems = survey.parseSector(
                    content=sectorContent,
                    format=sectorFormat,
                    reporter=reporter)
            finally:
                if reporter:
                    reporter.popPrefix()

            # NOTE: If there is a stock sector where this custom sector is going to
            # be placed, the database code requires that the new sector object has
            # the same id as the one to be replaced.
            existingSectorInfo = existingSectorInfos.get((rawMetadata.x(), rawMetadata.y()))
            assert(False) # TODO: This needs rewritten to work with new conversion process
            dbSector = multiverse.convertRawSectorToDbSector(
                sectorId=existingSectorInfo.id() if existingSectorInfo else None,
                milieu=milieu,
                rawMetadata=rawMetadata,
                rawSystems=rawSystems,
                rawStockAllegiances=rawStockAllegiances,
                rawStockSophonts=rawStockSophonts,
                rawStockStyleSheet=rawStockStyleSheet)
            dbSectors.append(dbSector)
        except Exception as ex:
            # TODO: Log something but continue
            print(ex)
            continue

    if progressCallback:
        progressCallback(
            f'Converting: Complete!',
            len(sectorData),
            len(sectorData))

    if not dbSectors:
        # There were legacy custom sectors but none of the could be loaded.
        return

    multiverse.UniverseManager.instance().updateSectors(
        id=universeId,
        sectors=dbSectors,
        progressCallback=progressCallback)
