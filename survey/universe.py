import json
import survey

def parseUniverseInfo(
        content: str
        ) -> survey.RawUniverseInfo:
    universeElement = json.loads(content)

    sectorsElement = universeElement.get('Sectors')
    sectorInfos = []
    if not sectorsElement:
        raise RuntimeError('No Sectors element found')

    for sectorElement in sectorsElement:
        sectorX = sectorElement.get('X')
        if sectorX is None:
            raise RuntimeError('Sector has no X Position')
        sectorX = int(sectorX)

        sectorY = sectorElement.get('Y')
        if sectorY is None:
            raise RuntimeError('Sector has no Y Position')
        sectorY = int(sectorY)

        milieu = sectorElement.get('Milieu')
        if not milieu:
            raise RuntimeError('Sector has no Milieu')

        abbreviation = sectorElement.get('Abbreviation')
        if abbreviation is not None:
            abbreviation = str(abbreviation)

        tags = sectorElement.get('Tags')
        if tags is not None:
            tags = str(tags)

        namesElements = sectorElement.get('Names')
        nameInfos = None
        if namesElements and len(namesElements) > 0:
            nameInfos = []
            for nameElement in namesElements:
                name = nameElement.get('Text')
                if not name:
                    raise RuntimeError('Sector Name element has no Text')
                name = str(name)

                language = nameElement.get('Lang')
                if language is not None:
                    language = str(language)

                source = nameElement.get('Source')
                if source is not None:
                    source = str(source)

                nameInfos.append(survey.RawNameInfo(
                    name=name,
                    language=language,
                    source=source))

        sectorInfos.append(survey.RawSectorInfo(
            x=sectorX,
            y=sectorY,
            milieu=milieu,
            abbreviation=abbreviation,
            tags=tags,
            nameInfos=nameInfos))

    return survey.RawUniverseInfo(
        sectorInfos=sectorInfos)

def formatUniverseInfo(
        universeInfo: survey.RawUniverseInfo
        ) -> str:
    universeElement = {}

    sectorsElement = []
    for sectorInfo in universeInfo.sectorInfos():
        sectorElement = {
            'X': sectorInfo.x(),
            'Y': sectorInfo.y(),
            'Milieu': sectorInfo.milieu()}

        if sectorInfo.abbreviation():
            sectorElement['Abbreviation'] = sectorInfo.abbreviation()

        if sectorInfo.tags():
            sectorElement['Tags'] = sectorInfo.tags()

        if sectorInfo.nameInfos():
            namesElement = []
            for nameInfo in sectorInfo.nameInfos():
                nameElement = {'Text': nameInfo.name()}

                if nameInfo.language():
                    nameElement['Lang'] = nameInfo.language()

                if nameInfo.source():
                    nameElement['Source'] = nameInfo.source()

                namesElement.append(nameElement)

            sectorElement['Names'] = namesElement

        sectorsElement.append(sectorElement)

    universeElement['Sectors'] = sectorsElement

    return json.dumps(universeElement, indent=4).encode()
