import enum
import common
import json
import logging
import survey
import typing
import xml.etree.ElementTree

class MetadataFormat(enum.Enum):
    JSON = 0
    XML = 1

_XmlFloatDecimalPlaces = 2

def _isAllDashes(string: str) -> bool:
    if not string:
        return False # Empty string isn't all dashes
    for c in string:
        if c != '-':
            return False
    return True

def _convertAttributeToBool(
        attributeMap: typing.Mapping[str, typing.Any],
        attributeName: str,
        elementName: str,
        elementIndex: typing.Optional[int] = None
        ) -> typing.Optional[int]:
    value = attributeMap.get(attributeName)
    if value == None:
        return None

    try:
        return str(value).lower() == 'true'
    except Exception as ex:
        raise RuntimeError('Failed to convert {attribute} attribute "{value}" to bool for {element} ({exception})'.format(
            attribute=attributeName,
            value=value,
            element=elementName if elementIndex is None else f'{elementName} {elementIndex}',
            exception=str(ex)))

def _convertAttributeToInt(
        attributeMap: typing.Mapping[str, typing.Any],
        attributeName: str,
        elementName: str,
        elementIndex: typing.Optional[int] = None
        ) -> typing.Optional[int]:
    value = attributeMap.get(attributeName)
    if value == None:
        return None

    try:
        return int(value)
    except Exception as ex:
        raise RuntimeError('Failed to convert {attribute} attribute "{value}" to int for {element} ({exception})'.format(
            attribute=attributeName,
            value=value,
            element=elementName if elementIndex is None else f'{elementName} {elementIndex}',
            exception=str(ex)))

def _convertAttributeToFloat(
        attributeMap: typing.Mapping[str, typing.Any],
        attributeName: str,
        elementName: str,
        elementIndex: typing.Optional[int] = None
        ) -> typing.Optional[int]:
    value = attributeMap.get(attributeName)
    if value == None:
        return None

    try:
        return float(value)
    except Exception as ex:
        raise RuntimeError('Failed to convert {attribute} attribute "{value}" to float for {element} ({exception})'.format(
            attribute=attributeName,
            value=value,
            element=elementName if elementIndex is None else f'{elementName} {elementIndex}',
            exception=str(ex)))

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
        ) -> survey.RawMetadata:
    if format is None:
        format = detectMetadataFormat(content=content)
        if format is None:
            raise ValueError('Unable to detect metadata format')

    if format == MetadataFormat.XML:
        return parseXMLMetadata(content=content)
    elif format == MetadataFormat.JSON:
        return parseJSONMetadata(content=content)

    raise RuntimeError(f'Unknown metadata format {format}')

def parseXMLMetadata(content: str) -> survey.RawMetadata:
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

    sectorLabelElement = sectorElement.find('./Label')
    sectorLabel = sectorLabelElement.text if sectorLabelElement != None else None

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
            code = element.get('Index')
            if code == None:
                raise RuntimeError(f'Failed to find Index attribute for Subsector {index} in metadata')

            upperCode = code.upper()
            if len(code) != 1 or (ord(upperCode) < ord('A') or ord(upperCode) > ord('P')):
                raise RuntimeError(f'Invalid Index attribute "{code}" for Subsector {index} in metadata')

            subsectorNames[code] = element.text

    allegianceElements = sectorElement.findall('./Allegiances/Allegiance')
    allegiances = None
    if allegianceElements:
        allegiances = []
        for index, element in enumerate(allegianceElements):
            code = element.get('Code')
            if code == None:
                raise RuntimeError(f'Failed to find Code attribute for Allegiance {index} in metadata')

            # Ignore allegiances that are just a sequence of '-'
            if code and not _isAllDashes(code):
                allegiances.append(survey.RawAllegiance(
                    code=code,
                    name=element.text,
                    base=element.get('Base')))

    routeElements = sectorElement.findall('./Routes/Route')
    routes = None
    if routeElements:
        routes = []
        for index, element in enumerate(routeElements):
            startHex = element.get('Start')
            if not startHex:
                raise RuntimeError(f'Failed to find Start attribute for Route {index} in metadata')

            endHex = element.get('End')
            if not endHex:
                raise RuntimeError(f'Failed to find End attribute for Route {index} in metadata')

            startOffsetX = _convertAttributeToInt(element, 'StartOffsetX', 'Route', index)
            startOffsetY = _convertAttributeToInt(element, 'StartOffsetY', 'Route', index)
            endOffsetX = _convertAttributeToInt(element, 'EndOffsetX', 'Route', index)
            endOffsetY = _convertAttributeToInt(element, 'EndOffsetY', 'Route', index)
            width = _convertAttributeToFloat(element, 'Width', 'Route', index)

            routes.append(survey.RawRoute(
                startHex=startHex,
                endHex=endHex,
                startOffsetX=startOffsetX,
                startOffsetY=startOffsetY,
                endOffsetX=endOffsetX,
                endOffsetY=endOffsetY,
                allegiance=element.get('Allegiance'),
                type=element.get('Type'),
                style=element.get('Style'),
                colour=element.get('Color'),
                width=width))

    borderElements = sectorElement.findall('./Borders/Border')
    borders = None
    if borderElements:
        borders = []
        for index, element in enumerate(borderElements):
            if not element.text:
                raise RuntimeError(f'No Path data specified for Border {index} in metadata')

            path = element.text.split(' ')
            showLabel = _convertAttributeToBool(element, 'ShowLabel', 'Border', index)
            wrapLabel = _convertAttributeToBool(element, 'WrapLabel', 'Border', index)
            labelOffsetX = _convertAttributeToFloat(element, 'LabelOffsetX', 'Border', index)
            labelOffsetY = _convertAttributeToFloat(element, 'LabelOffsetY', 'Border', index)

            borders.append(survey.RawBorder(
                hexList=path,
                allegiance=element.get('Allegiance'),
                showLabel=showLabel,
                wrapLabel=wrapLabel,
                labelHex=element.get('LabelPosition'),
                labelOffsetX=labelOffsetX,
                labelOffsetY=labelOffsetY,
                label=element.get('Label'),
                style=element.get('Style'),
                colour=element.get('Color')))

    labelElements = sectorElement.findall('./Labels/Label')
    labels = None
    if labelElements:
        labels = []
        for index, element in enumerate(labelElements):
            hex = element.get('Hex')
            if hex == None:
                raise RuntimeError(f'Failed to find Hex element for Label {index} in metadata')

            colour = element.get('Color')
            if colour == None:
                raise RuntimeError(f'Failed to find Color element for Label {index} in metadata')

            wrap = _convertAttributeToBool(element, 'Wrap', 'Label', index)
            offsetX = _convertAttributeToFloat(element, 'OffsetX', 'Label', index)
            offsetY = _convertAttributeToFloat(element, 'OffsetY', 'Label', index)

            labels.append(survey.RawLabel(
                text=element.text,
                hex=hex,
                colour=colour,
                size=element.get('Size'),
                wrap=wrap,
                offsetX=offsetX,
                offsetY=offsetY))

    regionElements = sectorElement.findall('./Regions/Region')
    regions = None
    if regionElements:
        regions = []
        for index, element in enumerate(regionElements):
            if not element.text:
                raise RuntimeError(f'No Path data specified for Region {index} in metadata')

            path = element.text.split(' ')
            showLabel = _convertAttributeToBool(element, 'ShowLabel', 'Region', index)
            wrapLabel = _convertAttributeToBool(element, 'WrapLabel', 'Region', index)
            labelOffsetX = _convertAttributeToFloat(element, 'LabelOffsetX', 'Region', index)
            labelOffsetY = _convertAttributeToFloat(element, 'LabelOffsetY', 'Region', index)

            regions.append(survey.RawRegion(
                hexList=path,
                showLabel=showLabel,
                wrapLabel=wrapLabel,
                labelHex=element.get('LabelPosition'),
                labelOffsetX=labelOffsetX,
                labelOffsetY=labelOffsetY,
                label=element.get('Label'),
                colour=element.get('Color')))

    creditsElements = sectorElement.find('./Credits')
    primaryElements = sectorElement.find('./DataFile')
    productsElements = sectorElement.findall('./Product')
    sources = None
    if creditsElements != None or primaryElements != None or productsElements != None:
        primary = None
        if primaryElements != None:
            publication = primaryElements.get('Source')
            author = primaryElements.get('Author')
            publisher = primaryElements.get('Publisher')
            reference = primaryElements.get('Ref')

            if publication or author or publisher or reference:
                primary = survey.RawSource(
                    publication=publication,
                    author=author,
                    publisher=publisher,
                    reference=reference)

        products = None
        if productsElements != None:
            products = []
            for element in productsElements:
                products.append(survey.RawSource(
                    publication=element.get('Title'),
                    author=element.get('Author'),
                    publisher=element.get('Publisher'),
                    reference=element.get('Ref')))

        sources = survey.RawSources(
            credits=creditsElements.text if creditsElements != None else None,
            primary=primary,
            products=products)

    styleSheetElement = sectorElement.find('./Stylesheet')
    styleSheet = styleSheetElement.text if styleSheetElement != None else None

    return survey.RawMetadata(
        canonicalName=names[0],
        alternateNames=names[1:],
        nameLanguages=nameLanguages,
        abbreviation=sectorElement.get('Abbreviation'),
        sectorLabel=sectorLabel,
        subsectorNames=subsectorNames,
        x=x,
        y=y,
        selected=_convertAttributeToBool(sectorElement, 'Selected', 'Sector'),
        tags=sectorElement.get('Tags'),
        allegiances=allegiances,
        routes=routes,
        borders=borders,
        labels=labels,
        regions=regions,
        sources=sources,
        styleSheet=styleSheet)

def parseJSONMetadata(content: str) -> survey.RawMetadata:
    sectorElement = json.loads(content)

    nameElements = sectorElement.get('Names')
    if not nameElements:
        raise RuntimeError('Failed to find Names element in metadata')

    names = []
    nameLanguages = {}
    for element in nameElements:
        name = element.get('Text')
        if name == None:
            logging.warning('Skipping name with no Text element in metadata')
            continue
        names.append(str(name))

        lang = element.get('Lang')
        if lang != None:
            nameLanguages[name] = str(lang)

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
            for element in subsectorElements:
                name = element.get('Name')
                if name == None:
                    raise RuntimeError('Failed to find Name element for Subsector in metadata')

                code = element.get('Index')
                if code == None:
                    raise RuntimeError('Failed to find Index element for Subsector in metadata')

                upperCode = code.upper()
                if len(code) != 1 or (ord(upperCode) < ord('A') or ord(upperCode) > ord('P')):
                    raise RuntimeError(f'Invalid Index attribute "{code}" for Subsector in metadata')

                subsectorNames[code] = name

    allegianceElements = sectorElement.get('Allegiances')
    allegiances = None
    if allegianceElements:
        allegiances = []
        if allegianceElements:
            for index, element in enumerate(allegianceElements):
                name = element.get('Name')
                if name == None:
                    raise RuntimeError('Failed to find Name element for Allegiance in metadata')

                code = element.get('Code')
                if code == None:
                    raise RuntimeError('Failed to find Code element for Allegiance in metadata')

                # Ignore allegiances that are just a sequence of '-'
                if code and not _isAllDashes(code):
                    allegiances.append(survey.RawAllegiance(
                        code=code,
                        name=name,
                        base=element.get('Base')))

    routeElements = sectorElement.get('Routes')
    routes = None
    if routeElements:
        routes = []
        for index, element in enumerate(routeElements):
            startHex = element.get('Start')
            if startHex == None:
                raise RuntimeError(f'Failed to find Start element for Route {index} in metadata')

            endHex = element.get('End')
            if endHex == None:
                raise RuntimeError(f'Failed to find End element for Route {index} in metadata')

            startOffsetX = _convertAttributeToInt(element, 'StartOffsetX', 'Route', index)
            startOffsetY = _convertAttributeToInt(element, 'StartOffsetY', 'Route', index)
            endOffsetX = _convertAttributeToInt(element, 'EndOffsetX', 'Route', index)
            endOffsetY = _convertAttributeToInt(element, 'EndOffsetY', 'Route', index)
            width = _convertAttributeToFloat(element, 'Width', 'Route', index)

            routes.append(survey.RawRoute(
                startHex=startHex,
                endHex=endHex,
                startOffsetX=startOffsetX,
                startOffsetY=startOffsetY,
                endOffsetX=endOffsetX,
                endOffsetY=endOffsetY,
                allegiance=element.get('Allegiance'),
                type=element.get('Type'),
                style=element.get('Style'),
                colour=element.get('Color'),
                width=width))

    borderElements = sectorElement.get('Borders')
    borders = None
    if borderElements:
        borders = []
        for index, element in enumerate(borderElements):
            path = element.get('Path')
            if path == None:
                raise RuntimeError(f'Failed to find Path element for Border {index} in metadata')
            path = path.split(' ')

            showLabel = _convertAttributeToBool(element, 'ShowLabel', 'Border', index)
            wrapLabel = _convertAttributeToBool(element, 'WrapLabel', 'Border', index)
            labelOffsetX = _convertAttributeToFloat(element, 'LabelOffsetX', 'Border', index)
            labelOffsetY = _convertAttributeToFloat(element, 'LabelOffsetY', 'Border', index)

            borders.append(survey.RawBorder(
                hexList=path,
                allegiance=element.get('Allegiance'),
                showLabel=showLabel,
                wrapLabel=wrapLabel,
                labelHex=element.get('LabelPosition'),
                labelOffsetX=labelOffsetX,
                labelOffsetY=labelOffsetY,
                label=element.get('Label'),
                style=element.get('Style'),
                colour=element.get('Color')))

    labelElements = sectorElement.get('Labels')
    labels = None
    if labelElements:
        labels = []
        for index, element in enumerate(labelElements):
            text = element.get('Text')
            if text == None:
                raise RuntimeError(f'Failed to find Text element for Label {index} in metadata')

            hex = element.get('Hex')
            if hex == None:
                raise RuntimeError(f'Failed to find Hex element for Label {index} in metadata')

            colour = element.get('Color')
            if colour == None:
                raise RuntimeError(f'Failed to find Color element for Label {index} in metadata')

            wrap = _convertAttributeToBool(element, 'Wrap', 'Label', index)
            offsetX = _convertAttributeToFloat(element, 'OffsetX', 'Label', index)
            offsetY = _convertAttributeToFloat(element, 'OffsetY', 'Label', index)

            labels.append(survey.RawLabel(
                text=text,
                hex=hex,
                colour=colour,
                size=element.get('Size'),
                wrap=wrap,
                offsetX=offsetX,
                offsetY=offsetY))

    regionElements = sectorElement.get('Regions')
    regions = None
    if regionElements:
        regions = []
        for index, element in enumerate(regionElements):
            path = element.get('Path')
            if path == None:
                raise RuntimeError(f'Failed to find Path element for Region {index} in metadata')
            path = path.split(' ')

            showLabel = _convertAttributeToBool(element, 'ShowLabel', 'Region', index)
            wrapLabel = _convertAttributeToBool(element, 'WrapLabel', 'Region', index)
            labelOffsetX = _convertAttributeToFloat(element, 'LabelOffsetX', 'Region', index)
            labelOffsetY = _convertAttributeToFloat(element, 'LabelOffsetY', 'Region', index)

            regions.append(survey.RawRegion(
                hexList=path,
                showLabel=showLabel,
                wrapLabel=wrapLabel,
                labelHex=element.get('LabelPosition'),
                labelOffsetX=labelOffsetX,
                labelOffsetY=labelOffsetY,
                label=element.get('Label'),
                colour=element.get('Color')))

    creditsElements = sectorElement.get('Credits')
    primaryElements = sectorElement.get('DataFile')
    productsElements = sectorElement.get('Products')
    sources = None
    if creditsElements != None or primaryElements != None or productsElements != None:
        primary = None
        if primaryElements != None:
            publication = primaryElements.get('Source')
            author = primaryElements.get('Author')
            publisher = primaryElements.get('Publisher')
            reference = primaryElements.get('Ref')

            if publication or author or publisher or reference:
                primary = survey.RawSource(
                    publication=publication,
                    author=author,
                    publisher=publisher,
                    reference=reference)

        products = None
        if productsElements != None:
            products = []
            for element in productsElements:
                products.append(survey.RawSource(
                    publication=element.get('Title'),
                    author=element.get('Author'),
                    publisher=element.get('Publisher'),
                    reference=element.get('Ref')))

        # NOTE: Credits aren't currently supported for JSON format as I don't
        # know what structure they use. The Traveller Map metadata API always
        # returns an empty list
        if primary or products:
            sources = survey.RawSources(
                credits=None,
                primary=primary,
                products=products)

    return survey.RawMetadata(
        canonicalName=names[0],
        alternateNames=names[1:],
        nameLanguages=nameLanguages,
        abbreviation=sectorElement.get('Abbreviation'),
        sectorLabel=sectorElement.get('Label'),
        subsectorNames=subsectorNames,
        x=x,
        y=y,
        selected=_convertAttributeToBool(sectorElement, 'Selected', 'Sector'),
        tags=sectorElement.get('Tags'),
        allegiances=allegiances,
        routes=routes,
        borders=borders,
        labels=labels,
        regions=regions,
        sources=sources,
        styleSheet=sectorElement.get('StyleSheet'))

def formatMetadata(
        metadata: survey.RawMetadata,
        format: MetadataFormat
        ) -> str:
    if format == MetadataFormat.XML:
        return formatXMLMetadata(metadata=metadata)
    elif format == MetadataFormat.JSON:
        return formatJSONMetadata(metadata=metadata)

    raise RuntimeError(f'Unknown metadata format {format}')

def formatXMLMetadata(metadata: survey.RawMetadata) -> str:
    sectorAttributes = {}

    if metadata.selected() != None:
        sectorAttributes['Selected'] = str(metadata.selected())

    # NOTE: The Traveller Map documentation doesn't mention Tags or Abbreviation for the XML
    # format but the XSD does have them
    # https://travellermap.com/doc/metadata
    if metadata.tags() != None:
        sectorAttributes['Tags'] = metadata.tags()

    if metadata.abbreviation() != None:
        sectorAttributes['Abbreviation'] = metadata.abbreviation()

    sectorElement = xml.etree.ElementTree.Element('Sector', sectorAttributes)

    names = [metadata.canonicalName()]
    if metadata.alternateNames():
        names.extend(metadata.alternateNames())
    for name in names:
        attributes = {}
        language = metadata.nameLanguage(name)
        if language:
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
        for allegiance in allegiances:
            attributes = {'Code': allegiance.code()}
            if allegiance.base():
                attributes['Base'] = allegiance.base()
            allegianceElement = xml.etree.ElementTree.SubElement(allegiancesElement, 'Allegiance', attributes)
            allegianceElement.text = allegiance.name()

    routes = metadata.routes()
    if routes:
        routesElement = xml.etree.ElementTree.SubElement(sectorElement, 'Routes')
        for route in routes:
            attributes = {
                'Start': route.startHex(),
                'End': route.endHex()}
            if route.startOffsetX():
                attributes['StartOffsetX'] = str(route.startOffsetX())
            if route.startOffsetY():
                attributes['StartOffsetY'] = str(route.startOffsetY())
            if route.endOffsetX():
                attributes['EndOffsetX'] = str(route.endOffsetX())
            if route.endOffsetY():
                attributes['EndOffsetY'] = str(route.endOffsetY())
            if route.allegiance() != None:
                attributes['Allegiance'] = route.allegiance()
            if route.type() != None:
                attributes['Type'] = route.type()
            if route.style() != None:
                attributes['Style'] = route.style()
            if route.colour() != None:
                attributes['Color'] = route.colour()
            if route.width() != None:
                attributes['Width'] = str(route.width())

            xml.etree.ElementTree.SubElement(routesElement, 'Route', attributes)

    borders = metadata.borders()
    if borders:
        bordersElement = xml.etree.ElementTree.SubElement(sectorElement, 'Borders')
        for border in borders:
            attributes = {}
            if border.allegiance() != None:
                attributes['Allegiance'] = border.allegiance()
            if border.showLabel() != None:
                attributes['ShowLabel'] = str(border.showLabel()).lower()
            if border.wrapLabel() != None:
                attributes['WrapLabel'] = str(border.wrapLabel()).lower()
            if border.labelHex() != None:
                attributes['LabelPosition'] = border.labelHex()
            if border.labelOffsetX() != None:
                attributes['LabelOffsetX'] = common.formatNumber(
                    number=border.labelOffsetX(),
                    decimalPlaces=_XmlFloatDecimalPlaces)
            if border.labelOffsetY() != None:
                attributes['LabelOffsetY'] = common.formatNumber(
                    number=border.labelOffsetY(),
                    decimalPlaces=_XmlFloatDecimalPlaces)
            if border.label() != None:
                attributes['Label'] = border.label()
            if border.style() != None:
                attributes['Style'] = border.style()
            if border.colour() != None:
                attributes['Color'] = border.colour()

            borderElement = xml.etree.ElementTree.SubElement(bordersElement, 'Border', attributes)
            borderElement.text = ' '.join(border.hexList())

    labels = metadata.labels()
    if labels:
        labelsElement = xml.etree.ElementTree.SubElement(sectorElement, 'Labels')
        for label in labels:
            attributes = {
                'Hex': label.hex(),
                'Color': label.colour()}
            if label.size() != None:
                attributes['Size'] = label.size()
            if label.wrap() != None:
                attributes['Wrap'] = str(label.wrap()).lower()
            if label.offsetX() != None:
                attributes['OffsetX'] = common.formatNumber(
                    number=label.offsetX(),
                    decimalPlaces=_XmlFloatDecimalPlaces)
            if label.offsetY() != None:
                attributes['OffsetY'] = common.formatNumber(
                    number=label.offsetY(),
                    decimalPlaces=_XmlFloatDecimalPlaces)

            labelElement = xml.etree.ElementTree.SubElement(labelsElement, 'Label', attributes)
            labelElement.text = label.text()

    regions = metadata.regions()
    if regions:
        regionsElement = xml.etree.ElementTree.SubElement(sectorElement, 'Regions')
        for region in regions:
            attributes = {}
            if region.showLabel() != None:
                attributes['ShowLabel'] = str(region.showLabel()).lower()
            if region.wrapLabel() != None:
                attributes['WrapLabel'] = str(region.wrapLabel()).lower()
            if region.labelHex() != None:
                attributes['LabelPosition'] = region.labelHex()
            if region.labelOffsetX() != None:
                attributes['LabelOffsetX'] = common.formatNumber(
                    number=region.labelOffsetX(),
                    decimalPlaces=_XmlFloatDecimalPlaces)
            if region.labelOffsetY() != None:
                attributes['LabelOffsetY'] = common.formatNumber(
                    number=region.labelOffsetY(),
                    decimalPlaces=_XmlFloatDecimalPlaces)
            if region.label() != None:
                attributes['Label'] = region.label()
            if region.colour() != None:
                attributes['Color'] = region.colour()

            regionElement = xml.etree.ElementTree.SubElement(regionsElement, 'Region', attributes)
            regionElement.text = ' '.join(region.hexList())

    sources = metadata.sources()
    if sources:
        if sources.credits():
            creditsElement = xml.etree.ElementTree.SubElement(sectorElement, 'Credits')
            creditsElement.text = sources.credits()

        if sources.primary():
            primary = sources.primary()
            attributes = {}
            if primary.publication():
                attributes['Source'] = primary.publication()
            if primary.author():
                attributes['Author'] = primary.author()
            if primary.publisher():
                attributes['Publisher'] = primary.publisher()
            if primary.reference():
                attributes['Ref'] = primary.reference()

            if attributes:
                xml.etree.ElementTree.SubElement(sectorElement, 'DataFile', attributes)

        if sources.products():
            for product in sources.products():
                attributes = {}
                if product.publication():
                    attributes['Title'] = product.publication()
                if product.author():
                    attributes['Author'] = product.author()
                if product.publisher():
                    attributes['Publisher'] = product.publisher()
                if product.reference():
                    attributes['Ref'] = product.reference()

                if attributes:
                    xml.etree.ElementTree.SubElement(sectorElement, 'Product', attributes)

    if metadata.styleSheet() != None:
        styleSheetElement = xml.etree.ElementTree.SubElement(sectorElement, 'StyleSheet')
        styleSheetElement.text = metadata.styleSheet()

    xml.etree.ElementTree.indent(sectorElement, space="\t", level=0)
    resultBytes: bytes = xml.etree.ElementTree.tostring(
        element=sectorElement,
        encoding='utf-8',
        xml_declaration=True)
    return resultBytes.decode('utf-8')

def formatJSONMetadata(metadata: survey.RawMetadata) -> str:
    sectorElement = {}

    if metadata.tags() != None:
        sectorElement['Tags'] = metadata.tags()

    if metadata.abbreviation() != None:
        sectorElement['Abbreviation'] = metadata.abbreviation()

    namesElement = []
    sectorElement['Names'] = namesElement

    names = [metadata.canonicalName()] + metadata.alternateNames()
    for name in names:
        nameElement = {'Text': name}
        language = metadata.nameLanguage(name)
        if language:
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
        for allegiance in allegiances:
            allegianceElement = {
                'Name': allegiance.name(),
                'Code': allegiance.code()}
            if allegiance.base():
                allegianceElement['Base'] = allegiance.base()
            allegiancesElement.append(allegianceElement)

    routes = metadata.routes()
    if routes:
        routesElement = []
        sectorElement['Routes'] = routesElement
        for route in routes:
            routeElement = {
                'Start': route.startHex(),
                'End': route.endHex()}
            if route.startOffsetX() != None:
                routeElement['StartOffsetX'] = route.startOffsetX()
            if route.startOffsetY() != None:
                routeElement['StartOffsetY'] = route.startOffsetY()
            if route.endOffsetX() != None:
                routeElement['EndOffsetX'] = route.endOffsetX()
            if route.endOffsetY() != None:
                routeElement['EndOffsetY'] = route.endOffsetY()
            if route.allegiance() != None:
                routeElement['Allegiance'] = route.allegiance()
            if route.type() != None:
                routeElement['Type'] = route.type()
            if route.style() != None:
                routeElement['Style'] = route.style()
            if route.colour() != None:
                routeElement['Color'] = route.colour()
            if route.width() != None:
                routeElement['Width'] = route.width()

            routesElement.append(routeElement)

    borders = metadata.borders()
    if borders:
        bordersElement = []
        sectorElement['Borders'] = bordersElement
        for border in borders:
            borderElement = {'Path': ' '.join(border.hexList())}
            if border.allegiance() != None:
                borderElement['Allegiance'] = border.allegiance()
            if border.showLabel() != None:
                borderElement['ShowLabel'] = border.showLabel()
            if border.wrapLabel() != None:
                borderElement['WrapLabel'] = border.wrapLabel()
            if border.labelHex() != None:
                borderElement['LabelPosition'] = border.labelHex()
            if border.labelOffsetX() != None:
                borderElement['LabelOffsetX'] = border.labelOffsetX()
            if border.labelOffsetY() != None:
                borderElement['LabelOffsetY'] = border.labelOffsetY()
            if border.label() != None:
                borderElement['Label'] = border.label()
            if border.style() != None:
                borderElement['Style'] = border.style()
            if border.colour() != None:
                borderElement['Color'] = border.colour()

            bordersElement.append(borderElement)

    labels = metadata.labels()
    if labels:
        labelsElement = []
        sectorElement['Labels'] = labelsElement
        for label in labels:
            labelElement = {
                'Text': label.text(),
                'Hex': label.hex(),
                'Color': label.colour()}
            if label.size() != None:
                labelElement['Size'] = label.size()
            if label.wrap() != None:
                labelElement['Wrap'] = label.wrap()
            if label.offsetX() != None:
                labelElement['OffsetX'] = label.offsetX()
            if label.offsetY() != None:
                labelElement['OffsetY'] = label.offsetY()

            labelsElement.append(labelsElement)

    regions = metadata.regions()
    if regions:
        regionsElement = []
        sectorElement['Regions'] = regionsElement
        for region in regions:
            regionElement = {'Path': ' '.join(region.hexList())}
            if region.showLabel() != None:
                regionElement['ShowLabel'] = region.showLabel()
            if region.wrapLabel() != None:
                regionElement['WrapLabel'] = region.wrapLabel()
            if region.labelHex() != None:
                regionElement['LabelPosition'] = region.labelHex()
            if region.labelOffsetX() != None:
                regionElement['LabelOffsetX'] = region.labelOffsetX()
            if region.labelOffsetY() != None:
                regionElement['LabelOffsetY'] = region.labelOffsetY()
            if region.label() != None:
                regionElement['Label'] = region.label()
            if region.colour() != None:
                regionElement['Color'] = region.colour()

            regionsElement.append(regionElement)

    sources = metadata.sources()
    if sources:
        # NOTE: The Credits string isn't written out as I don't know what
        # format it's mean to be in for JSON. The Traveller Map metadata
        # API returns an empty array for sectors with credits when JSON
        # is requested

        if sources.primary():
            primary = sources.primary()
            primaryElement = {}
            if primary.publication():
                primaryElement['Source'] = primary.publication()
            if primary.author():
                primaryElement['Author'] = primary.author()
            if primary.publisher():
                primaryElement['Publisher'] = primary.publisher()
            if primary.reference():
                primaryElement['Ref'] = primary.reference()

            if primaryElement:
                sectorElement['DataFile'] = primaryElement

        if sources.products():
            productsElement = []
            for product in sources.products():
                productElement = {}
                if product.publication():
                    productElement['Title'] = product.publication()
                if product.author():
                    productElement['Author'] = product.author()
                if product.publisher():
                    productElement['Publisher'] = product.publisher()
                if product.reference():
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
