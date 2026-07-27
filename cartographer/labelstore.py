import astronomer
import cartographer
import common
import logging
import multiverse
import typing
import xml.etree.ElementTree

class WorldLabel(object):
    def __init__(
            self,
            text: str,
            options: cartographer.RenderOptions,
            position: cartographer.PointF,
            biasX: int = 0,
            biasY: int = 0,
            ) -> None:
        self.text = text
        self.options = options
        self.position = cartographer.PointF(position)
        self.biasX = biasX
        self.biasY = biasY

class LabelStore(object):
    _WorldLabelPath = 'labels/Worlds.xml'

    _cachedWorldLabelsXml = None

    def __init__(
            self,
            universe: astronomer.Universe
            ) -> None:
        self._universe = universe
        self._worldLabels = self._loadWorldLabels(self._universe)

    def worldLabels(self) -> typing.Collection[WorldLabel]:
        return self._worldLabels

    @staticmethod
    def _loadWorldLabels(universe: astronomer.Universe) -> typing.List[WorldLabel]:
        if LabelStore._cachedWorldLabelsXml is None:
            content = multiverse.SnapshotManager.instance().readTextResource(
                filePath=LabelStore._WorldLabelPath)
            LabelStore._cachedWorldLabelsXml = xml.etree.ElementTree.fromstring(content)

        labels: typing.List[WorldLabel] = []
        for index, worldElement in enumerate(LabelStore._cachedWorldLabelsXml.findall('./World')):
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
                        options |= cartographer.RenderOptions.WorldsHomeworlds
                    elif token == 'WorldsCapitals':
                        options |= cartographer.RenderOptions.WorldsCapitals

                locationElement = worldElement.find('./Location')
                if locationElement is None:
                    raise RuntimeError('World label has no Location element')
                sector = locationElement.attrib.get('Sector')
                if sector is None:
                    raise RuntimeError('Location element has no Sector attribute')
                hex = locationElement.attrib.get('Hex')
                if hex is None:
                    raise RuntimeError('Location element has no Hex attribute')
                sectorHex = f'{sector} {hex}'
                # TODO: This is currently broken for milieu other than M1105 as the labels use sector hex
                # positions using M1105 sector names
                # TODO: Using the closestTo field is a hack introduced when I removed the requirement
                # that sector names are unique. It means we'll use the worlds closest to core if there
                # happen to be sectors with duplicate names.
                worlds = universe.worldsBySectorHex(
                    sectorHex=sectorHex,
                    closestTo=astronomer.HexPosition(0, 0))
                if not worlds:
                    # The world doesn't exist in this universe so skip the label
                    logging.debug(
                        f'Skipping world label {index} as no world at location {sectorHex}')
                    continue
                location = worlds[0].hex()
                centerX, centerY = location.worldCenter()
                location = cartographer.PointF(x=centerX, y=centerY)

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
