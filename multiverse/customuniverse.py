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

def haveLegacyCustomSectorsBeenImported(directoryPath: str) -> bool:
    if not os.path.isdir(directoryPath):
        return False # No directory means nothing to import

    path = os.path.join(directoryPath, _ImportFlagFileName)
    return os.path.exists(path)

def importLegacyCustomSectors(
        directoryPath: str,
        appVersion: str,
        progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
        ) -> None:
    if haveLegacyCustomSectorsBeenImported(directoryPath):
        raise RuntimeError('Legacy custom sectors have already been imported')

    rawStockAllegiances = multiverse.readSnapshotStockAllegiances()
    rawStockSophonts = multiverse.readSnapshotStockSophonts()
    rawStockStyleSheet = multiverse.readSnapshotStyleSheet()

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

    if not totalSectorCount:
        # No legacy custom sectors to load but still create the flag file to indicate
        # custom sectors have been imported to avoid going through this process again
        _createLegacySectorsImportedFlagFile(
            directoryPath=directoryPath,
            appVersion=appVersion)
        return

    dbSectors: typing.List[multiverse.DbSector] = []
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

                dbSector = multiverse.convertRawSectorToDbSector(
                    milieu=milieu,
                    rawMetadata=rawMetadata,
                    rawSystems=rawSystems,
                    rawStockAllegiances=rawStockAllegiances,
                    rawStockSophonts=rawStockSophonts,
                    rawStockStyleSheet=rawStockStyleSheet)
                dbSectors.append(dbSector)
            except Exception as ex:
                # TODO: Log something but continue
                continue

    if progressCallback:
        progressCallback(
            f'Reading: Complete!',
            totalSectorCount,
            totalSectorCount)

    if not dbSectors:
        # There were legacy custom sectors but none of the could be loaded.
        # Still create the flag file to indicate custom sectors have been
        # imported to avoid going through this process again
        _createLegacySectorsImportedFlagFile(
            directoryPath=directoryPath,
            appVersion=appVersion)
        return

    # TODO: Need to handle the case where the custom universe with this name
    # already exists.
    multiverse.UniverseManager.instance().createCustomUniverse(
        universeId=_CustomUniverseId,
        name=_CustomUniverseName,
        description='',
        copyStock=True,
        sectors=dbSectors,
        progressCallback=progressCallback)

    # Create flag file to indicate custom sectors have already been imported.
    _createLegacySectorsImportedFlagFile(
        directoryPath=directoryPath,
        appVersion=appVersion)

def _createLegacySectorsImportedFlagFile(
        directoryPath: str,
        appVersion: str
        ) -> None:
    flagFilePath = os.path.join(directoryPath, _ImportFlagFileName)
    with open(flagFilePath, 'w') as file:
        file.write(appVersion)