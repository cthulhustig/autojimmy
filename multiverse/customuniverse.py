import common
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

# For now we're not supporting multiple custom universes so a single universe
# with a known id and name are used
_CustomUniverseId = '35229f9b-c2e8-49c3-9334-0176a60015fd'
_CustomUniverseName = 'Custom Universe'

_ImportFlagFileName = 'database_import_flag_file'

_SectorFormatExtensions = {
    # NOTE: The sec format is short for second survey, not the legacy sec format
    survey.SectorFormat.T5Column: 'sec',
    survey.SectorFormat.T5Tab: 'tab'}
_MetadataFormatExtensions = {
    survey.MetadataFormat.JSON: 'json',
    survey.MetadataFormat.XML: 'xml'}

def customUniverseId() -> str:
    return _CustomUniverseId

def hasCustomUniverseBeenCreated() -> bool:
    universeInfo = multiverse.MultiverseDb.instance().universeInfoById(
        universeId=_CustomUniverseId)
    return universeInfo is not None

def createCustomUniverse(
        progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
        ) -> None:
    if progressCallback:
        progressCallback(f'Creating: Custom Universe', 0, 1)

    universe = multiverse.DbUniverse(
        id=_CustomUniverseId,
        name=_CustomUniverseName)
    multiverse.MultiverseDb.instance().saveUniverse(universe=universe)

    if progressCallback:
        progressCallback(f'Creating: Custom Universe', 1, 1)

def haveCustomSectorsBeenImported(directoryPath: str) -> bool:
    if not os.path.isdir(directoryPath):
        return False # No directory means nothing to import

    path = os.path.join(directoryPath, _ImportFlagFileName)
    return os.path.exists(path)

def importLegacyCustomSectors(
        directoryPath: str,
        progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
        ) -> None:
    flagFilePath = os.path.join(directoryPath, _ImportFlagFileName)
    if os.path.exists(flagFilePath):
        raise RuntimeError('Legacy custom sectors have already been imported')

    rawStockAllegiances = multiverse.readSnapshotStockAllegiances()
    rawStockSophonts = multiverse.readSnapshotStockSophonts()

    universePath = os.path.join(directoryPath, 'milieu')
    milieuSectors: typing.List[typing.Tuple[
        str, # Milieu
        typing.List[typing.Tuple[
            str, # Sector name
            survey.MetadataFormat,
            survey.SectorFormat
        ]]]] = []
    totalSectorCount = 0
    for milieu in [d for d in os.listdir(universePath) if os.path.isdir(os.path.join(universePath, d))]:
        milieuPath = os.path.join(universePath, milieu)
        universeInfoPath = os.path.join(milieuPath, 'universe.json')
        try:
            logging.info(f'Loading legacy custom universe file {universeInfoPath}')

            with open(universeInfoPath, 'r', encoding='utf-8-sig') as file:
                universeInfoContent = file.read()
            universeElement = json.loads(universeInfoContent)

            sectorsElement = universeElement.get('Sectors')
            if not sectorsElement:
                raise RuntimeError(f'No Sectors element found in "{universeInfoPath}"')

            sectorNames: typing.List[typing.Tuple[
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

                sectorNames.append((str(sectorName), metadataFormat, sectorFormat))
                totalSectorCount += 1

            milieuSectors.append((milieu, sectorNames))
        except Exception as ex:
            # Log and continue to import any custom sectors that can be processed
            # TODO: I should probably do something to inform the user that some
            # of the data couldn't be imported
            logging.warn(
                f'Legacy custom sector import failed to process "{universeInfoPath}"',
                exc_info=ex)

    rawData: typing.List[typing.Tuple[
        str, # Milieu
        survey.RawMetadata,
        typing.Collection[survey.RawWorld]
        ]] = []
    progressCount = 0
    for milieu, sectorNames in milieuSectors:
        milieuPath = os.path.join(universePath, milieu)
        for sectorName, metadataFormat, sectorFormat in sectorNames:
            try:
                if progressCallback:
                    progressCallback(
                        f'Reading: {milieu} - {sectorName}',
                        progressCount,
                        totalSectorCount)
                    progressCount += 1

                escapedName = common.encodeFileName(rawFileName=sectorName)

                metadataExtension = _MetadataFormatExtensions[metadataFormat]
                metadataPath = os.path.join(milieuPath, f'{escapedName}.{metadataExtension}')
                logging.info(f'Loading legacy custom metadata file {metadataPath}')
                with open(metadataPath, 'r', encoding='utf-8-sig') as file:
                    rawMetadata = survey.parseMetadata(
                        content=file.read(),
                        format=metadataFormat)

                sectorExtension = _SectorFormatExtensions[sectorFormat]
                sectorPath = os.path.join(milieuPath, f'{escapedName}.{sectorExtension}')
                logging.info(f'Loading legacy custom sector file {sectorPath}')
                with open(sectorPath, 'r', encoding='utf-8-sig') as file:
                    rawSystems = survey.parseSector(
                        content=file.read(),
                        format=sectorFormat)
                rawData.append((milieu, rawMetadata, rawSystems))
            except Exception as ex:
                # TODO: Log something but continue
                continue

    if progressCallback:
        progressCallback(
            f'Reading: Complete!',
            totalSectorCount,
            totalSectorCount)

    dbUniverse = multiverse.MultiverseDb.instance().loadUniverse(
        universeId=_CustomUniverseId,
        includeDefaultSectors=False,
        progressCallback=progressCallback)
    if not dbUniverse:
        raise RuntimeError('No custom universe to import legacy custom sectors into')

    totalSectorCount = len(rawData)
    for progressCount, (milieu, rawMetadata, rawSystems) in enumerate(rawData):
        existingSector = dbUniverse.sector(
            milieu=milieu,
            sectorX=rawMetadata.x(),
            sectorY=rawMetadata.y())
        if existingSector and existingSector.isCustom():
            logging.warning(
                f'Skipping import of legacy custom sector {rawMetadata.canonicalName()} at ({rawMetadata.x()}, {rawMetadata.y()}) from {milieu} as a custom sector already exists at that location')
            continue

        if progressCallback:
            progressCallback(
                f'Converting: {milieu} - {rawMetadata.canonicalName()}',
                progressCount,
                totalSectorCount)

        logging.info(
            f'Converting legacy custom sector {rawMetadata.canonicalName()} at ({rawMetadata.x()}, {rawMetadata.y()}) from {milieu}')
        dbUniverse.addSector(multiverse.convertRawSectorToDbSector(
            milieu=milieu,
            rawMetadata=rawMetadata,
            rawSystems=rawSystems,
            rawStockAllegiances=rawStockAllegiances,
            rawStockSophonts=rawStockSophonts,
            isCustom=True))

    if progressCallback:
        progressCallback(
            f'Converting: Complete!',
            totalSectorCount,
            totalSectorCount)

    multiverse.MultiverseDb.instance().saveUniverse(
        universe=dbUniverse,
        progressCallback=progressCallback)

    # Create flag file to indicate custom sectors have already been imported
    # TODO: I should pass a transaction into the saveUniverse call and only
    # commit it if I also manage to write the flag. If writing fails it should
    # roll back the commit
    with open(flagFilePath, 'w') as file:
        file.write(common.utcnow().isoformat())