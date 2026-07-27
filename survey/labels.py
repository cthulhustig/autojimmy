import common
import logging
import survey
import typing
import xml.etree.ElementTree

# TODO: Do more with reporter
def parseUniverseLabels(
        content: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.List[survey.RawUniverseLabel]:
    _, rows = common.parseTabTableContent(content=content)
    labels = []
    for data in rows:
        labels.append(survey.RawUniverseLabel(
            text=data['Text'].replace('\\n', '\n'),
            worldX=float(data['X']),
            worldY=float(data['Y']),
            minor=common.stringToBool(data['Minor'], strict=False)))
    return labels

# TODO: Do more with reporter
def parseWorldLabels(
        content: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.List[survey.RawWorldLabel]:
    parsedXml = xml.etree.ElementTree.fromstring(content)

    labels: typing.List[survey.RawWorldLabel] = []
    for index, worldElement in enumerate(parsedXml.findall('./World')):
        try:
            nameElement = worldElement.find('./Name')
            if nameElement is None:
                raise RuntimeError('World label has no Name element')
            name = nameElement.text

            optionsElement = worldElement.find('./MapOptions')
            if optionsElement is None:
                raise RuntimeError('World label has no MapOptions element')
            options = optionsElement.text.split()
            if not options:
                raise RuntimeError('World label has empty MapOptions element')

            locationElement = worldElement.find('./Location')
            if locationElement is None:
                raise RuntimeError('World label has no Location element')
            sector = locationElement.attrib.get('Sector')
            if sector is None:
                raise RuntimeError('Location element has no Sector attribute')
            if not sector:
                raise RuntimeError('Location element has empty Sector attribute')
            hex = locationElement.attrib.get('Hex')
            if hex is None:
                raise RuntimeError('Location element has no Hex attribute')
            if not hex:
                raise RuntimeError('Location element has empty Hex attribute')
            hexX, hexY = survey.parseHexString(string=hex, reporter=reporter)

            biasXElement = worldElement.find('./LabelBiasX')
            biasX = None
            if biasXElement is not None:
                biasX = int(biasXElement.text)
            biasYElement = worldElement.find('./LabelBiasY')
            biasY = None
            if biasYElement is not None:
                biasY = int(biasYElement.text)

            labels.append(survey.RawWorldLabel(
                name=name,
                sector=sector,
                hexX=hexX,
                hexY=hexY,
                options=options,
                biasX=biasX,
                biasY=biasY))
        except Exception as ex:
            logging.warning(
                f'Failed to read world label {index}',
                exc_info=ex)

    return labels
