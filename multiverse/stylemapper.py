import common
import logging
import survey
import typing

_ValidLineStyles = set(['solid', 'dashed', 'dotted'])

class StyleMapper(object):
    def __init__(
            self,
            rawSectors: typing.List[typing.Tuple[survey.RawMetadata, typing.List[survey.RawWorld]]],
            rawStockStyleSheet: survey.RawStyleSheet,
            ) -> None:
        self._metadataToRouteStyleData: typing.Dict[
            typing.Optional[survey.RawMetadata], # None = global
            typing.Dict[
                typing.Optional[str], # Style tag, None for default style
                typing.Tuple[
                    typing.Optional[str], # Colour
                    typing.Optional[str], # Style
                    typing.Optional[float]] # Width
            ]] = {}
        self._metadataToBorderStyleData: typing.Dict[
            typing.Optional[survey.RawMetadata], # None = global
            typing.Dict[
                typing.Optional[str], # Style tag, None for default style
                typing.Tuple[
                    typing.Optional[str], # Colour
                    typing.Optional[str]] # Style
            ]] = {}

        self._populate(
            rawSectors=rawSectors,
            rawStockStyleSheet=rawStockStyleSheet)

    def hasRouteStyle(
            self,
            rawMetadata: survey.RawMetadata,
            tag: typing.Optional[str]
            ) -> bool:
        # First check if there is a sector specific style
        styleMap = self._metadataToRouteStyleData.get(rawMetadata)
        if styleMap is not None:
            if tag in styleMap:
                return True

        # No sector specific style so check if there is a global one
        styleMap = self._metadataToRouteStyleData.get(None)
        if styleMap is not None:
            if tag in styleMap:
                return True

        return False

    def lookupRouteStyle(
            self,
            rawMetadata: survey.RawMetadata,
            tag: typing.Optional[str]
            ) -> typing.Tuple[
                typing.Optional[str], # Colour
                typing.Optional[str], # Style
                typing.Optional[float]]: # Width
        # First check if there is a sector specific style
        styleMap = self._metadataToRouteStyleData.get(rawMetadata)
        if styleMap is not None:
            style = styleMap.get(tag)
            if style is not None:
                return style

        # No sector specific style so check if there is a global one
        styleMap = self._metadataToRouteStyleData.get(None)
        if styleMap is not None:
            style = styleMap.get(tag)
            if style is not None:
                return style

        return (None, None, None) # No style for this tag

    def hasBorderStyle(
            self,
            rawMetadata: survey.RawMetadata,
            tag: typing.Optional[str]
            ) -> bool:
        # First check if there is a sector specific style
        styleMap = self._metadataToBorderStyleData.get(rawMetadata)
        if styleMap is not None:
            if tag in styleMap:
                return True

        # No sector specific style so check if there is a global one
        styleMap = self._metadataToBorderStyleData.get(None)
        if styleMap is not None:
            if tag in styleMap:
                return True

        return False

    def lookupBorderStyle(
            self,
            rawMetadata: survey.RawMetadata,
            tag: typing.Optional[str]
            ) -> typing.Tuple[
                typing.Optional[str], # Colour
                typing.Optional[str]]: # Style
        # First check if there is a sector specific style
        styleMap = self._metadataToBorderStyleData.get(rawMetadata)
        if styleMap is not None:
            style = styleMap.get(tag)
            if style is not None:
                return style

        # No sector specific style so check if there is a global one
        styleMap = self._metadataToBorderStyleData.get(None)
        if styleMap is not None:
            style = styleMap.get(tag)
            if style is not None:
                return style

        return (None, None) # No style for this tag

    def _populate(
            self,
            rawSectors: typing.List[typing.Tuple[survey.RawMetadata, typing.List[survey.RawWorld]]],
            rawStockStyleSheet: survey.RawStyleSheet
            ) -> None:
        self._stockRouteStyleData = self._createRouteStyleData(
            rawStyleSheet=rawStockStyleSheet,
            loggingName='Stock Styles')
        self._stockBorderStyleData = self._createBorderStyleData(
            rawStyleSheet=rawStockStyleSheet,
            loggingName='Stock Styles')

        for rawMetadata, _ in rawSectors:
            sectorRouteStyleData = self._stockRouteStyleData
            sectorBorderStyleData = self._stockBorderStyleData
            rawStyleSheet = rawMetadata.styleSheet()
            if rawStyleSheet:
                sectorRouteStyleData = self._mergeRouteStyleData(
                    sectorStyles=self._createRouteStyleData(
                        rawStyleSheet=rawStyleSheet,
                        loggingName=rawMetadata.canonicalName()),
                    stockStyles=sectorRouteStyleData)
                sectorBorderStyleData = self._mergeBorderStyleData(
                    sectorStyles=self._createBorderStyleData(
                        rawStyleSheet=rawStyleSheet,
                        loggingName=rawMetadata.canonicalName()),
                    stockStyles=sectorBorderStyleData)
            self._metadataToRouteStyleData[rawMetadata] = sectorRouteStyleData
            self._metadataToBorderStyleData[rawMetadata] = sectorBorderStyleData

    def _createRouteStyleData(
            self,
            rawStyleSheet: survey.RawStyleSheet,
            loggingName: str
            ) -> typing.Dict[
                str, # Style tag
                typing.Tuple[
                    typing.Optional[str], # Colour
                    typing.Optional[str], # Style
                    typing.Optional[float]]]: # Width
        styleMap = {}

        defaultColour = defaultStyle = defaultWidth = None
        for rawStyle in rawStyleSheet.routeStyles():
            tag = rawStyle.tag()
            if tag is not None:
                continue

            colour = rawStyle.colour()
            style = rawStyle.style()
            width = rawStyle.width()

            if colour is not None:
                try:
                    colour = common.canonicalHtmlColour(colour)
                except:
                    logging.warning(f'Converter ignoring invalid colour {colour} for default route style from sector style sheet for {loggingName}')
                    colour = None
            if style is not None:
                if style.lower() in _ValidLineStyles:
                    style = style.lower()
                else:
                    logging.warning(f'Converter ignoring invalid line style {style} for default route style from sector style sheet for {loggingName}')
                    style = None

            if colour is not None:
                defaultColour = colour
            if style is not None:
                defaultStyle = style
            if width is not None:
                defaultWidth = width

        if defaultColour is not None or defaultStyle is not None or defaultWidth is not None:
            styleMap[None] = (defaultColour, defaultStyle, defaultWidth)

        for rawStyle in rawStyleSheet.routeStyles():
            tag = rawStyle.tag()
            if tag is None:
                continue
            colour = rawStyle.colour()
            style = rawStyle.style()
            width = rawStyle.width()

            if colour is not None:
                try:
                    colour = common.canonicalHtmlColour(colour)
                except:
                    logging.warning(f'Converter ignoring invalid colour {colour} for route style {tag} from sector style sheet for {loggingName}')
                    colour = None
            if style is not None:
                if style.lower() in _ValidLineStyles:
                    style = style.lower()
                else:
                    logging.warning(f'Converter ignoring invalid line style {style} for route style {tag} from sector style sheet for {loggingName}')
                    style = None

            if colour is None:
                colour = defaultColour
            if style is None:
                style = defaultStyle
            if width is None:
                width = defaultWidth

            if colour is not None or style is not None or width is not None:
                styleMap[tag] = (colour, style, width)

        return styleMap

    def _mergeRouteStyleData(
            self,
            sectorStyles: typing.Optional[typing.Dict[
                str, # Style tag
                typing.Tuple[
                    str, # Colour
                    str, # Style
                    float]]], # Width
            stockStyles: typing.Optional[typing.Dict[
                str, # Style tag
                typing.Tuple[
                    str, # Colour
                    str, # Style
                    float]]] # Width
            ) -> typing.Dict[
                str, # Style tag
                typing.Tuple[
                    str, # Colour
                    str, # Style
                    float]]: # Width
        mergedStyleMap: typing.Dict[str, typing.Tuple[str, str, float]] = {}

        if sectorStyles:
            for tag, (sectorColour, sectorStyle, sectorWidth) in sectorStyles.items():
                mergedStyleMap[tag] = (sectorColour, sectorStyle, sectorWidth)

        if stockStyles:
            for tag, (stockColour, stockStyle, stockWidth) in stockStyles.items():
                colour, style, width = mergedStyleMap.get(tag, (None, None, None))
                if colour is None:
                    colour = stockColour
                if style is None:
                    style = stockStyle
                if width is None:
                    width = stockWidth

                mergedStyleMap[tag] = (colour, style, width)

        # Update all tag mappings with default values
        if None in mergedStyleMap:
            defaultColour, defaultStyle, defaultWidth = mergedStyleMap.get(None)
            for tag in mergedStyleMap.keys():
                colour, style, width = mergedStyleMap[tag]
                if colour is None:
                    colour = defaultColour
                if style is None:
                    style = defaultStyle
                if width is None:
                    width = defaultWidth
                mergedStyleMap[tag] = (colour, style, width)

        return mergedStyleMap

    def _createBorderStyleData(
            self,
            rawStyleSheet: survey.RawStyleSheet,
            loggingName: str
            ) -> typing.Dict[
                typing.Optional[str], # Style tag, None means default
                typing.Tuple[
                    typing.Optional[str], # Colour
                    typing.Optional[str]]]: # Style
        styleMap = {}

        defaultColour = defaultStyle = None
        for rawStyle in rawStyleSheet.borderStyles():
            tag = rawStyle.tag()
            if tag is not None:
                continue

            colour = rawStyle.colour()
            style = rawStyle.style()

            if colour is not None:
                try:
                    colour = common.canonicalHtmlColour(colour)
                except:
                    logging.warning(f'Converter ignoring invalid colour {colour} for default border style from sector style sheet for {loggingName}')
                    colour = None
            if style is not None:
                if style.lower() in _ValidLineStyles:
                    style = style.lower()
                else:
                    logging.warning(f'Converter ignoring invalid line style {style} for default border style from sector style sheet for {loggingName}')
                    style = None

            if colour is not None:
                defaultColour = colour
            if style is not None:
                defaultStyle = style

        if defaultColour is not None or defaultStyle is not None:
            styleMap[None] = (defaultColour, defaultStyle)

        for rawStyle in rawStyleSheet.borderStyles():
            tag = rawStyle.tag()
            if tag is None:
                continue
            colour = rawStyle.colour()
            style = rawStyle.style()

            if colour is not None:
                try:
                    colour = common.canonicalHtmlColour(colour)
                except:
                    logging.warning(f'Converter ignoring invalid colour {colour} for route style {tag} from sector style sheet for {loggingName}')
                    colour = None
            if style is not None:
                if style.lower() in _ValidLineStyles:
                    style = style.lower()
                else:
                    logging.warning(f'Converter ignoring invalid line style {style} for route style {tag} from sector style sheet for {loggingName}')
                    style = None

            if colour is None:
                colour = defaultColour
            if style is None:
                style = defaultStyle

            if colour is not None or style is not None:
                styleMap[tag] = (colour, style)

        return styleMap

    def _mergeBorderStyleData(
            self,
            sectorStyles: typing.Optional[typing.Dict[
                str, # Style tag
                typing.Tuple[
                    str, # Colour
                    str]]], # Style
            stockStyles: typing.Optional[typing.Dict[
                str, # Style tag
                typing.Tuple[
                    str, # Colour
                    str ]]] # Style
            ) -> typing.Dict[
                str, # Style tag
                typing.Tuple[
                    str, # Colour
                    str]]: # Style
        mergedStyleMap: typing.Dict[str, typing.Tuple[str, str]] = {}

        if sectorStyles:
            for tag, (sectorColour, sectorStyle) in sectorStyles.items():
                mergedStyleMap[tag] = (sectorColour, sectorStyle)

        if stockStyles:
            for tag, (stockColour, stockStyle) in stockStyles.items():
                colour, style = mergedStyleMap.get(tag, (None, None))
                if colour is None:
                    colour = stockColour
                if style is None:
                    style = stockStyle

                mergedStyleMap[tag] = (colour, style)

        # Update all tag mappings with default values
        if None in mergedStyleMap:
            defaultColour, defaultStyle = mergedStyleMap.get(None)
            for tag in mergedStyleMap.keys():
                colour, style = mergedStyleMap[tag]
                if colour is None:
                    colour = defaultColour
                if style is None:
                    style = defaultStyle
                mergedStyleMap[tag] = (colour, style)

        return mergedStyleMap