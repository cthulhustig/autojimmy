import cartographer
import re
import travellermap
import typing

class StyleCache(object):
    _BorderPattern = re.compile(r'border\.(\w+)')
    _RoutePattern = re.compile(r'route\.(\w+)')

    _DefaultStylePath = 'styles/otu.css'

    _StyleMap = {
        'solid': cartographer.LineStyle.Solid,
        'dashed': cartographer.LineStyle.Dash,
        'dotted': cartographer.LineStyle.Dot}

    def __init__(self):
        self._borderStyles = {}
        self._routeStyles = {}

        content = travellermap.readCssContent(
            travellermap.DataStore.instance().loadTextResource(
                filePath=StyleCache._DefaultStylePath))
        for group, properties in content.items():
            match = StyleCache._BorderPattern.match(group)
            if match:
                key = match.group(1)
                colour = properties.get('color')
                style = properties.get('style')
                if style:
                    style = StyleCache._StyleMap.get(style.lower())
                self._borderStyles[key] = (colour, style)

            match = StyleCache._RoutePattern.match(group)
            if match:
                key = match.group(1)
                colour = properties.get('color')
                style = properties.get('style')
                if style:
                    style = StyleCache._StyleMap.get(style.lower())
                width = properties.get('width')
                if width:
                    width = float(width)
                self._routeStyles[key] = (colour, style, width)

    def borderStyle(self, key: str) -> typing.Tuple[
            typing.Optional[str], # Colour
            typing.Optional[cartographer.LineStyle]]:
        return self._borderStyles.get(key, (None, None))

    def routeStyle(self, key: str) -> typing.Tuple[
            typing.Optional[str], # Colour
            typing.Optional[cartographer.LineStyle],
            typing.Optional[float]]: # Width
        return self._routeStyles.get(key, (None, None, None))
