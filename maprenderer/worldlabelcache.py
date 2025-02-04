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
            mapOptions: maprenderer.MapOptions,
            location: maprenderer.AbstractPointF,
            labelBiasX: int = 0,
            labelBiasY: int = 0,
            ) -> None:
        self.name = name
        self.mapOptions = mapOptions
        self.location = maprenderer.AbstractPointF(location)
        self.labelBiasX = labelBiasX
        self.labelBiasY = labelBiasY

    # TODO: I don't like the fact this lives here. All rendering should
    # be in the render context
    def paint(
            self,
            graphics: maprenderer.AbstractGraphics,
            dotColor: str,
            labelBrush: maprenderer.AbstractBrush,
            labelFont: maprenderer.AbstractFont
            ) -> None:
        pt = maprenderer.AbstractPointF(self.location)

        with graphics.save():
            graphics.translateTransform(dx=pt.x(), dy=pt.y())
            graphics.scaleTransform(
                scaleX=1.0 / travellermap.ParsecScaleX,
                scaleY=1.0 / travellermap.ParsecScaleY)

            radius = 3
            brush = maprenderer.AbstractBrush(dotColor)
            pen = maprenderer.AbstractPen(dotColor, 1)
            graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)
            graphics.drawEllipse(
                pen=pen,
                brush=brush,
                rect=maprenderer.AbstractRectangleF(x=-radius / 2, y=-radius / 2, width=radius, height=radius))

            if self.labelBiasX > 0:
                if self.labelBiasY < 0:
                    format = maprenderer.TextFormat.BottomLeft
                elif self.labelBiasY > 0:
                    format = maprenderer.TextFormat.TopLeft
                else:
                    format = maprenderer.TextFormat.MiddleLeft
            elif self.labelBiasX < 0:
                if self.labelBiasY < 0:
                    format = maprenderer.TextFormat.BottomRight
                elif self.labelBiasY > 0:
                    format = maprenderer.TextFormat.TopRight
                else:
                    format = maprenderer.TextFormat.MiddleRight
            else:
                if self.labelBiasY < 0:
                    format = maprenderer.TextFormat.BottomCenter
                elif self.labelBiasY > 0:
                    format = maprenderer.TextFormat.TopCenter
                else:
                    format = maprenderer.TextFormat.Center

            maprenderer.drawStringHelper(
                graphics=graphics,
                text=self.name,
                font=labelFont,
                brush=labelBrush,
                x=self.labelBiasX * radius / 2,
                y=self.labelBiasY * radius / 2,
                format=format)

# TODO: Should possibly combine this with map label cache
class WorldLabelCache(object):
    _WorldLabelPath = 'res/labels/Worlds.xml'

    def __init__(self, basePath: str):
        filePath = os.path.join(basePath, WorldLabelCache._WorldLabelPath)
        with open(filePath, 'r', encoding='utf-8-sig') as file:
            content = file.read()

        rootElement = xml.etree.ElementTree.fromstring(content)

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
                location = maprenderer.AbstractPointF(x=centerX, y=centerY)

                biasXElement = worldElement.find('./LabelBiasX')
                biasX = 0
                if biasXElement is not None:
                    biasX = int(biasXElement.text)
                biasYElement = worldElement.find('./LabelBiasY')
                biasY = 0
                if biasYElement is not None:
                    biasY = int(biasYElement.text)

                self.labels.append(WorldLabel(
                    name=name,
                    mapOptions=options,
                    location=location,
                    labelBiasX=biasX,
                    labelBiasY=biasY))
            except Exception as ex:
                logging.warning(f'Failed to read world label {index} from "{filePath}"', exc_info=ex)
