import logging
import maprenderer
import os
import traveller
import travellermap
import typing
import xml.etree.ElementTree

# TODO: This should probably live elsewhere
class WorldLabel(object):
    def __init__(
            self,
            name: str,
            options: maprenderer.MapOptions,
            location: maprenderer.PointF,
            biasX: int = 0,
            biasY: int = 0,
            ) -> None:
        self._name = name
        self._options = options
        self._location = maprenderer.PointF(location)
        self._biasX = biasX
        self._biasY = biasY

    def name(self) -> str:
        return self._name

    def options(self) -> maprenderer.MapOptions:
        return self._options

    def location(self) -> maprenderer.PointF:
        return self._location

    def biasX(self) -> int:
        return self._biasX

    def biasY(self) -> int:
        return self._biasY

# TODO: Should possibly combine this with map label cache
class WorldLabelCache(object):
    _WorldLabelPath = 'res/labels/Worlds.xml'

    def __init__(self):
        rootElement = xml.etree.ElementTree.fromstring(
            travellermap.DataStore.instance().loadTextResource(
                filePath=WorldLabelCache._WorldLabelPath))

        self.labels: typing.List[WorldLabel] = []
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

                self.labels.append(WorldLabel(
                    name=name,
                    options=options,
                    location=location,
                    biasX=biasX,
                    biasY=biasY))
            except Exception as ex:
                logging.warning(
                    f'Failed to read world label {index} from "{WorldLabelCache._WorldLabelPath}"',
                    exc_info=ex)
