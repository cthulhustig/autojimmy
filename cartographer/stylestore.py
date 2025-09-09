import cartographer
import re
import multiverse
import typing

class StyleStore(object):
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

        content = multiverse.readCssContent(
            multiverse.DataStore.instance().loadTextResource(
                filePath=StyleStore._DefaultStylePath))
        for group, properties in content.items():
            match = StyleStore._BorderPattern.match(group)
            if match:
                key = match.group(1)
                colour = properties.get('color')
                style = properties.get('style')
                if style:
                    style = StyleStore._StyleMap.get(style.lower())
                self._borderStyles[key] = (colour, style)

            match = StyleStore._RoutePattern.match(group)
            if match:
                key = match.group(1)
                colour = properties.get('color')
                style = properties.get('style')
                if style:
                    style = StyleStore._StyleMap.get(style.lower())
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
