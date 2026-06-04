import enum
import common
import json
import survey
import typing
import xml.etree.ElementTree

# TODO: I think I want to add my own custom Sophonts elements to the metadata (similar to how
# allegiances are defined).
# Things to support
# - Name
# - Code
# - Language
# Things that will need updated
# - Raw metadata reader
# - Raw metadata writer
# - Database schema will need updated to add an optional language field to sophonts
# - Database sophont object will need updated to store language
# - Astro 2 Db converter will need updated to pass the language
# - Db 2 AStro converter will need updated to pass the language
# - Raw 2 Db converter will need updated to combine sophonts defined in the metadata and sophonts referenced in the sector in the same way as it does for allegiances
# - Db 2 Raw converter will need updated to create sophonts in the RawMetadata

class MetadataFormat(enum.Enum):
    JSON = 0
    XML = 1

_XmlFloatDecimalPlaces = 2

def _parseStringAttribute(
        attributeMap: typing.Mapping[str, typing.Any],
        attributeName: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    value = attributeMap.get(attributeName)
    if value is None:
        return None

    try:
        string = str(value)
    except:
        if reporter:
            reporter.addMessage(f'Ignoring invalid {attributeName} attribute "{value}"')
        return None

    if not string:
        if reporter:
            reporter.addMessage(f'Ignoring empty {attributeName} attribute')
        return None

    return string

def _parseBoolAttribute(
        attributeMap: typing.Mapping[str, typing.Any],
        attributeName: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[int]:
    value = attributeMap.get(attributeName)
    if value is None:
        return None

    try:
        return str(value).lower() == 'true'
    except:
        if reporter:
            reporter.addMessage(f'Ignoring invalid {attributeName} attribute "{value}"')
        return None

def _parseIntAttribute(
        attributeMap: typing.Mapping[str, typing.Any],
        attributeName: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[int]:
    value = attributeMap.get(attributeName)
    if value is None:
        return None

    try:
        return int(value)
    except:
        if reporter:
            reporter.addMessage(f'Ignoring invalid {attributeName} attribute "{value}"')
        return None

def _parseFloatAttribute(
        attributeMap: typing.Mapping[str, typing.Any],
        attributeName: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[int]:
    value = attributeMap.get(attributeName)
    if value is None:
        return None

    try:
        return float(value)
    except:
        if reporter:
            reporter.addMessage(f'Ignoring invalid {attributeName} attribute "{value}"')
        return None

def _parseSystemHexAttribute(
        attributeMap: typing.Mapping[str, typing.Any],
        attributeName: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Tuple[typing.Optional[int], typing.Optional[int]]:
    value = attributeMap.get(attributeName)
    if value is None:
        return (None, None)

    x, y = survey.parseHexString(string=value, reporter=reporter)
    if x is None or y is None:
        if reporter:
            reporter.addMessage(f'Ignoring invalid {attributeName} attribute "{value}"')
        return (None, None)
    return (x, y)

def _parseAllegianceCodeAttribute(
        attributeMap: typing.Mapping[str, typing.Any],
        attributeName: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    value = attributeMap.get(attributeName)
    if value is None:
        return None
    return survey.parseAllegianceCodeString(string=value, reporter=reporter)

def _parseAllegianceNameAttribute(
        attributeMap: typing.Mapping[str, typing.Any],
        attributeName: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    value = attributeMap.get(attributeName)
    if value is None:
        return None
    return survey.parseAllegianceNameString(string=value, reporter=reporter)

def _parseLineWidthAttribute(
        attributeMap: typing.Mapping[str, typing.Any],
        attributeName: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[float]:
    value = attributeMap.get(attributeName)
    if value is None:
        return None

    try:
        width = float(value)
    except:
        if reporter:
            reporter.addMessage(f'Ignoring invalid {attributeName} attribute "{value}"')
        return None

    if width < 0:
        if reporter:
            reporter.addMessage(f'Ignoring negative {attributeName} attribute "{value}"')
        return None

    return width

def _parseLineStyleAttribute(
        attributeMap: typing.Mapping[str, typing.Any],
        attributeName: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    value = attributeMap.get(attributeName)
    if value is None:
        return None
    return survey.parseLineStyleString(string=value, reporter=reporter)

def _parseLabelHexAttribute(
        attributeMap: typing.Mapping[str, typing.Any],
        attributeName: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Tuple[typing.Optional[int], typing.Optional[int]]:
    value = attributeMap.get(attributeName)
    if value is None:
        return (None, None)

    x, y = survey.parseHexString(string=value, allowInvalid=True, reporter=reporter)
    if x is None or y is None:
        if reporter:
            reporter.addMessage(f'Ignoring invalid {attributeName} attribute "{value}"')
        return (None, None)
    return (x, y)

def _parseLabelSizeAttribute(
        attributeMap: typing.Mapping[str, typing.Any],
        attributeName: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    value = attributeMap.get(attributeName)
    if value is None:
        return None
    return survey.parseLabelSizeString(string=value, reporter=reporter)

def _parseHtmlColourAttribute(
        attributeMap: typing.Mapping[str, typing.Any],
        attributeName: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    value = attributeMap.get(attributeName)
    if value is None:
        return None
    return survey.parseHtmlColourString(string=value, reporter=reporter)

def detectMetadataFormat(content: str) -> typing.Optional[MetadataFormat]:
    try:
        xml.etree.ElementTree.fromstring(content)
        return MetadataFormat.XML
    except:
        pass

    try:
        json.loads(content)
        return MetadataFormat.JSON
    except:
        pass

    return None

def parseMetadata(
        content: str,
        format: typing.Optional[MetadataFormat] = None,
        reporter: typing.Optional[common.Reporter] = None
        ) -> survey.RawMetadata:
    if format is None:
        format = detectMetadataFormat(content=content)
        if format is None:
            raise ValueError('Unable to detect metadata format')

    if format == MetadataFormat.XML:
        return parseXMLMetadata(content=content, reporter=reporter)
    elif format == MetadataFormat.JSON:
        return parseJSONMetadata(content=content, reporter=reporter)

    raise RuntimeError(f'Unknown metadata format {format}')

def parseXMLMetadata(
        content: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> survey.RawMetadata:
    sectorElement = xml.etree.ElementTree.fromstring(content)

    nameElements = sectorElement.findall('./Name')
    if not nameElements:
        raise RuntimeError('Failed to find Name element in metadata')

    names = []
    nameLanguages = {}
    for element in nameElements:
        name = element.text
        names.append(name)

        lang = element.attrib.get('Lang')
        if lang != None:
            nameLanguages[name] = lang

    xElement = sectorElement.find('./X')
    if xElement == None:
        raise RuntimeError('Failed to find X element in metadata')
    try:
        x = int(xElement.text)
    except Exception as ex:
        raise RuntimeError(f'Failed to convert X value "{xElement.text}" to int in metadata ({str(ex)})')

    yElement = sectorElement.find('./Y')
    if yElement == None:
        raise RuntimeError('Failed to find Y element in metadata')
    try:
        y = int(yElement.text)
    except Exception as ex:
        raise RuntimeError(f'Failed to convert Y value "{yElement.text}" to int in metadata ({str(ex)})')

    subsectorElements = sectorElement.findall('./Subsectors/Subsector')
    subsectorNames = None
    if subsectorElements:
        subsectorNames = {}
        for index, element in enumerate(subsectorElements):
            if reporter:
                reporter.pushPrefix(f'Subsector {index + 1}: ')

            try:
                code = _parseStringAttribute(element, 'Index', reporter)
                if not code:
                    if reporter:
                        reporter.addMessage('Ignoring Subsector with no valid Index attribute')
                    continue
                upperCode = code.upper()
                if len(code) != 1 or (ord(upperCode) < ord('A') or ord(upperCode) > ord('P')):
                    if reporter:
                        reporter.addMessage(f'Ignoring Subsector with invalid Index "{code}"')
                    continue

                if not element.text:
                    # NOTE: This is silently ignored as the stock data does it a LOT when
                    # there is a subsector with no name
                    #if reporter:
                    #    reporter.addMessage('Ignoring Subsector with no name text')
                    continue

                subsectorNames[code] = element.text
            finally:
                if reporter:
                    reporter.popPrefix()

    allegianceElements = sectorElement.findall('./Allegiances/Allegiance')
    allegiances = None
    if allegianceElements:
        allegiances = []
        for index, element in enumerate(allegianceElements):
            if reporter:
                reporter.pushPrefix(f'Allegiance {index + 1}: ')

            try:
                code = _parseAllegianceCodeAttribute(element, 'Code', reporter)
                if not code:
                    if reporter:
                        reporter.addMessage('Ignoring Allegiance with no valid Code attribute')
                    continue

                if not element.text:
                    if reporter:
                        reporter.addMessage('Ignoring Allegiance with no name text')
                    continue
                name = survey.parseAllegianceNameString(
                    string=element.text,
                    reporter=reporter)
                if not name:
                    if reporter:
                        reporter.addMessage('Ignoring Allegiance with invalid name')
                    continue

                allegiances.append(survey.RawAllegiance(
                    code=code,
                    name=name,
                    base=_parseAllegianceCodeAttribute(element, 'Base', reporter)))
            finally:
                if reporter:
                    reporter.popPrefix()

    routeElements = sectorElement.findall('./Routes/Route')
    routes = None
    if routeElements:
        routes = []
        for index, element in enumerate(routeElements):
            if reporter:
                reporter.pushPrefix(f'Route {index + 1}: ')

            try:
                startHexX, startHexY = _parseSystemHexAttribute(element, 'Start', reporter)
                if startHexX is None or startHexY is None:
                    if reporter:
                        reporter.addMessage(f'Ignoring Route with no valid Start attribute')
                    continue

                endHexX, endHexY = _parseSystemHexAttribute(element, 'End', reporter)
                if endHexX is None or endHexY is None:
                    if reporter:
                        reporter.addMessage(f'Ignoring Route with no valid End attribute')
                    continue

                routes.append(survey.RawRoute(
                    startHexX=startHexX,
                    startHexY=startHexY,
                    endHexX=endHexX,
                    endHexY=endHexY,
                    startOffsetX=_parseIntAttribute(element, 'StartOffsetX', reporter),
                    startOffsetY=_parseIntAttribute(element, 'StartOffsetY', reporter),
                    endOffsetX=_parseIntAttribute(element, 'EndOffsetX', reporter),
                    endOffsetY=_parseIntAttribute(element, 'EndOffsetY', reporter),
                    allegianceCode=_parseAllegianceCodeAttribute(element, 'Allegiance', reporter),
                    type=_parseStringAttribute(element, 'Type', reporter),
                    style=_parseLineStyleAttribute(element, 'Style', reporter),
                    colour=_parseHtmlColourAttribute(element, 'Color', reporter),
                    width=_parseLineWidthAttribute(element, 'Width', reporter)))
            finally:
                if reporter:
                    reporter.popPrefix()

    borderElements = sectorElement.findall('./Borders/Border')
    borders = None
    if borderElements:
        borders = []
        for index, element in enumerate(borderElements):
            if reporter:
                reporter.pushPrefix(f'Border {index + 1}: ')

            try:
                if not element.text:
                    if reporter:
                        reporter.addMessage(f'Ignoring Border with no Path string')
                    continue
                path = survey.parseHexListString(
                    string=element.text,
                    allowInvalid=True,
                    reporter=reporter)
                if not path:
                    if reporter:
                        reporter.addMessage(f'Ignoring Border with empty path')
                    continue

                labelHexX, labelHexY = _parseLabelHexAttribute(element, 'LabelPosition', reporter)

                borders.append(survey.RawBorder(
                    hexes=path,
                    allegianceCode=_parseAllegianceCodeAttribute(element, 'Allegiance', reporter),
                    showLabel=_parseBoolAttribute(element, 'ShowLabel', reporter),
                    wrapLabel=_parseBoolAttribute(element, 'WrapLabel', reporter),
                    labelHexX=labelHexX,
                    labelHexY=labelHexY,
                    labelOffsetX=_parseFloatAttribute(element, 'LabelOffsetX', reporter),
                    labelOffsetY=_parseFloatAttribute(element, 'LabelOffsetY', reporter),
                    label=_parseStringAttribute(element, 'Label', reporter),
                    style=_parseLineStyleAttribute(element, 'Style', reporter),
                    colour=_parseHtmlColourAttribute(element, 'Color', reporter)))
            finally:
                if reporter:
                    reporter.popPrefix()

    regionElements = sectorElement.findall('./Regions/Region')
    regions = None
    if regionElements:
        regions = []
        for index, element in enumerate(regionElements):
            if reporter:
                reporter.pushPrefix(f'Region {index + 1}: ')

            try:
                if not element.text:
                    if reporter:
                        reporter.addMessage(f'Ignoring Region with no Path string')
                    continue
                path = survey.parseHexListString(
                    string=element.text,
                    allowInvalid=True,
                    reporter=reporter)
                if not path:
                    if reporter:
                        reporter.addMessage(f'Ignoring Region with empty path')
                    continue

                labelHexX, labelHexY = _parseLabelHexAttribute(element, 'LabelPosition', reporter)

                regions.append(survey.RawRegion(
                    hexes=path,
                    showLabel=_parseBoolAttribute(element, 'ShowLabel', reporter),
                    wrapLabel=_parseBoolAttribute(element, 'WrapLabel', reporter),
                    labelHexX=labelHexX,
                    labelHexY=labelHexY,
                    labelOffsetX=_parseFloatAttribute(element, 'LabelOffsetX', reporter),
                    labelOffsetY=_parseFloatAttribute(element, 'LabelOffsetY', reporter),
                    label=_parseStringAttribute(element, 'Label', reporter),
                    colour=_parseHtmlColourAttribute(element, 'Color', reporter)))
            finally:
                if reporter:
                    reporter.popPrefix()

    labelElements = sectorElement.findall('./Labels/Label')
    labels = None
    if labelElements:
        labels = []
        for index, element in enumerate(labelElements):
            if reporter:
                reporter.pushPrefix(f'Label {index + 1}: ')

            try:
                if not element.text:
                    if reporter:
                        reporter.addMessage(f'Ignoring Label with no text string')
                    continue

                hexX, hexY = _parseLabelHexAttribute(element, 'Hex', reporter)
                if hexX is None or hexY is None:
                    if reporter:
                        reporter.addMessage(f'Ignoring Label with no valid Hex attribute')
                    continue

                labels.append(survey.RawLabel(
                    text=element.text,
                    hexX=hexX,
                    hexY=hexY,
                    colour=_parseHtmlColourAttribute(element, 'Color', reporter),
                    size=_parseLabelSizeAttribute(element, 'Size', reporter),
                    wrap=_parseBoolAttribute(element, 'Wrap', reporter),
                    offsetX=_parseFloatAttribute(element, 'OffsetX', reporter),
                    offsetY=_parseFloatAttribute(element, 'OffsetY', reporter)))
            finally:
                if reporter:
                    reporter.popPrefix()

    creditsElement = sectorElement.find('./Credits')
    dataFileElement = sectorElement.find('./DataFile')
    productsElements = sectorElement.findall('./Product')
    sources = None
    if creditsElement is not None or dataFileElement is not None or productsElements is not None:
        credits = None
        if creditsElement is not None and creditsElement.text:
            credits = creditsElement.text

        primary = None
        if dataFileElement is not None:
            if reporter:
                reporter.pushPrefix('DataFile: ')

            try:
                publication = _parseStringAttribute(dataFileElement, 'Source', reporter)
                author = _parseStringAttribute(dataFileElement, 'Author', reporter)
                publisher = _parseStringAttribute(dataFileElement, 'Publisher', reporter)
                reference = _parseStringAttribute(dataFileElement, 'Ref', reporter)
                if publication or author or publisher or reference:
                    primary = survey.RawSource(
                        publication=publication,
                        author=author,
                        publisher=publisher,
                        reference=reference)
            finally:
                if reporter:
                    reporter.popPrefix()

        products = None
        if productsElements is not None:
            products = []
            for index, element in enumerate(productsElements):
                if reporter:
                    reporter.pushPrefix(f'Product {index + 1}: ')

                try:
                    publication = _parseStringAttribute(element, 'Title', reporter)
                    author = _parseStringAttribute(element, 'Author', reporter)
                    publisher = _parseStringAttribute(element, 'Publisher', reporter)
                    reference = _parseStringAttribute(element, 'Ref', reporter)
                    if publication or author or publisher or reference:
                        products.append(survey.RawSource(
                            publication=publication,
                            author=author,
                            publisher=publisher,
                            reference=reference))
                finally:
                    if reporter:
                        reporter.popPrefix()

        if credits or primary or products:
            sources = survey.RawSources(
                credits=credits,
                primary=primary,
                products=products)

    styleSheetElement = sectorElement.find('./Stylesheet')
    styleSheet = None
    if styleSheetElement is not None and styleSheetElement.text is not None:
        if reporter:
            reporter.pushPrefix('Style Sheet: ')

        try:
            styleSheet = survey.parseStyleSheet(
                content=styleSheetElement.text,
                reporter=reporter)
        finally:
            if reporter:
                reporter.popPrefix()

    if reporter:
        reporter.pushPrefix('Sector: ')

    tags = _parseStringAttribute(sectorElement, 'Tags', reporter)
    if tags is not None:
        tags = tags.split(' ')

    try:
        return survey.RawMetadata(
            x=x,
            y=y,
            canonicalName=names[0],
            alternateNames=names[1:],
            nameLanguages=nameLanguages,
            abbreviation=_parseStringAttribute(sectorElement, 'Abbreviation', reporter),
            sectorLabel=_parseStringAttribute(sectorElement, 'Label', reporter),
            subsectorNames=subsectorNames,
            selected=_parseBoolAttribute(sectorElement, 'Selected', reporter),
            tags=tags,
            allegiances=allegiances,
            routes=routes,
            borders=borders,
            labels=labels,
            regions=regions,
            sources=sources,
            styleSheet=styleSheet)
    finally:
        if reporter:
            reporter.popPrefix()

def parseJSONMetadata(
        content: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> survey.RawMetadata:
    sectorElement = json.loads(content)

    nameElements = sectorElement.get('Names')
    if not nameElements:
        raise RuntimeError('Failed to find Names element in metadata')

    names = []
    nameLanguages = {}
    for index, element in enumerate(nameElements):
        if reporter:
            reporter.pushPrefix(f'Sector Name {index + 1}: ')

        try:
            name = _parseStringAttribute(element, 'Text', reporter)
            if not name:
                if reporter:
                    reporter.addMessage('Ignoring Sector Name with no valid Text attribute')
                continue
            names.append(name)

            lang = _parseStringAttribute(element, 'Lang', reporter)
            if lang:
                nameLanguages[name] = str(lang)
        finally:
            if reporter:
                reporter.popPrefix()

    x = sectorElement.get('X')
    if x == None:
        raise RuntimeError('Failed to find X element in metadata')
    try:
        x = int(x)
    except Exception as ex:
        raise RuntimeError(f'Failed to convert X value "{x}" to int in metadata ({str(ex)})')

    y = sectorElement.get('Y')
    if y == None:
        raise RuntimeError('Failed to find Y element in metadata')
    try:
        y = int(y)
    except Exception as ex:
        raise RuntimeError(f'Failed to convert Y value "{y}" to int in metadata ({str(ex)})')

    subsectorElements = sectorElement.get('Subsectors')
    subsectorNames = None
    if subsectorElements:
        subsectorNames = {}
        if subsectorElements:
            for index, element in enumerate(subsectorElements):
                if reporter:
                    reporter.pushPrefix(f'Subsector {index + 1}: ')

                try:
                    code = _parseStringAttribute(element, 'Index', reporter)
                    if not code:
                        if reporter:
                            reporter.addMessage('Ignoring Subsector with no valid Index attribute')
                        continue
                    upperCode = code.upper()
                    if len(code) != 1 or (ord(upperCode) < ord('A') or ord(upperCode) > ord('P')):
                        if reporter:
                            reporter.addMessage(f'Ignoring Subsector with invalid Index "{code}"')
                        continue

                    name = _parseStringAttribute(element, 'Name', reporter)
                    if not name:
                        if reporter:
                            reporter.addMessage(f'Ignoring Subsector with no valid Name attribute')
                        continue

                    subsectorNames[code] = name
                finally:
                    if reporter:
                        reporter.popPrefix()

    allegianceElements = sectorElement.get('Allegiances')
    allegiances = None
    if allegianceElements:
        allegiances = []
        if allegianceElements:
            for index, element in enumerate(allegianceElements):
                if reporter:
                    reporter.pushPrefix(f'Allegiance {index + 1}: ')

                try:
                    code = _parseAllegianceCodeAttribute(element, 'Code', reporter)
                    if not code:
                        if reporter:
                            reporter.addMessage('Ignoring Allegiance with no valid Code attribute')
                        continue

                    name = _parseAllegianceNameAttribute(element, 'Name', reporter)
                    if not name:
                        if reporter:
                            reporter.addMessage('Ignoring Allegiance with no valid Name attribute')
                        continue

                    allegiances.append(survey.RawAllegiance(
                        code=code,
                        name=name,
                        base=_parseAllegianceCodeAttribute(element, 'Base', reporter)))
                finally:
                    if reporter:
                        reporter.popPrefix()

    routeElements = sectorElement.get('Routes')
    routes = None
    if routeElements:
        routes = []
        for index, element in enumerate(routeElements):
            if reporter:
                reporter.pushPrefix(f'Route {index + 1}: ')

            try:
                startHexX, startHexY = _parseSystemHexAttribute(element, 'Start', reporter)
                if startHexX is None or startHexY is None:
                    if reporter:
                        reporter.addMessage(f'Ignoring Route with no valid Start attribute')
                    continue

                endHexX, endHexY = _parseSystemHexAttribute(element, 'End', reporter)
                if endHexX is None or endHexY is None:
                    if reporter:
                        reporter.addMessage(f'Ignoring Route with no valid End attribute')
                    continue

                routes.append(survey.RawRoute(
                    startHexX=startHexX,
                    startHexY=startHexY,
                    endHexX=endHexX,
                    endHexY=endHexY,
                    startOffsetX=_parseIntAttribute(element, 'StartOffsetX', reporter),
                    startOffsetY=_parseIntAttribute(element, 'StartOffsetY', reporter),
                    endOffsetX=_parseIntAttribute(element, 'EndOffsetX', reporter),
                    endOffsetY=_parseIntAttribute(element, 'EndOffsetY', reporter),
                    allegianceCode=_parseAllegianceCodeAttribute(element, 'Allegiance', reporter),
                    type=_parseStringAttribute(element, 'Type', reporter),
                    style=_parseLineStyleAttribute(element, 'Style', reporter),
                    colour=_parseHtmlColourAttribute(element, 'Color', reporter),
                    width=_parseLineWidthAttribute(element, 'Width', reporter)))
            finally:
                if reporter:
                    reporter.popPrefix()

    borderElements = sectorElement.get('Borders')
    borders = None
    if borderElements:
        borders = []
        for index, element in enumerate(borderElements):
            if reporter:
                reporter.pushPrefix(f'Border {index + 1}: ')

            try:
                path = _parseStringAttribute(element, 'Path', reporter)
                if not path:
                    if reporter:
                        reporter.addMessage(f'Ignoring Border with no valid Path attribute')
                    continue
                path = survey.parseHexListString(
                    string=path,
                    allowInvalid=True,
                    reporter=reporter)
                if not path:
                    if reporter:
                        reporter.addMessage(f'Ignoring Border with empty path')
                    continue

                labelHexX, labelHexY = _parseLabelHexAttribute(element, 'LabelPosition', reporter)

                borders.append(survey.RawBorder(
                    hexes=path,
                    allegianceCode=_parseAllegianceCodeAttribute(element, 'Allegiance', reporter),
                    showLabel=_parseBoolAttribute(element, 'ShowLabel', reporter),
                    wrapLabel=_parseBoolAttribute(element, 'WrapLabel', reporter),
                    labelHexX=labelHexX,
                    labelHexY=labelHexY,
                    labelOffsetX=_parseFloatAttribute(element, 'LabelOffsetX', reporter),
                    labelOffsetY=_parseFloatAttribute(element, 'LabelOffsetY', reporter),
                    label=_parseStringAttribute(element, 'Label', reporter),
                    style=_parseLineStyleAttribute(element, 'Style', reporter),
                    colour=_parseHtmlColourAttribute(element, 'Color', reporter)))
            finally:
                if reporter:
                    reporter.popPrefix()

    regionElements = sectorElement.get('Regions')
    regions = None
    if regionElements:
        regions = []
        for index, element in enumerate(regionElements):
            if reporter:
                reporter.pushPrefix(f'Region {index + 1}: ')

            try:
                path = _parseStringAttribute(element, 'Path', reporter)
                if not path:
                    if reporter:
                        reporter.addMessage(f'Ignoring Region with no valid Path attribute')
                    continue
                path = survey.parseHexListString(
                    string=path,
                    allowInvalid=True,
                    reporter=reporter)
                if not path:
                    if reporter:
                        reporter.addMessage(f'Ignoring Region with empty path')
                    continue

                labelHexX, labelHexY = _parseLabelHexAttribute(element, 'LabelPosition', reporter)

                regions.append(survey.RawRegion(
                    hexes=path,
                    showLabel=_parseBoolAttribute(element, 'ShowLabel', reporter),
                    wrapLabel=_parseBoolAttribute(element, 'WrapLabel', reporter),
                    labelHexX=labelHexX,
                    labelHexY=labelHexY,
                    labelOffsetX=_parseFloatAttribute(element, 'LabelOffsetX', reporter),
                    labelOffsetY=_parseFloatAttribute(element, 'LabelOffsetY', reporter),
                    label=_parseStringAttribute(element, 'Label', reporter),
                    colour=_parseHtmlColourAttribute(element, 'Color', reporter)))
            finally:
                if reporter:
                    reporter.popPrefix()

    labelElements = sectorElement.get('Labels')
    labels = None
    if labelElements:
        labels = []
        for index, element in enumerate(labelElements):
            if reporter:
                reporter.pushPrefix(f'Label {index + 1}: ')

            try:
                text = _parseStringAttribute(element, 'Text', reporter)
                if not text:
                    if reporter:
                        reporter.addMessage(f'Ignoring Label with no valid Text attribute')
                    continue

                hexX, hexY = _parseLabelHexAttribute(element, 'Hex', reporter)
                if hexX is None or hexY is None:
                    if reporter:
                        reporter.addMessage(f'Ignoring Label with no valid Hex attribute')
                    continue

                labels.append(survey.RawLabel(
                    text=text,
                    hexX=hexX,
                    hexY=hexY,
                    colour=_parseHtmlColourAttribute(element, 'Color', reporter),
                    size=_parseLabelSizeAttribute(element, 'Size', reporter),
                    wrap=_parseBoolAttribute(element, 'Wrap',  reporter),
                    offsetX=_parseFloatAttribute(element, 'OffsetX', reporter),
                    offsetY=_parseFloatAttribute(element, 'OffsetY', reporter)))
            finally:
                if reporter:
                    reporter.popPrefix()

    # NOTE: Credits aren't currently supported for JSON format as I don't
    # know what structure they use. The Traveller Map metadata API always
    # returns an empty list
    primaryElements = sectorElement.get('DataFile')
    productsElements = sectorElement.get('Products')
    sources = None
    if primaryElements != None or productsElements != None:
        primary = None
        if primaryElements != None:
            if reporter:
                reporter.pushPrefix('DataFile: ')

            try:
                publication = _parseStringAttribute(primaryElements, 'Source', reporter)
                author = _parseStringAttribute(primaryElements, 'Author', reporter)
                publisher = _parseStringAttribute(primaryElements, 'Publisher', reporter)
                reference = _parseStringAttribute(primaryElements, 'Ref', reporter)
                if publication or author or publisher or reference:
                    primary = survey.RawSource(
                        publication=publication,
                        author=author,
                        publisher=publisher,
                        reference=reference)
            finally:
                if reporter:
                    reporter.popPrefix()

        products = None
        if productsElements != None:
            products = []
            for index, element in enumerate(productsElements):
                if reporter:
                    reporter.pushPrefix(f'Product {index + 1}: ')

                try:
                    publication = _parseStringAttribute(primaryElements, 'Title', reporter)
                    author = _parseStringAttribute(primaryElements, 'Author', reporter)
                    publisher = _parseStringAttribute(primaryElements, 'Publisher', reporter)
                    reference = _parseStringAttribute(primaryElements, 'Ref', reporter)
                    if publication or author or publisher or reference:
                        products.append(survey.RawSource(
                            publication=publication,
                            author=author,
                            publisher=publisher,
                            reference=reference))
                finally:
                    if reporter:
                        reporter.popPrefix()

        if primary or products:
            sources = survey.RawSources(
                credits=None,
                primary=primary,
                products=products)

    if reporter:
        reporter.pushPrefix('Sector: ')

    tags = _parseStringAttribute(sectorElement, 'Tags', reporter)
    if tags is not None:
        tags = tags.split(' ')

    try:
        return survey.RawMetadata(
            x=x,
            y=y,
            canonicalName=names[0],
            alternateNames=names[1:],
            nameLanguages=nameLanguages,
            abbreviation=_parseStringAttribute(sectorElement, 'Abbreviation', reporter),
            sectorLabel=_parseStringAttribute(sectorElement, 'Label', reporter),
            subsectorNames=subsectorNames,
            selected=_parseBoolAttribute(sectorElement, 'Selected', reporter),
            tags=tags,
            allegiances=allegiances,
            routes=routes,
            borders=borders,
            labels=labels,
            regions=regions,
            sources=sources,
            # Style sheets aren't supported for JSON metadata as I've no idea what they look
            # like as Traveller Map doesn't include them
            styleSheet=None)
    finally:
        if reporter:
            reporter.popPrefix()

def formatMetadata(
        metadata: survey.RawMetadata,
        format: MetadataFormat,
        reporter: typing.Optional[common.Reporter] = None
        ) -> str:
    if format == MetadataFormat.XML:
        return formatXMLMetadata(metadata=metadata, reporter=reporter)
    elif format == MetadataFormat.JSON:
        return formatJSONMetadata(metadata=metadata, reporter=reporter)

    raise RuntimeError(f'Unknown metadata format {format}')

def formatXMLMetadata(
        metadata: survey.RawMetadata,
        reporter: typing.Optional[common.Reporter] = None
        ) -> str:
    sectorAttributes = {}

    if metadata.selected() is not None:
        sectorAttributes['Selected'] = str(metadata.selected()).lower()

    # NOTE: The Traveller Map documentation doesn't mention Tags or Abbreviation for the XML
    # format but the XSD does have them
    # https://travellermap.com/doc/metadata
    if metadata.tags() is not None:
        sectorAttributes['Tags'] = ' '.join(metadata.tags())

    if metadata.abbreviation() is not None:
        sectorAttributes['Abbreviation'] = metadata.abbreviation()

    if metadata.sectorLabel() is not None:
        sectorAttributes['Label'] = metadata.sectorLabel()

    sectorElement = xml.etree.ElementTree.Element('Sector', sectorAttributes)

    names = [metadata.canonicalName()]
    if metadata.alternateNames():
        names.extend(metadata.alternateNames())
    for name in names:
        attributes = {}
        language = metadata.nameLanguage(name)
        if language is not None:
            attributes['Lang'] = language

        nameElement = xml.etree.ElementTree.SubElement(sectorElement, 'Name', attributes)
        nameElement.text = name

    xElement = xml.etree.ElementTree.SubElement(sectorElement, 'X')
    xElement.text = str(metadata.x())

    yElement = xml.etree.ElementTree.SubElement(sectorElement, 'Y')
    yElement.text = str(metadata.y())

    subsectorNames = metadata.subsectorNames()
    if subsectorNames:
        subsectorsElement = xml.etree.ElementTree.SubElement(sectorElement, 'Subsectors')
        for code, name in subsectorNames.items():
            attributes = {'Index': code}
            subsectorElement = xml.etree.ElementTree.SubElement(subsectorsElement, 'Subsector', attributes)
            subsectorElement.text = name

    allegiances = metadata.allegiances()
    if allegiances:
        allegiancesElement = xml.etree.ElementTree.SubElement(sectorElement, 'Allegiances')
        for allegianceCode in sorted(allegiances, key=lambda a: a.code()):
            attributes = {}

            code = survey.formatAllegianceCodeString(
                string=allegianceCode.code(),
                reporter=reporter)
            if code is not None:
                attributes['Code'] = code

            if allegianceCode.base() is not None:
                base = survey.formatAllegianceCodeString(
                    string=allegianceCode.base(),
                    reporter=reporter)
                if base is not None:
                    attributes['Base'] = base

            allegianceElement = xml.etree.ElementTree.SubElement(allegiancesElement, 'Allegiance', attributes)

            name = survey.formatAllegianceNameString(string=allegianceCode.name(), reporter=reporter)
            if name is not None:
                allegianceElement.text = name

    routes = metadata.routes()
    if routes:
        routesElement = xml.etree.ElementTree.SubElement(sectorElement, 'Routes')
        for index, route in enumerate(routes):
            if reporter:
                reporter.pushPrefix(f'Route {index + 1}: ')

            try:
                attributes = {}

                startHex = survey.formatHexString(
                    x=route.startHexX(),
                    y=route.startHexY(),
                    reporter=reporter)
                if startHex is not None:
                    attributes['Start'] = startHex

                endHex = survey.formatHexString(
                    x=route.endHexX(),
                    y=route.endHexY(),
                    reporter=reporter)
                if endHex is not None:
                    attributes['End'] = endHex

                if route.startOffsetX() is not None:
                    attributes['StartOffsetX'] = str(route.startOffsetX())
                if route.startOffsetY() is not None:
                    attributes['StartOffsetY'] = str(route.startOffsetY())
                if route.endOffsetX() is not None:
                    attributes['EndOffsetX'] = str(route.endOffsetX())
                if route.endOffsetY() is not None:
                    attributes['EndOffsetY'] = str(route.endOffsetY())
                if route.allegianceCode() is not None:
                    allegianceCode = survey.formatAllegianceCodeString(
                        string=route.allegianceCode(),
                        reporter=reporter)
                    if allegianceCode is not None:
                        attributes['Allegiance'] = allegianceCode
                if route.type() is not None:
                    attributes['Type'] = route.type()
                if route.style() is not None:
                    attributes['Style'] = route.style()
                if route.colour() is not None:
                    attributes['Color'] = route.colour()
                if route.width() is not None:
                    attributes['Width'] = str(route.width())

                xml.etree.ElementTree.SubElement(routesElement, 'Route', attributes)
            finally:
                if reporter:
                    reporter.popPrefix()

    borders = metadata.borders()
    if borders:
        bordersElement = xml.etree.ElementTree.SubElement(sectorElement, 'Borders')
        for index, border in enumerate(borders):
            if reporter:
                reporter.pushPrefix(f'Border {index + 1}: ')

            try:
                attributes = {}

                if border.allegianceCode():
                    allegianceCode = survey.formatAllegianceCodeString(
                        string=border.allegianceCode(),
                        reporter=reporter)
                    if allegianceCode:
                        attributes['Allegiance'] = allegianceCode
                # NOTE: Only write out show label and wrap if they are not the
                # default (true and false respectively)
                if border.showLabel() is not None and not border.showLabel():
                    attributes['ShowLabel'] = str(border.showLabel()).lower()
                if border.wrapLabel() is not None and border.wrapLabel():
                    attributes['WrapLabel'] = str(border.wrapLabel()).lower()
                if border.labelHexX() is not None and border.labelHexY()  is not None:
                    labelPosition = survey.formatHexString(
                        x=border.labelHexX(),
                        y=border.labelHexY(),
                        allowInvalid=True,
                        reporter=reporter)
                    if labelPosition is not None:
                        attributes['LabelPosition'] = labelPosition
                if border.labelOffsetX() is not None:
                    attributes['LabelOffsetX'] = common.formatNumber(
                        number=border.labelOffsetX(),
                        decimalPlaces=_XmlFloatDecimalPlaces)
                if border.labelOffsetY() is not None:
                    attributes['LabelOffsetY'] = common.formatNumber(
                        number=border.labelOffsetY(),
                        decimalPlaces=_XmlFloatDecimalPlaces)
                if border.label() is not None:
                    attributes['Label'] = border.label()
                if border.style() is not None:
                    attributes['Style'] = border.style()
                if border.colour() is not None:
                    attributes['Color'] = border.colour()

                borderElement = xml.etree.ElementTree.SubElement(bordersElement, 'Border', attributes)
                borderElement.text = survey.formatHexListString(
                    hexes=border.hexes(),
                    allowInvalid=True,
                    reporter=reporter)
            finally:
                if reporter:
                    reporter.popPrefix()

    regions = metadata.regions()
    if regions:
        regionsElement = xml.etree.ElementTree.SubElement(sectorElement, 'Regions')
        for index, region in enumerate(regions):
            if reporter:
                reporter.pushPrefix(f'Region {index + 1}: ')

            try:
                attributes = {}
                # NOTE: Only write out show label and wrap if they are not the
                # default (true and false respectively)
                if region.showLabel() is not None and not region.showLabel():
                    attributes['ShowLabel'] = str(region.showLabel()).lower()
                if region.wrapLabel() is not None and region.wrapLabel():
                    attributes['WrapLabel'] = str(region.wrapLabel()).lower()
                if region.labelHexX() is not None and region.labelHexY() is not None:
                    labelPosition = survey.formatHexString(
                        x=region.labelHexX(),
                        y=region.labelHexY(),
                        allowInvalid=True,
                        reporter=reporter)
                    if labelPosition is not None:
                        attributes['LabelPosition'] = labelPosition
                if region.labelOffsetX() is not None:
                    attributes['LabelOffsetX'] = common.formatNumber(
                        number=region.labelOffsetX(),
                        decimalPlaces=_XmlFloatDecimalPlaces)
                if region.labelOffsetY() is not None:
                    attributes['LabelOffsetY'] = common.formatNumber(
                        number=region.labelOffsetY(),
                        decimalPlaces=_XmlFloatDecimalPlaces)
                if region.label() is not None:
                    attributes['Label'] = region.label()
                if region.colour() is not None:
                    attributes['Color'] = region.colour()

                regionElement = xml.etree.ElementTree.SubElement(regionsElement, 'Region', attributes)
                regionElement.text = survey.formatHexListString(
                    hexes=region.hexes(),
                    allowInvalid=True,
                    reporter=reporter)
            finally:
                if reporter:
                    reporter.popPrefix()

    labels = metadata.labels()
    if labels:
        labelsElement = xml.etree.ElementTree.SubElement(sectorElement, 'Labels')
        for index, label in enumerate(labels):
            if reporter:
                reporter.pushPrefix(f'Label {index + 1}: ')

            try:
                attributes = {}

                hex = survey.formatHexString(
                    x=label.hexX(),
                    y=label.hexY(),
                    allowInvalid=True,
                    reporter=reporter)
                if hex is not None:
                    attributes['Hex'] = hex

                colour = survey.formatHtmlColourString(
                    string=label.colour(),
                    reporter=reporter)
                if colour is not None:
                    attributes['Color'] = colour

                if label.size() is not None:
                    attributes['Size'] = label.size()
                if label.wrap() is not None:
                    attributes['Wrap'] = str(label.wrap()).lower()
                if label.offsetX() is not None:
                    attributes['OffsetX'] = common.formatNumber(
                        number=label.offsetX(),
                        decimalPlaces=_XmlFloatDecimalPlaces)
                if label.offsetY() is not None:
                    attributes['OffsetY'] = common.formatNumber(
                        number=label.offsetY(),
                        decimalPlaces=_XmlFloatDecimalPlaces)

                labelElement = xml.etree.ElementTree.SubElement(labelsElement, 'Label', attributes)
                labelElement.text = label.text()
            finally:
                if reporter:
                    reporter.popPrefix()

    sources = metadata.sources()
    if sources:
        if sources.credits() is not None:
            creditsElement = xml.etree.ElementTree.SubElement(sectorElement, 'Credits')
            creditsElement.text = sources.credits()

        if sources.primary() is not None:
            primary = sources.primary()
            attributes = {}
            if primary.publication()is not None:
                attributes['Source'] = primary.publication()
            if primary.author() is not None:
                attributes['Author'] = primary.author()
            if primary.publisher() is not None:
                attributes['Publisher'] = primary.publisher()
            if primary.reference() is not None:
                attributes['Ref'] = primary.reference()

            if attributes:
                xml.etree.ElementTree.SubElement(sectorElement, 'DataFile', attributes)

        if sources.products():
            for product in sources.products():
                attributes = {}
                if product.publication() is not None:
                    attributes['Title'] = product.publication()
                if product.author() is not None:
                    attributes['Author'] = product.author()
                if product.publisher() is not None:
                    attributes['Publisher'] = product.publisher()
                if product.reference() is not None:
                    attributes['Ref'] = product.reference()

                if attributes:
                    xml.etree.ElementTree.SubElement(sectorElement, 'Product', attributes)

    # TODO: Writing style sheet is not supported. It would need a reverse of survey.readCssContent.
    # Currently there is no need for it as the conversion process flattens the style info
    """
    if metadata.styleSheet() != None:
        styleSheetElement = xml.etree.ElementTree.SubElement(sectorElement, 'StyleSheet')
        styleSheetElement.text = ''
    """

    xml.etree.ElementTree.indent(sectorElement, space="\t", level=0)
    resultBytes: bytes = xml.etree.ElementTree.tostring(
        element=sectorElement,
        encoding='utf-8',
        xml_declaration=True)
    return resultBytes.decode('utf-8')

def formatJSONMetadata(
        metadata: survey.RawMetadata,
        reporter: typing.Optional[common.Reporter] = None
        ) -> str:
    sectorElement = {}

    if metadata.selected() is not None:
        sectorElement['Selected'] = str(metadata.selected()).lower()

    if metadata.tags() is not None:
        sectorElement['Tags'] = ' '.join(metadata.tags())

    if metadata.abbreviation() is not None:
        sectorElement['Abbreviation'] = metadata.abbreviation()

    if metadata.sectorLabel() is not None:
        sectorElement['Label'] = metadata.sectorLabel()

    namesElement = []
    sectorElement['Names'] = namesElement

    names = [metadata.canonicalName()] + metadata.alternateNames()
    for name in names:
        nameElement = {'Text': name}
        language = metadata.nameLanguage(name)
        if language is not None:
            nameElement['Lang'] = language
        namesElement.append(nameElement)

    sectorElement['X'] = str(metadata.x())
    sectorElement['Y'] = str(metadata.y())

    subsectorNames = metadata.subsectorNames()
    if subsectorNames:
        subsectorsElement = []
        sectorElement['Subsectors'] = subsectorsElement
        for code, name in subsectorNames.items():
            subsectorElement = {
                'Name': name,
                'Index': code,
                'IndexNumber': ord(code) - ord('A')}
            subsectorsElement.append(subsectorElement)

    allegiances = metadata.allegiances()
    if allegiances:
        allegiancesElement = []
        sectorElement['Allegiances'] = allegiancesElement
        for allegianceCode in sorted(allegiances, key=lambda a: a.code()):
            allegianceElement = {}

            name = survey.formatAllegianceNameString(
                string=allegianceCode.name(),
                reporter=reporter)
            if name is not None:
                allegianceElement['Name'] = name

            code = survey.formatAllegianceCodeString(
                string=allegianceCode.code(),
                reporter=reporter)
            if code is not None:
                allegianceElement['Code'] = code

            if allegianceCode.base() is not None:
                base = survey.formatAllegianceCodeString(
                    string=allegianceCode.base(),
                    reporter=reporter)
                if base is not None:
                    allegianceElement['Base'] = base

            allegiancesElement.append(allegianceElement)

    routes = metadata.routes()
    if routes:
        routesElement = []
        sectorElement['Routes'] = routesElement
        for index, route in enumerate(routes):
            if reporter:
                reporter.pushPrefix(f'Route {index + 1}: ')

            try:
                routeElement = {}

                startHex = survey.formatHexString(
                    x=route.startHexX(),
                    y=route.startHexY(),
                    reporter=reporter)
                if startHex is not None:
                    routeElement['Start'] = startHex

                endHex = survey.formatHexString(
                    x=route.endHexX(),
                    y=route.endHexY(),
                    reporter=reporter)
                if endHex is not None:
                    routeElement['End'] = endHex

                if route.startOffsetX() is not None:
                    routeElement['StartOffsetX'] = route.startOffsetX()
                if route.startOffsetY() is not None:
                    routeElement['StartOffsetY'] = route.startOffsetY()
                if route.endOffsetX() is not None:
                    routeElement['EndOffsetX'] = route.endOffsetX()
                if route.endOffsetY() is not None:
                    routeElement['EndOffsetY'] = route.endOffsetY()
                if route.allegianceCode() is not None:
                    allegianceCode = survey.formatAllegianceCodeString(
                        string=route.allegianceCode(),
                        reporter=reporter)
                    if allegianceCode is not None:
                        routeElement['Allegiance'] = allegianceCode
                if route.type() is not None:
                    routeElement['Type'] = route.type()
                if route.style() is not None:
                    routeElement['Style'] = route.style()
                if route.colour() is not None:
                    routeElement['Color'] = route.colour()
                if route.width() is not None:
                    routeElement['Width'] = route.width()

                routesElement.append(routeElement)
            finally:
                if reporter:
                    reporter.popPrefix()

    borders = metadata.borders()
    if borders:
        bordersElement = []
        sectorElement['Borders'] = bordersElement
        for border in borders:
            if reporter:
                reporter.pushPrefix(f'Border {index + 1}: ')

            try:
                borderElement = {}

                path = survey.formatHexListString(
                    hexes=border.hexes(),
                    allowInvalid=True,
                    reporter=reporter)
                if path is not None:
                    borderElement['Path'] = path

                if border.allegianceCode() is not None:
                    allegianceCode = survey.formatAllegianceCodeString(
                        string=border.allegianceCode(),
                        reporter=reporter)
                    if allegianceCode:
                        borderElement['Allegiance'] = allegianceCode
                # NOTE: Only write out show label and wrap if they are not the
                # default (true and false respectively)
                if border.showLabel() is not None and not border.showLabel():
                    borderElement['ShowLabel'] = border.showLabel()
                if border.wrapLabel() is not None and border.wrapLabel():
                    borderElement['WrapLabel'] = border.wrapLabel()
                if border.labelHexX() is not None and border.labelHexY() is not None:
                    labelPosition = survey.formatHexString(
                        x=border.labelHexX(),
                        y=border.labelHexY(),
                        allowInvalid=True,
                        reporter=reporter)
                    if labelPosition is not None:
                        borderElement['LabelPosition'] = labelPosition
                if border.labelOffsetX() is not None:
                    borderElement['LabelOffsetX'] = border.labelOffsetX()
                if border.labelOffsetY() is not None:
                    borderElement['LabelOffsetY'] = border.labelOffsetY()
                if border.label() is not None:
                    borderElement['Label'] = border.label()
                if border.style() is not None:
                    borderElement['Style'] = border.style()
                if border.colour() is not None:
                    borderElement['Color'] = border.colour()

                bordersElement.append(borderElement)
            finally:
                if reporter:
                    reporter.popPrefix()

    regions = metadata.regions()
    if regions:
        regionsElement = []
        sectorElement['Regions'] = regionsElement
        for region in regions:
            if reporter:
                reporter.pushPrefix(f'Region {index + 1}: ')

            try:
                regionElement = {}

                path = survey.formatHexListString(
                    hexes=region.hexes(),
                    allowInvalid=True,
                    reporter=reporter)
                if path is not None:
                    regionElement['Path'] = path

                # NOTE: Only write out show label and wrap if they are not the
                # default (true and false respectively)
                if region.showLabel() is not None and not region.showLabel():
                    regionElement['ShowLabel'] = region.showLabel()
                if region.wrapLabel() is not None and region.wrapLabel():
                    regionElement['WrapLabel'] = region.wrapLabel()
                if region.labelHexX() is not None and region.labelHexY() is not None:
                    labelPosition = survey.formatHexString(
                        x=region.labelHexX(),
                        y=region.labelHexY(),
                        allowInvalid=True,
                        reporter=reporter)
                    if labelPosition is not None:
                        regionElement['LabelPosition'] = labelPosition
                if region.labelOffsetX() is not None:
                    regionElement['LabelOffsetX'] = region.labelOffsetX()
                if region.labelOffsetY() is not None:
                    regionElement['LabelOffsetY'] = region.labelOffsetY()
                if region.label() is not None:
                    regionElement['Label'] = region.label()
                if region.colour() is not None:
                    regionElement['Color'] = region.colour()

                regionsElement.append(regionElement)
            finally:
                if reporter:
                    reporter.popPrefix()

    labels = metadata.labels()
    if labels:
        labelsElement = []
        sectorElement['Labels'] = labelsElement
        for label in labels:
            if reporter:
                reporter.pushPrefix(f'Label {index + 1}: ')

            try:
                labelElement = {'Text': label.text()}

                hex = survey.formatHexString(
                    x=label.hexX(),
                    y=label.hexY(),
                    allowInvalid=True,
                    reporter=reporter)
                if hex is not None:
                    labelElement['Hex'] = hex

                colour = survey.formatHtmlColourString(string=label.colour(), reporter=reporter)
                if colour is not None:
                    labelElement['Color'] = colour

                if label.size() is not None:
                    labelElement['Size'] = label.size()

                if label.wrap() is not None:
                    labelElement['Wrap'] = label.wrap()

                if label.offsetX() is not None:
                    labelElement['OffsetX'] = label.offsetX()

                if label.offsetY() is not None:
                    labelElement['OffsetY'] = label.offsetY()

                labelsElement.append(labelsElement)
            finally:
                if reporter:
                    reporter.popPrefix()

    sources = metadata.sources()
    if sources:
        # NOTE: The Credits string isn't written out as I don't know what
        # format it's mean to be in for JSON. The Traveller Map metadata
        # API returns an empty array for sectors with credits when JSON
        # is requested

        if sources.primary():
            primary = sources.primary()
            primaryElement = {}
            if primary.publication() is not None:
                primaryElement['Source'] = primary.publication()
            if primary.author() is not None:
                primaryElement['Author'] = primary.author()
            if primary.publisher() is not None:
                primaryElement['Publisher'] = primary.publisher()
            if primary.reference() is not None:
                primaryElement['Ref'] = primary.reference()

            if primaryElement:
                sectorElement['DataFile'] = primaryElement

        if sources.products():
            productsElement = []
            for product in sources.products():
                productElement = {}
                if product.publication() is not None:
                    productElement['Title'] = product.publication()
                if product.author() is not None:
                    productElement['Author'] = product.author()
                if product.publisher() is not None:
                    productElement['Publisher'] = product.publisher()
                if product.reference() is not None:
                    productElement['Ref'] = product.reference()

                if productElement:
                    productsElement.append(productElement)

            if productsElement:
                sectorElement['Products'] = productsElement

    # NOTE: The JSON metadata returned by Traveller Map doesn't include
    # style sheet information
    """
    if metadata.styleSheet() != None:
        sectorElement['StyleSheet'] = metadata.styleSheet()
    """

    return json.dumps(sectorElement, indent=4)
