import logging
import multiverse
import typing

def convertRawUniverseToDbUniverse(
        universeName: str,
        isCustom: bool,
        rawSectors: typing.List[typing.Tuple[
            str, # Milieu
            multiverse.RawMetadata,
            typing.Collection[multiverse.RawWorld]
            ]],
        universeId: typing.Optional[str] = None,
        progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
        ) -> multiverse.DbUniverse:
    dbUniverse = multiverse.DbUniverse(
        id=universeId,
        name=universeName)
    totalSectorCount = len(rawSectors)
    for progressCount, (milieu, rawMetadata, rawSystems) in enumerate(rawSectors):
        if progressCallback:
            progressCallback(
                f'Converting: {milieu} - {rawMetadata.canonicalName()}',
                progressCount,
                totalSectorCount)

        dbUniverse.addSector(convertRawSectorToDbSector(
            milieu=milieu,
            rawMetadata=rawMetadata,
            rawSystems=rawSystems,
            isCustom=isCustom))

    if progressCallback:
        progressCallback(
            f'Converting: Complete!',
            totalSectorCount,
            totalSectorCount)

    return dbUniverse

def convertRawSectorToDbSector(
        milieu: str,
        rawMetadata: multiverse.RawMetadata,
        rawSystems: typing.Collection[multiverse.RawWorld],
        isCustom: bool,
        sectorId: typing.Optional[str] = None,
        universeId: typing.Optional[str] = None,
        ) -> multiverse.DbUniverse:
        dbAlternateNames = None
        if rawMetadata.alternateNames():
            dbAlternateNames = [(name, rawMetadata.nameLanguage(name)) for name in rawMetadata.alternateNames()]

        dbSubsectorNames = None
        if rawMetadata.subsectorNames():
            dbSubsectorNames = []
            for code, name in rawMetadata.subsectorNames().items():
                if not name:
                    continue
                dbSubsectorNames.append((ord(code) - ord('A'), name))

        dbProducts = None
        rawSources = rawMetadata.sources()
        rawPrimarySource = rawSources.primary() if rawSources else None
        if rawSources and rawSources.products():
            dbProducts = []
            for product in rawSources.products():
                dbProducts.append(multiverse.DbProduct(
                    publication=product.publication(),
                    author=product.author(),
                    publisher=product.publisher(),
                    reference=product.reference()))

        dbAllegiances = None
        if rawMetadata.allegiances():
            dbAllegiances = []
            for rawAllegiance in rawMetadata.allegiances():
                dbAllegiances.append(multiverse.DbAllegiance(
                    code=rawAllegiance.code(),
                    name=rawAllegiance.name(),
                    base=rawAllegiance.base()))

        dbSystems = None
        if rawSystems:
            dbSystems = []
            for rawWorld in rawSystems:
                rawHex = rawWorld.attribute(multiverse.WorldAttribute.Hex)
                if not rawHex:
                    assert(False) # TODO: Better error handling

                rawUWP = rawWorld.attribute(multiverse.WorldAttribute.UWP)
                if rawUWP is None:
                    assert(False) # TODO: Better error handling

                rawSystemWorlds = rawWorld.attribute(multiverse.WorldAttribute.SystemWorlds)

                dbSystems.append(multiverse.DbSystem(
                    hexX=int(rawHex[:2]),
                    hexY=int(rawHex[-2:]),
                    # TODO: Should I make name optional? Some sectors don't have names
                    # (e.g. some of the ones that have a UWP of ???????-?).
                    name=rawWorld.attribute(multiverse.WorldAttribute.Name),
                    uwp=rawUWP,
                    remarks=rawWorld.attribute(multiverse.WorldAttribute.Remarks),
                    importance=rawWorld.attribute(multiverse.WorldAttribute.Importance),
                    economics=rawWorld.attribute(multiverse.WorldAttribute.Economics),
                    culture=rawWorld.attribute(multiverse.WorldAttribute.Culture),
                    nobility=rawWorld.attribute(multiverse.WorldAttribute.Nobility),
                    bases=rawWorld.attribute(multiverse.WorldAttribute.Bases),
                    zone=rawWorld.attribute(multiverse.WorldAttribute.Zone),
                    pbg=rawWorld.attribute(multiverse.WorldAttribute.PBG),
                    systemWorlds=int(rawSystemWorlds) if rawSystemWorlds else None,
                    allegiance=rawWorld.attribute(multiverse.WorldAttribute.Allegiance),
                    stellar=rawWorld.attribute(multiverse.WorldAttribute.Stellar)))

        dbRoutes = None
        if rawMetadata.routes():
            dbRoutes = []
            for rawRoute in rawMetadata.routes():
                rawStartHex = rawRoute.startHex()
                rawEndHex = rawRoute.endHex()
                rawStartOffsetX = rawRoute.startOffsetX()
                rawStartOffsetY = rawRoute.startOffsetY()
                rawEndOffsetX = rawRoute.endOffsetX()
                rawEndOffsetY = rawRoute.endOffsetY()

                dbRoutes.append(multiverse.DbRoute(
                    startHexX=int(rawStartHex[:2]),
                    startHexY=int(rawStartHex[-2:]),
                    endHexX=int(rawEndHex[:2]),
                    endHexY=int(rawEndHex[-2:]),
                    startOffsetX=rawStartOffsetX if rawStartOffsetX is not None else 0,
                    startOffsetY=rawStartOffsetY if rawStartOffsetY is not None else 0,
                    endOffsetX=rawEndOffsetX if rawEndOffsetX is not None else 0,
                    endOffsetY=rawEndOffsetY if rawEndOffsetY is not None else 0,
                    allegiance=rawRoute.allegiance(),
                    type=rawRoute.type(),
                    style=rawRoute.style(),
                    colour=rawRoute.colour(),
                    width=rawRoute.width()))

        dbBorders = None
        if rawMetadata.borders():
            dbBorders = []
            for rawBorder in rawMetadata.borders():
                dbHexes = []
                for rawHex in rawBorder.hexList():
                    dbHexes.append((int(rawHex[:2]), int(rawHex[-2:])))

                rawLabel = rawBorder.label()
                rawShowLabel = rawBorder.showLabel()
                rawWrapLabel = rawBorder.wrapLabel()
                rawLabelHex = rawBorder.labelHex()

                dbBorders.append(multiverse.DbBorder(
                    hexes=dbHexes,
                    showLabel=rawShowLabel if rawShowLabel is not None else False,
                    wrapLabel=rawWrapLabel if rawWrapLabel is not None else False,
                    label=rawLabel,
                    labelHexX=int(rawLabelHex[:2]) if rawLabelHex is not None else None,
                    labelHexY=int(rawLabelHex[-2:]) if rawLabelHex is not None else None,
                    labelOffsetX=rawBorder.labelOffsetX(),
                    labelOffsetY=rawBorder.labelOffsetY(),
                    colour=rawBorder.colour(),
                    style=rawBorder.style(),
                    allegiance=rawBorder.allegiance()))

        dbRegions = None
        if rawMetadata.regions():
            dbRegions = []
            for rawRegion in rawMetadata.regions():
                dbHexes = []
                for rawHex in rawRegion.hexList():
                    dbHexes.append((int(rawHex[:2]), int(rawHex[-2:])))

                rawLabel = rawRegion.label()
                rawShowLabel = rawRegion.showLabel()
                rawWrapLabel = rawRegion.wrapLabel()
                rawLabelHex = rawRegion.labelHex()

                dbRegions.append(multiverse.DbRegion(
                    hexes=dbHexes,
                    showLabel=rawShowLabel if rawShowLabel is not None else False,
                    wrapLabel=rawWrapLabel if rawWrapLabel is not None else False,
                    label=rawRegion.label(),
                    labelHexX=int(rawLabelHex[:2]) if rawLabelHex is not None else None,
                    labelHexY=int(rawLabelHex[-2:]) if rawLabelHex is not None else None,
                    labelOffsetX=rawRegion.labelOffsetX(),
                    labelOffsetY=rawRegion.labelOffsetY(),
                    colour=rawRegion.colour()))

        dbLabels = None
        if rawMetadata.labels():
            dbLabels = []
            for rawLabel in rawMetadata.labels():
                rawHex = rawLabel.hex()
                rawWrap = rawLabel.wrap()

                dbLabels.append(multiverse.DbLabel(
                    text=rawLabel.text(),
                    hexX=int(rawHex[:2]),
                    hexY=int(rawHex[-2:]),
                    wrap=rawWrap if rawWrap is not None else False,
                    colour=rawLabel.colour(),
                    size=rawLabel.size(),
                    offsetX=rawLabel.offsetX(),
                    offsetY=rawLabel.offsetY()))

        return multiverse.DbSector(
            id=sectorId,
            universeId=universeId,
            isCustom=isCustom,
            milieu=milieu,
            sectorX=rawMetadata.x(),
            sectorY=rawMetadata.y(),
            primaryName=rawMetadata.canonicalName(),
            primaryLanguage=rawMetadata.nameLanguage(rawMetadata.canonicalName()),
            alternateNames=dbAlternateNames,
            abbreviation=rawMetadata.abbreviation(),
            sectorLabel=rawMetadata.sectorLabel(),
            subsectorNames=dbSubsectorNames,
            selected=rawMetadata.selected() if rawMetadata.selected() is not None else False,
            tags=rawMetadata.tags(),
            styleSheet=rawMetadata.styleSheet(),
            credits=rawSources.credits() if rawSources else None,
            publication=rawPrimarySource.publication() if rawPrimarySource else None,
            author=rawPrimarySource.author() if rawPrimarySource else None,
            publisher=rawPrimarySource.publisher() if rawPrimarySource else None,
            reference=rawPrimarySource.reference() if rawPrimarySource else None,
            products=dbProducts,
            allegiances=dbAllegiances,
            systems=dbSystems,
            routes=dbRoutes,
            borders=dbBorders,
            regions=dbRegions,
            labels=dbLabels)

def convertDbUniverseToRawUniverse(
        dbUniverse: multiverse.DbUniverse,
        progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
        ) -> typing.List[typing.Tuple[
            str, # Milieu
            multiverse.RawMetadata,
            typing.Collection[multiverse.RawWorld]
            ]]:
    dbSectors = dbUniverse.sectors()
    if not dbSectors:
        return []

    totalSectorCount = len(dbSectors)
    rawSectors = []

    for progressCount, dbSector in enumerate(dbSectors):
        if progressCallback:
            progressCallback(
                f'Converting: {dbSector.milieu()} - {dbSector.primaryName()}',
                progressCount,
                totalSectorCount)

        rawSectors.append(convertDbSectorToRawSector(dbSector=dbSector))

    return rawSectors

def convertDbSectorToRawSector(
        dbSector: multiverse.DbSector
        ) -> typing.Tuple[
            str, # Milieu
            multiverse.RawMetadata,
            typing.Collection[multiverse.RawWorld]
            ]:
    rawAlternateNames = rawNameLanguages = None
    if dbSector.alternateNames() is not None or dbSector.primaryLanguage() is not None:
        rawAlternateNames = []
        rawNameLanguages = {}
        if dbSector.primaryLanguage() is not None:
            rawNameLanguages[dbSector.primaryName()] = dbSector.primaryLanguage()

        if dbSector.alternateNames() is not None:
            for dbName, dbLanguage in dbSector.alternateNames():
                rawAlternateNames.append(dbName)
                if dbLanguage is not None:
                    rawNameLanguages[dbName] = dbLanguage

    rawSubsectorNames = None
    if dbSector.subsectorNames() is not None:
        dbSubsectorNames = {k: v for k, v in dbSector.subsectorNames()}
        rawSubsectorNames = {}
        for index in range(16):
            dbSubsectorName = dbSubsectorNames.get(index)
            if dbSubsectorName is None:
                continue
            code = chr(ord('A') + index)
            rawSubsectorNames[code] = dbSubsectorName

    rawAllegiances = None
    if dbSector.allegiances() is not None:
        rawAllegiances = []
        for dbAllegiance in dbSector.allegiances():
            rawAllegiances.append(multiverse.RawAllegiance(
                code=dbAllegiance.code(),
                name=dbAllegiance.name(),
                base=dbAllegiance.base(),
                fileIndex=0))

    rawRoutes = None
    if dbSector.routes() is not None:
        rawRoutes = []
        for dbRoute in dbSector.routes():
            rawRoutes.append(multiverse.RawRoute(
                startHex=f'{dbRoute.startHexX():02d}{dbRoute.startHexY():02d}',
                endHex=f'{dbRoute.endHexX():02d}{dbRoute.endHexY():02d}',
                startOffsetX=dbRoute.startOffsetX(),
                startOffsetY=dbRoute.startOffsetY(),
                endOffsetX=dbRoute.endOffsetX(),
                endOffsetY=dbRoute.endOffsetY(),
                allegiance=dbRoute.allegiance(),
                type=dbRoute.type(),
                style=dbRoute.style(),
                colour=dbRoute.colour(),
                width=dbRoute.width(),
                fileIndex=0))

    rawBorders = None
    if dbSector.borders() is not None:
        rawBorders = []
        for dbBorder in dbSector.borders():
            rawHexes = []
            for dbHexX, dbHexY in dbBorder.hexes():
                rawHexes.append(f'{dbHexX:02d}{dbHexY:02d}')

            rawBorders.append(multiverse.RawBorder(
                hexList=rawHexes,
                allegiance=dbBorder.allegiance(),
                showLabel=dbBorder.showLabel(),
                wrapLabel=dbBorder.wrapLabel(),
                labelHex=f'{dbBorder.labelHexX():02d}{dbBorder.labelHexY():02d}' if dbBorder.labelHexX() is not None and dbBorder.labelHexY() is not None else None,
                labelOffsetX=dbBorder.labelOffsetX(),
                labelOffsetY=dbBorder.labelOffsetY(),
                label=dbBorder.label(),
                style=dbBorder.style(),
                colour=dbBorder.colour(),
                fileIndex=0))

    rawRegions = None
    if dbSector.regions() is not None:
        rawRegions = []
        for dbRegion in dbSector.regions():
            rawHexes = []
            for dbHexX, dbHexY in dbRegion.hexes():
                rawHexes.append(f'{dbHexX:02d}{dbHexY:02d}')

            rawRegions.append(multiverse.RawRegion(
                hexList=rawHexes,
                showLabel=dbRegion.showLabel(),
                wrapLabel=dbRegion.wrapLabel(),
                labelHex=f'{dbRegion.labelHexX():02d}{dbRegion.labelHexY():02d}' if dbRegion.labelHexX() is not None and dbRegion.labelHexY() is not None else None,
                labelOffsetX=dbRegion.labelOffsetX(),
                labelOffsetY=dbRegion.labelOffsetY(),
                label=dbRegion.label(),
                colour=dbRegion.colour(),
                fileIndex=0))

    rawLabels = None
    if dbSector.labels() is not None:
        rawLabels = []
        for dbLabel in dbSector.labels():
            rawLabels.append(multiverse.RawLabel(
                text=dbLabel.text(),
                hex=f'{dbLabel.hexX():02d}{dbLabel.hexY():02d}',
                colour=dbLabel.colour(),
                size=dbLabel.size(),
                wrap=dbLabel.wrap(),
                offsetX=dbLabel.offsetX(),
                offsetY=dbLabel.offsetY(),
                fileIndex=0))

    rawSources = None
    if dbSector.credits() is not None or dbSector.author() is not None or \
        dbSector.publication() is not None or dbSector.publisher() is not None or \
        dbSector.reference() is not None or dbSector.products() is not None:
        rawPrimary = None
        if dbSector.author() is not None or dbSector.publication() is not None or \
            dbSector.publisher() is not None or dbSector.reference() is not None:
            rawPrimary = multiverse.RawSource(
                publication=dbSector.publication(),
                author=dbSector.author(),
                publisher=dbSector.publisher(),
                reference=dbSector.reference())

        rawProducts = None
        if dbSector.products() is not None:
            rawProducts = []
            for dbProduct in dbSector.products():
                rawProducts.append(multiverse.RawSource(
                    publication=dbProduct.publication(),
                    author=dbProduct.author(),
                    publisher=dbProduct.publisher(),
                    reference=dbProduct.reference()))

        rawSources = multiverse.RawSources(
            credits=dbSector.credits(),
            primary=rawPrimary,
            products=rawProducts)

    rawMetadata = multiverse.RawMetadata(
        canonicalName=dbSector.primaryName(),
        alternateNames=rawAlternateNames,
        nameLanguages=rawNameLanguages,
        abbreviation=dbSector.abbreviation(),
        sectorLabel=dbSector.sectorLabel(),
        subsectorNames=rawSubsectorNames,
        x=dbSector.sectorX(),
        y=dbSector.sectorY(),
        selected=dbSector.selected(),
        tags=dbSector.tags(),
        allegiances=rawAllegiances,
        routes=rawRoutes,
        borders=rawBorders,
        labels=rawLabels,
        regions=rawRegions,
        sources=rawSources,
        styleSheet=dbSector.styleSheet())

    rawSystems = None
    if dbSector.systems() is not None:
        rawSystems = []
        for dbSystem in dbSector.systems():
            rawSystem = multiverse.RawWorld(0)
            rawSystem.setAttribute(
                attribute=multiverse.WorldAttribute.Hex,
                value=f'{dbSystem.hexX():02d}{dbSystem.hexY():02d}')
            rawSystem.setAttribute(
                attribute=multiverse.WorldAttribute.Name,
                value=dbSystem.name())
            rawSystem.setAttribute(
                attribute=multiverse.WorldAttribute.UWP,
                value=dbSystem.uwp())
            if dbSystem.remarks() is not None:
                rawSystem.setAttribute(
                    attribute=multiverse.WorldAttribute.Remarks,
                    value=dbSystem.remarks())
            if dbSystem.importance() is not None:
                rawSystem.setAttribute(
                    attribute=multiverse.WorldAttribute.Importance,
                    value=dbSystem.importance())
            if dbSystem.economics() is not None:
                rawSystem.setAttribute(
                    attribute=multiverse.WorldAttribute.Economics,
                    value=dbSystem.economics())
            if dbSystem.culture() is not None:
                rawSystem.setAttribute(
                    attribute=multiverse.WorldAttribute.Culture,
                    value=dbSystem.culture())
            if dbSystem.nobility() is not None:
                rawSystem.setAttribute(
                    attribute=multiverse.WorldAttribute.Nobility,
                    value=dbSystem.nobility())
            if dbSystem.bases() is not None:
                rawSystem.setAttribute(
                    attribute=multiverse.WorldAttribute.Bases,
                    value=dbSystem.bases())
            if dbSystem.zone() is not None:
                rawSystem.setAttribute(
                    attribute=multiverse.WorldAttribute.Zone,
                    value=dbSystem.zone())
            if dbSystem.pbg() is not None:
                rawSystem.setAttribute(
                    attribute=multiverse.WorldAttribute.PBG,
                    value=dbSystem.pbg())
            if dbSystem.systemWorlds() is not None:
                rawSystem.setAttribute(
                    attribute=multiverse.WorldAttribute.SystemWorlds,
                    value=str(dbSystem.systemWorlds()))
            if dbSystem.allegiance() is not None:
                rawSystem.setAttribute(
                    attribute=multiverse.WorldAttribute.Allegiance,
                    value=dbSystem.allegiance())
            if dbSystem.stellar() is not None:
                rawSystem.setAttribute(
                    attribute=multiverse.WorldAttribute.Stellar,
                    value=dbSystem.stellar())

            rawSystems.append(rawSystem)

    return (dbSector.milieu(), rawMetadata, rawSystems)
