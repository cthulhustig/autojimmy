import os
import re
import traveller
import travellermap
import typing

class DefaultStyleCache(object):
    _BorderPattern = re.compile(r'border\.(\w+)')
    _RoutePattern = re.compile(r'route\.(\w+)')
    _DefaultStylePath = 'res/styles/otu.css'

    _RouteStyleMap = {
        'solid': traveller.Route.Style.Solid,
        'dashed': traveller.Route.Style.Dashed,
        'dotted': traveller.Route.Style.Dotted}

    def __init__(self, basePath: str):
        self._borderStyles = {}
        self._routeStyles = {}

        content = travellermap.readCssFile(
            os.path.join(basePath, DefaultStyleCache._DefaultStylePath))
        for group, properties in content.items():
            match = DefaultStyleCache._BorderPattern.match(group)
            if match:
                key = match.group(1)
                color = properties.get('color')
                style = properties.get('style')
                if style:
                    style = DefaultStyleCache._RouteStyleMap.get(style.lower())
                self._borderStyles[key] = (color, style)

            match = DefaultStyleCache._RoutePattern.match(group)
            if match:
                key = match.group(1)
                color = properties.get('color')
                style = properties.get('style')
                if style:
                    style = DefaultStyleCache._RouteStyleMap.get(style.lower())
                width = properties.get('width')
                if width:
                    width = float(width)
                self._routeStyles[key] = (color, style, width)

    def defaultBorderStyle(self, key: str) -> typing.Tuple[
            typing.Optional[str], # Colour
            typing.Optional[traveller.Border.Style]]:
        return self._borderStyles.get(key, (None, None))

    def defaultRouteStyle(self, key: str) -> typing.Tuple[
            typing.Optional[str], # Colour
            typing.Optional[traveller.Route.Style],
            typing.Optional[float]]: # Width
        return self._routeStyles.get(key, (None, None, None))