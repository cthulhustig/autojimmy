import common
import logging
import maprenderer
import traveller
import travellermap
import typing
import xml.etree.ElementTree

class MapLabel(object):
    def __init__(
            self,
            text: str,
            position: maprenderer.PointF,
            minor: bool = False
            ) -> None:
        self.text = text
        self.position = maprenderer.PointF(position)
        self.minor = minor

class WorldLabel(object):
    def __init__(
            self,
            text: str,
            options: maprenderer.MapOptions,
            position: maprenderer.PointF,
            biasX: int = 0,
            biasY: int = 0,
            ) -> None:
        self.text = text
        self.options = options
        self.position = maprenderer.PointF(position)
        self.biasX = biasX
        self.biasY = biasY

class LabelCache(object):
    _MinorLabelsPath = 'res/labels/minor_labels.tab'
    _MajorLabelsPath = 'res/labels/mega_labels.tab'
    _WorldLabelPath = 'res/labels/Worlds.xml'

    def __init__(self):
        self.minorLabels = self._parseMapLabels(
            travellermap.DataStore.instance().loadTextResource(
                filePath=LabelCache._MinorLabelsPath))
        self.megaLabels = self._parseMapLabels(
            travellermap.DataStore.instance().loadTextResource(
                filePath=LabelCache._MajorLabelsPath))
        self.worldLabels = self._parseWorldLabels(
            travellermap.DataStore.instance().loadTextResource(
                filePath=LabelCache._WorldLabelPath))

    def _parseMapLabels(self, content: str) -> typing.List[MapLabel]:
        _, rows = maprenderer.parseTabContent(content=content)
        labels = []
        for data in rows:
            labels.append(MapLabel(
                text=data['Text'].replace('\\n', '\n'),
                position=maprenderer.PointF(x=float(data['X']), y=float(data['Y'])),
                minor=common.stringToBool(data['Minor'], strict=False)))
        return labels

    def _parseWorldLabels(self, content) -> typing.List[WorldLabel]:
        rootElement = xml.etree.ElementTree.fromstring(content)

        labels: typing.List[WorldLabel] = []
        for index, worldElement in enumerate(rootElement.findall('./World')):
            try:
                nameElement = worldElement.find('./Name')
                if nameElement is None:
                    raise RuntimeError('World label has no Name element')
                name = nameElement.text

                optionsElement = worldElement.find('./MapOptions')
                if optionsElement is None:
                    raise RuntimeError('World label has no MapOptions element')
                options = 0
                for token in optionsElement.text.split():
                    if token == 'WorldsHomeworlds':
                        options |= maprenderer.MapOptions.WorldsHomeworlds
                    elif token == 'WorldsCapitals':
                        options |= maprenderer.MapOptions.WorldsCapitals

                locationElement = worldElement.find('./Location')
                if locationElement is None:
                    raise RuntimeError('World label has no Location element')
                sector = locationElement.attrib.get('Sector')
                if sector is None:
                    raise RuntimeError('Location element has no Sector attribute')
                hex = locationElement.attrib.get('Hex')
                if hex is None:
                    raise RuntimeError('Location element has no Hex attribute')
                location = traveller.WorldManager.instance().sectorHexToPosition(f'{sector} {hex}')
                centerX, centerY = location.absoluteCenter()
                location = maprenderer.PointF(x=centerX, y=centerY)

                biasXElement = worldElement.find('./LabelBiasX')
                biasX = 1 # Default comes from traveller map default
                if biasXElement is not None:
                    biasX = int(biasXElement.text)
                biasYElement = worldElement.find('./LabelBiasY')
                biasY = 1 # Default comes from traveller map default
                if biasYElement is not None:
                    biasY = int(biasYElement.text)

                labels.append(WorldLabel(
                    text=name,
                    options=options,
                    position=location,
                    biasX=biasX,
                    biasY=biasY))
            except Exception as ex:
                logging.warning(
                    f'Failed to read world label {index}',
                    exc_info=ex)

        return labels